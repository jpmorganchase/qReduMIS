###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
from braket.ahs.atom_arrangement import AtomArrangement
from braket.ahs.field import Field
from braket.ahs.pattern import Pattern
from braket.ahs.shifting_field import ShiftingField

from braket.timings.time_series import TimeSeries
from braket.ahs.pattern import Pattern

import sys
import numpy as np
import math
import argparse


def _squished_sigmoid(x, x_min=None, x_max=None, smoothness=2, tol=1e-15):
    """
    Helper function.
    Squished sigmoid function that maps the domain to [-1,1] smoothly
    """
    if x_max is None:
        x_max = np.max(x)
    if x_min is None:
        x_min = np.min(x)
    z = (x - x_min) / (x_max - x_min) + tol
    w = 1 / (1 + (z / np.abs(1 - z)) ** (-smoothness))
    return w


def _piecewise_step(x, x_max=None, ramp_ratio=0.25, smoothness=2, tol=1e-15):
    """
    Helper function.
    Smooth approximation of a step function using _squished_sigmoid
    """
    if x_max is None:
        x_max = len(x)
    num_points = len(x)
    idx1 = int(num_points * ramp_ratio)
    idx2 = num_points - int(num_points * ramp_ratio)
    max1 = np.max(x[:idx1])
    max2 = np.max(x[idx2:])
    w1 = _squished_sigmoid(x[:idx1], x_max=max1, smoothness=smoothness, tol=tol)
    w2 = [1] * (num_points - 2 * int(num_points * ramp_ratio))
    w3 = 1 - _squished_sigmoid(x[idx2:], x_max=max2, smoothness=smoothness, tol=tol)
    return np.concatenate((w1, w2, w3))


def generate_graph(atom_positions, scale=4e-6):
    """
    Helper function to generate a NetworkX graph and Braket AtomArrangement,
    with union-jack (UJ) connectivity, given specified parameters for size of
    underlying square lattice, and
    atomic positions given as list of tuples [(0,0), (0,1), ...].

    Input:
        atom_positions: Positions of nodes (atoms) in 2D
        scale: [Optional] Lattice spacing a in SI units (defaults to 4um)
    Output:
        nx_graph: NetworkX OrderedGraph of specified type and parameters
    """
    lattice_width = max([x for x, _ in atom_positions]) + 1
    lattice_height = max([y for _, y in atom_positions]) + 1
    atom_positions_si = [(x * scale, y * scale) for x, y in atom_positions]
    node_labels = range(len(atom_positions))

    edge_dict = {}
    for i in range(len(atom_positions)):
        x, y = atom_positions[i]
        edge_dict[node_labels[i]] = []
        for j in range(i + 1, len(atom_positions)):
            u, v = atom_positions[j]
            if abs(x - u) <= 1 and abs(y - v) <= 1:
                edge_dict[node_labels[i]] += [node_labels[j]]

    atoms = AtomArrangement()
    for atom in atom_positions_si:
        atoms.add(atom)

    return atoms


def get_schedule(
    time_max=4e-6,
    ratio_time_ramp=0.15,
    detuning_min=-9 * 10**6 * 2 * np.pi,
    detuning_max=7 * 10**6 * 2 * np.pi,
):
    omega_min = 0
    omega_max = 2.5e6 * 2 * np.pi

    time_ramp = ratio_time_ramp * time_max
    time_points = [0, time_ramp, time_max - time_ramp, time_max]
    omega_values = [omega_min, omega_max, omega_max, omega_min]
    detuning_values = [detuning_min, detuning_min, detuning_max, detuning_max]
    phase_values = [0, 0, 0, 0]

    schedule = {
        "time_points": time_points,
        "omega_values": omega_values,
        "detuning_values": detuning_values,
        "phase_values": phase_values,
    }
    return schedule


def get_schedule_and_shift(
    atom_positions: list, time_max=4e-6, ratio_time_ramp=0.15, detuning_max=7
):
    """This is a very simple schedule for the Rydberg atom machine, it returns the important information to define a schedule"""
    schedule = get_schedule(
        time_max=time_max, ratio_time_ramp=ratio_time_ramp, detuning_max=detuning_max
    )

    Delta_local = TimeSeries()
    Delta_local.put(0.0, 0.0).put(time_max, 0.0)
    h = Pattern([0] * len(atom_positions))

    shift = ShiftingField(magnitude=Field(time_series=Delta_local, pattern=h))

    return schedule, shift


def get_smooth_trig_schedule(time_max=4e-6, ratio_time_ramp=0.15, detuning_max=7):
    """This is a very simple schedule for the Rydberg atom machine, it returns the important information to define a schedule"""

    omega_min = 0
    omega_max = 2.5e6 * 2 * np.pi
    detuning_min = -9e6 * 2 * np.pi
    detuning_max = 7e6 * 2 * np.pi

    time_ramp = ratio_time_ramp * time_max
    time_points = [0, time_ramp, time_max - time_ramp, time_max]

    omega_values = [
        omega_max * (math.sin((math.pi / 2) * math.sin(math.pi * time / time_max))) ** 2
        for time in time_points
    ]
    detuning_values = [
        detuning_min * math.cos(math.pi * time / time_max) for time in time_points
    ]
    phase_values = [0, 0, 0, 0]

    schedule = {
        "time_points": time_points,
        "omega_values": omega_values,
        "detuning_values": detuning_values,
        "phase_values": phase_values,
    }

    return schedule


def get_smooth_erf_schedule(
    *,
    time_max=4e-6,
    num_points=50,
    amp_smoothness=2,
    det_smoothness=2,
    amp_ramp_ratio=1.0 / 3,
    omega_max=4 * 2e6 * np.pi,
    detuning_max=3 * 2e6 * np.pi
):
    """A simple, smooth schedule for driving the Rydberg atom machine. Returns the important information to define a schedule"""

    time_points = np.linspace(0, time_max, num_points)
    omega_values = omega_max * _piecewise_step(
        time_points, ramp_ratio=amp_ramp_ratio, smoothness=amp_smoothness
    )
    detuning_values = (
        2
        * detuning_max
        * _squished_sigmoid(time_points, x_max=time_max, smoothness=det_smoothness)
        - detuning_max
    )
    phase_values = [0] * len(time_points)

    schedule = {
        "time_points": time_points.tolist(),
        "omega_values": omega_values.tolist(),
        "detuning_values": detuning_values.tolist(),
        "phase_values": phase_values,
    }

    return schedule


def main():
    # Add warning using warnings.warn that only outputting smoothed schedule is currently supported
    import warnings

    warnings.warn("Only outputting smoothed schedule using erf is currently supported")

    parser = argparse.ArgumentParser(
        prog="simple_schedule.py",
        description="Generate simple, smoothed AHS schedules and export to json",
    )
    parser.add_argument(
        "--time_max",
        type=float,
        default=4e-6,
        help="Maximum time for the schedule (default: 4e-6)",
    )
    parser.add_argument(
        "--ratio_time_ramp",
        type=float,
        default=0.15,
        help="Ratio of ramp time to total time (default: 0.15)",
    )  ## TO ASK: this arg is not passed?
    parser.add_argument(
        "--num_points",
        type=int,
        default=50,
        help="Number of points in the smooth schedule (default: 50)",
    )
    parser.add_argument(
        "--amp_smoothness",
        type=float,
        default=2,
        help="Smoothness parameter for the amplitude ramp (default: 2)",
    )
    parser.add_argument(
        "--det_smoothness",
        type=float,
        default=8,
        help="Smoothness parameter for the detuning ramp (default: 8)",
    )
    parser.add_argument(
        "--amp_ramp_ratio",
        type=float,
        default=1.0 / 3,
        help="Ratio of ramp over which to smooth (default: 1.0/3)",
    )
    parser.add_argument(
        "--detuning_max",
        type=float,
        default=3e6 * 2 * np.pi,
        help="Maximum detuning in MHz (default: 3)",
    )
    parser.add_argument(
        "--omega_max",
        type=float,
        default=2.5e6 * 2 * np.pi,
        help="Maximum amplitude (default: 2.5e6 * 2 * pi)",
    )
    parser.add_argument(
        "--out_filename",
        type=str,
        default="schedule.json",
        help="Filename for the output json (default: ./schedule.json)",
    )
    args = parser.parse_args()

    # Call get_smooth_erf_schedule with the parsed arguments
    schedule = get_smooth_erf_schedule(
        time_max=args.time_max,
        num_points=args.num_points,
        amp_smoothness=args.amp_smoothness,
        det_smoothness=args.det_smoothness,
        amp_ramp_ratio=args.amp_ramp_ratio,
        omega_max=args.omega_max,
        detuning_max=args.detuning_max,
    )
    # Save the schedule to a json file
    import json

    with open(args.out_filename, "w") as f:
        json.dump(schedule, f, indent=4)


if __name__ == "__main__":
    main()

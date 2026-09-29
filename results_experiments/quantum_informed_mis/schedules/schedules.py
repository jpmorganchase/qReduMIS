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
import numpy as np

from ahs_utils import get_drive


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


omega_max = 2.5e6 * 2 * np.pi


def get_simple_drive(
    time_max=4e-6, ratio_time_ramp=0.15, detuning_max=7, num_points=100
):
    """This is a very simple schedule for the Rydberg atom machine, it returns the important information to define a schedule"""
    omega_min = 0
    # omega_max = 2.5e6 * 2 * np.pi
    detuning_min = -9e6 * 2 * np.pi
    detuning_max = detuning_max * 10**6 * 2 * np.pi

    time_ramp = ratio_time_ramp * time_max
    time_points = [0, time_ramp, time_max - time_ramp, time_max]
    omega_values = [omega_min, omega_max, omega_max, omega_min]
    detuning_values = [detuning_min, detuning_min, detuning_max, detuning_max]
    phase_values = [0, 0, 0, 0]

    drive = get_drive(time_points, omega_values, detuning_values, phase_values)

    return drive


def get_optimized_piecewise_linear_drive(
    tau_i=None,
    tau_f=None,
    tau_m=None,
    Delta_i=None,
    Delta_m=None,
    Delta_f=None,
    t_f=4e-6,
    omega_min=0,
    omega_max=2.5e6 * 2 * np.pi,
    Delta_UB=7e6 * 2 * np.pi,
):
    if tau_i is None:
        tau_i = 0.22 * t_f
    if tau_f is None:
        tau_f = 0.12 * t_f
    if tau_m is None:
        tau_m = 0.34 * t_f
    if Delta_i is None:
        Delta_i = -0.83 * Delta_UB
    if Delta_m is None:
        Delta_m = 0.36 * Delta_UB
    if Delta_f is None:
        Delta_f = Delta_UB

    def interpolate_value(t, t1, t2, v1, v2):
        """Linear interpolation between two points"""
        return v1 + (v2 - v1) * (t - t1) / (t2 - t1)

    time_points = sorted([0, tau_i, tau_m, t_f - tau_f, t_f])
    omega_values = []
    detuning_values = []

    for t in time_points:
        # Handle omega values
        if t <= tau_i:
            # Linear interpolation from omega_min to omega_max
            omega = interpolate_value(t, 0, tau_i, omega_min, omega_max)
        elif t >= t_f - tau_f:
            # Linear interpolation from omega_max to omega_min
            omega = interpolate_value(t, t_f - tau_f, t_f, omega_max, omega_min)
        else:
            # Constant omega_max in between
            omega = omega_max

        # Handle delta values (detuning)
        if t <= tau_m:
            # Linear interpolation from Delta_i to Delta_m
            delta = interpolate_value(t, 0, tau_m, Delta_i, Delta_m)
        else:
            # Linear interpolation from Delta_m to Delta_f
            delta = interpolate_value(t, tau_m, t_f, Delta_m, Delta_f)

        omega_values.append(omega)
        detuning_values.append(delta)

    phase_values = [0] * len(time_points)

    schedule = {
        "time_points": time_points,
        "omega_values": omega_values,
        "detuning_values": detuning_values,
        "phase_values": phase_values,
    }
    drive = get_drive(
        schedule["time_points"],
        schedule["omega_values"],
        schedule["detuning_values"],
        schedule["phase_values"],
    )
    return drive


def get_smooth_drive(time_max=4e-6, omega_0=2.5, delta_0=7, num_points=100):
    omega_0 = omega_0 * 10**6 * 2 * np.pi
    delta_0 = delta_0 * 10**6 * 2 * np.pi

    time_points = np.linspace(0, time_max, num_points)
    omega_values = (
        omega_0 * np.sin((np.pi / 2) * np.sin(np.pi * time_points / time_max)) ** 2
    )
    detuning_values = -delta_0 * np.cos(np.pi * time_points / time_max)
    phase_values = [0] * len(time_points)

    # drive = get_drive(time_points, omega_values, detuning_values, phase_values)

    return {
        "time_points": time_points.tolist(),
        "omega_values": omega_values.tolist(),
        "detuning_values": detuning_values.tolist(),
        "phase_values": phase_values,
    }


def get_drive_low_freq(time_max=4e-6, ratio_time_ramp=0.15, detuning_max=7):
    # omega_max = 2.5e6 * 2 * np.pi
    detuning_min = -9e6 * 2 * np.pi
    detuning_max = detuning_max * 10**6 * 2 * np.pi

    params = {
        "omega_max": omega_max,
        "tau": ratio_time_ramp,
        "delta_initial": -detuning_min,
        "delta_final": -detuning_max,
    }
    drive = get_drive_real(time_max, params, lowpass=True)
    return drive


def get_shift(atom_positions, time_max=4e-6):

    Delta_local = TimeSeries()
    Delta_local.put(0.0, 0.0).put(time_max, 0.0)
    h = Pattern([0] * len(atom_positions))

    shift = ShiftingField(magnitude=Field(time_series=Delta_local, pattern=h))

    return shift


drive_dict = {
    "simple": get_simple_drive,
    "low freq": get_drive_low_freq,
    "smooth": get_smooth_drive,
}

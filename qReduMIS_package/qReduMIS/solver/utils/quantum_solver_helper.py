###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import json
import os
from typing import List
from braket.timings.time_series import TimeSeries
from braket.ahs.driving_field import DrivingField

from qReduMIS.solver.utils.config_helper import read_config


def load_schedule():
    """
    Loads the Rydberg drive schedule referenced by ``configurations.ini``.

    The ``[quantum] schedule`` entry may be either an absolute path or a path
    relative to the package root (the directory containing
    ``configurations.ini``).  Relative paths are resolved against the package
    root first, then against the current working directory, so the schedule can
    be found regardless of where the process was launched from.

    Returns:
        dict or None: The schedule loaded from the file, or None if an error occurs.
    """

    config = read_config()
    file_path = config["quantum"]["schedule"]

    if not file_path:
        print("Error: No file path provided.")
        return None

    # Resolve relative schedule paths against the package root so the schedule
    # is found no matter the current working directory.
    if not os.path.isabs(file_path) and not os.path.exists(file_path):
        package_root = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
        )
        candidate = os.path.join(package_root, file_path)
        if os.path.exists(candidate):
            file_path = candidate

    try:
        with open(file_path, "r") as file:
            schedule = json.load(file)

    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None

    except Exception as e:
        print(f"An error occurred while loading the file: {e}")
        return None

    return schedule


def get_drive(
    times: List[float],
    amplitude_values: List[float],
    detuning_values: List[float],
    phase_values: List[float],
) -> DrivingField:
    """
    Obtains the driving field from a set of time points and values of the fields.

    Args:
        times (List[float]): The time points of the driving field.
        amplitude_values (List[float]): The values of the amplitude.
        detuning_values (List[float]): The values of the detuning.
        phase_values (List[float]): The values of the phase.

    Returns:
        DrivingField: The driving field obtained.
    """

    assert len(times) == len(amplitude_values)
    assert len(times) == len(detuning_values)
    assert len(times) == len(phase_values)

    amplitude = TimeSeries()
    detuning = TimeSeries()
    phase = TimeSeries()

    for t, amplitude_value, detuning_value, phase_value in zip(
        times, amplitude_values, detuning_values, phase_values
    ):
        amplitude.put(t, amplitude_value)
        detuning.put(t, detuning_value)
        phase.put(t, phase_value)

    drive = DrivingField(amplitude=amplitude, detuning=detuning, phase=phase)

    return drive

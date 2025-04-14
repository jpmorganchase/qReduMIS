###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import numpy as np
import time
import json
import tracemalloc
from abc import abstractmethod
from collections import Counter
from typing import List, Tuple, Dict, Optional

from braket.ahs.hamiltonian import Hamiltonian
from braket.ahs.atom_arrangement import AtomArrangement
from braket.ahs.analog_hamiltonian_simulation import AnalogHamiltonianSimulation
from braket.ahs.field import Field
from braket.ahs.pattern import Pattern
from braket.ahs.shifting_field import ShiftingField
from braket.timings.time_series import TimeSeries
from braket.aws import AwsDevice, AwsSession, AwsQuantumTask

from qReduMIS.solver.quantum_informer.backend_system.base_backend import Backend
from qReduMIS.solver.utils.quantum_solver_helper import get_drive, load_schedule


class RydbergAtomBackend(Backend):
    """
    A backend for simulating quantum experiments using Rydberg atoms.

    Args:
        scale (float): The lattice space in meters.
    """

    def __init__(self, scale: float = 5.45e-6):
        super().__init__()
        my_bucket = "amazon-braket-us-east-1-231197392483"
        my_prefix = "hello_quera"
        self.schedule = None
        self.s3_folder = (my_bucket, my_prefix)
        self.C6 = 5420367982440
        self.scale = scale

    def _setup_hamiltonian(self, atom_positions: List[Tuple[int, int]]) -> Hamiltonian:
        """
        Sets up the Hamiltonian given the schedule defined in configurations.ini.

        Args:
            atom_positions (List[Tuple[int, int]]): List of atom positions in the space.

        Returns:
            Hamiltonian: The configured Hamiltonian.
        """
        # Setup timeseries for the local field
        Delta_local = TimeSeries()
        Delta_local.put(0.0, 0.0).put(self.schedule["time_points"][-1], 0.0)

        # Create pattern for all atoms (initialized to zero)
        h = Pattern([0] * len(atom_positions))

        # Create shifting field
        shift = ShiftingField(magnitude=Field(time_series=Delta_local, pattern=h))

        # Setup drive from schedule parameters
        drive = get_drive(
            self.schedule["time_points"],
            self.schedule["omega_values"],
            self.schedule["detuning_values"],
            self.schedule["phase_values"],
        )

        # Initialize Hamiltonian
        Hfix = Hamiltonian()
        Hfix += drive

        # Add shift for tensor network simulator
        if self.backend_id == "Tensor Network Simulator":
            Hfix += shift

        return Hfix

    def _check_connectivity(self):
        """
        Checks the unit-disk Union-Jack like connectivity of the graph, required for the backend.
        """
        # Calculate Rydberg blockade radius
        omega_max = max(self.schedule["omega_values"])
        rb = (self.C6 / omega_max) ** (1 / 6)

        # Check connectivity constraints
        rb_scaled = rb / (self.scale * 1e6)

        if not (rb_scaled < 2 and np.sqrt(2) < rb_scaled):
            raise ValueError("Not Union-Jack connectivity")

    def _prepare_ahs_program(
        self, atom_positions: List[Tuple[int, int]], Hfix: Hamiltonian
    ) -> AnalogHamiltonianSimulation:
        """
        Prepares the Analog Hamiltonian Simulation program.

        Args:
            atom_positions (List[Tuple[int, int]]): List of atom positions in the space.
            Hfix (Hamiltonian): The Hamiltonian to use.

        Returns:
            AnalogHamiltonianSimulation: The prepared AHS program.
        """
        # Setup atom arrangement
        atoms = AtomArrangement()
        for atom in atom_positions:
            atoms.add(atom)

        # Create analog Hamiltonian simulation program
        ahs_program = AnalogHamiltonianSimulation(register=atoms, hamiltonian=Hfix)

        return ahs_program

    def run_experiment(
        self, atom_positions: List[Tuple[int, int]], num_shots: int, iteration: int
    ) -> List[Dict[str, int]]:
        """
        Runs the experiment on the specified backend.

        Args:
            atom_positions (List[Tuple[int, int]]): List of atom positions.
            num_shots (int): Number of shots to run on backend.
            iteration (int): Current iteration of the qReduMIS algorithm.

        Returns:
            List[Dict[str, int]]: Post-processed counts from the experiment.
        """
        self.schedule = load_schedule()

        if self.schedule is None:
            raise ValueError("Schedule must be provided")

        try:
            # Set up Hamiltonian
            Hfix = self._setup_hamiltonian(atom_positions)

            # Check connectivity
            self._check_connectivity()

            # Convert atom positions to SI units
            atom_positions_si = [
                (x * self.scale, y * self.scale) for x, y in atom_positions
            ]

            # Prepare Analog Hamiltonian Simulation
            ahs_program = self._prepare_ahs_program(atom_positions_si, Hfix)

            # Setup and run experiment
            task = self.execute(ahs_program, num_shots)

            counts_postprocessed = self.get_results(task, iteration)

            return counts_postprocessed

        except Exception as e:
            raise e

    def execute(
        self, ahs_program: AnalogHamiltonianSimulation, num_shots: int
    ) -> AwsQuantumTask:
        """
        Executes the AHS program on the quantum device.

        Args:
            ahs_program (AnalogHamiltonianSimulation): The program to execute.
            num_shots (int): The number of shots to run the program.

        Returns:
            AwsQuantumTask: The task containing the results.
        """
        if self.backend_id == "Aquila":
            ahs_program = ahs_program.discretize(self.device)

        task = self.device.run(
            ahs_program, s3_destination_folder=self.s3_folder, shots=num_shots
        )

        return task

    def get_counts_from_result(self, result) -> List[Dict[str, int]]:
        """
        Extracts solutions and their counts from the result.

        Args:
            result (AnalogHamiltonianSimulationQuantumTaskResult): The result from the execution on the backend.

        Returns:
            List[Dict[str, int]]: A list of dictionaries containing the nodes of the solutions and their counts.
        """
        if not result:
            raise ValueError("No result received")

        states = ["e", "r", "g"]  # e = empty, r = Rydberg, g = ground state
        state_labels = []
        for shot in result.measurements:
            pre = shot.pre_sequence
            post = shot.post_sequence
            state_idx = np.array(pre) * (1 + np.array(post))
            state_labels.append("".join([states[s_idx] for s_idx in state_idx]))

        occurrence_count = Counter(state_labels)
        sols = list(occurrence_count.keys())
        sols_postselection = list(
            Counter(
                [
                    state_label
                    for state_label in state_labels
                    if state_label.count("e") == 0
                ]
            ).keys()
        )

        all_sols_postselection = []
        for sol in sols_postselection:
            sol_dict_postselection = {}
            atoms_mis_postselection = [
                pos for pos, char in enumerate(sol) if char == "r"
            ]  # Drop the information of all the 'e' (empty)
            sol_dict_postselection["nodes"] = tuple(atoms_mis_postselection)
            sol_dict_postselection["count"] = occurrence_count[sol]
            all_sols_postselection.append(sol_dict_postselection)

        return all_sols_postselection

    def get_results(self, task: AwsQuantumTask, iteration: int) -> List[Dict[str, int]]:
        """
        Retrieves and processes results from the quantum backend.

        Args:
            task (AwsQuantumTask): The task submitted to the quantum backend or simulator.
            iteration (int): Current iteration of the qReduMIS algorithm.

        Returns:
            List[Dict[str, int]]: Post-processed counts from the experiment.
        """
        result = task.result()
        raw_result = []
        counts_postprocessed = self.get_counts_from_result(result)

        if len(counts_postprocessed) == 0:
            raise ValueError("Postprocessed counts are empty!")

        for shot in result.measurements:
            pre = shot.pre_sequence
            post = shot.post_sequence
            raw_result.append(
                {
                    "pre": list(pre),
                    "post": list(post),
                }
            )

        def convert_to_serializable(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                return {
                    key: convert_to_serializable(value) for key, value in obj.items()
                }
            return obj

        # Convert the data
        raw_result = convert_to_serializable(raw_result)

        results = {
            "task_id": task.id,
            "raw_result": raw_result,
            "counts_postprocessed": counts_postprocessed,
        }

        # Storing results
        with open(f"result_backend_it{iteration}.json", "w") as f:
            json.dump(results, f)

        return counts_postprocessed

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

from braket.ahs.hamiltonian import Hamiltonian
from braket.ahs.atom_arrangement import AtomArrangement
from braket.ahs.analog_hamiltonian_simulation import AnalogHamiltonianSimulation
from braket.ahs.field import Field
from braket.ahs.pattern import Pattern
from braket.ahs.shifting_field import ShiftingField
from braket.timings.time_series import TimeSeries
from braket.ahs.pattern import Pattern
from braket.aws import AwsDevice, AwsSession, AwsQuantumTask

from qReduMIS.solver.quantum_informer.backend_system.base_backend import Backend
from qReduMIS.solver.utils.quantum_solver_helper import get_drive, load_schedule


class RydbergAtomBackend(Backend):

    def __init__(self, scale=5.45e-6):
        """
        Args:
            scale (float): this is the lattice space in meters
        """
        super().__init__()
        my_bucket = "amazon-braket-us-east-1-231197392483"
        my_prefix = "hello_quera"
        self.schedule = None
        self.s3_folder = (my_bucket, my_prefix)
        self.C6 = 5420367982440
        self.scale = scale

    def _setup_hamiltonian(self, atom_positions):
        """
        Method to setup hamiltonian given the schedule defined in configurations.ini

        Args:
            atom_positions: list[[int, int]] of atom positions in the space

        Returns:
            Hfix: Hamiltonian
        """
        # setup timeseries for the local field
        Delta_local = TimeSeries()
        Delta_local.put(0.0, 0.0).put(self.schedule["time_points"][-1], 0.0)

        # create pattern for all atoms (initialized to zero)
        h = Pattern([0] * len(atom_positions))

        # create shifting field
        shift = ShiftingField(magnitude=Field(time_series=Delta_local, pattern=h))

        # setup drive from schedule parameters
        drive = get_drive(
            self.schedule["time_points"],
            self.schedule["omega_values"],
            self.schedule["detuning_values"],
            self.schedule["phase_values"],
        )

        # initialize Hamiltonian
        Hfix = Hamiltonian()
        Hfix += drive

        # add shift for tensor network simulator
        if self.backend_id == "Tensor Network Simulator":
            Hfix += shift

        return Hfix

    def _check_connectivity(self):
        """
        This method performs a check to ensure the unit-disk Union-Jack like connectivity of the graph because this is required for the backend (both hardware and simulator)
        """
        # calculate rydberg blockade radius
        omega_max = max(self.schedule["omega_values"])
        rb = (self.C6 / omega_max) ** (1 / 6)

        # check connectivity constraints
        rb_scaled = rb / (self.scale * 1e6)

        if not (rb_scaled < 2 and np.sqrt(2) < rb_scaled):
            raise ValueError("not Union-Jack connectivity")

    def _prepare_ahs_program(self, atom_positions, Hfix):
        """
        Args:
            atom_positions: list[[int, int]] of atom positions in the space
            Hfix: Hamiltonian of type braket.ahs.hamiltonian.Hamiltonian
        
        Returns: 
            ahs_program (braket.ahs.analog_hamiltonian_simulation.AnalogHamiltonianSimulation): Analog Hamiltonian Simulation program
        """
        # setup atom arrangement
        atoms = AtomArrangement()
        for atom in atom_positions:
            atoms.add(atom)

        # create analog hamilton simulation program
        ahs_program = AnalogHamiltonianSimulation(register=atoms, hamiltonian=Hfix)

        return ahs_program

    def run_experiment(self, atom_positions, num_shots, iteration):
        """
        Runs the experiment on the specified backend

        Args:
            atom_positions: list of atom positions
            num_shots: int number of shots to run on backend
            iteration: int refers to the current iteration of the qReduMIS algorithm

        Returns:
            counts_postprocessed (dict): Post-processed counts from the experiment
        """
        self.schedule = load_schedule()

        if self.schedule is None:
            raise ValueError("Schedule must be provided")

        try:
            # set up Hamiltonian
            Hfix = self._setup_hamiltonian(atom_positions)

            # check connectivity
            self._check_connectivity()

            # convert atom positions to si
            atom_positions_si = [
                (x * self.scale, y * self.scale) for x, y in atom_positions
            ]

            # prepare Analog Hamiltonian Simulation
            ahs_program = self._prepare_ahs_program(atom_positions_si, Hfix)

            # setup and run experiment
            task = self.execute(ahs_program, num_shots)

            counts_postprocessed = self.get_results(task, iteration)

            return counts_postprocessed

        except Exception as e:
            raise e

    def execute(self, ahs_program, num_shots: int):
        """
        Method to execute the AHS program on the quantum device

        Args:
            ahs_program (braket.ahs.analog_hamiltonian_simulation.AnalogHamiltonianSimulation): the program to execute
            num_shots (int): the number of shots to run the program
        
        Returns:
            task: (braket.tasks.analog_hamiltonian_simulation_quantum_task_result.AnalogHamiltonianSimulationQuantumTaskResult): the task containing the results
        """
        if self.backend_id == "Aquila":
            ahs_program = ahs_program.discretize(self.device)

        task = self.device.run(
            ahs_program, s3_destination_folder=self.s3_folder, shots=num_shots
        )

        return task

    def get_counts_from_result(self, result):
        """
        Method to extract solutions and their counts from the result

        Args:
            result (AnalogHamiltonianSimulationQuantumTaskResult): The result from the execution on the backend.

        Returns:
            all_sols_postselection (list): A list of dictionaries containing the nodes of the solutions and their counts.
        """
        if not result:
            raise ValueError("No result received")

        states = [
            "e",
            "r",
            "g",
        ]  # e = empty, r=rydberg, g=ground state [state of atoms]
        state_labels = []
        for shot in result.measurements:
            pre = shot.pre_sequence
            post = shot.post_sequence
            state_idx = np.array(pre) * (1 + np.array(post))
            state_labels.append("".join([states[s_idx] for s_idx in state_idx]))

        occurence_count = Counter(state_labels)
        sols = list(occurence_count.keys())
        sols_postselection = list(
            Counter(
                [
                    state_label
                    for state_label in state_labels
                    if state_label.count("e") == 0
                ]
            ).keys()
        )

        all_sols = []
        for sol in sols:
            sol_dict = {}
            atoms_mis = [
                pos for pos, char in enumerate(sol) if char == "r"
            ]  ## we drop the information of all the 'e' (empty)
            sol_dict["nodes"] = tuple(atoms_mis)
            sol_dict["count"] = occurence_count[sol]
            all_sols.append(sol_dict)

        all_sols_postselection = []
        for sol in sols_postselection:
            sol_dict_postselection = {}
            atoms_mis_postselection = [
                pos for pos, char in enumerate(sol) if char == "r"
            ]  ## we drop the information of all the 'e' (empty)
            sol_dict_postselection["nodes"] = tuple(atoms_mis_postselection)
            sol_dict_postselection["count"] = occurence_count[sol]
            all_sols_postselection.append(sol_dict_postselection)

        return all_sols_postselection

    def get_results(self, task, iteration):
        """
        Method to retrieve and process results from quantum backend

        Args:
            task (AwsQuantumTask): The task submitted to the quantum backend or simulator.
            iteration (int): Current iteration of the qReduMIS algorithm.

        Returns:
            counts_postprocessed (dict): Post-processed counts from the experiment
        """
        result = task.result()
        raw_result = []
        counts_postprocessed = self.get_counts_from_result(result)

        if len(counts_postprocessed) == 0:
            raise ValueError("postprocessed counts are empty!")

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
            "raw_result": raw_result,  ## TO DO: make sure to store this in json seriable
            "counts_postprocessed": counts_postprocessed,
        }

        # storing results
        with open(f"result_backend_it{iteration}.json", "w") as f:
            json.dump(results, f)

        return counts_postprocessed

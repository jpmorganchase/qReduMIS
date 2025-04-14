###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

import numpy as np
import networkx as nx
import json
import random
from typing import List, Tuple, Optional

from qReduMIS.solver.quantum_informer.quantum_selection import (
    quantum_mis,
    quantum_select,
)
from qReduMIS.solver.utils.graph_helper import construct_graph_from_atom_positions
from qReduMIS.solver.utils.quantum_solver_helper import get_drive, load_schedule
from qReduMIS.solver.quantum_informer.corrector_strategies.fixer import (
    get_fixup_sol,
    remove_with_check_and_add,
)
from qReduMIS.solver.quantum_informer.backend_system.base_backend import Backend


class QuantumSolver:
    """
    A class to handle quantum computations for solving the Maximum Independent Set (MIS) problem.

    Args:
        quantum_backend (Backend): The quantum backend to run experiments.
        selection_strategy (str): The strategy for selecting nodes ("outset" or "inset").
        num_shots (int): The number of shots to run on the quantum backend.
    """

    def __init__(
        self, quantum_backend: Backend, selection_strategy: str, num_shots: int
    ):
        self.quantum_backend = quantum_backend
        self.selection_strategy = selection_strategy
        self.num_shots = num_shots

        self.clean_counts = None

    def get_clean_counts(
        self,
        atom_positions: List[Tuple[float, float]],
        iteration: int,
        graph: Optional[nx.Graph] = None,
    ) -> List[dict]:
        """
        Runs an experiment on the quantum backend and processes the results.

        Args:
            atom_positions (List[Tuple[float, float]]): List of atom positions.
            iteration (int): The current iteration number.
            graph (Optional[nx.Graph]): Graph representation of atom positions.

        Returns:
            List[dict]: Clean solutions after processing and validation.
        """
        # Run experiments on backend
        all_counts = self.quantum_backend.run_experiment(
            atom_positions, self.num_shots, iteration
        )

        if graph is None:
            graph = construct_graph_from_atom_positions(atom_positions)

        # Extract edges for solution validation
        edges_list = list(graph.edges())

        # Process and validate solutions
        clean_solutions = self._get_clean_solutions(all_counts, edges_list)

        return clean_solutions

    def _get_clean_solutions(
        self,
        all_counts: List[dict],
        edges_list: List[Tuple[int, int]],
        method=remove_with_check_and_add,
    ) -> List[dict]:
        """
        Fixes the input counts based on a method to ensure independence (i.e., no edge between selected nodes).

        Args:
            all_counts (List[dict]): The input counts from the quantum backend.
            edges_list (List[Tuple[int, int]]): The edge list of the graph.
            method (function): The method to fix the counts.

        Returns:
            List[dict]: The fixed solutions.
        """
        return get_fixup_sol(all_counts, edges_list, method)

    def find_maximum_independent_set(
        self,
        clean_counts: List[dict],
        atom_positions: List[Tuple[float, float]],
        seed: int,
    ) -> List[Tuple[float, float]]:
        """
        Finds the largest solution measured, representing the MIS given by the backend.

        Args:
            clean_counts (List[dict]): The clean counts from the quantum backend.
            atom_positions (List[Tuple[float, float]]): The input graph given by the atom positions.
            seed (int): Random seed for reproducibility.

        Returns:
            List[Tuple[float, float]]: The maximum independent set.
        """
        return quantum_mis(clean_counts, atom_positions, seed)

    def select_nodes(
        self,
        clean_counts: List[dict],
        atom_positions: List[Tuple[float, float]],
        kernel_graph: nx.Graph,
        original_positions: List[Tuple[float, float]],
        seed: int,
        k_size: int = 2,
        num_nodes_frac: float = 0.4,
    ) -> Tuple[
        List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]
    ]:
        """
        Selects nodes to be included in or removed from the solution based on the selection strategy.

        Args:
            clean_counts (List[dict]): Processed results from quantum computation.
            atom_positions (List[Tuple[float, float]]): List of atom positions in the kernel.
            kernel_graph (nx.Graph): Reduced graph (kernel).
            original_positions (List[Tuple[float, float]]): Original list of atom positions.
            seed (int): Random seed for reproducibility.
            k_size (int): Largest solution size to consider.
            num_nodes_frac (float): Fraction of nodes to consider.

        Returns:
            Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]:
                - selected_in_positions: Nodes selected to be part of the solution.
                - selected_out_positions: Nodes selected to be removed from the solution.
                - to_remove_positions: Positions of nodes to be removed from the kernel.
        """
        return quantum_select(
            clean_counts,
            atom_positions,
            kernel_graph,
            original_positions,
            seed,
            k_size,
            num_nodes_frac,
            selection_algo=self.selection_strategy,
        )

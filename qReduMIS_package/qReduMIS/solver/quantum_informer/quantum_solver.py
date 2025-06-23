###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import numpy as np
import json
import random

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

    def __init__(
        self, quantum_backend: Backend, selection_strategy: str, num_shots: int
    ):
        self.quantum_backend = quantum_backend
        self.selection_strategy = selection_strategy
        self.num_shots = num_shots

        self.clean_counts = None

    def get_clean_counts(self, atom_positions, iteration, graph=None):
        """
        Method to run experiment on quantum backend and process results

        Args:
            atom_positions: list of atom positions
            graph: graph representation of atom positions

        Returns:
            clean_solutions (list):
        """
        # run experiments on backend
        all_counts = self.quantum_backend.run_experiment(
            atom_positions, self.num_shots, iteration
        )

        if graph is None:
            graph = construct_graph_from_atom_positions(atom_positions)

        # extract edges for solution validation
        edges_list = list(graph.edges())

        # process and validate solutions
        clean_solutions = self._get_clean_solutions(all_counts, edges_list)

        return clean_solutions

    def _get_clean_solutions(
        self, all_counts, edges_list, method=remove_with_check_and_add
    ):
        """
        Given the input counts and the edge list of the graph, the counts are fixed based on a method. It can occur that nodes selected do not meet the independence (i.e., no edge between them) requirement and we
        fix these counts
        """
        return get_fixup_sol(all_counts, edges_list, method)

    def find_maximum_independent_set(self, clean_counts, atom_positions, seed):
        """
        Given the clean counts and the input graph given by the atom positions, we get the largest solution measured, which represents the MIS given by the backend
        """
        return quantum_mis(clean_counts, atom_positions, seed)

    def select_nodes(
        self,
        clean_counts,
        atom_positions,
        kernel_graph,
        original_positions,
        seed,
        k_size=2,
        num_nodes_frac=0.4,
    ):
        """
        Args:
            clean_counts: processed results from quantum computation
            atom_positions: list of atom positions in the kernel
            kernel_graph: reduced graph (kernel)
            original_positions: orginal list of atom positions
            seed: random seed for reproducibility
            k_size: largest solution size to consider
            num_nodes_frac: fraction of nodes to consider

        Returns:
            tuple: selected_in_positions, selected_out_positions, to_remove_positions
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

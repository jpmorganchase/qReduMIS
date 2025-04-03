###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

import json
import time
import random
import logging
from copy import deepcopy
from typing import Literal

from qReduMIS.solver.utils.graph_helper import (
    construct_graph_from_atom_positions,
    get_reduction_factor,
    load_atoms,
    separate_atom_positions,
)
from qReduMIS.solver.classical_reducer.reducer import Reducer
from qReduMIS.solver.quantum_informer.quantum_solver import QuantumSolver
from qReduMIS.solver.quantum_informer.backend_system.base_backend import Backend

logger = logging.getLogger(__name__)


class MISSolver:
    """
    This class implements the qReduMIS algorithm which combines classical graph reduction techniques
    with quantum computing to find maximum independent sets in a given graph

    Args:
        top_k_solutions: the number of top (largest) counts considered to select nodes to inform the next reduction
        selection_strategy: this indicates the selection strategy utilized to inform the next reduction
        quantum_backend: indicates the backend to be used to execute experiment and inform the next reduction
        quantum_shots: the number of shots to run on quantum backend
        max_iteration_limit: the maximum number of iterations allowed for the algorithm
    """

    def __init__(
        self,
        top_k_solutions: int,
        selection_strategy: Literal["outset", "inset"],
        quantum_backend: Backend,
        quantum_shots: int,
        max_iteration_limit: int = 10,
    ):
        self.top_k_solutions = top_k_solutions
        self.max_iteration_limit = max_iteration_limit

        self.classical_reducer = Reducer(verbose=True)
        self.quantum_solver = QuantumSolver(
            quantum_backend=quantum_backend,
            selection_strategy=selection_strategy,
            num_shots=quantum_shots,
        )

        # initialize solution sets
        self.S = set()  # selected nodes for the final solution,
        self.W = set()  # incumbent solution
        self.R = set()  # removed nodes

    def solve(self, atom_positions, enable_storing=True):
        """
        Given the problem instance expressed with the atom_positions, this method solves the MIS problem using qReduMIS

        Args:
            atom_positions (list[int, int]): Position of the atoms in the space
        Returns:
            solution (list[int, int]): Position of the nodes selected for the solution of the MIS
            iterations (int): The number of iterations the algorithm executed for
        """
        solution, iterations = self._solve_problem(atom_positions, enable_storing)
        return solution, iterations

    def _solve_problem(self, atom_positions, enable_storing=False, current_iteration=0):
        """
        Implements QReduMIS algorithm. Given the problem instance expressed with the atom_positions, it finds the MIS.
        Note that this is an interative algorithm, which is implemented recursively.
        Args:
            atom_positions: list[int, int] containins the position of the atoms in the space
            enable_storing: boolean to enable to storing of information data through each iteration of the algorithm
            current_iteration: int indicates the current iteration of the algorithm

        Returns:
            W: the best solution find, this is a set containins the position of the nodes
            iterations: number of iterations required for the algorithm to fully reduce the input graph.
        """
        # check termination condition
        if current_iteration == self.max_iteration_limit:
            return self.W, current_iteration

        G = construct_graph_from_atom_positions(atom_positions)
        if not G or len(G.nodes()) == 0:
            return self.W, current_iteration

        # keep original graph for reference
        orig_graph = deepcopy(G)  # should not be class variable

        # apply classical reduction
        K, r, s = self.classical_reducer.reduce(G)

        classical_selected_positions = [
            atom_positions[i] for i in range(len(atom_positions)) if i in s
        ]
        classical_removed_positions = [
            atom_positions[i] for i in range(len(atom_positions)) if i in r
        ]
        ## this is the output kernel
        classical_kernel_positions = [
            atom_positions[i]
            for i in range(len(atom_positions))
            if i not in r and i not in s
        ]

        ## update the nodes selected
        self.S.update(tuple(position) for position in classical_selected_positions)
        ## update the nodes removed
        self.R.update(tuple(position) for position in classical_removed_positions)

        reduction_factor = get_reduction_factor(orig_graph, K)

        if reduction_factor == 1:  ## if it is fully reducible, we finish here
            if len(self.S) > len(self.W):
                self.W = self.S.copy()
                
                if enable_storing:
                    info_iteration = {
                        "iteration": current_iteration,
                        "input": atom_positions,
                        "classical reduction factor": reduction_factor,
                        "classical kernel": classical_kernel_positions,
                        "classical selected": classical_selected_positions,
                        "classical removed": classical_removed_positions,
                        "S": list(self.S),
                        "W": list(self.W),
                        "R": list(self.R),
                    }

                    with open(f"info_{current_iteration}.json", "w") as f:
                        json.dump(info_iteration, f)

            return self.W, current_iteration

        clean_counts = self.quantum_solver.get_clean_counts(
            classical_kernel_positions, current_iteration
        )

        # set a random seed for reproducibility
        seed = random.randint(1, 10000)

        # get the maximum independent set from quantum computation
        I = self.quantum_solver.find_maximum_independent_set(
            clean_counts, classical_kernel_positions, seed
        )

        ## update W
        if len(self.S) + len(I) > len(self.W):
            self.W = self.S.union(tuple(position) for position in I)

        selected_in_positions, selected_out_positions, to_remove_positions = (
            self.quantum_solver.select_nodes(
                clean_counts,
                classical_kernel_positions,
                K,
                atom_positions,
                seed,
                self.top_k_solutions,
            )
        )

        # update solution sets with quantum-guided choices
        self.R.update(
            tuple(position) for position in selected_out_positions
        )  # the total nodes we have removed so far
        self.S.update(
            tuple(position) for position in selected_in_positions
        )  # the total nodes we have selected so far

        # prepare atom positions for the next iteration (removing selected and removed positions)
        new_atom_positions = [
            pos for pos in classical_kernel_positions if pos not in to_remove_positions
        ]

        if enable_storing:
            info_iteration = {
                "iteration": current_iteration,
                "input": atom_positions,
                "classical reduction factor": reduction_factor,
                "classical kernel": classical_kernel_positions,
                "classical selected": classical_selected_positions,
                "classical removed": classical_removed_positions,
                "quantum selected": selected_in_positions,
                "quantum removed": selected_out_positions,
                "quantum best sol": I,
                "quantum kernel": new_atom_positions,
                "S": list(self.S),
                "W": list(self.W),
                "R": list(self.R),
                "seed": seed,
            }

            with open(f"info_{current_iteration}.json", "w") as f:
                json.dump(info_iteration, f)

        # recursively solve the reduced problem
        next_iteration = current_iteration + 1

        return self._solve_problem(new_atom_positions, current_iteration=next_iteration)

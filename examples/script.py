###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import sys
sys.path.append("../")

import json
import pickle

from qReduMIS.mis_solver import MISSolver
from qReduMIS.solver.utils.graph_helper import load_atoms
from qReduMIS.solver.quantum_informer.backend_system.backend_generator import BackendFactory


def main():

    atom_positions = load_atoms("input_data/problem_instances/atoms_L8_seed3559.json")
    quantum_backend = BackendFactory.get_backend("Local Simulator") 

    mis_solver = MISSolver(
        top_k_solutions = 2,
        selection_strategy = "inset",
        quantum_backend = quantum_backend,
        quantum_shots = 1,
        max_iteration_limit = 1
    )

    result, num_iterations = mis_solver.solve(atom_positions, enable_storing=True)

    final_result = {
        'atom positions MIS' : list(result), # a list of tuples with the position in space of atoms in the solution (x, y)
        'num iteration' : num_iterations     # the number of iterations ran by the algorithm
    }
    with open(f"final_res.json", 'w') as f:
        json.dump(final_result, f)


if __name__ == "__main__":
    main()
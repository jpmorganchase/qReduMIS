###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import sys

sys.path.append("./")

import pytest
import json
from unittest.mock import patch, MagicMock
from qReduMIS.mis_solver import MISSolver
from qReduMIS.solver.quantum_informer.quantum_solver import QuantumSolver
from qReduMIS.solver.quantum_informer.backend_system.backend_generator import (
    BackendFactory,
)


def test_solve_problem_BMW2023_HP1435_inset(
    mock_data_BMW2023_HP1435,
    mock_quantum_solver_counts_BMW2023_HP1435_inset,
    mock_seeds_BMW2023_HP1435_inset,
):
    quantum_backend = BackendFactory.get_backend("Local Simulator")

    solver = MISSolver(
        top_k_solutions=2,
        selection_strategy="inset",
        quantum_backend=quantum_backend,
        quantum_shots=10,
        max_iteration_limit=4,
    )

    solution, iterations = solver._solve_problem(mock_data_BMW2023_HP1435, 0)

    assert isinstance(solution, set)
    assert iterations <= solver.max_iteration_limit
    assert iterations == 2
    assert len(solution) > 0

    expected_solution = json.load(
        open(
            "tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/results_qReduMIS_it2.json",
            "r",
        )
    )["W"]
    formatted_expected_solution = set(tuple(sublist) for sublist in expected_solution)
    assert formatted_expected_solution == solution


def test_solve_problem_BMW2023_HP125_inset(
    mock_data_BMW2023_HP125,
    mock_quantum_solver_counts_BMW2023_HP125_inset,
    mock_seeds_BMW2023_HP125_inset,
):
    quantum_backend = BackendFactory.get_backend("Local Simulator")

    solver = MISSolver(
        top_k_solutions=2,
        selection_strategy="inset",
        quantum_backend=quantum_backend,
        quantum_shots=10,
        max_iteration_limit=4,
    )

    solution, iterations = solver._solve_problem(mock_data_BMW2023_HP125, 0)

    assert isinstance(solution, set)
    assert iterations <= solver.max_iteration_limit
    assert iterations == 3
    assert len(solution) > 0

    expected_solution = json.load(
        open(
            "tests/assertions/simulated_results_TN_BMW2023_HP125/inset/results_qReduMIS_it3.json",
            "r",
        )
    )["W"]
    formatted_expected_solution = set(tuple(sublist) for sublist in expected_solution)
    assert formatted_expected_solution == solution


def test_solve_problem_BMW2023_HP125_outset(
    mock_data_BMW2023_HP125,
    mock_quantum_solver_counts_BMW2023_HP125_outset,
    mock_seeds_BMW2023_HP125_outset,
):

    quantum_backend = BackendFactory.get_backend("Local Simulator")
    solver = MISSolver(
        top_k_solutions=2,
        selection_strategy="outset",
        quantum_backend=quantum_backend,
        quantum_shots=10,
        max_iteration_limit=7,
    )

    solution, iterations = solver._solve_problem(mock_data_BMW2023_HP125, 0)

    assert isinstance(solution, set)
    assert iterations <= solver.max_iteration_limit
    assert iterations == 6
    assert len(solution) > 0

    expected_solution = json.load(
        open(
            "tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_qReduMIS_it6.json",
            "r",
        )
    )["W"]
    formatted_expected_solution = set(tuple(sublist) for sublist in expected_solution)
    assert formatted_expected_solution == solution


def test_solve_problem_BMW2023_HP1435_outset(
    mock_data_BMW2023_HP1435,
    mock_quantum_solver_counts_BMW2023_HP1435_outset,
    mock_seeds_BMW2023_HP1435_outset,
):
    quantum_backend = BackendFactory.get_backend("Local Simulator")

    solver = MISSolver(
        top_k_solutions=2,
        selection_strategy="outset",
        quantum_backend=quantum_backend,
        quantum_shots=10,
        max_iteration_limit=5,
    )

    solution, iterations = solver._solve_problem(mock_data_BMW2023_HP1435, 0)

    assert isinstance(solution, set)
    assert iterations <= solver.max_iteration_limit
    assert iterations == 4
    assert len(solution) > 0

    expected_solution = json.load(
        open(
            "tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_qReduMIS_it4.json",
            "r",
        )
    )["W"]
    formatted_expected_solution = set(tuple(sublist) for sublist in expected_solution)
    assert formatted_expected_solution == solution


def test_solve_problem_with_iteration_termination(
    mock_data_BMW2023_HP1435,
    mock_quantum_solver_counts_BMW2023_HP1435_outset,
    mock_seeds_BMW2023_HP1435_outset,
):
    quantum_backend = BackendFactory.get_backend("Local Simulator")

    max_iteration_limit = 3

    solver = MISSolver(
        top_k_solutions=2,
        selection_strategy="outset",
        quantum_backend=quantum_backend,
        quantum_shots=10,
        max_iteration_limit=max_iteration_limit,
    )

    solution, iterations = solver._solve_problem(mock_data_BMW2023_HP1435, 0)

    assert isinstance(solution, set)
    assert iterations <= solver.max_iteration_limit
    assert iterations == max_iteration_limit
    assert len(solution) > 0

    expected_solution = json.load(
        open(
            f"tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_qReduMIS_it{max_iteration_limit-1}.json",
            "r",
        )
    )["W"]
    formatted_expected_solution = set(tuple(sublist) for sublist in expected_solution)
    assert formatted_expected_solution == solution


if __name__ == "__main__":
    pytest.main(["tests/test_mis_solver.py"])

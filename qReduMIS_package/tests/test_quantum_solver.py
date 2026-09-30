###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import sys

sys.path.append("./")

import pytest
import json
import pickle
from unittest.mock import Mock, patch
from braket.devices import LocalSimulator
from qReduMIS.solver.informers.quantum.quantumannealing.informer import QuantumSolver
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.rydberg.rydberg_backend import (
    RydbergAtomBackend,
)
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.backend_generator import (
    BackendFactory,
)
from qReduMIS.solver.informers.corrector_strategies.fixer import (
    remove_with_check_and_add,
)


# Fixture for the QuantumSolver instance
@pytest.fixture
def quantum_solver():
    mock_backend = Mock(spec=RydbergAtomBackend)
    return QuantumSolver(
        quantum_backend=mock_backend, selection_strategy="default", num_shots=100
    )


# Fixture for the QuantumSolver instance with TNSimulator backend
@pytest.fixture
def quantum_solver_with_tn_simulator():
    backend = BackendFactory.get_backend("Local Simulator")
    return QuantumSolver(
        quantum_backend=backend, selection_strategy="default", num_shots=100
    )


# Test for get_clean_counts method
def test_get_clean_counts(quantum_solver):
    mock_atom_positions = [
        [9, 0],
        [8, 1],
        [9, 1],
        [10, 1],
        [2, 2],
        [3, 2],
        [9, 2],
        [1, 3],
        [2, 3],
        [3, 3],
        [4, 3],
        [0, 4],
        [1, 4],
        [2, 4],
        [3, 4],
        [0, 5],
        [2, 5],
        [3, 5],
        [0, 6],
        [1, 6],
        [3, 6],
        [0, 7],
        [2, 7],
        [3, 7],
        [1, 8],
        [2, 8],
        [3, 8],
        [0, 9],
        [1, 9],
        [2, 9],
        [4, 9],
        [1, 10],
        [2, 10],
        [3, 10],
        [0, 11],
        [2, 11],
        [0, 12],
        [1, 12],
        [3, 12],
        [1, 13],
        [2, 13],
    ]
    mock_iteration = 1
    mock_graph = Mock()

    # # Mock the backend's run_experiment method
    # with open(f"data/test_results/results_iter0", "r") as infile:
    #             res = json.loads(json.load(infile))
    #             mocked_counts =res['raw_sols']

    quantum_solver.quantum_backend.run_experiment.return_value = ["mocked_counts"]

    # Mock the construct_graph_from_atom_positions function
    with patch(
        "qReduMIS.solver.utils.graph_helper.construct_graph_from_atom_positions",
        return_value=mock_graph,
    ):
        # Mock the _get_clean_solutions method
        with patch.object(
            QuantumSolver, "_get_clean_solutions", return_value=["mocked_solutions"]
        ) as mock_get_clean_solutions:
            clean_counts = quantum_solver.get_clean_counts(
                mock_atom_positions, mock_iteration
            )

            # Assertions
            quantum_solver.quantum_backend.run_experiment.assert_called_once_with(
                mock_atom_positions, 100, mock_iteration
            )
            mock_get_clean_solutions.assert_called_once()
            assert clean_counts == ["mocked_solutions"]


# Test for _get_clean_solutions method
def test_get_clean_solutions(quantum_solver):

    mock_all_counts = ["mocked_counts"]
    mock_edges_list = [(0, 1), (0, 2), (0, 3)]
    mocked_fixup_sol = ["fixed_sol"]

    with patch(
        "qReduMIS.solver.informers.quantum.quantumannealing.informer.get_fixup_sol",
        return_value=mocked_fixup_sol,
    ) as mock_get_fixup_sol:
        clean_solutions = quantum_solver._get_clean_solutions(
            mock_all_counts, mock_edges_list
        )

        # Assertions
        mock_get_fixup_sol.assert_called_once_with(
            mock_all_counts, mock_edges_list, remove_with_check_and_add
        )
        assert clean_solutions == mocked_fixup_sol


# Test for find_maximum_independent_set method
def test_find_maximum_independent_set(quantum_solver):
    mock_clean_counts = ["clean_counts"]
    mock_atom_positions = ["atom_positions"]
    mock_seed = 426773

    with patch(
        "qReduMIS.solver.informers.quantum.quantumannealing.informer.quantum_mis",
        return_value="max_independent_set",
    ) as mock_quantum_mis:
        result = quantum_solver.find_maximum_independent_set(
            mock_clean_counts, mock_atom_positions, mock_seed
        )

        # Assertions
        mock_quantum_mis.assert_called_once_with(
            mock_clean_counts, mock_atom_positions, mock_seed
        )
        assert result == "max_independent_set"


# Test for select_nodes method
def test_select_nodes(quantum_solver):
    mock_clean_counts = [
        [9, 0],
        [8, 1],
        [9, 1],
        [10, 1],
        [2, 2],
        [3, 2],
        [9, 2],
        [1, 3],
        [2, 3],
        [3, 3],
        [4, 3],
        [0, 4],
        [1, 4],
        [2, 4],
        [3, 4],
        [0, 5],
        [2, 5],
        [3, 5],
        [0, 6],
        [1, 6],
        [3, 6],
        [0, 7],
        [2, 7],
        [3, 7],
        [2, 8],
        [3, 8],
        [0, 9],
        [1, 9],
        [2, 9],
        [4, 9],
        [1, 10],
        [2, 10],
        [3, 10],
        [0, 11],
        [2, 11],
        [0, 12],
        [1, 12],
        [3, 12],
        [1, 13],
        [2, 13],
    ]
    mock_atom_positions = [
        [9, 0],
        [8, 1],
        [9, 1],
        [10, 1],
        [2, 2],
        [3, 2],
        [9, 2],
        [1, 3],
        [2, 3],
        [3, 3],
        [4, 3],
        [0, 4],
        [1, 4],
        [2, 4],
        [3, 4],
        [0, 5],
        [2, 5],
        [3, 5],
        [0, 6],
        [1, 6],
        [3, 6],
        [0, 7],
        [2, 7],
        [3, 7],
        [1, 8],
        [2, 8],
        [3, 8],
        [0, 9],
        [1, 9],
        [2, 9],
        [4, 9],
        [1, 10],
        [2, 10],
        [3, 10],
        [0, 11],
        [2, 11],
        [0, 12],
        [1, 12],
        [3, 12],
        [1, 13],
        [2, 13],
    ]
    mock_kernel_graph = Mock()
    mock_original_positions = [
        [9, 0],
        [8, 1],
        [9, 1],
        [10, 1],
        [2, 2],
        [3, 2],
        [9, 2],
        [1, 3],
        [2, 3],
        [3, 3],
        [4, 3],
        [0, 4],
        [1, 4],
        [2, 4],
        [3, 4],
        [0, 5],
        [2, 5],
        [3, 5],
        [0, 6],
        [1, 6],
        [3, 6],
        [0, 7],
        [2, 7],
        [3, 7],
        [1, 8],
        [2, 8],
        [3, 8],
        [0, 9],
        [1, 9],
        [2, 9],
        [4, 9],
        [1, 10],
        [2, 10],
        [3, 10],
        [0, 11],
        [2, 11],
        [0, 12],
        [1, 12],
        [3, 12],
        [1, 13],
        [2, 13],
    ]
    mock_seed = 426773
    mock_k_size = 2
    mock_num_nodes_frac = 0.4

    with patch(
        "qReduMIS.solver.informers.quantum.quantumannealing.informer.quantum_select",
        return_value=("selected", "removed", "unchanged"),
    ) as mock_quantum_select:
        result = quantum_solver.select_nodes(
            mock_clean_counts,
            mock_atom_positions,
            mock_kernel_graph,
            mock_original_positions,
            mock_seed,
            mock_k_size,
            mock_num_nodes_frac,
        )

        # Assertions
        mock_quantum_select.assert_called_once_with(
            mock_clean_counts,
            mock_atom_positions,
            mock_kernel_graph,
            mock_original_positions,
            mock_seed,
            mock_k_size,
            mock_num_nodes_frac,
            selection_algo=quantum_solver.selection_strategy,
        )
        assert result == ("selected", "removed", "unchanged")


# Test to assert the type of self.device
def test_device_type_in_execute(quantum_solver_with_tn_simulator):
    mock_atom_positions = [(0, 0), (1, 1)]
    mock_iteration = 1

    # Mock the run_experiment method to capture the device type
    with patch.object(
        quantum_solver_with_tn_simulator.quantum_backend,
        "run_experiment",
        return_value={"result": "mocked_counts"},
    ) as mock_run_experiment:
        quantum_solver_with_tn_simulator.quantum_backend.run_experiment(
            mock_atom_positions, mock_iteration
        )

        # Assert that the device is of type LocalSimulator
        assert isinstance(
            quantum_solver_with_tn_simulator.quantum_backend.device, LocalSimulator
        )

        # Ensure the run_experiment method was called
        mock_run_experiment.assert_called_once_with(mock_atom_positions, mock_iteration)

###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import sys

sys.path.append("./")

import pytest
import json
from qReduMIS.solver.quantum_informer.quantum_selection import quantum_mis
from qReduMIS.solver.quantum_informer.quantum_selection import quantum_select


# Test for quantum_mis method
def test_quantum_mis(mock_clean_counts_BM2023_HP1435_inset):
    input_atom_positions = json.load(
        open(
            "tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/atom_positions.json",
            "r",
        )
    )

    result = quantum_mis(
        mock_clean_counts_BM2023_HP1435_inset, input_atom_positions, 476579
    )
    expected_solution = json.load(
        open(
            "tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/largest_solution_476579.json",
            "r",
        )
    )

    assert result == expected_solution


def test_quantum_select_inset(
    mock_clean_counts_BM2023_HP1435_inset,
    mock_kernel_graph_inset,
    mock_kernel_atoms_inset,
    mock_initial_atom_positions_inset,
):
    k_size = 2
    num_nodes_frac = 0.4
    seed = 476579
    selection_algo = "inset"

    (
        selected_in_positions_result,
        selected_out_positions_result,
        to_remove_positions_result,
    ) = quantum_select(
        mock_clean_counts_BM2023_HP1435_inset,
        mock_kernel_atoms_inset,
        mock_kernel_graph_inset,
        mock_initial_atom_positions_inset,
        seed=seed,
        k_size=k_size,
        num_nodes_frac=num_nodes_frac,
        selection_algo=selection_algo,
    )

    assert selected_in_positions_result == [[5, 6]]
    assert selected_out_positions_result == [[5, 5], [6, 5], [6, 6], [4, 7], [6, 7]]
    assert to_remove_positions_result == [
        [5, 6],
        [5, 5],
        [6, 5],
        [6, 6],
        [4, 7],
        [6, 7],
    ]


def test_quantum_select_outset(
    mock_clean_counts_BM2023_HP1435_outset,
    mock_kernel_graph_outset,
    mock_kernel_atoms_outset,
    mock_initial_atom_positions_outset,
):
    k_size = 2
    num_nodes_frac = 0.4
    seed = 634747
    selection_algo = "outset"

    (
        selected_in_positions_result,
        selected_out_positions_result,
        to_remove_positions_result,
    ) = quantum_select(
        mock_clean_counts_BM2023_HP1435_outset,
        mock_kernel_atoms_outset,
        mock_kernel_graph_outset,
        mock_initial_atom_positions_outset,
        seed=seed,
        k_size=k_size,
        num_nodes_frac=num_nodes_frac,
        selection_algo=selection_algo,
    )

    assert selected_in_positions_result == []
    assert selected_out_positions_result == [[12, 4]]
    assert to_remove_positions_result == [[12, 4]]


if __name__ == "__main__":
    pytest.main(["tests/test_quantum_selection.py"])

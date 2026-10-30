###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

import json
from pathlib import Path

import pytest
from networkx.readwrite import json_graph

# Anchor asset paths to this file so the tests pass regardless of the working
# directory pytest is invoked from.
_ASSETS = (
    Path(__file__).resolve().parent
    / "assertions"
    / "simulated_results_TN_BMW2023_HP1435"
)


# ---------------------------------------------------------------------------
# Fixtures for the positions-based quantum-annealing selection tests
# (``tests/test_quantum_selection.py``).  These load pre-recorded clean_counts
# and kernel artifacts from ``tests/assertions/``.
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_clean_counts_BM2023_HP1435_inset():
    clean_counts = json.load(open(_ASSETS / "inset" / "clean_counts_476579.json", "r"))
    return clean_counts


@pytest.fixture
def mock_clean_counts_BM2023_HP1435_outset():
    clean_counts = json.load(open(_ASSETS / "outset" / "clean_counts_634747.json", "r"))
    return clean_counts


@pytest.fixture
def mock_kernel_graph_inset():
    kernel_data = json.load(open(_ASSETS / "inset" / "kernel_graph_476579.json", "r"))
    kernel_graph = json_graph.node_link_graph(kernel_data)
    return kernel_graph


@pytest.fixture
def mock_kernel_atoms_inset():
    kernel_atoms = json.load(open(_ASSETS / "inset" / "kernel_atoms_476579.json", "r"))
    return kernel_atoms


@pytest.fixture
def mock_initial_atom_positions_inset():
    original_atom_positions = json.load(
        open(_ASSETS / "inset" / "original_positions_476579.json", "r")
    )
    return original_atom_positions


@pytest.fixture
def mock_kernel_graph_outset():
    kernel_data = json.load(open(_ASSETS / "outset" / "kernel_graph_634747.json", "r"))
    kernel_graph = json_graph.node_link_graph(kernel_data)
    return kernel_graph


@pytest.fixture
def mock_kernel_atoms_outset():
    kernel_atoms = json.load(open(_ASSETS / "outset" / "kernel_atoms_634747.json", "r"))
    return kernel_atoms


@pytest.fixture
def mock_initial_atom_positions_outset():
    original_atom_positions = json.load(
        open(_ASSETS / "outset" / "original_positions_634747.json", "r")
    )
    return original_atom_positions

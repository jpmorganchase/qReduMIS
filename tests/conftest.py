###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import pytest 
import json
from unittest.mock import patch
from networkx.readwrite import json_graph


@pytest.fixture
def mock_data_BMW2023_HP125():
    atom_positions = json.loads(open("tests/mock_data/atoms_BMW2023_HP125.json").read())
    return atom_positions


@pytest.fixture
def mock_quantum_solver_counts_BMW2023_HP125_inset():
    counts_list = [
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/inset/results_iter0")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/inset/results_iter1")))['raw_sols'],
           json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/inset/results_iter2")))['raw_sols']
           ]
    with patch('qReduMIS.solver.quantum_informer.backend_system.rydberg.rydberg_backend.RydbergAtomBackend.run_experiment', side_effect= counts_list):
        yield


@pytest.fixture
def mock_seeds_BMW2023_HP125_inset():
    seeds = [
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/inset/results_qReduMIS_it0.json", "r"))['seed'], 
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/inset/results_qReduMIS_it1.json", "r"))['seed'],
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/inset/results_qReduMIS_it2.json", "r"))['seed']
        ]

    with patch('qReduMIS.mis_solver.random.randint', side_effect=seeds):
        yield

@pytest.fixture
def mock_seeds_BMW2023_HP125_outset():
    seeds = [
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_qReduMIS_it0.json", "r"))['seed'], 
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_qReduMIS_it1.json", "r"))['seed'],
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_qReduMIS_it2.json", "r"))['seed'],
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_qReduMIS_it3.json", "r"))['seed'],
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_qReduMIS_it4.json", "r"))['seed'],
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_qReduMIS_it5.json", "r"))['seed'],
    ]

    with patch('qReduMIS.mis_solver.random.randint', side_effect=seeds):
        yield


@pytest.fixture
def mock_quantum_solver_counts_BMW2023_HP125_outset():
    counts_list = [
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_iter0")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_iter1")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_iter2")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_iter3")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_iter4")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP125/outset/results_iter5")))['raw_sols']
           ]
    with patch('qReduMIS.solver.quantum_informer.backend_system.rydberg.rydberg_backend.RydbergAtomBackend.run_experiment', side_effect= counts_list):
        yield


@pytest.fixture
def mock_data_BMW2023_HP1435():
    atom_positions = json.loads(open("tests/mock_data/atoms_BMW2023_HP1435.json").read())
    return atom_positions


@pytest.fixture
def mock_quantum_solver_counts_BMW2023_HP1435_inset():
    counts_list = [
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/results_iter0")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/results_iter1")))['raw_sols'],
           ]
    with patch('qReduMIS.solver.quantum_informer.backend_system.rydberg.rydberg_backend.RydbergAtomBackend.run_experiment', side_effect= counts_list):
        yield


@pytest.fixture
def mock_clean_counts_BM2023_HP1435_inset():
    clean_counts = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/clean_counts_476579.json", "r"))
    return clean_counts


@pytest.fixture
def mock_clean_counts_BM2023_HP1435_outset():
    clean_counts = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/clean_counts_634747.json", "r"))
    return clean_counts


@pytest.fixture
def mock_seeds_BMW2023_HP1435_inset():
    seeds = [
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/results_qReduMIS_it0.json", "r"))['seed'], 
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/results_qReduMIS_it1.json", "r"))['seed'],
        ]

    with patch('qReduMIS.mis_solver.random.randint', side_effect=seeds):
        yield

@pytest.fixture
def mock_quantum_solver_counts_BMW2023_HP1435_outset():
    counts_list = [
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_iter0")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_iter1")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_iter2")))['raw_sols'],
            json.loads(json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_iter3")))['raw_sols'],
           ]
           
    with patch('qReduMIS.solver.quantum_informer.backend_system.rydberg.rydberg_backend.RydbergAtomBackend.run_experiment', side_effect= counts_list):
        yield


@pytest.fixture
def mock_seeds_BMW2023_HP1435_outset():
    seeds = [
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_qReduMIS_it0.json", "r"))['seed'], 
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_qReduMIS_it1.json", "r"))['seed'],
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_qReduMIS_it2.json", "r"))['seed'],
            json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/results_qReduMIS_it3.json", "r"))['seed'],
        ]

    with patch('qReduMIS.mis_solver.random.randint', side_effect=seeds):
        yield


@pytest.fixture
def mock_kernel_graph_inset():
    kernel_data = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/kernel_graph_476579.json", "r"))
    kernel_graph = json_graph.node_link_graph(kernel_data)
    return kernel_graph


@pytest.fixture
def mock_kernel_atoms_inset():
    kernel_atoms = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/kernel_atoms_476579.json", "r"))
    return kernel_atoms


@pytest.fixture
def mock_initial_atom_positions_inset():
    original_atom_positions = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/original_positions_476579.json", "r"))
    return original_atom_positions


@pytest.fixture
def mock_kernel_graph_outset():
    kernel_data = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/kernel_graph_634747.json", "r"))
    kernel_graph = json_graph.node_link_graph(kernel_data)
    return kernel_graph


@pytest.fixture
def mock_kernel_atoms_outset():
    kernel_atoms = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/kernel_atoms_634747.json", "r"))
    return kernel_atoms


@pytest.fixture
def mock_initial_atom_positions_outset():
    original_atom_positions = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/outset/original_positions_634747.json", "r"))
    return original_atom_positions
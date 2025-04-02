import pytest 
import json
from unittest.mock import patch


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

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

def test_quantum_mis(mock_clean_counts_BM2023_HP1435_inset):
    input_atom_positions = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/atom_positions.json",  "r"))
    
    result = quantum_mis(mock_clean_counts_BM2023_HP1435_inset, input_atom_positions, 476579)
    expected_solution = json.load(open("tests/assertions/simulated_results_TN_BMW2023_HP1435/inset/largest_solution_476579.json", "r"))
    
    assert result == expected_solution

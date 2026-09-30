###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import sys

sys.path.append("./")

import pytest
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.base_backend import (
    Backend,
)
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.rydberg.local_simulator import (
    Simulator,
)
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.rydberg.aquila import (
    Aquila,
)
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.backend_generator import (
    BackendFactory,
)


def test_get_backend_local_simulator():
    """
    Test that the BackendFactory returns a Simulator instance for 'Local Simulator' type.
    """
    backend = BackendFactory.get_backend("Local Simulator")
    assert isinstance(backend, Simulator), "Expected a Simulator instance"


def test_get_backend_unknown_type():
    """
    Test that the BackendFactory raises a ValueError for an unknown backend type.
    """
    with pytest.raises(ValueError, match="Unknown backend type: UnknownType"):
        BackendFactory.get_backend("UnknownType")

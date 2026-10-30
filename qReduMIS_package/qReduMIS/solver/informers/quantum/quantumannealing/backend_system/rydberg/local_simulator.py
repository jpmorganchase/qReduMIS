###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
from braket.devices import LocalSimulator
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.rydberg.rydberg_backend import (
    RydbergAtomBackend,
)


class Simulator(RydbergAtomBackend):
    """Local Braket analog-Hamiltonian-simulation (``braket_ahs``) backend."""

    def __init__(self):
        """Set up the local ``braket_ahs`` simulator device."""
        super().__init__()
        self.setup_device()

    def setup_device(self):
        """Instantiate the Braket ``LocalSimulator("braket_ahs")`` device."""
        self.device = LocalSimulator("braket_ahs")
        self.backend_id = "Local Simulator"

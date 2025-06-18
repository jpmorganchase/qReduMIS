###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import sys
import json
from braket.devices import LocalSimulator
from qReduMIS.solver.quantum_informer.backend_system.rydberg.rydberg_backend import (
    RydbergAtomBackend,
)


class Simulator(RydbergAtomBackend):

    def __init__(self):
        super().__init__()
        self.setup_device()

    def setup_device(self):
        self.device = LocalSimulator("braket_ahs")
        self.backend_id = "Local Simulator"

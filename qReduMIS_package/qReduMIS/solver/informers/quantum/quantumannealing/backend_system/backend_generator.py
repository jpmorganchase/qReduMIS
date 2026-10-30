###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.base_backend import (
    Backend,
)
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.rydberg.local_simulator import (
    Simulator,
)
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.rydberg.aquila import (
    Aquila,
)


class BackendFactory:
    """
    Factory Class to create backend instance based on specified type
    """

    @staticmethod
    def get_backend(backend_type: str) -> Backend:
        """
        Method to return backend instance based on specified backend type
        """

        if backend_type == "Local Simulator":
            return Simulator()

        elif backend_type == "Aquila":
            return Aquila()

        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

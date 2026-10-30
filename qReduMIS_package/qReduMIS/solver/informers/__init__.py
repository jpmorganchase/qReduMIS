###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
qReduMIS informers — pluggable node-selection backends.

An *informer* is a component that takes the current reduced kernel graph and
returns information used to pick a frozen node for the next reduction step.

Sub-packages
------------

Quantum informers (:mod:`qReduMIS.solver.informers.quantum`):

  - :mod:`~qReduMIS.solver.informers.quantum.qaoa`
        QAOA (statevector / pytket emulator)
  - :mod:`~qReduMIS.solver.informers.quantum.quantumannealing`
        Quantum annealing on Rydberg-atom backends (Braket, Aquila)

Classical informers (:mod:`qReduMIS.solver.informers.classical`):

  - :mod:`~qReduMIS.solver.informers.classical.sa`
        Simulated annealing (C++ binary)

Shared helpers:

  - :mod:`qReduMIS.solver.informers.corrector_strategies`
"""

from qReduMIS.solver.informers.base import Informer
from qReduMIS.solver.informers.quantum.qaoa import QAOAInformer, QuantumStatevector

__all__ = ["Informer", "QAOAInformer", "QuantumStatevector"]

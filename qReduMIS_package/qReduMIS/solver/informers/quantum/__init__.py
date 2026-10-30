###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
Quantum informers for qReduMIS.

Sub-packages
------------

  - :mod:`qReduMIS.solver.informers.quantum.qaoa`
        QAOA informer on a local Qiskit Aer simulator (``QAOAInformer``).
  - :mod:`qReduMIS.solver.informers.quantum.quantumannealing`
        Quantum-annealing informer on Rydberg-atom backends
        (``QuantumAnnealingInformer``; Braket ``LocalSimulator`` / QuEra Aquila).

Imports are intentionally kept out of this package ``__init__`` so that
``import qReduMIS`` does not pull heavy optional extras (``qiskit-aer``,
``amazon-braket-sdk``).  Import the concrete informer explicitly, e.g.::

    from qReduMIS.solver.informers.quantum.qaoa import QAOAInformer
"""

__all__: list[str] = []

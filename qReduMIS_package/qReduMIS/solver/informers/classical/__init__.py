###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
Classical informers for qReduMIS.

Sub-packages
------------

  - :mod:`qReduMIS.solver.informers.classical.sa`
        Simulated-annealing informer backed by a compiled C++ solver
        (``SAInformer``).
  - :mod:`qReduMIS.solver.informers.classical.exact`
        Exact / baseline informer (``ClassicalSolver``; OR-Tools / NetworkX).

Imports are intentionally kept out of this package ``__init__`` so that
``import qReduMIS`` does not pull heavy optional extras (``ortools``, a C++
compiler toolchain).  Import the concrete informer explicitly, e.g.::

    from qReduMIS.solver.informers.classical.sa import SAInformer
"""

__all__: list[str] = []

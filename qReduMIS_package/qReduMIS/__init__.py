###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
qReduMIS — hybrid classical-quantum solver for the Maximum Independent Set
problem.

Public API
----------

Generic graph-based solver with a pluggable informer:

    from qReduMIS import MISSolver
    from qReduMIS.solver.informers.quantum.qaoa import QAOAInformer
    # or:
    # from qReduMIS.solver.informers.classical.sa import SAInformer

    solver = MISSolver(
        informer=QAOAInformer(selection_strategy="inset", num_shots=1000, p=2),
        top_k_solutions=2,
        max_iteration_limit=10,
    )
    solution, n_iter = solver.solve(G, seed_graph=0, cshot=0)

Additional informers live under :mod:`qReduMIS.solver.informers` (the
``classical`` and ``quantum`` sub-packages).
"""

from qReduMIS.mis_solver import MISSolver

__all__ = ["MISSolver"]

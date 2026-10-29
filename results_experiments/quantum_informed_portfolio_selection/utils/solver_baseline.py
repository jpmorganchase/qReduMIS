###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
solver_baseline — Exact MIS solver using Google OR-Tools
========================================================

Provides the ground-truth Maximum Independent Set (MIS) solution for a
given ``networkx.Graph`` via the SCIP mixed-integer programming backend
in Google OR-Tools.

Used throughout the benchmark to obtain reference solutions against which
QAOA and qReduMIS outputs are compared.

SPDX-License-Identifier: Apache-2.0
"""

from ortools.linear_solver import pywraplp
import numpy as np


def or_tool_solver(graph):
    # Create the solver
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return None

    # Create a variable for each node
    x = {}
    for node in graph.nodes():
        x[node] = solver.IntVar(0, 1, f'x_{node}')

    # Add constraints: for each edge, at most one of its endpoints can be in the independent set
    for u, v in graph.edges():
        solver.Add(x[u] + x[v] <= 1)

    # Objective: maximize the number of nodes in the independent set
    solver.Maximize(solver.Sum(x[node] for node in graph.nodes()))

    # Solve the problem
    status = solver.Solve()

    # Check the result
    if status == pywraplp.Solver.OPTIMAL:
        independent_set = [node for node in graph.nodes() if x[node].solution_value() == 1]
        return independent_set
    else:
        return None
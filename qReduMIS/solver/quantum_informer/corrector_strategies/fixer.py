###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""fixer.py: tools utilized to fix the counts from backend. It can occur that nodes selected do not meet the independence (i.e., no edge between them) requirement and we
fix these counts"""
from typing import List, Tuple, Callable, Dict
from collections import Counter
from qReduMIS.solver.utils.corrector_helper import get_conflicting_edges


def remove_with_check(graph: List[Tuple[int, int]], mis: List[int]) -> List[int]:
    """Add a check whether removal is still necessary
    One of the two nodes may have already been removed by a previous step."""
    fixed = mis[:]  # copy the input for modification
    for a, b in get_conflicting_edges(graph, mis):
        if a in fixed and b in fixed:
            fixed.remove(a)  # only remove one if it's still necessary
    return fixed


def greedy_add(graph: List[Tuple[int, int]], mis: List[int]) -> List[int]:
    """Greedily add nodes to a candidate mis where possible."""
    neighbors = {}
    counts = {}
    # Calculate the degree and number of set neighbors for each node
    for a, b in graph:
        if a not in counts:
            neighbors[a] = []
            counts[a] = {"deg": 0, "set": 0}
        neighbors[a] += [b]
        counts[a]["deg"] += 1
        if b in mis:
            counts[a]["set"] += 1

        if b not in counts:
            neighbors[b] = []
            counts[b] = {"deg": 0, "set": 0}
        neighbors[b] += [a]
        counts[b]["deg"] += 1
        if a in mis:
            counts[b]["set"] += 1
    # candidates are all the ones with 0 neighbors in mis
    # (that are not set them selves)
    candidates = []
    for node, count in counts.items():
        if node in mis:
            continue
        if count["set"] > 0:
            continue
        candidates += [(count["deg"], node)]
    # Iterate them by increasing degree (=greedy)
    for deg, node in sorted(candidates):
        # Check that they are still valid candidates
        # (may have been invalidated by another addition)
        valid = True
        for neighbor in neighbors[node]:
            if neighbor in mis:
                valid = False
                break
        if valid:
            mis += [node]
    return sorted(mis)


def remove_with_check_and_add(
    graph: List[Tuple[int, int]], mis: List[int]
) -> List[int]:
    """Run remove_with_check, then greedily add nodes."""
    mis_r = remove_with_check(graph, mis)
    return greedy_add(graph, mis_r)


def remove_by_participation(graph: List[Tuple[int, int]], mis: List[int]) -> List[int]:
    """Preferentially remove nodes which are in multiple conflicts."""
    fixed = mis[:]  # copy the input for modification
    counter = Counter()
    conflicting = get_conflicting_edges(graph, mis)
    for a, b in conflicting:
        counter[a] += 1
        counter[b] += 1
    for a, b in conflicting:
        if a in fixed and b in fixed:
            if counter[b] > counter[a]:
                fixed.remove(b)
            else:
                fixed.remove(a)
    return fixed


def get_fixup_sol(
    counts: List[Dict[Tuple, int]],
    edges_list: List[Tuple[int, int]],
    strategy: Callable,
) -> List[Dict[str, int]]:
    """given some counts, the edge_list of the problem instance and a fixup method defined in this module,
    it returns the fixed counts"""

    list_fixed_sols = []

    for dict_solution in counts:
        possible_mis = list(dict_solution["nodes"])
        count = dict_solution["count"]
        fixed_sol = {}
        sol = strategy(edges_list, possible_mis)
        fixed_sol["nodes"] = sol
        fixed_sol["count"] = count
        list_fixed_sols.append(fixed_sol)

    return list_fixed_sols

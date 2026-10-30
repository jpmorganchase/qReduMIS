###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

from typing import List, Tuple, Callable, Dict
from collections import Counter
from qReduMIS.solver.utils.corrector_helper import get_conflicting_edges


def remove_first(graph: list[tuple[int, int]], mis: list[int]) -> list[int]:
    """Resolve by removing the first node in each conflicting edge."""
    fixed = mis[:]  # copy the input for modification
    for a, _ in get_conflicting_edges(graph, mis):
        if a in fixed:
            fixed.remove(a)  # we could also pick a random one
    return fixed


def remove_with_check(graph: List[Tuple[int, int]], mis: List[int]) -> List[int]:
    """
    Removes nodes from a maximum independent set (MIS) if they are part of a conflict, ensuring removal is still necessary.

    Args:
        graph (List[Tuple[int, int]]): The graph represented as a list of edges.
        mis (List[int]): The current maximal independent set.

    Returns:
        List[int]: The corrected maximal independent set.
    """
    fixed = mis[:]  # Copy the input for modification
    for a, b in get_conflicting_edges(graph, mis):
        if a in fixed and b in fixed:
            fixed.remove(a)  # Only remove one if it's still necessary
    return fixed


def greedy_add(graph: List[Tuple[int, int]], mis: List[int]) -> List[int]:
    """
    Greedily adds nodes to a candidate MIS where possible.

    Args:
        graph (List[Tuple[int, int]]): The graph represented as a list of edges.
        mis (List[int]): The current maximal independent set.

    Returns:
        List[int]: The expanded maximal independent set.
    """
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
    # Candidates are all the ones with 0 neighbors in MIS
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
    """
    Runs remove_with_check, then greedily adds nodes.

    Args:
        graph (List[Tuple[int, int]]): The graph represented as a list of edges.
        mis (List[int]): The current maximal independent set.

    Returns:
        List[int]: The corrected and expanded maximal independent set.
    """
    mis_r = remove_with_check(graph, mis)
    return greedy_add(graph, mis_r)


def remove_by_participation(graph: List[Tuple[int, int]], mis: List[int]) -> List[int]:
    """
    Preferentially removes nodes which are in multiple conflicts.

    Args:
        graph (List[Tuple[int, int]]): The graph represented as a list of edges.
        mis (List[int]): The current maximal independent set.

    Returns:
        List[int]: The corrected maximal independent set.
    """
    fixed = mis[:]  # Copy the input for modification
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


FIXUP_STRATEGIES = {
    "remove_first": remove_first,
    "remove_with_check": remove_with_check,
    "remove_by_participation": remove_by_participation,
    "greedy_add": greedy_add,
    "remove_with_check_and_add": remove_with_check_and_add,
}


def resolve_fixup_strategy(name: str) -> Callable:
    """Return the fixup strategy function for the given *name*.

    Raises ``ValueError`` with a helpful message when the name is unknown.
    """
    try:
        return FIXUP_STRATEGIES[name]
    except KeyError:
        valid = ", ".join(sorted(FIXUP_STRATEGIES))
        raise ValueError(f"Unknown fixup strategy '{name}'. Valid choices: {valid}")


def get_fixup_sol(
    counts: List[Dict[Tuple, int]],
    edges_list: List[Tuple[int, int]],
    strategy: Callable,
) -> List[Dict[str, int]]:
    """
    Given some counts, the edge list of the problem instance, and a fixup method, returns the fixed counts.

    Args:
        counts (List[Dict[Tuple, int]]): The input counts from the quantum backend.
        edges_list (List[Tuple[int, int]]): The edge list of the graph.
        strategy (Callable): The fixup method to apply.

    Returns:
        List[Dict[str, int]]: The fixed solutions.
    """
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

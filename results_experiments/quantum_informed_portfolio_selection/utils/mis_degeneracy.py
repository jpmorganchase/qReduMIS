###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
mis_degeneracy.py
=================
Count the number of independent sets (IS) of a given size in a graph.

Used by the hardness notebooks to compute the degeneracy of the MIS and of
the first sub-optimal solution (MIS − 1)::

    from utils.mis_degeneracy import analyze_graph
    info = analyze_graph(G, mis_size)   # {"deg_mis": ..., "deg_mis_minus_1": ...}
"""

from __future__ import annotations

import time

import networkx as nx


# ── Core algorithm ────────────────────────────────────────────────────────

def count_independent_sets(G: nx.Graph, target_size: int) -> int:
    """Count **all** independent sets of exactly *target_size* in *G*.

    Uses depth-limited backtracking with adjacency-based pruning.
    The candidate list is sorted by degree (highest first) so that the
    search tree is pruned as early as possible.

    Parameters
    ----------
    G : nx.Graph
        Undirected graph (self-loops are ignored).
    target_size : int
        Exact size of the independent sets to count.

    Returns
    -------
    int
        Number of distinct IS of size *target_size*.
    """
    if target_size <= 0:
        return 1 if target_size == 0 else 0

    nodes = sorted(G.nodes(), key=lambda v: G.degree(v), reverse=True)
    adj = {v: set(G.neighbors(v)) for v in nodes}
    count = 0

    def _backtrack(candidates: list, depth: int) -> None:
        nonlocal count
        if depth == target_size:
            count += 1
            return
        remaining_needed = target_size - depth
        for i, v in enumerate(candidates):
            # Prune: not enough candidates left
            if len(candidates) - i < remaining_needed:
                return
            # New candidates: everything after v that is NOT adjacent to v
            new_candidates = [u for u in candidates[i + 1:] if u not in adj[v]]
            _backtrack(new_candidates, depth + 1)

    _backtrack(nodes, 0)
    return count


def analyze_graph(
    G: nx.Graph,
    mis_size: int,
    *,
    compute_mis_minus_1: bool = True,
) -> dict:
    """Return degeneracy counts for MIS and (optionally) MIS − 1.

    Parameters
    ----------
    G : nx.Graph
    mis_size : int
        Known MIS size for this graph.
    compute_mis_minus_1 : bool
        If *True* (default), also count IS of size ``mis_size - 1``.

    Returns
    -------
    dict with keys:
        N, n_edges, mis_size, deg_mis, deg_mis_minus_1 (or None),
        time_mis_s, time_mis_minus_1_s
    """
    N = G.number_of_nodes()
    E = G.number_of_edges()

    t0 = time.perf_counter()
    deg_mis = count_independent_sets(G, mis_size)
    t_mis = time.perf_counter() - t0

    deg_sub = None
    t_sub = 0.0
    if compute_mis_minus_1 and mis_size >= 2:
        t1 = time.perf_counter()
        deg_sub = count_independent_sets(G, mis_size - 1)
        t_sub = time.perf_counter() - t1

    return {
        "N": N,
        "n_edges": E,
        "mis_size": mis_size,
        "deg_mis": deg_mis,
        "deg_mis_minus_1": deg_sub,
        "time_mis_s": round(t_mis, 3),
        "time_mis_minus_1_s": round(t_sub, 3),
    }

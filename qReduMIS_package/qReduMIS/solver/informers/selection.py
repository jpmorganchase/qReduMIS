###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
Shared node-selection logic for qReduMIS informers.

Every informer (QAOA, simulated annealing, exact, quantum annealing) produces
the *same* intermediate representation of candidate solutions — a list of
``clean_counts`` dicts of the form::

    [{"nodes": [n0, n1, ...], "count": c}, ...]

Given that representation, the *selection* step (deciding which node(s) to
freeze into the solution and which to remove from the kernel) is identical
regardless of how the counts were obtained.  Historically this logic was
copy-pasted into each informer sub-package; it now lives here so all informers
share a single, tested implementation.

Two intermediate representations are supported, differing only in *what* they
return:

- **index-based** (``*_nodes`` functions) — used by the graph-native informers
  (QAOA, simulated annealing, exact).  Selection is expressed as integer node
  ids of the relabelled ``0..N-1`` kernel graph.
- **positions-based** (``*_positions`` functions) — used by the Rydberg-atom
  quantum-annealing path (``QuantumAnnealingInformer``), which tracks atoms by
  their ``(x, y)`` coordinates.  These are thin adapters that delegate the actual
  decision to the index-based functions and then map node ids back to atom
  positions.

Public API
----------
- :func:`get_inset_nodes`   — nodes most likely to be *in* the MIS.
- :func:`get_outset_nodes`  — nodes most likely to be *out* of the MIS.
- :func:`find_maximum_independent_set` — largest IS across all candidates (indices).
- :func:`select_frozen_nodes` — pick ``(selected_in, selected_out, to_remove)`` (indices).
- :func:`find_maximum_independent_set_positions` — largest IS mapped to atom positions.
- :func:`select_frozen_positions` — ``select_frozen_nodes`` mapped to atom positions.
"""
from __future__ import annotations

import logging
import random
from collections import Counter
from typing import Dict, List, Tuple, Union

import networkx as nx

from qReduMIS.solver.utils.graph_helper import construct_graph_from_atom_positions

logger = logging.getLogger(__name__)


def _node_frequencies(clean_counts: List[dict], k_size: int) -> Dict[int, int]:
    """Weighted occurrence of each node across the top-``k_size`` solution sizes.

    Parameters
    ----------
    clean_counts : list of dict
        Candidate solutions, each ``{"nodes": [...], "count": c}``.
    k_size : int
        Number of distinct (largest) solution sizes to consider.

    Returns
    -------
    dict
        ``{node: total_count}`` restricted to solutions whose size is among the
        top-``k_size`` sizes.
    """
    solution_sizes = sorted({len(sol["nodes"]) for sol in clean_counts}, reverse=True)
    sizes_to_consider = set(solution_sizes[:k_size])

    freq: Dict[int, int] = {}
    for sol in clean_counts:
        if len(sol["nodes"]) in sizes_to_consider:
            weight = sol.get("count", 1)
            for node in sol["nodes"]:
                freq[node] = freq.get(node, 0) + weight
    return freq


def get_inset_nodes(
    clean_counts: List[dict], k_size: int = 2, num_select: int = 4
) -> List[int]:
    """Return the ``num_select`` nodes appearing most often in top solutions.

    These are the nodes with the highest probability of belonging to the MIS.
    """
    freq = _node_frequencies(clean_counts, k_size)
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [node for node, _ in ranked[:num_select]]


def get_outset_nodes(
    clean_counts: List[dict],
    num_nodes: int,
    num_select: int,
    k_size: int = 2,
) -> List[int]:
    """Return ``num_select`` nodes least likely to belong to the MIS.

    Nodes that never appear in a candidate solution come first; if more are
    needed, the lowest-frequency observed nodes are appended.

    Parameters
    ----------
    clean_counts : list of dict
        Candidate solutions.
    num_nodes : int
        Total number of nodes in the (relabelled 0..N-1) kernel graph.
    num_select : int
        Number of nodes to return.
    k_size : int
        Number of distinct (largest) solution sizes to consider.
    """
    counter = Counter(_node_frequencies(clean_counts, k_size))
    observed = set(counter.keys())
    nodes_out = [n for n in range(num_nodes) if n not in observed]

    if len(nodes_out) >= num_select:
        return nodes_out[:num_select]

    remaining = num_select - len(nodes_out)
    lowest_probability = [node for node, _ in counter.most_common()[::-1][:remaining]]
    nodes_out.extend(lowest_probability)
    return nodes_out


def find_maximum_independent_set(clean_counts: List[dict], seed: int) -> List[int]:
    """Return the nodes of the largest independent set across all candidates.

    Ties (multiple solutions of the same maximum size) are broken randomly
    using ``seed`` for reproducibility.
    """
    random.seed(seed)
    largest_size = max(len(sol["nodes"]) for sol in clean_counts)
    solutions = [
        sol["nodes"] for sol in clean_counts if len(sol["nodes"]) == largest_size
    ]
    return random.choice(solutions)


def select_frozen_nodes(
    clean_counts: List[dict],
    kernel_graph: nx.Graph,
    seed: int,
    strategy: str = "inset",
    k_size: int = 2,
    num_nodes_frac: float = 0.4,
) -> Tuple[List[int], List[int], List[int]]:
    """Pick nodes to freeze/remove for the next classical reduction.

    Parameters
    ----------
    clean_counts : list of dict
        Candidate solutions from an informer.
    kernel_graph : nx.Graph
        The current kernel graph (node labels are used directly).
    seed : int
        RNG seed for reproducible tie-breaking.
    strategy : {"inset", "outset"}
        - ``"inset"``: freeze a high-probability node into the MIS and remove it
          together with all its neighbours from the kernel.
        - ``"outset"``: remove a single low-probability node from the kernel
          (it is excluded from the MIS).
    k_size : int
        Number of distinct (largest) solution sizes to consider.
    num_nodes_frac : float
        Fraction of kernel nodes forming the candidate pool to sample from.

    Returns
    -------
    (selected_in, selected_out, to_remove) : tuple of list
        Nodes frozen into the MIS, nodes excluded from the MIS, and all nodes
        to remove from the kernel for the next iteration.
    """
    random.seed(seed)
    num_kernel_nodes = kernel_graph.number_of_nodes()
    # ``num_select`` follows the original qReduMIS heuristic: it is a fraction of
    # the number of *distinct nodes observed* across the top-``k_size`` solution
    # sizes (not the total kernel size), keeping the candidate pool tied to what
    # the informer actually sampled.
    num_observed = len(_node_frequencies(clean_counts, k_size))
    num_select = max(1, int(num_nodes_frac * num_observed))

    if strategy == "inset":
        top_nodes = get_inset_nodes(clean_counts, k_size=k_size, num_select=num_select)
        if not top_nodes:
            return [], [], []
        node = random.choice(top_nodes)
        to_remove = [node] + list(kernel_graph.neighbors(node))
        return [node], [], to_remove

    if strategy == "outset":
        nodes_out = get_outset_nodes(
            clean_counts, num_kernel_nodes, num_select, k_size=k_size
        )
        if not nodes_out:
            return [], [], []
        node = random.choice(nodes_out)
        return [], [node], [node]

    raise NotImplementedError(f"Unknown selection strategy: {strategy!r}")


# ---------------------------------------------------------------------------
# Positions-based adapters (Rydberg-atom / quantum-annealing path)
# ---------------------------------------------------------------------------
# The functions below share every bit of decision logic with their index-based
# counterparts above; they only translate the resulting node ids into the atom
# ``(x, y)`` positions expected by the positions-based quantum-annealing informer.


def find_maximum_independent_set_positions(
    clean_counts: List[Dict[str, Union[List[int], str, int]]],
    atom_positions: List[Tuple[float, float]],
    seed: int,
    version: str = "semi-greedy",
) -> List[Tuple[float, float]]:
    """Largest independent set across all candidates, mapped to atom positions.

    Delegates to :func:`find_maximum_independent_set` and maps the returned node
    indices onto ``atom_positions``.

    Parameters
    ----------
    clean_counts : list of dict
        Processed results from the quantum backend.
    atom_positions : list of (float, float)
        Atom positions in the kernel (index-aligned with the ``0..N-1`` node ids).
    seed : int
        Random seed for reproducible tie-breaking.
    version : str
        Kept for API compatibility; unused.

    Returns
    -------
    list of (float, float)
        Atom positions belonging to the selected maximum independent set.
    """
    nodes = find_maximum_independent_set(clean_counts, seed)
    return [atom_positions[i] for i in nodes]


def select_frozen_positions(
    clean_counts: List[Dict[str, Union[List[int], str, int]]],
    atom_positions: List[Tuple[float, float]],
    kernel_graph: nx.Graph,
    original_positions: List[Tuple[float, float]],
    seed: int,
    k_size: int = 2,
    num_nodes_frac: float = 0.4,
    selection_algo: str = "outset",
    version: str = "semi-greedy",
) -> Tuple[
    List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]
]:
    """Positions-based counterpart of :func:`select_frozen_nodes`.

    The node selection itself is delegated to :func:`select_frozen_nodes`; the
    resulting node indices are then mapped back to atom positions.

    Parameters
    ----------
    clean_counts : list of dict
        Processed results from the quantum backend.
    atom_positions : list of (float, float)
        Atom positions in the kernel (index-aligned with the relabelled
        ``kernel_graph`` node ids).
    kernel_graph : nx.Graph
        Reduced graph (kernel).  Its original labels need not be index-aligned
        with ``clean_counts``; a 0-indexed graph is rebuilt from
        ``atom_positions`` so the shared logic operates in the counts' index
        space.
    original_positions : list of (float, float)
        Original list of atom positions (kept for API compatibility).
    seed : int
        Seed for reproducibility.
    k_size : int
        Number of largest solution sizes to consider.
    num_nodes_frac : float
        Fraction of nodes forming the candidate pool.
    selection_algo : {"outset", "inset"}
        Selection strategy.
    version : str
        Kept for API compatibility; unused.

    Returns
    -------
    (selected_in_positions, selected_out_positions, to_remove_positions)
        Selection result expressed as atom positions.
    """
    if len(clean_counts) == 0 or len(atom_positions) == 0:
        logger.warning("Empty input provided to select_frozen_positions")
        return [], [], []

    # The positions-based path indexes candidate solutions by their position in
    # ``atom_positions`` (0..N-1).  The kernel graph handed in by the
    # positions-based quantum-annealing path keeps the *original* node labels,
    # which are not index-aligned with ``clean_counts``.  Rebuild a 0-indexed kernel graph from
    # the atom positions so the shared selection logic operates in the same index
    # space as the counts (the graph-based ``MISSolver`` relabels the kernel to
    # 0..N-1 for exactly the same reason).
    indexed_kernel_graph = construct_graph_from_atom_positions(atom_positions)

    selected_in, selected_out, to_remove = select_frozen_nodes(
        clean_counts,
        indexed_kernel_graph,
        seed,
        strategy=selection_algo,
        k_size=k_size,
        num_nodes_frac=num_nodes_frac,
    )

    # The shared "inset" selection only freezes the chosen node and folds its
    # neighbours into ``to_remove`` (the graph-based solver tracks removals via
    # ``to_remove``).  The positions-based solver instead records excluded nodes
    # through ``selected_out``; restore the neighbours there so its bookkeeping
    # (and the historical assertions) stay consistent.
    if selection_algo == "inset":
        selected_out = [n for n in to_remove if n not in selected_in]

    def _to_positions(indices: List[int]) -> List[Tuple[float, float]]:
        """Map a list of node indices to their ``(x, y)`` atom positions."""
        return [atom_positions[i] for i in indices]

    return (
        _to_positions(selected_in),
        _to_positions(selected_out),
        _to_positions(to_remove),
    )

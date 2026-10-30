###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

"""
SA-based informer for qReduMIS.

This module wraps the C++ simulated-annealing MIS solver (``sa_solver``)
and exposes the same interface used by the quantum informer so it can be
used as a drop-in replacement inside the qReduMIS loop.

Key responsibilities:
  1. Convert a NetworkX graph to METIS format.
  2. Call the ``sa_solver`` binary and parse the JSON output.
  3. Aggregate replica solutions into the ``clean_counts`` format
     (list of ``{"nodes": [...], "count": N}`` dicts).
  4. Provide ``find_maximum_independent_set`` and ``select_nodes``
     with the same semantics as the quantum emulator.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import networkx as nx

from qReduMIS.solver.informers.corrector_strategies.fixer import (
    get_fixup_sol,
    remove_first,
)
from qReduMIS.solver.informers.selection import (
    find_maximum_independent_set,
    select_frozen_nodes,
)

# ═══════════════════════════════════════════════════════════════════════════
# METIS I/O
# ═══════════════════════════════════════════════════════════════════════════


def write_metis(G: nx.Graph, filename: str) -> None:
    """Write a NetworkX graph to METIS 4.0 format (1-indexed adjacency list).

    Parameters
    ----------
    G : nx.Graph
        The graph to write.  Node labels are assumed to be integers
        ``0 … N-1`` (if not, the graph is relabeled internally).
    filename : str
        Output file path.
    """
    # Ensure nodes are 0-indexed integers
    nodes = sorted(G.nodes())
    mapping = {n: i for i, n in enumerate(nodes)}
    H = nx.relabel_nodes(G, mapping)

    num_vertices = H.number_of_nodes()
    num_edges = H.number_of_edges()

    with open(filename, "w") as f:
        f.write(f"{num_vertices} {num_edges}\n")
        for node in range(num_vertices):
            neighbors = sorted([nbr + 1 for nbr in H.neighbors(node)])  # 1-indexed
            f.write(" ".join(map(str, neighbors)) + "\n")


def read_metis(filename: str) -> nx.Graph:
    """Read a METIS 4.0 file and return a 0-indexed NetworkX graph."""
    G = nx.Graph()
    with open(filename) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("%")]
    header = lines[0].split()
    n_nodes = int(header[0])
    G.add_nodes_from(range(n_nodes))
    for i, line in enumerate(lines[1:]):
        for nbr_str in line.split():
            nbr = int(nbr_str) - 1  # convert 1-indexed → 0-indexed
            if nbr > i:
                G.add_edge(i, nbr)
    return G


# ═══════════════════════════════════════════════════════════════════════════
# SA binary wrapper
# ═══════════════════════════════════════════════════════════════════════════

# Default location: the compiled binary lives in the sibling ``_cpp`` folder
# alongside the C++ source and Makefile.
_SA_BINARY = str(Path(__file__).resolve().parent / "_cpp" / "sa_solver")


def run_sa(
    metis_file: str,
    replicas: int = 10_000,
    steps: int = 32,
    b_min: float = 10.0,
    b_max: float = 5000.0,
    seed: int = 0,
    sa_binary: str = _SA_BINARY,
) -> dict:
    """Run the SA solver binary and return parsed JSON output.

    Returns
    -------
    dict
        ``{"solutions": [{"nodes": [...], "size": N}, ...], "best_size": N}``
    """
    if not os.path.isfile(sa_binary):
        raise FileNotFoundError(
            f"SA binary not found at {sa_binary}.  "
            "Please compile sa_solver.cc first (see the SA README.md in this folder)."
        )

    cmd = [
        sa_binary,
        metis_file,
        str(replicas),
        str(steps),
        str(b_min),
        str(b_max),
        str(seed),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(
            f"SA solver failed (rc={result.returncode}):\n{result.stderr}"
        )
    return json.loads(result.stdout)


def sa_solutions_to_clean_counts(
    sa_output: dict,
    reversed_mapping: Dict[int, int],
) -> List[dict]:
    """Convert SA solver JSON output to ``clean_counts`` format.

    Each unique solution (set of nodes) is aggregated with a count of how
    many replicas found it.  Node indices are mapped back to the original
    graph labels via *reversed_mapping* (key = SA 0-index, value = original
    graph label).

    Parameters
    ----------
    sa_output : dict
        Parsed JSON from ``run_sa()``.
    reversed_mapping : dict
        ``{sa_node_id: original_node_label}``.

    Returns
    -------
    list of dict
        ``[{"nodes": (orig_label, ...), "count": N}, ...]``
    """
    counter: Dict[tuple, int] = {}
    for sol in sa_output["solutions"]:
        # Map SA 0-indexed nodes → original node labels
        mapped = tuple(sorted(reversed_mapping[n] for n in sol["nodes"]))
        counter[mapped] = counter.get(mapped, 0) + 1

    return [{"nodes": list(nodes), "count": cnt} for nodes, cnt in counter.items()]


# ═══════════════════════════════════════════════════════════════════════════
# SAInformer class — drop-in replacement for QuantumStatevector
# ═══════════════════════════════════════════════════════════════════════════


class SAInformer:
    """SA-based informer that mirrors the ``QuantumStatevector`` interface.

    Parameters
    ----------
    selection_strategy : str
        Node selection strategy (``"inset"`` supported).
    replicas : int
        Number of SA replicas per call.
    steps : int
        Number of annealing sweeps per replica.
    b_min : float
        Starting inverse temperature.
    b_max : float
        Final inverse temperature.
    sa_binary : str or None
        Path to the compiled ``sa_solver`` binary.  Defaults to the binary
        located next to this Python file.
    """

    def __init__(
        self,
        selection_strategy: str = "inset",
        replicas: int = 10_000,
        steps: int = 32,
        b_min: float = 10.0,
        b_max: float = 5000.0,
        sa_binary: Optional[str] = None,
    ):
        """Store the SA hyperparameters and binary path (see class docstring)."""
        self.selection_strategy = selection_strategy
        self.replicas = replicas
        self.steps = steps
        self.b_min = b_min
        self.b_max = b_max
        self.sa_binary = sa_binary or _SA_BINARY
        self.clean_counts = None

    def get_clean_counts(
        self,
        K: nx.Graph,
        N: int,
        reversed_mapping: Dict[int, int],
        seed_graph: int,
        cshot: int,
        current_iteration: int,
        name_store: str = None,
        folder_storing: str = None,
        **kwargs,
    ) -> List[dict]:
        """Run SA on the kernel graph and return clean_counts.

        Parameters
        ----------
        K : nx.Graph
            The kernel graph (0-indexed after relabeling).
        N : int
            Number of nodes in K.
        reversed_mapping : dict
            ``{K_node_id: original_node_label}``
        seed_graph : int
            Seed identifier (for tracking / reproducibility).
        cshot : int
            Classical shot index (used as part of the SA seed).
        current_iteration : int
            Current qReduMIS iteration.

        Returns
        -------
        list of dict
            ``[{"nodes": [...], "count": N}, ...]``
        """
        # Write kernel to temp METIS file
        with tempfile.NamedTemporaryFile(
            suffix=".metis", mode="w", delete=False
        ) as tmp:
            tmp_path = tmp.name
        try:
            write_metis(K, tmp_path)
            sa_seed = abs(hash((seed_graph, cshot, current_iteration))) % (2**31)
            sa_output = run_sa(
                tmp_path,
                replicas=self.replicas,
                steps=self.steps,
                b_min=self.b_min,
                b_max=self.b_max,
                seed=sa_seed,
                sa_binary=self.sa_binary,
            )
        finally:
            os.unlink(tmp_path)

        clean_counts = sa_solutions_to_clean_counts(sa_output, reversed_mapping)

        # Safety check: fix any IS violations (the C++ solver should
        # produce valid independent sets, but we apply the same fixup
        # used in the quantum pipeline to be safe).
        mapped_edges = [
            (reversed_mapping[u], reversed_mapping[v]) for u, v in K.edges()
        ]
        clean_counts = get_fixup_sol(clean_counts, mapped_edges, remove_first)

        self.clean_counts = clean_counts

        # Optionally store results
        if folder_storing is not None:
            folder_name_sub = f"{folder_storing}/intermediate_iterations/"
            os.makedirs(folder_name_sub, exist_ok=True)
            out_file = (
                f"{folder_name_sub}/sa_counts_it{current_iteration}"
                f"_N{N}_seed{seed_graph}_cshot{cshot}.json"
            )
            with open(out_file, "w") as f:
                json.dump(clean_counts, f, indent=2)

        return clean_counts

    def find_maximum_independent_set(
        self,
        clean_counts: List[dict],
        seed: int,
    ) -> list:
        """Return the nodes of the largest IS found across all SA replicas.

        If multiple solutions share the same maximum size, one is chosen
        at random (seeded by *seed*).
        """
        return find_maximum_independent_set(clean_counts, seed)

    def select_nodes(
        self,
        clean_counts: List[dict],
        kernel_graph: nx.Graph,
        seed: int,
        k_size: int = 2,
        num_nodes_frac: float = 0.4,
    ) -> Tuple[list, list, list]:
        """Select nodes to freeze / remove based on SA solution frequencies.

        Uses the *inset* strategy: pick the most-frequently-appearing node
        across top-k solutions, freeze it into the IS, and remove it together
        with its neighbors from the kernel.

        Returns
        -------
        selected_in : list
            Nodes selected into the IS.
        selected_out : list
            (empty for inset strategy)
        to_remove : list
            Nodes to remove from the kernel (selected + its neighbors).
        """
        return select_frozen_nodes(
            clean_counts,
            kernel_graph,
            seed,
            strategy=self.selection_strategy,
            k_size=k_size,
            num_nodes_frac=num_nodes_frac,
        )

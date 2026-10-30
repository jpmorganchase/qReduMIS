###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
Unified graph-based qReduMIS solver.

This is the canonical implementation.  It accepts any object implementing the
:class:`Informer` interface so the choice of quantum / classical backend is
decoupled from the reduction loop.

Earlier releases shipped one solver class per backend (QAOA statevector, QAOA
via an external emulator, simulated annealing, Rydberg atoms).  Those variants
have been unified into this single class; pick a backend by passing the
corresponding informer instead.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import List, Optional, Set, Tuple

import networkx as nx
import numpy as np

from qReduMIS.solver.classical_reducer.reducer import Reducer
from qReduMIS.solver.informers.base import Informer
from qReduMIS.solver.utils.graph_helper import get_reduction_factor


class MISSolver:
    """
    Implements the qReduMIS algorithm on a NetworkX graph using a pluggable
    *informer* (QAOA, SA, …).

    Parameters
    ----------
    informer : Informer
        Concrete informer implementation (QAOAInformer, SAInformer, …).
    top_k_solutions : int, default 2
        Number of top solution sizes considered for frozen-node selection.
    max_iteration_limit : int, default 10
        Hard cap on the number of qReduMIS iterations.
    """

    def __init__(
        self,
        informer: Informer,
        top_k_solutions: int = 2,
        max_iteration_limit: int = 10,
    ):
        self.informer = informer
        self.top_k_solutions = top_k_solutions
        self.max_iteration_limit = max_iteration_limit

        self.classical_reducer = Reducer(verbose=False)

        # Solution sets — re-initialised in every solve() call.
        self.S: Set = set()  # Selected (frozen) nodes
        self.W: Set = set()  # Incumbent solution
        self.R: Set = set()  # Removed nodes
        self.initial_size: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def solve(
        self,
        G: nx.Graph,
        seed_graph: int,
        cshot: int,
        folder_storing: Optional[str] = None,
        name_store: Optional[str] = None,
        top_sample: int = 0,
        three_regular: bool = False,
    ) -> Tuple[set, int]:
        """
        Run qReduMIS on *G*.

        Parameters
        ----------
        G : nx.Graph
            Problem graph.
        seed_graph : int
            Seed identifier (used by informers for reproducibility and by the
            storing layer for file naming).
        cshot : int
            Classical shot index — used as RNG seed for tie-breaking inside the
            informer and as part of stored-file names.
        folder_storing : str or None
            Output folder for per-iteration JSON diagnostics.  ``None`` disables
            storing.
        name_store : str or None
            Optional file-name prefix when storing.
        top_sample : int, default 0
            For QAOA: pick from the 1st/2nd/3rd most-probable solutions
            (accumulative).  0 means use all bitstrings.  Ignored by SA.
        three_regular : bool, default False
            For QAOA on 3-regular graphs: enables 3-regular-specific tuning.
            Ignored by SA.

        Returns
        -------
        solution : set
            Best independent set found.
        iterations : int
            Number of qReduMIS iterations executed.
        """
        # Reset state — solver instances may be reused across instances.
        self.S, self.W, self.R = set(), set(), set()
        self.initial_size = len(G.nodes())

        # The classical reducer mutates the graph it is given in place; operate
        # on a private copy so the caller's graph is left untouched (important
        # for post-hoc visualisation / verification).
        G = deepcopy(G)

        return self._solve_problem(
            G,
            seed_graph,
            cshot,
            folder_storing=folder_storing,
            name_store=name_store,
            top_sample=top_sample,
            three_regular=three_regular,
        )

    # ------------------------------------------------------------------
    # Recursive driver
    # ------------------------------------------------------------------
    def _solve_problem(
        self,
        G: nx.Graph,
        seed_graph: int,
        cshot: int,
        folder_storing: Optional[str] = None,
        current_iteration: int = 0,
        name_store: Optional[str] = None,
        top_sample: int = 0,
        three_regular: bool = False,
    ) -> Tuple[set, int]:
        if current_iteration == self.max_iteration_limit:
            return self.W, current_iteration

        if not G or len(G.nodes()) == 0:
            return self.W, current_iteration

        orig_graph = deepcopy(G)

        # ── Classical reduction ─────────────────────────────────────────
        K, r, s = self.classical_reducer.reduce(G)
        self.S.update(s)
        self.R.update(r)
        reduction_factor = get_reduction_factor(orig_graph, K)

        if reduction_factor == 1:  # Fully reducible
            if len(self.S) > len(self.W):
                self.W = self.S.copy()
            if folder_storing is not None:
                self._store_iteration(
                    folder_storing,
                    current_iteration,
                    seed_graph,
                    cshot,
                    orig_graph,
                    K,
                    s,
                    r,
                    reduction_factor,
                    top_sample=top_sample,
                    fully_reducible=True,
                )
            return self.W, current_iteration

        print(
            f"  - {datetime.now():%Y-%m-%d %H:%M:%S} Classical reduction: "
            f"{np.round(reduction_factor * 100, 2)}% — kernel has "
            f"{len(K.nodes())} nodes → running informer "
            f"({type(self.informer).__name__})"
        )

        # ── Relabel kernel to 0..N-1 for the informer ───────────────────
        mapping = {old: new for new, old in enumerate(K.nodes())}
        reversed_mapping = {v: k for k, v in mapping.items()}
        K_mapped = nx.relabel_nodes(K, mapping)

        # ── Informer call ───────────────────────────────────────────────
        clean_counts = self.informer.get_clean_counts(
            K_mapped,
            len(K_mapped.nodes()),
            reversed_mapping,
            seed_graph,
            cshot,
            current_iteration,
            name_store=name_store,
            folder_storing=folder_storing,
            top_sample=top_sample,
            three_regular=three_regular,
        )

        # ── Track incumbent ─────────────────────────────────────────────
        I = self.informer.find_maximum_independent_set(clean_counts, cshot)
        if len(self.S) + len(I) > len(self.W):
            self.W = self.S.union(I)

        # ── Pick frozen nodes ───────────────────────────────────────────
        selected_in, selected_out, to_remove = self.informer.select_nodes(
            clean_counts,
            K,
            cshot,
            k_size=self.top_k_solutions,
        )
        self.R.update(to_remove)
        self.S.update(selected_in)

        # ── Build next kernel ───────────────────────────────────────────
        K_new = deepcopy(K)
        K_new.remove_nodes_from(to_remove)

        if folder_storing is not None:
            self._store_iteration(
                folder_storing,
                current_iteration,
                seed_graph,
                cshot,
                orig_graph,
                K,
                s,
                r,
                reduction_factor,
                top_sample=top_sample,
                selected_in=selected_in,
                to_remove=to_remove,
                I=I,
                K_new=K_new,
            )

        if len(K.nodes()) > 0:
            quantum_rf = (len(K.nodes()) - len(K_new.nodes())) / len(K.nodes())
            print(
                f"  - {datetime.now():%Y-%m-%d %H:%M:%S} Informer reduced "
                f"the kernel by {np.round(quantum_rf * 100, 2)}%"
            )

        return self._solve_problem(
            K_new,
            seed_graph,
            cshot,
            folder_storing=folder_storing,
            current_iteration=current_iteration + 1,
            name_store=name_store,
            top_sample=top_sample,
            three_regular=three_regular,
        )

    # ------------------------------------------------------------------
    # Storage helper
    # ------------------------------------------------------------------
    def _store_iteration(
        self,
        folder_storing: str,
        iteration: int,
        seed_graph: int,
        cshot: int,
        orig_graph: nx.Graph,
        K: nx.Graph,
        s: List,
        r: List,
        reduction_factor: float,
        top_sample: int = 0,
        fully_reducible: bool = False,
        selected_in: Optional[List] = None,
        to_remove: Optional[List] = None,
        I: Optional[List] = None,
        K_new: Optional[nx.Graph] = None,
    ) -> None:
        info = {
            "iteration": iteration,
            "input": list(orig_graph.nodes()),
            "classical reduction factor": reduction_factor,
            "classical kernel": list(K.nodes()),
            "classical selected": list(s),
            "classical removed": list(r),
            "S": list(self.S),
            "W": list(self.W),
            "R": list(self.R),
        }
        if not fully_reducible:
            info["quantum selected"] = list(selected_in or [])
            info["quantum removed"] = list(to_remove or [])
            info["quantum best sol"] = list(I or [])
            info["quantum kernel"] = list(K_new.nodes()) if K_new is not None else []
            info["cshot"] = cshot

        folder_name_sub = os.path.join(folder_storing, "intermediate_iterations")
        os.makedirs(folder_name_sub, exist_ok=True)
        fname = os.path.join(
            folder_name_sub,
            f"info_{iteration}_N{self.initial_size}"
            f"_seed{seed_graph}_cshot{cshot}_top{top_sample}.json",
        )
        with open(fname, "w") as f:
            json.dump(info, f)

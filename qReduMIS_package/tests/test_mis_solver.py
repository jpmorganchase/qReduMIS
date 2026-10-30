###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
Tests for the unified graph-based :class:`qReduMIS.mis_solver.MISSolver`.

The solver is decoupled from any particular backend via the
:class:`~qReduMIS.solver.informers.base.Informer` interface.  These tests use a
deterministic, offline ``FakeInformer`` so the qReduMIS reduction loop can be
exercised without a quantum backend or the compiled SA binary.

They verify:
  - fully-reducible graphs are solved by classical reduction alone
  - the informer is queried only when a non-trivial kernel remains
  - the returned solution is a valid independent set
  - the incumbent size is correct on small graphs
  - ``max_iteration_limit`` is honoured
  - ``top_k_solutions`` is forwarded to the informer
  - solver state does not leak across ``solve()`` calls
  - the caller's input graph is left untouched
"""

import networkx as nx
import pytest

from qReduMIS.mis_solver import MISSolver
from qReduMIS.solver.informers.base import Informer


# ═══════════════════════════════════════════════════════════════════════════
# Helper graphs & utilities
# ═══════════════════════════════════════════════════════════════════════════
def _triangle():
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2), (0, 2)])
    return G  # MIS = 1 (fully reducible)


def _cycle5():
    return nx.cycle_graph(5)  # odd hole, not fully reducible, MIS = 2


def _petersen():
    return nx.petersen_graph()  # MIS = 4


def _greedy_mis(H):
    """Deterministic minimum-degree greedy independent set."""
    H = H.copy()
    chosen = []
    while H.number_of_nodes() > 0:
        v = min(H.nodes(), key=lambda n: (H.degree(n), n))
        chosen.append(v)
        H.remove_nodes_from(list(H.neighbors(v)) + [v])
    return chosen


def _is_independent_set(G, nodes):
    nodes = list(nodes)
    return all(
        not G.has_edge(u, v) for i, u in enumerate(nodes) for v in nodes[i + 1 :]
    )


class FakeInformer(Informer):
    """
    Deterministic, offline informer used to drive the MISSolver loop.

    On each call it computes a greedy independent set on the relabeled kernel,
    maps the nodes back to their original labels, and freezes a single node
    (whose neighbours are removed) so the kernel is guaranteed to shrink and the
    loop terminates.
    """

    def __init__(self):
        self.selection_strategy = "inset"
        self.clean_counts = None
        self.calls = 0

    def get_clean_counts(
        self,
        K,
        N,
        reversed_mapping,
        seed_graph,
        cshot,
        current_iteration,
        name_store=None,
        folder_storing=None,
        **kwargs,
    ):
        self.calls += 1
        mis_orig = [reversed_mapping[n] for n in _greedy_mis(K)]
        self.clean_counts = [{"nodes": mis_orig, "count": 10}]
        return self.clean_counts

    def find_maximum_independent_set(self, clean_counts, seed):
        best = max(clean_counts, key=lambda c: len(c["nodes"]))
        return list(best["nodes"])

    def select_nodes(
        self,
        clean_counts,
        kernel_graph,
        seed,
        k_size=2,
        num_nodes_frac=0.4,
    ):
        best = max(clean_counts, key=lambda c: len(c["nodes"]))
        selected_in = [best["nodes"][0]]
        to_remove = set(selected_in)
        for v in selected_in:
            to_remove.update(kernel_graph.neighbors(v))
        return selected_in, [], list(to_remove)


# ═══════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestMISSolver:
    def test_triangle_fully_reducible(self):
        """A triangle is solved by classical reduction; informer untouched."""
        informer = FakeInformer()
        solver = MISSolver(informer)
        sol, iters = solver.solve(_triangle(), seed_graph=1, cshot=0)
        assert isinstance(sol, set)
        assert len(sol) == 1  # MIS of a triangle is 1
        assert iters == 0  # solved at iteration 0
        assert informer.calls == 0  # informer never queried

    def test_cycle5_uses_informer(self):
        """An odd cycle leaves a kernel, so the informer is queried."""
        informer = FakeInformer()
        solver = MISSolver(informer)
        G = _cycle5()
        sol, iters = solver.solve(G, seed_graph=1, cshot=0)
        assert informer.calls >= 1
        assert _is_independent_set(G, sol)
        assert len(sol) == 2  # MIS of C5 is 2
        assert iters <= solver.max_iteration_limit

    def test_solution_is_independent_petersen(self):
        """The returned solution must be a valid independent set."""
        informer = FakeInformer()
        solver = MISSolver(informer)
        G = _petersen()
        sol, iters = solver.solve(G, seed_graph=7, cshot=0)
        assert informer.calls >= 1
        assert _is_independent_set(G, sol)
        assert len(sol) >= 3  # greedy loop reaches the MIS (4) here
        assert iters <= solver.max_iteration_limit

    def test_max_iteration_limit(self):
        """The loop must stop at max_iteration_limit."""
        informer = FakeInformer()
        solver = MISSolver(informer, max_iteration_limit=1)
        G = _petersen()
        sol, iters = solver.solve(G, seed_graph=1, cshot=0)
        assert iters <= 1
        assert _is_independent_set(G, sol)

    def test_top_k_solutions_is_forwarded(self):
        """top_k_solutions is passed to the informer's select_nodes as k_size."""
        captured = {}

        class RecordingInformer(FakeInformer):
            def select_nodes(
                self, clean_counts, kernel_graph, seed, k_size=2, num_nodes_frac=0.4
            ):
                captured["k_size"] = k_size
                return super().select_nodes(
                    clean_counts, kernel_graph, seed, k_size, num_nodes_frac
                )

        informer = RecordingInformer()
        solver = MISSolver(informer, top_k_solutions=3)
        solver.solve(_cycle5(), seed_graph=1, cshot=0)
        assert captured.get("k_size") == 3

    def test_state_reset_between_solves(self):
        """Reusing a solver instance must not leak state across solves."""
        informer = FakeInformer()
        solver = MISSolver(informer)
        solver.solve(_petersen(), seed_graph=1, cshot=0)
        sol2, _ = solver.solve(_triangle(), seed_graph=2, cshot=0)
        assert len(sol2) == 1  # triangle result, no petersen carry-over
        assert _is_independent_set(_triangle(), sol2)

    def test_input_graph_untouched(self):
        """solve() operates on a copy; the caller's graph is preserved."""
        informer = FakeInformer()
        solver = MISSolver(informer)
        G = _petersen()
        nodes_before = set(G.nodes())
        edges_before = set(map(frozenset, G.edges()))
        sol, _ = solver.solve(G, seed_graph=1, cshot=0)
        assert isinstance(sol, set)
        assert set(G.nodes()) == nodes_before
        assert set(map(frozenset, G.edges())) == edges_before


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

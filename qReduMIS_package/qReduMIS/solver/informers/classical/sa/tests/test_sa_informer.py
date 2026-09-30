###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

"""
Tests for SA informer and MIS solver SA integration.

These tests verify:
  - METIS format I/O
  - SA binary invocation and JSON parsing
  - clean_counts aggregation
  - Node selection (inset strategy)
  - find_maximum_independent_set
  - Full qReduMIS loop with SA informer
"""

import json
import os
import tempfile
from pathlib import Path

import networkx as nx
import pytest

# Module under test
from qReduMIS.mis_solver import MISSolver
from qReduMIS.solver.informers.classical.sa.informer import (
    SAInformer,
    read_metis,
    run_sa,
    sa_solutions_to_clean_counts,
    write_metis,
)
from qReduMIS.solver.informers.selection import get_inset_nodes

# The compiled binary lives in ``sa/_cpp`` and the sample kernel in ``sa/tests/data``.
_SA_DIR = Path(__file__).resolve().parent.parent
SA_BINARY = str(_SA_DIR / "_cpp" / "sa_solver")
METIS_FILE = str(
    Path(__file__).resolve().parent / "data" / "kernel_1_atoms_L17_seed46.metis"
)

# The `sa_solver` binary is intentionally not distributed with the library, so
# this whole module is opt-in. A plain `pytest` run deselects it (see the
# `addopts = ["-m", "not sa"]` setting in pyproject.toml); build the binary and
# run `pytest -m sa` to exercise these tests.
pytestmark = pytest.mark.sa


def _has_sa_binary():
    """Return True if the compiled ``sa_solver`` binary is present."""
    return os.path.isfile(SA_BINARY)


# Helper graphs
def _triangle():
    """Return a 3-node triangle graph (MIS size 1)."""
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2), (0, 2)])
    return G


def _path4():
    """Return the 4-node path graph 0-1-2-3 (MIS size 2)."""
    return nx.path_graph(4)  # 0-1-2-3, MIS = {0,2} or {1,3}


def _petersen():
    """Return the Petersen graph (10 nodes, MIS size 4)."""
    return nx.petersen_graph()  # 10 nodes, MIS = 4


# ═══════════════════════════════════════════════════════════════════════════
# METIS I/O
# ═══════════════════════════════════════════════════════════════════════════


class TestWriteMetis:
    """Tests for writing graphs to METIS format."""

    def test_triangle(self, tmp_path):
        """A triangle is written with the correct header and node count."""
        G = _triangle()
        path = str(tmp_path / "tri.metis")
        write_metis(G, path)
        with open(path) as f:
            lines = f.readlines()
        assert lines[0].strip() == "3 3"  # 3 nodes, 3 edges
        # Each node should list its neighbors (1-indexed)
        assert len(lines) == 4  # header + 3 nodes

    def test_path4(self, tmp_path):
        """A path-4 graph is written with the correct header."""
        G = _path4()
        path = str(tmp_path / "p4.metis")
        write_metis(G, path)
        with open(path) as f:
            lines = f.readlines()
        assert lines[0].strip() == "4 3"  # 4 nodes, 3 edges

    def test_roundtrip(self, tmp_path):
        """Writing then reading a graph preserves node and edge counts."""
        G = _petersen()
        path = str(tmp_path / "petersen.metis")
        write_metis(G, path)
        H = read_metis(path)
        assert H.number_of_nodes() == G.number_of_nodes()
        assert H.number_of_edges() == G.number_of_edges()

    def test_non_contiguous_nodes(self, tmp_path):
        """Graphs with non-0-based node labels should still work."""
        G = nx.Graph()
        G.add_edges_from([(10, 20), (20, 30)])
        path = str(tmp_path / "nc.metis")
        write_metis(G, path)
        H = read_metis(path)
        assert H.number_of_nodes() == 3
        assert H.number_of_edges() == 2


class TestReadMetis:
    """Tests for reading graphs from METIS format."""

    def test_existing_file(self):
        """The bundled sample kernel reads back with the expected size."""
        G = read_metis(METIS_FILE)
        assert G.number_of_nodes() == 71
        assert G.number_of_edges() == 223


# ═══════════════════════════════════════════════════════════════════════════
# SA binary invocation
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not _has_sa_binary(), reason="sa_solver binary not compiled")
class TestRunSA:
    """Tests for invoking the compiled ``sa_solver`` binary."""

    def test_basic_run(self, tmp_path):
        """A basic SA run returns solutions and the correct best size."""
        G = _path4()
        metis = str(tmp_path / "p4.metis")
        write_metis(G, metis)
        result = run_sa(metis, replicas=10, steps=8, sa_binary=SA_BINARY)
        assert "solutions" in result
        assert "best_size" in result
        assert result["best_size"] == 2  # MIS of path-4 is 2

    def test_triangle(self, tmp_path):
        """SA finds the MIS of a triangle (size 1)."""
        G = _triangle()
        metis = str(tmp_path / "tri.metis")
        write_metis(G, metis)
        result = run_sa(metis, replicas=10, steps=8, sa_binary=SA_BINARY)
        assert result["best_size"] == 1  # MIS of triangle is 1

    def test_petersen(self, tmp_path):
        """SA finds the MIS of the Petersen graph (size 4)."""
        G = _petersen()
        metis = str(tmp_path / "pet.metis")
        write_metis(G, metis)
        result = run_sa(metis, replicas=100, steps=32, sa_binary=SA_BINARY)
        assert result["best_size"] == 4  # MIS of Petersen graph is 4

    def test_real_instance(self):
        """SA on the bundled real kernel returns the expected best size and count."""
        result = run_sa(METIS_FILE, replicas=100, steps=32, sa_binary=SA_BINARY)
        assert result["best_size"] == 21
        assert len(result["solutions"]) == 100

    def test_replicas_count(self, tmp_path):
        """The number of returned solutions matches the requested replica count."""
        G = _path4()
        metis = str(tmp_path / "p4.metis")
        write_metis(G, metis)
        result = run_sa(metis, replicas=5, steps=8, sa_binary=SA_BINARY)
        assert len(result["solutions"]) == 5

    def test_missing_binary(self, tmp_path):
        """A missing SA binary raises ``FileNotFoundError``."""
        with pytest.raises(FileNotFoundError, match="SA binary not found"):
            run_sa("dummy.metis", sa_binary="/nonexistent/sa_solver")


# ═══════════════════════════════════════════════════════════════════════════
# Clean counts conversion
# ═══════════════════════════════════════════════════════════════════════════


class TestSASolutionsToCleanCounts:
    """Tests for converting raw SA output into aggregated clean_counts."""

    def test_aggregation(self):
        """Duplicate solutions are aggregated into weighted counts."""
        sa_output = {
            "solutions": [
                {"nodes": [0, 2], "size": 2},
                {"nodes": [1, 3], "size": 2},
                {"nodes": [0, 2], "size": 2},  # duplicate
            ],
            "best_size": 2,
        }
        identity_map = {0: 0, 1: 1, 2: 2, 3: 3}
        cc = sa_solutions_to_clean_counts(sa_output, identity_map)
        assert len(cc) == 2  # two unique solutions
        counts = {tuple(sorted(c["nodes"])): c["count"] for c in cc}
        assert counts[(0, 2)] == 2
        assert counts[(1, 3)] == 1

    def test_with_mapping(self):
        """Node ids are remapped back to the original graph labels."""
        sa_output = {
            "solutions": [{"nodes": [0, 1], "size": 2}],
            "best_size": 2,
        }
        mapping = {0: 10, 1: 20}
        cc = sa_solutions_to_clean_counts(sa_output, mapping)
        assert cc[0]["nodes"] == [10, 20]


# ═══════════════════════════════════════════════════════════════════════════
# Inset node selection
# ═══════════════════════════════════════════════════════════════════════════


class TestGetInsetNodes:
    """Tests for the shared inset-node selection helper."""

    def test_basic(self):
        """Only the top-``k_size`` solution sizes contribute candidate nodes."""
        cc = [
            {"nodes": [0, 2, 4], "count": 10},
            {"nodes": [1, 3], "count": 5},
            {"nodes": [0, 2], "count": 3},
        ]
        top = get_inset_nodes(cc, k_size=1, num_select=2)
        # Only size-3 solutions are top-1, so nodes 0,2,4 each have count 10
        assert len(top) == 2
        assert all(n in [0, 2, 4] for n in top)

    def test_weighted_by_count(self):
        """Node frequency is weighted by each solution's count."""
        cc = [
            {"nodes": [0, 1], "count": 100},
            {"nodes": [0, 2], "count": 1},
        ]
        top = get_inset_nodes(cc, k_size=2, num_select=1)
        assert top == [0]  # node 0 appears in both, highest frequency


# ═══════════════════════════════════════════════════════════════════════════
# SAInformer class
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not _has_sa_binary(), reason="sa_solver binary not compiled")
class TestSAInformer:
    """Tests for the ``SAInformer`` Informer implementation."""

    def test_get_clean_counts(self):
        """``get_clean_counts`` returns well-formed candidates for a path-4 kernel."""
        G = _path4()
        mapping = {i: i for i in range(4)}
        reversed_mapping = {i: i for i in range(4)}
        informer = SAInformer(replicas=50, steps=16, sa_binary=SA_BINARY)
        cc = informer.get_clean_counts(
            G, 4, reversed_mapping, seed_graph=1, cshot=0, current_iteration=0
        )
        assert len(cc) > 0
        assert all("nodes" in s and "count" in s for s in cc)
        best = max(len(s["nodes"]) for s in cc)
        assert best == 2  # MIS of path-4

    def test_find_maximum_independent_set(self):
        """The largest candidate independent set is returned."""
        cc = [
            {"nodes": [0, 2], "count": 5},
            {"nodes": [1, 3], "count": 3},
            {"nodes": [0], "count": 2},
        ]
        informer = SAInformer(sa_binary=SA_BINARY)
        mis = informer.find_maximum_independent_set(cc, seed=42)
        assert len(mis) == 2
        assert mis in [[0, 2], [1, 3]]

    def test_select_nodes_inset(self):
        """The inset strategy freezes a node and removes it with its neighbours."""
        G = _path4()
        cc = [
            {"nodes": [0, 2], "count": 10},
            {"nodes": [1, 3], "count": 5},
        ]
        informer = SAInformer(sa_binary=SA_BINARY)
        sel_in, sel_out, to_remove = informer.select_nodes(cc, G, seed=42)
        assert len(sel_in) == 1
        assert sel_in[0] in [0, 1, 2, 3]
        assert sel_in[0] in to_remove
        # All neighbors of sel_in[0] should be in to_remove
        for nbr in G.neighbors(sel_in[0]):
            assert nbr in to_remove

    def test_stores_results(self, tmp_path):
        """Per-call SA counts are written to the storing folder."""
        G = _path4()
        mapping = {i: i for i in range(4)}
        informer = SAInformer(replicas=10, steps=8, sa_binary=SA_BINARY)
        cc = informer.get_clean_counts(
            G,
            4,
            mapping,
            seed_graph=1,
            cshot=0,
            current_iteration=0,
            folder_storing=str(tmp_path),
        )
        stored = list(tmp_path.glob("intermediate_iterations/sa_counts_*.json"))
        assert len(stored) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Full solver integration
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not _has_sa_binary(), reason="sa_solver binary not compiled")
class TestMISSolverSA:
    """Integration tests for the full qReduMIS loop with the SA informer."""

    def test_triangle_fully_reducible(self):
        """Triangle should be solved by classical reduction alone."""
        solver = MISSolver(SAInformer(replicas=10, steps=8, sa_binary=SA_BINARY))
        G = _triangle()
        sol, iters = solver.solve(G, seed_graph=1, cshot=0)
        assert len(sol) == 1  # MIS of triangle is 1
        assert iters == 0  # Solved at iteration 0

    def test_path4(self):
        """Path-4 should find MIS of size 2."""
        solver = MISSolver(SAInformer(replicas=50, steps=16, sa_binary=SA_BINARY))
        G = _path4()
        sol, iters = solver.solve(G, seed_graph=1, cshot=0)
        assert len(sol) >= 2  # MIS of path-4 is 2

    def test_petersen(self):
        """Petersen graph: MIS = 4."""
        solver = MISSolver(
            SAInformer(replicas=100, steps=32, sa_binary=SA_BINARY),
            max_iteration_limit=15,
        )
        G = _petersen()
        sol, iters = solver.solve(G, seed_graph=1, cshot=0)
        assert len(sol) >= 3  # should get close to or at 4

    def test_stores_iteration_info(self, tmp_path):
        """The solver writes per-iteration info files when storing is enabled."""
        solver = MISSolver(SAInformer(replicas=50, steps=16, sa_binary=SA_BINARY))
        G = _path4()
        sol, iters = solver.solve(
            G, seed_graph=1, cshot=0, folder_storing=str(tmp_path)
        )
        stored = list(tmp_path.glob("intermediate_iterations/info_*.json"))
        assert len(stored) >= 1

    def test_separate_solves_are_independent(self):
        """Two solve calls should not leak state."""
        solver = MISSolver(SAInformer(replicas=50, steps=16, sa_binary=SA_BINARY))
        G1 = _path4()
        sol1, _ = solver.solve(G1, seed_graph=1, cshot=0)
        G2 = _triangle()
        sol2, _ = solver.solve(G2, seed_graph=2, cshot=0)
        assert len(sol2) == 1  # should not carry over from path-4

    def test_max_iteration_limit(self):
        """Should stop at max_iteration_limit."""
        solver = MISSolver(
            SAInformer(replicas=10, steps=8, sa_binary=SA_BINARY),
            max_iteration_limit=1,
        )
        G = _petersen()
        sol, iters = solver.solve(G, seed_graph=1, cshot=0)
        assert iters <= 1

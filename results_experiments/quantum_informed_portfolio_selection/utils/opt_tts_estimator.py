###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
opt_tts_estimator — General optTTS Estimator Module
====================================================

Computes the optimal Time-to-Solution (optTTS) of iterative
reduction + solver methods (qReduMIS) for the MIS (Maximum Independent Set)
problem.  Instances are discovered from the results directory structure (or
the ``consolidated_results/`` tables that replace it) and the intermediate
iteration records are inspected to find the earliest iteration at which
optimality was reached.  Both **folder-based** and **DB-based** (SQLite)
layouts are supported.

Core formulas (arXiv:2503.12551)
---------------------------------
.. math::

    \\text{TTS}(t_f) = t_f \\cdot \\frac{\\ln(1 - p_d)}{\\ln(1 - p_S(t_f))}

    \\text{optTTS} = \\min_{t_f} \\text{TTS}(t_f)

with the convention :math:`p_S(t_i) = (i - 0.5) / M` for sorted
successful runtimes :math:`t_1 \\le \\ldots \\le t_{M_{\\text{success}}}`.

Main entry point
----------------
>>> from opt_tts_estimator import estimate_opt_tts
>>> df = estimate_opt_tts(
...     graph_dir="path/to/graphml_files",
...     results_dir="path/to/results",
...     method_type="redumis",
...     cost_per_call=5,
... )

Dependencies
------------
- ``tts_utils.compute_opt_tts``, ``tts_utils.bootstrap_opt_tts``
- ``solver_baseline.or_tool_solver`` (fallback ground truth only)

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import warnings
from collections import defaultdict
from typing import Callable

import networkx as nx
import numpy as np
import pandas as pd

# ── Path setup for project imports ───────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure utils/ directory itself is on sys.path (tts_utils, solver_baseline live here)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from tts_utils import compute_opt_tts, bootstrap_opt_tts  # noqa: E402
from solver_baseline import or_tool_solver as _default_mis_solver  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
# §1  Ground-truth MIS sizes (loading + cached fallback)
# ═══════════════════════════════════════════════════════════════════════

_gt_cache: dict = {}


def load_ground_truth(path: str, mis_key: str = "mis_size") -> dict:
    """Load a ground-truth dict from a JSON file.

    Backward-compatible: files saved by older versions (tuple keys
    only) still load correctly.  Newer files may also contain
    ``instance_name`` string keys for threshold-varied instances.

    Parameters
    ----------
    path : str
        Ground-truth JSON file (a list of ``{N, seed, <mis_key>}`` records).
    mis_key : str
        JSON key that holds the MIS size value.  Common values:

        - ``"mis_size"`` (default) — standard format
        - ``"mis_full"`` — full-graph MIS (testbed format)
        - ``"mis_kernel"`` — kernel (reduced-graph) MIS

    Returns
    -------
    dict
        Mapping ``(N, seed) -> MIS_size`` and/or
        ``instance_name -> MIS_size``.
    """
    with open(path) as f:
        records = json.load(f)
    gt: dict = {}
    for r in records:
        # Resolve the MIS value from the requested key
        mis_val = r.get(mis_key)
        if mis_val is None:
            continue  # skip entries that lack the requested key
        mis_val = int(mis_val)

        if "instance_name" in r:
            gt[r["instance_name"]] = mis_val
        else:
            gt[(int(r["N"]), int(r["seed"]))] = mis_val
    return gt


def get_ground_truth_mis_size(
    N: int,
    seed: int,
    graph_dirs: list[str],
    mis_solver: Callable | None = None,
    graph_prefix: str = "graph_unweighted",
    graph_suffix: str = "",
) -> int | None:
    """Compute and cache the optimal MIS size for instance ``(N, seed)``.

    Searches *graph_dirs* using two layout conventions:

    - **Nested:** ``<graph_dir>/graphs_N{N}/{prefix}_{seed}.graphml``
    - **Flat:**   ``<graph_dir>/{prefix}_N{N}_seed{seed}.graphml``

    Parameters
    ----------
    N, seed :
        Instance identifiers.
    graph_dirs :
        Directories to search for ``.graphml`` files.
    mis_solver :
        ``(nx.Graph) -> list[node]``.  Defaults to OR-Tools
        (``solver_baseline.or_tool_solver``).
    graph_prefix :
        Filename prefix (default ``"graph_unweighted"``).

    Returns
    -------
    int or None
        MIS size, or *None* if the graph file was not found.
    """
    if mis_solver is None:
        mis_solver = _default_mis_solver

    key = (tuple(graph_dirs), int(N), int(seed), graph_suffix)
    if key in _gt_cache:
        return _gt_cache[key]

    for gdir in graph_dirs:
        candidates = [
            os.path.join(
                gdir, f"graphs_N{N}", f"{graph_prefix}_{seed}.graphml"
            ),
            os.path.join(gdir, f"{graph_prefix}_N{N}_seed{seed}.graphml"),
        ]
        # Also try with suffix (e.g. threshold-varied instances)
        if graph_suffix:
            candidates.insert(
                0,
                os.path.join(
                    gdir,
                    f"{graph_prefix}_N{N}_seed{seed}{graph_suffix}.graphml",
                ),
            )
        for p in candidates:
            if os.path.exists(p):
                G = nx.read_graphml(p)
                sol = mis_solver(G)
                if sol is not None:
                    _gt_cache[key] = len(sol)
                    return len(sol)
    return None


# ═══════════════════════════════════════════════════════════════════════
# §1b  Derived-table fallback
# ═══════════════════════════════════════════════════════════════════════
#
# The per-iteration ``info_*.json`` files are the primary source of truth,
# but they are not shipped: the fields this module actually reads
# (``len(S)``, ``len(W)``, ``len(classical kernel)``) are folded into
# ``consolidated_results/iterations.csv``.
#
# The helpers below let the estimator fall back to that table whenever the
# raw tree is absent, so a release that ships only ``consolidated_results/`` can still
# recompute optTTS from scratch.  When the raw files *are* present they are
# always preferred, which keeps behaviour unchanged for existing checkouts.

_DERIVED_ITER_CACHE: dict[str, pd.DataFrame | None] = {}


def _find_derived_iterations(start: str | None = None) -> pd.DataFrame | None:
    """Locate and load ``consolidated_results/iterations.csv``.

    Walks up from *start* (default: this file's directory) looking for a
    sibling ``consolidated_results/`` folder.  The result is cached per start location;
    a missing table caches as ``None`` so the lookup is attempted once.

    Returns
    -------
    pandas.DataFrame or None
        The iterations table with an extra ``dirpath`` column holding the
        absolute directory each row was read from, or ``None`` if no
        derived table exists.
    """
    start = os.path.abspath(start or os.path.dirname(os.path.abspath(__file__)))
    if start in _DERIVED_ITER_CACHE:
        return _DERIVED_ITER_CACHE[start]

    path = None
    cur = start
    for _ in range(6):
        cand = os.path.join(cur, "consolidated_results", "iterations.csv")
        if os.path.exists(cand):
            path = cand
            break
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    if path is None:
        _DERIVED_ITER_CACHE[start] = None
        return None

    df = pd.read_csv(path)
    root = os.path.dirname(os.path.dirname(path))  # the folder holding consolidated_results/
    df["dirpath"] = [
        os.path.normpath(os.path.join(root, t, r))
        for t, r in zip(df["tree"], df["run"])
    ]
    _DERIVED_ITER_CACHE[start] = df
    return df


def _derived_rows_for(results_dir: str) -> pd.DataFrame | None:
    """Rows of the derived iterations table that live under *results_dir*.

    Matching is by absolute-path prefix on the directory each raw
    ``info_*.json`` was read from, so it works for both the nested
    (ReduMIS+SA) and flat (qReduMIS) layouts.

    Returns ``None`` when no derived table exists, and an empty frame when
    the table exists but covers nothing under *results_dir*.
    """
    df = _find_derived_iterations(results_dir)
    if df is None:
        return None
    target = os.path.normpath(os.path.abspath(results_dir))
    mask = (df["dirpath"] == target) | df["dirpath"].str.startswith(
        target + os.sep
    )
    return df.loc[mask]


def _info_sort_key(N: int, seed: int, cshot: int, top: int, it: int) -> str:
    """Reproduce the raw filename, so lexicographic ordering is preserved.

    ``_discover_redumis_folder_trials`` picks the last iteration file with a
    *lexicographic* sort of the file names.  For trials with >= 10 iterations
    that differs from numeric ordering, so the derived path must sort on the
    same string to stay bit-for-bit compatible.
    """
    return f"info_{it}_N{N}_seed{seed}_cshot{cshot}_top{top}.json"


def _read_db_records(db_path: str) -> list[dict]:
    """Records of a ``benchmark_*.db``, from the file or from ``consolidated_results/``.

    The SQLite files are consolidated into ``consolidated_results/benchmarks.csv`` and
    removed in a released checkout, so fall back to the table whenever the
    file is absent.  Both paths yield the same dicts in the same order.
    """
    if os.path.exists(db_path):
        # Read-only: a read-write connection would create -shm/-wal scratch
        # files next to the database.
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return [
                json.loads(rj)
                for (rj,) in conn.execute("SELECT result_json FROM results")
            ]
        finally:
            conn.close()

    try:
        from utils.derived import DerivedData
    except ImportError:
        return []
    try:
        return DerivedData().db_records(db_path)
    except FileNotFoundError:
        return []


def _known_db_names(results_dir: str, kind: str) -> list[str]:
    """``benchmark_*.db`` names under *results_dir* matching *kind*.

    Looks on disk first, then at the ``db`` column of the derived benchmarks
    table, so discovery still works once the SQLite files are gone.
    """
    if os.path.isdir(results_dir):
        names = [
            f for f in os.listdir(results_dir)
            if f.endswith(".db") and kind in f.lower()
        ]
        if names:
            return sorted(names)

    try:
        from utils.derived import DerivedData

        d = DerivedData()
    except (ImportError, FileNotFoundError):
        return []

    b = d.benchmarks
    target = os.path.normpath(os.path.abspath(results_dir))
    names = {
        row.db
        for row in b.itertuples()
        if kind in str(row.db).lower()
        and os.path.normpath(os.path.join(d.root, row.tree, row.run)) == target
    }
    return sorted(names)


# ═══════════════════════════════════════════════════════════════════════
# §2  Optimal solver calls for ReduMIS-like methods
# ═══════════════════════════════════════════════════════════════════════


def get_optimal_solver_calls(
    N: int,
    seed: int,
    cshot: int,
    iterations: int,
    mis_size: int,
    results_dir: str,
    ground_truth_size: int,
    instance_name: str | None = None,
) -> int | float:
    """Find the minimum number of solver (QPU / SA) calls to reach optimality.

    Generalises both ``get_opt_num_qpu_calls`` (for qReduMIS) and
    ``get_opt_num_sa_calls`` (for ReduMIS+SA).  Both follow the same
    iterative structure::

        CPU₀ → if done: 0 calls
             → else: Solver₀ → LOG₀
        CPU₁ → if done: 1 call (or 0 if CPU₁ alone sufficed)
             → else: Solver₁ → LOG₁
        …

    At each logged iteration *it*, three checks are performed in order:

    1. ``len(S) − 1 == ground_truth`` — classical reduction alone
       sufficed at this iteration → *it* solver calls were needed.
    2. ``len(S) == ground_truth`` — solver call reached optimal
       → *it + 1* calls.
    3. ``len(W) == ground_truth`` — incumbent reached optimal
       → *it + 1* calls.

    Two directory layouts are auto-detected:

    - **Nested** (ReduMIS+SA):
      ``results_dir/market_N{N}_seed{seed}/cshot_{cshot}/
      intermediate_iterations/``
    - **Flat** (qReduMIS):
      ``results_dir/intermediate_iterations/``

    Parameters
    ----------
    N, seed, cshot :
        Instance and trial identifiers.
    iterations :
        Total iterations performed by this trial.
    mis_size :
        Final MIS size found by this trial.
    results_dir :
        Root results directory.
    ground_truth_size :
        Exact MIS size from an optimal solver.

    Returns
    -------
    int or np.inf
        Minimum solver calls to first reach optimality, or ``np.inf``
        if the trial did not reach optimality.
    """
    if mis_size != ground_truth_size:
        return np.inf
    if iterations == 0:
        return 0

    # Auto-detect directory layout
    _inst_dir_name = instance_name or f"market_N{N}_seed{seed}"
    inter_dir = None
    for candidate in [
        # Nested (ReduMIS+SA)
        os.path.join(
            results_dir,
            _inst_dir_name,
            f"cshot_{cshot}",
            "intermediate_iterations",
        ),
        # Flat (qReduMIS)
        os.path.join(results_dir, "intermediate_iterations"),
    ]:
        probe = os.path.join(
            candidate, f"info_0_N{N}_seed{seed}_cshot{cshot}_top0.json"
        )
        if os.path.exists(probe):
            inter_dir = candidate
            break

    if inter_dir is None:
        # No raw files.  Try the derived table before giving up.
        records = _derived_iteration_records(
            results_dir, N, seed, cshot, iterations
        )
        if records is None:
            # Nothing to inspect; fall back to total iterations
            return iterations
        return _first_optimal_iteration(
            records, iterations, ground_truth_size
        )

    records = []
    for it in range(iterations + 1):
        fpath = os.path.join(
            inter_dir,
            f"info_{it}_N{N}_seed{seed}_cshot{cshot}_top0.json",
        )
        if not os.path.exists(fpath):
            continue

        with open(fpath) as f:
            data = json.load(f)

        # Detect whether a solver (QPU / SA) call was actually made
        # at this iteration.  When the classical reduction factor is
        # 1.0 (equivalently, the classical kernel is empty), no solver
        # call was made — the entire iteration was classical.
        kernel = data.get("classical kernel", None)
        records.append(
            (
                it,
                len(data["S"]),
                len(data.get("W", [])),
                kernel is None or len(kernel) > 0,
            )
        )

    return _first_optimal_iteration(records, iterations, ground_truth_size)


def _derived_iteration_records(
    results_dir: str,
    N: int,
    seed: int,
    cshot: int,
    iterations: int,
) -> list[tuple[int, int, int, bool]] | None:
    """Per-iteration records for one trial, taken from the derived table.

    Returns the same ``(iteration, len_S, len_W, solver_called)`` tuples the
    raw-file path produces, or ``None`` when no derived data covers this
    trial.
    """
    rows = _derived_rows_for(results_dir)
    if rows is None or rows.empty:
        return None
    sel = rows[
        (rows["N"] == N)
        & (rows["seed"] == seed)
        & (rows["cshot"] == cshot)
        & (rows["top"] == 0)
        & (rows["iteration"] <= iterations)
    ]
    if sel.empty:
        return None
    return [
        (
            int(r.iteration),
            int(r.len_S),
            int(r.len_W),
            bool(pd.isna(r.kernel_size) or r.kernel_size > 0),
        )
        for r in sel.sort_values("iteration").itertuples()
    ]


def _first_optimal_iteration(
    records: list[tuple[int, int, int, bool]],
    iterations: int,
    ground_truth_size: int,
) -> int | float:
    """Walk per-iteration records and return the first optimal call count.

    *records* is a sequence of ``(iteration, len_S, len_W, solver_called)``
    ordered by iteration.  See :func:`get_optimal_solver_calls` for the
    three checks applied at each step.
    """
    for it, S_after, W_after, solver_called in records:
        if solver_called:
            # The solver selects exactly one node per call, so the
            # state before the solver call was one node smaller.
            S_before = S_after - 1

            # 1) Classical reduction alone reached optimal
            if S_before == ground_truth_size:
                return it

            # 2) Solver call reached optimal via S
            if S_after == ground_truth_size:
                return it + 1

            # 3) Incumbent W reached optimal
            if W_after == ground_truth_size:
                return it + 1
        else:
            # No solver call at this iteration (classical reduction
            # consumed the entire kernel).  Any optimality here was
            # achieved without an additional solver call.
            if S_after == ground_truth_size:
                return it

            if W_after == ground_truth_size:
                return it

    # Optimality was reached in the final (unlogged) CPU reduction
    return iterations


# ═══════════════════════════════════════════════════════════════════════
# §3  Instance discovery helpers
# ═══════════════════════════════════════════════════════════════════════


def _discover_redumis_folder_trials(
    results_dir: str,
    sizes: set[int] | None = None,
) -> list[dict]:
    """Discover trials from ReduMIS+SA folder structure.

    Expects the layout::

        results_dir/
            market_N{N}_seed{seed}/
                cshot_{c}/
                    intermediate_iterations/
                        info_{it}_N{N}_seed{seed}_cshot{c}_top0.json

    Parameters
    ----------
    results_dir :
        Root results directory.
    sizes : set[int], optional
        If given, only discover instances whose ``N`` is in this set.
        Skips directories for other sizes entirely (faster I/O).

    Returns
    -------
    list of dict
        Each dict has keys: ``N, seed, cshot, results_dir,
        iterations, mis_size``.
    """
    trials: list[dict] = []
    if not os.path.isdir(results_dir):
        return _discover_redumis_folder_trials_derived(results_dir, sizes)

    for d in sorted(os.listdir(results_dir)):
        m = re.match(r"market_N(\d+)_seed(\d+)(.*)", d)
        if not m:
            continue
        N_val, seed_val = int(m.group(1)), int(m.group(2))
        suffix = m.group(3)  # e.g. "_thres0.38253" or ""

        # Early exit: skip directories for sizes we don't need
        if sizes is not None and N_val not in sizes:
            continue

        inst_path = os.path.join(results_dir, d)
        if not os.path.isdir(inst_path):
            continue

        for cshot_dir in sorted(os.listdir(inst_path)):
            m_c = re.match(r"cshot_(\d+)", cshot_dir)
            if not m_c:
                continue
            cshot_val = int(m_c.group(1))
            inter_dir = os.path.join(
                inst_path, cshot_dir, "intermediate_iterations"
            )
            if not os.path.isdir(inter_dir):
                continue

            # Extract iterations and mis_size from the iteration files
            info_files = sorted(
                f for f in os.listdir(inter_dir) if f.startswith("info_")
            )
            if not info_files:
                continue

            iterations = len(info_files) - 1
            last_info = os.path.join(inter_dir, info_files[-1])
            with open(last_info) as f:
                data = json.load(f)
            W_size = len(data.get("W", []))
            S_size = len(data.get("S", []))
            mis_size = max(W_size, S_size)

            trials.append(
                {
                    "N": N_val,
                    "seed": seed_val,
                    "cshot": cshot_val,
                    "results_dir": results_dir,
                    "iterations": iterations,
                    "mis_size": mis_size,
                    "instance_name": d,
                    "graph_suffix": suffix,
                }
            )
    if not trials:
        return _discover_redumis_folder_trials_derived(results_dir, sizes)
    return trials


def _discover_redumis_folder_trials_derived(
    results_dir: str,
    sizes: set[int] | None = None,
) -> list[dict]:
    """Derived-table equivalent of :func:`_discover_redumis_folder_trials`.

    Used when the raw ``info_*.json`` tree has been consolidated away.
    Produces the identical schema, including the lexicographic choice of
    "last" iteration file, so downstream results are unchanged.
    """
    rows = _derived_rows_for(results_dir)
    if rows is None or rows.empty:
        return []

    # Keep only rows whose directory looks like the nested ReduMIS+SA
    # layout, and recover the instance directory name from the path.
    trials: list[dict] = []
    target = os.path.normpath(os.path.abspath(results_dir))

    inst_names = []
    for p in rows["dirpath"]:
        rel = os.path.relpath(p, target).split(os.sep)
        # expected: <instance>/cshot_<c>/intermediate_iterations
        inst_names.append(rel[0] if len(rel) >= 3 else None)
    rows = rows.assign(instance_name=inst_names)
    rows = rows[rows["instance_name"].notna()]
    if rows.empty:
        return []

    for (inst, N_val, seed_val, cshot_val), grp in rows.groupby(
        ["instance_name", "N", "seed", "cshot"], sort=True
    ):
        m = re.match(r"market_N(\d+)_seed(\d+)(.*)", str(inst))
        if not m:
            continue
        if sizes is not None and int(N_val) not in sizes:
            continue

        # Mirror `sorted(os.listdir(...))[-1]`: lexicographic on file name.
        names = [
            _info_sort_key(
                int(r.N), int(r.seed), int(r.cshot), int(r.top), int(r.iteration)
            )
            for r in grp.itertuples()
        ]
        last = max(range(len(names)), key=lambda i: names[i])
        last_row = grp.iloc[last]

        trials.append(
            {
                "N": int(N_val),
                "seed": int(seed_val),
                "cshot": int(cshot_val),
                "results_dir": results_dir,
                "iterations": len(grp) - 1,
                "mis_size": int(
                    max(last_row["len_W"], last_row["len_S"])
                ),
                "instance_name": str(inst),
                "graph_suffix": m.group(3),
            }
        )
    return trials


def _discover_redumis_db_trials(
    results_dir: str,
    sizes: set[int] | None = None,
) -> list[dict]:
    """Discover trials from a qReduMIS SQLite database.

    Looks for ``*.db`` files containing ``qredumis`` in the name inside
    *results_dir*.  Intermediate iteration files are expected at
    ``results_dir/intermediate_iterations/``.

    Parameters
    ----------
    results_dir :
        Root results directory.
    sizes : set[int], optional
        If given, only return trials whose ``N`` is in this set.

    Returns
    -------
    list of dict
        Same schema as :func:`_discover_redumis_folder_trials`.
    """
    trials: list[dict] = []

    db_files = _known_db_names(results_dir, "qredumis")
    if not db_files:
        return trials

    db_path = os.path.join(results_dir, db_files[0])
    for rec in _read_db_records(db_path):
        N = int(rec["N"])
        # Early exit: skip records for sizes we don't need
        if sizes is not None and N not in sizes:
            continue
        seed_val = int(rec["seed"])
        cshot = int(rec.get("cshot", 0))
        iterations = int(
            rec.get("num iteration", rec.get("num_iteration", 0))
        )
        # MIS size from the solution found
        sol_key = "atom positions MIS"
        if sol_key not in rec:
            sol_key = "atom_positions_MIS"
        mis_size = len(rec.get(sol_key, []))

        trials.append(
            {
                "N": N,
                "seed": seed_val,
                "cshot": cshot,
                "results_dir": results_dir,
                "iterations": iterations,
                "mis_size": mis_size,
            }
        )

    return trials


# ═══════════════════════════════════════════════════════════════════════
# §4  Per-instance optTTS computation
# ═══════════════════════════════════════════════════════════════════════


def _compute_instance_tts_bootstrap(
    runtimes: np.ndarray,
    successes: np.ndarray,
    p_d: float = 0.99,
    n_boot: int = 10_000,
    ci_level: float = 0.95,
    rng: np.random.Generator | None = None,
) -> dict:
    """Compute optTTS with bootstrap CIs for one instance.

    Delegates to ``compute_opt_tts`` and ``bootstrap_opt_tts`` from
    ``tts_utils``.

    Parameters
    ----------
    runtimes :
        Runtime/cost of every trial; shape ``(n_trials,)``.
    successes :
        Boolean array; ``True`` if the trial found the optimum.
    p_d :
        Desired probability for the TTS formula.
    n_boot :
        Number of bootstrap resamples.
    ci_level :
        Confidence interval level.
    rng :
        Random generator for reproducibility.

    Returns
    -------
    dict
        Keys: ``opt_tts, opt_tf, p_success, boot_median, ci_lo, ci_hi``.
    """
    runtimes = np.asarray(runtimes, dtype=float)
    successes = np.asarray(successes, dtype=bool)
    n_total = len(runtimes)
    p_success = float(successes.mean())

    # Point estimate
    success_rts = runtimes[successes]
    result = compute_opt_tts(success_rts, n_total, pd=p_d)

    # Bootstrap
    boot = bootstrap_opt_tts(
        runtimes, successes, n_boot=n_boot, pd=p_d, rng=rng
    )
    # Inf-aware: median and CI are computed over ALL bootstrap values
    # (including inf) so that the 95 % CI is statistically valid.
    alpha = (1 - ci_level) / 2
    boot_median = float(np.median(boot))
    ci_lo = float(np.percentile(boot, 100 * alpha))
    ci_hi = float(np.percentile(boot, 100 * (1 - alpha)))

    return {
        "opt_tts": result["opt_tts"],
        "opt_tf": result["opt_tf"],
        "p_success": p_success,
        "boot_median": boot_median,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
    }


# ═══════════════════════════════════════════════════════════════════════
# §5  Internal estimators
# ═══════════════════════════════════════════════════════════════════════


def _estimate_redumis(
    graph_dirs: list[str],
    results_dirs: list[str],
    mis_solver: Callable,
    p_d: float,
    n_boot: int,
    ci_level: float,
    rng: np.random.Generator,
    cost_per_call: float,
    instance_filter: set | None,
    sizes: set[int] | None,
    graph_prefix: str,
    verbose: bool,
    ground_truth: dict | None = None,
) -> pd.DataFrame:
    """Estimate optTTS for ReduMIS-like methods (internal)."""

    # ── Discover all trials across results directories ────────────────
    all_trials: list[dict] = []
    for rdir in results_dirs:
        folder_trials = _discover_redumis_folder_trials(rdir, sizes=sizes)
        if folder_trials:
            all_trials.extend(folder_trials)
        else:
            db_trials = _discover_redumis_db_trials(rdir, sizes=sizes)
            all_trials.extend(db_trials)

    if not all_trials:
        warnings.warn(f"No trials discovered in {results_dirs}")
        return pd.DataFrame()

    # ── Ensure every trial has an instance_name ─────────────────────
    for t in all_trials:
        t.setdefault("instance_name", f"market_N{t['N']}_seed{t['seed']}")
        t.setdefault("graph_suffix", "")

    # ── De-duplicate by (instance_name, cshot) ────────────────────────
    seen: set = set()
    unique_trials: list[dict] = []
    for t in all_trials:
        key = (t["instance_name"], t["cshot"])
        if key not in seen:
            seen.add(key)
            unique_trials.append(t)

    # ── Apply instance filter ─────────────────────────────────────────
    if instance_filter is not None:
        unique_trials = [
            t
            for t in unique_trials
            if (int(t["N"]), int(t["seed"])) in instance_filter
        ]

    # ── Apply size filter ─────────────────────────────────────────────
    if sizes is not None:
        unique_trials = [
            t for t in unique_trials if int(t["N"]) in sizes
        ]

    if verbose:
        n_inst = len({t["instance_name"] for t in unique_trials})
        print(
            f"Discovered {len(unique_trials)} trials "
            f"across {n_inst} instances"
        )

    # ── Group by instance_name ────────────────────────────────────────
    grouped: dict[str, list] = defaultdict(list)
    for t in unique_trials:
        grouped[t["instance_name"]].append(t)

    rows: list[dict] = []
    total = len(grouped)

    for idx, (inst_name, trials) in enumerate(sorted(grouped.items())):
        # Extract N/seed from the first trial in the group
        N = trials[0]["N"]
        seed_val = trials[0]["seed"]
        _suffix = trials[0].get("graph_suffix", "")

        n_cshots = len(trials)
        runtimes: list[float] = []
        successes: list[bool] = []
        opt_calls_list: list[float] = []
        iters_list: list[int] = []

        # Look up ground truth: try instance_name key first (for
        # threshold-varied instances), then fall back to (N, seed).
        if ground_truth is not None and inst_name in ground_truth:
            gt_size = ground_truth[inst_name]
        elif ground_truth is not None and (int(N), int(seed_val)) in ground_truth:
            gt_size = ground_truth[(int(N), int(seed_val))]
        else:
            gt_size = get_ground_truth_mis_size(
                N, seed_val, graph_dirs, mis_solver, graph_prefix,
                graph_suffix=_suffix,
            )
        if gt_size is None:
            if verbose:
                print(
                    f"  WARNING: No graph found for {inst_name}"
                )
            continue

        # ── Fast path: fully reducible instance (0 iterations) ────
        # When every trial has iterations == 0, the classical
        # reduction solved the problem completely — no SA / QAOA
        # call was needed.  All trials that match the ground truth
        # are successes with runtime 0, so optTTS = 0.
        all_iters = [t["iterations"] for t in trials]
        if max(all_iters) == 0:
            all_match = all(t["mis_size"] == gt_size for t in trials)
            p_succ = 1.0 if all_match else float(
                np.mean([t["mis_size"] == gt_size for t in trials])
            )
            rows.append(
                {
                    "N": int(N),
                    "seed": int(seed_val),
                    "instance_name": inst_name,
                    "n_cshots": n_cshots,
                    "mean_iterations": 0.0,
                    "mean_opt_calls": 0.0,
                    "opt_tts": 0.0,
                    "opt_tf": 0.0,
                    "p_success": p_succ,
                    "boot_median": 0.0,
                    "ci_lo": 0.0,
                    "ci_hi": 0.0,
                }
            )
            if verbose:
                print(f"  {inst_name}: fully reducible "
                      f"(0 iterations, p_success={p_succ:.2f})")
            continue

        for trial in trials:
            iterations = trial["iterations"]
            mis_size = trial["mis_size"]
            cshot = trial["cshot"]
            rdir = trial["results_dir"]
            iters_list.append(iterations)

            opt_calls = get_optimal_solver_calls(
                N, seed_val, cshot, iterations, mis_size, rdir, gt_size,
                instance_name=inst_name,
            )

            if np.isinf(opt_calls):
                rt = iterations * cost_per_call
                successes.append(False)
                opt_calls_list.append(np.inf)
            else:
                rt = opt_calls * cost_per_call
                successes.append(True)
                opt_calls_list.append(opt_calls)

            runtimes.append(rt)

        rt_arr = np.array(runtimes, dtype=float)
        succ_arr = np.array(successes, dtype=bool)

        tts_result = _compute_instance_tts_bootstrap(
            rt_arr, succ_arr, p_d=p_d, n_boot=n_boot,
            ci_level=ci_level, rng=rng,
        )

        finite_calls = [c for c in opt_calls_list if not np.isinf(c)]
        mean_opt_calls = float(np.mean(finite_calls)) if finite_calls else np.inf
        mean_iters = float(np.mean(iters_list))

        rows.append(
            {
                "N": int(N),
                "seed": int(seed_val),
                "instance_name": inst_name,
                "n_cshots": n_cshots,
                "mean_iterations": mean_iters,
                "mean_opt_calls": mean_opt_calls,
                **tts_result,
            }
        )

        if verbose and (idx + 1) % 100 == 0:
            print(f"  [{idx + 1}/{total}] instances processed...")

    df = pd.DataFrame(rows)
    if verbose and len(df) > 0:
        n_inf = int((df["opt_tts"] == np.inf).sum())
        print(f"Done: {len(df)} instances, {n_inf} with optTTS=inf")
    return df


# ═══════════════════════════════════════════════════════════════════════
# §6  Main entry point
# ═══════════════════════════════════════════════════════════════════════


def estimate_opt_tts(
    graph_dir: str | list[str],
    results_dir: str | list[str],
    method_type: str = "redumis",
    *,
    mis_solver: Callable | None = None,
    p_d: float = 0.99,
    n_boot: int = 10_000,
    ci_level: float = 0.95,
    seed: int = 42,
    cost_per_call: float = 1.0,
    instance_filter: set[tuple[int, int]] | None = None,
    sizes: list[int] | None = None,
    ground_truth: dict | None = None,
    graph_prefix: str = "graph_unweighted",
    verbose: bool = False,
) -> pd.DataFrame:
    """Estimate optTTS for all instances in the results directory.

    This is the **main entry point** of the module.

    Parameters
    ----------
    graph_dir : str or list[str]
        Directory(ies) containing ``.graphml`` instance files.
        Supports both nested (``graphs_N{N}/``) and flat layouts.
    results_dir : str or list[str]
        Folder(s) containing per-instance sub-directories with
        intermediate iteration files, or a qReduMIS ``.db`` file (or their
        ``consolidated_results/`` equivalents).  Multiple directories are
        merged (e.g., for split runs or restarts).
    method_type : ``"redumis"``
        Family of solver method.  Only iterative reduction + solver
        methods (qReduMIS) are supported.
    mis_solver : callable, optional
        ``(nx.Graph) -> list[node]`` returning the exact MIS, used only for
        instances missing from *ground_truth*.  Defaults to
        ``or_tool_solver`` from ``solver_baseline``.
    p_d : float
        Desired success probability for the TTS formula (default 0.99).
    n_boot : int
        Number of bootstrap resamples (default 10 000).
    ci_level : float
        Confidence interval level (default 0.95).
    seed : int
        Random seed for bootstrap reproducibility (default 42).
    cost_per_call : float
        Cost multiplier per solver call; for qReduMIS typically the
        number of QPU shots per iteration.
    instance_filter : set of (int, int), optional
        If provided, only process instances whose ``(N, seed)``
        pair is in this set.
    sizes : list[int], optional
        If provided, only process instances whose number of nodes
        ``N`` is in this list.  Can be combined with
        *instance_filter* (both conditions must be satisfied).
    ground_truth : dict[(int, int), int], optional
        Pre-computed mapping ``(N, seed) -> MIS_size`` (see
        :func:`load_ground_truth`).  When provided, the (expensive) exact
        MIS solver is skipped for instances present in this dict.
    graph_prefix : str
        Filename prefix for graph files (default ``"graph_unweighted"``).
    verbose : bool
        Print progress information.

    Returns
    -------
    pd.DataFrame
        Per-instance results with columns
        ``N, seed, instance_name, n_cshots, mean_iterations,
        mean_opt_calls, opt_tts, opt_tf, p_success, boot_median,
        ci_lo, ci_hi``.

    Examples
    --------
    >>> gt = load_ground_truth(
    ...     "problem_instances/registries/ground_truth_testbed.json",
    ...     mis_key="mis_full",
    ... )
    >>> df = estimate_opt_tts(
    ...     graph_dir="problem_instances/market",
    ...     results_dir="<run>/intermediate_iterations",
    ...     method_type="redumis",
    ...     cost_per_call=5,
    ...     ground_truth=gt,
    ... )
    """
    # ── Normalize inputs ──────────────────────────────────────────────
    graph_dirs = [graph_dir] if isinstance(graph_dir, str) else list(graph_dir)
    method_type = method_type.strip().lower()

    if method_type != "redumis":
        raise ValueError(
            f"Unknown method_type={method_type!r}. Expected 'redumis'."
        )

    if mis_solver is None:
        mis_solver = _default_mis_solver

    # ── Build size filter set ─────────────────────────────────────────
    _sizes_set: set[int] | None = None
    if sizes is not None:
        _sizes_set = set(sizes)

    rng = np.random.default_rng(seed)

    results_dirs = (
        [results_dir] if isinstance(results_dir, str) else list(results_dir)
    )
    return _estimate_redumis(
        graph_dirs=graph_dirs,
        results_dirs=results_dirs,
        mis_solver=mis_solver,
        p_d=p_d,
        n_boot=n_boot,
        ci_level=ci_level,
        rng=rng,
        cost_per_call=cost_per_call,
        instance_filter=instance_filter,
        sizes=_sizes_set,
        graph_prefix=graph_prefix,
        verbose=verbose,
        ground_truth=ground_truth,
    )

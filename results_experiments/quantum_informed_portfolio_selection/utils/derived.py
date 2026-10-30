###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""Accessors for the consolidated result tables in ``consolidated_results/``.

The emulator and baseline pipelines originally wrote one small JSON per
(iteration, instance, classical shot), one SQLite database per benchmark run,
and a set of flat benchmark JSON files.  The records the notebooks read were
folded into four plain-text CSV tables; this module is the read side.

Each row carries the ``tree`` and ``run`` it came from, so a notebook can keep
addressing a result by the directory it used to walk on disk::

    from utils.derived import DerivedData

    D = DerivedData()                      # auto-locates consolidated_results/
    rows = D.iters_for_dir("<release>/data/.../intermediate_iterations")

The tables are loaded lazily and cached, so repeated calls are cheap.
"""
from __future__ import annotations

import os
from functools import cached_property

import pandas as pd

__all__ = ["DerivedData", "find_derived_dir", "NODE_SEP", "counts_filename"]

# Separator used to pack a solution's node ids into a single CSV field.
NODE_SEP = " "


def counts_filename(N: int, seed: int, p: int) -> str:
    """Name of the ``clean_counts_*.json`` file an instance came from.

    Only used to recover the original ``sorted(glob(...))`` ordering; the
    file itself no longer has to exist.
    """
    return f"clean_counts_N{int(N)}_seed{int(seed)}_p{int(p)}.json"


def find_derived_dir(start: str | None = None) -> str:
    """Locate ``consolidated_results/``.

    Without *start*, the release root next to this package is used, so the
    result does not depend on the current working directory.  Otherwise walk
    upwards from *start*.
    """
    if start is None:
        cand = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "consolidated_results",
        )
        if os.path.isdir(cand):
            return cand
    cur = os.path.abspath(start or os.getcwd())
    for _ in range(6):
        cand = os.path.join(cur, "consolidated_results")
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise FileNotFoundError(
        "could not locate a 'consolidated_results/' directory above "
        f"{start or os.getcwd()!r}."
    )


class DerivedData:
    """Lazy reader for ``consolidated_results/*.csv``."""

    def __init__(self, derived_dir: str | None = None):
        self.dir = derived_dir or find_derived_dir()

    # ------------------------------------------------------------ tables
    def _load(self, name: str) -> pd.DataFrame:
        path = os.path.join(self.dir, f"{name}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found")
        # pandas' default CSV float converter is fast but not exact: it can
        # land one ulp away from the value that was written, which shows up
        # as a last-digit disagreement against numbers a notebook computed
        # for itself.  'round_trip' returns the original float64 exactly.
        return pd.read_csv(path, float_precision="round_trip")

    @cached_property
    def iterations(self) -> pd.DataFrame:
        """One row per pipeline iteration (replaces ``info_*.json``)."""
        return self._load("iterations")

    @cached_property
    def benchmarks(self) -> pd.DataFrame:
        """One row per benchmark record (replaces the ``benchmark_*.db``)."""
        return self._load("benchmarks")

    @cached_property
    def schema(self) -> dict:
        """Column types the CSV tables cannot carry on their own.

        ``pandas`` widens any column with a missing value to ``float``, so
        ``consolidated_results/schema.json`` records which benchmark fields were integers
        in the original records.
        """
        import json as _json

        path = os.path.join(self.dir, "schema.json")
        if not os.path.isfile(path):
            return {}
        try:
            with open(path) as fh:
                return _json.load(fh)
        except (OSError, ValueError):
            return {}

    # ------------------------------------------------------ path-keyed API
    #
    # The notebooks address results by directory, e.g.
    # ``<run>/intermediate_iterations`` or ``<run>/counts``.  The helpers
    # below accept exactly those paths, so a notebook cell only has to swap
    # its file-walking body for a single call while keeping its own path
    # variables untouched.

    @property
    def root(self) -> str:
        """The directory that contains ``consolidated_results/`` (the release root)."""
        return os.path.dirname(os.path.abspath(self.dir))

    def _with_dirpath(self, df: pd.DataFrame) -> pd.DataFrame:
        if "dirpath" not in df.columns:
            df = df.copy()
            df["dirpath"] = [
                os.path.normpath(os.path.join(self.root, t, r))
                for t, r in zip(df["tree"], df["run"])
            ]
        return df

    @cached_property
    def _iterations_pathed(self) -> pd.DataFrame:
        return self._with_dirpath(self.iterations)

    def iters_for_dir(self, path: str,
                      last_only: bool = False) -> pd.DataFrame:
        """Iteration rows that came from *path* (an ``intermediate_iterations``
        directory). Returns an empty frame if nothing matches."""
        d = self._iterations_pathed
        target = os.path.normpath(os.path.abspath(path))
        out = d[d["dirpath"] == target]
        if last_only:
            out = out[out["is_last"]]
        return out

    # --------------------------------------------------------- drop-ins
    def weighted_energy_iterations(self, inter_dir: str,
                                   gt_dict: dict) -> pd.DataFrame:
        """Mean final ``|W|`` per instance, from the iterations table.

        Drop-in for the notebooks' ``load_qredumis_weighted_energy``.
        Returns ``N, seed, weighted_avg_IS, gt_mis, weighted_ar, n_trials``.
        """
        d = self.iters_for_dir(inter_dir, last_only=True)
        rows = []
        for (N, seed), grp in d.groupby(["N", "seed"], sort=True):
            gt_size = gt_dict.get((int(N), int(seed)))
            if gt_size is None or gt_size == 0:
                continue
            avg_is = grp["len_W"].mean()
            rows.append({
                "N": int(N), "seed": int(seed),
                "weighted_avg_IS": avg_is,
                "gt_mis": gt_size,
                "weighted_ar": avg_is / gt_size,
                "n_trials": int(len(grp)),
            })
        return pd.DataFrame(rows)

    def final_W_by_cshot(self, inter_dir: str) -> dict:
        """``cshot -> final |W|`` for a single-instance run directory."""
        d = self.iters_for_dir(inter_dir, last_only=True)
        return {int(r.cshot): int(r.len_W) for r in d.itertuples()}

    def W_sizes_by_seed(self, inter_dir: str) -> dict:
        """``seed -> [final |W| per cshot]`` for a multi-instance run."""
        d = self.iters_for_dir(inter_dir, last_only=True)
        out: dict[int, list[int]] = {}
        for r in d.itertuples():
            out.setdefault(int(r.seed), []).append(int(r.len_W))
        return out

    def trajectory_entries(self, inter_dir: str) -> dict:
        """``(N, seed) -> [(iteration, cshot, used_qpu, len_W, len_S), ...]``.

        Supplies everything the optTTS notebook's temp-directory adapter needs
        to rebuild the layout ``postprocess_qredumis`` expects.  ``used_qpu``
        mirrors ``("quantum selected" in info) or ("quantum kernel" in info)``.
        """
        d = self.iters_for_dir(inter_dir)
        out: dict[tuple[int, int], list] = {}
        for r in d.itertuples():
            used_qpu = bool(r.has_quantum_selected) or bool(
                r.has_quantum_kernel
            )
            out.setdefault((int(r.N), int(r.seed)), []).append(
                (int(r.iteration), int(r.cshot), used_qpu,
                 int(r.len_W), int(r.len_S))
            )
        return out

    # --------------------------------------------------------- run discovery
    @cached_property
    def _known_dirpaths(self) -> list[str]:
        """Every run directory recorded in any derived table."""
        seen: set[str] = set()
        for name in ("iterations", "counts", "benchmarks"):
            path = os.path.join(self.dir, name + ".csv")
            if not os.path.isfile(path):
                continue
            t = pd.read_csv(path, usecols=["tree", "run"]).drop_duplicates()
            for tree, run in t.itertuples(index=False):
                seen.add(os.path.normpath(os.path.join(self.root, tree, run)))
        return sorted(seen)

    def known_dirs(self, pattern: str) -> list[str]:
        """Recorded run directories matching a shell *pattern*, sorted.

        Drop-in for ``sorted(glob.glob(pattern))`` once the directories have
        been removed along with the raw files they held.  Wildcards do not
        cross path separators, so the result matches what ``glob`` returned.
        """
        import fnmatch

        pat = os.path.normpath(os.path.abspath(pattern))
        depth = pat.count(os.sep)
        return [d for d in self._known_dirpaths
                if d.count(os.sep) == depth and fnmatch.fnmatch(d, pat)]

    # --------------------------------------------- counts / db reconstruction
    @cached_property
    def _counts_raw(self) -> pd.DataFrame:
        """``counts`` with node ids preserved verbatim as strings."""
        path = os.path.join(self.dir, "counts.csv")
        df = pd.read_csv(path, dtype={"nodes": str},
                         keep_default_na=False, na_values=[])
        df["dirpath"] = [
            os.path.normpath(os.path.join(self.root, t, r))
            for t, r in zip(df["tree"], df["run"])
        ]
        return df

    def counts_records(self, counts_dir: str, N: int, seed: int,
                       p: int | None = None) -> list[dict]:
        """Rebuild one ``clean_counts_N*_seed*_p*.json`` exactly.

        Returns ``[{"nodes": [...], "count": n}, ...]`` in the original file
        order, so anything that expands the entries into a per-shot array -
        notably ``utils.utils_postproc.compute_metrics`` and its bootstrap -
        sees precisely the input it saw before consolidation.
        """
        d = self._counts_raw
        target = os.path.normpath(os.path.abspath(counts_dir))
        sel = d[(d["dirpath"] == target) & (d["N"] == N) & (d["seed"] == seed)]
        if p is not None:
            sel = sel[sel["p"] == p]
        if sel.empty:
            return []
        sel = sel.sort_values("order")
        return [
            {"nodes": r.nodes.split(NODE_SEP) if r.nodes else [],
             "count": int(r.count)}
            for r in sel.itertuples()
        ]

    def counts_instances(self, counts_dir: str) -> list[tuple[int, int, int]]:
        """``(N, seed, p)`` triples available for a ``counts/`` directory.

        Replaces ``sorted(glob('clean_counts_*.json'))`` + filename parsing,
        and reproduces that call's *lexicographic* order (``seed10`` before
        ``seed9``) so loops that share an RNG across instances draw the same
        numbers as before consolidation.
        """
        d = self._counts_raw
        target = os.path.normpath(os.path.abspath(counts_dir))
        sel = d[d["dirpath"] == target]
        if sel.empty:
            return []
        out = [(int(a), int(b), int(c)) for a, b, c in
               sel[["N", "seed", "p"]].drop_duplicates().itertuples(index=False)]
        return sorted(out, key=lambda t: counts_filename(*t))

    def db_records(self, db_path: str) -> list[dict]:
        """Rebuild the ``result_json`` records of one ``benchmark_*.db``.

        Returns the decoded dicts in their original row order, so a cell that
        did ``sqlite3.connect(db).execute("SELECT result_json FROM results")``
        and then ``json.loads`` can read them unchanged.
        """
        import json as _json

        b = self.benchmarks
        name = os.path.basename(db_path)
        parent = os.path.normpath(os.path.abspath(os.path.dirname(db_path)))
        dirpaths = [
            os.path.normpath(os.path.join(self.root, t, r))
            for t, r in zip(b["tree"], b["run"])
        ]
        sel = b[(b["db"] == name) & pd.Series(
            [d == parent for d in dirpaths], index=b.index)]
        if sel.empty:
            return []
        sel = sel.sort_values("order")
        drop = {"tree", "run", "db", "order"}
        bench_schema = self.schema.get("benchmarks", {})
        ints = set(bench_schema.get("int_columns", ()))
        key_orders = bench_schema.get("key_orders", ())
        out = []
        for row in sel.to_dict("records"):
            rec = {}
            for k, v in row.items():
                if k in drop or v is None or (isinstance(v, float)
                                              and pd.isna(v)):
                    continue
                if isinstance(v, str) and v[:1] in "[{":
                    try:
                        v = _json.loads(v)
                    except ValueError:
                        pass
                elif k in ints:
                    v = int(v)
                rec[k] = v
            # Restore the field order the record had in the database, so a
            # DataFrame built from these dicts keeps its original columns.
            for order in key_orders:
                if set(order) == set(rec):
                    rec = {k: rec[k] for k in order}
                    break
            out.append(rec)
        return out

    def db_frame(self, db_path: str) -> pd.DataFrame:
        """``pandas`` view of a ``benchmark_*.db``.

        Mirrors ``utils.utils_db.make_df_from_db``: one row per record, list
        fields decoded back into real lists.
        """
        return pd.DataFrame(self.db_records(db_path))

    def db_available(self, db_path: str) -> bool:
        """Whether ``db_path`` can be read, from SQLite *or* from derived.

        Drop-in for the ``os.path.exists(db)`` guards that used to decide
        whether a benchmark database was part of a run.
        """
        return os.path.isfile(db_path) or bool(self.db_records(db_path))

    # -------------------------------------------------- flat benchmark JSON
    @cached_property
    def flat_json(self) -> pd.DataFrame:
        """One row per record of the flat 3-regular benchmark JSON files."""
        return self._load("flat_json")

    def _flat_key(self, path: str) -> str:
        """Normalise *path* to the ``tree/name`` key used by the table."""
        p = os.path.normpath(os.path.abspath(path))
        root = os.path.normpath(os.path.abspath(self.root))
        if p.startswith(root + os.sep):
            p = os.path.relpath(p, root)
        return p.replace(os.sep, "/")

    def json_records(self, path: str) -> list[dict]:
        """Rebuild the records of one flat benchmark JSON file.

        Field order and integer types are restored from
        ``consolidated_results/schema.json``, so the dicts match what ``json.load`` used
        to return for *path*.
        """
        import json as _json

        key = self._flat_key(path)
        d = self.flat_json
        sel = d[d["file"] == key]
        if sel.empty:
            return []
        sel = sel.sort_values("order")
        flat_schema = self.schema.get("flat_json", {})
        # Field types are recorded per file: these files disagree with each
        # other about whether e.g. `seed` is an int or a string, so the
        # merged column is object-typed and every value in it reads back as
        # a string.  Restore the type *this* file used.
        types = flat_schema.get("types_by_file", {}).get(key, {})
        key_orders = flat_schema.get("key_orders", ())
        casts = {"int": int, "float": float, "str": str, "bool": bool}
        out = []
        for row in sel.to_dict("records"):
            rec = {}
            for k, v in row.items():
                if k in ("file", "order") or v is None or (
                        isinstance(v, float) and pd.isna(v)):
                    continue
                t = types.get(k)
                if t == "json":
                    if isinstance(v, str):
                        try:
                            v = _json.loads(v)
                        except ValueError:
                            pass
                elif t in casts:
                    try:
                        v = casts[t](v)
                    except (TypeError, ValueError):
                        pass
                elif isinstance(v, str) and v[:1] in "[{":
                    try:
                        v = _json.loads(v)
                    except ValueError:
                        pass
                rec[k] = v
            for order in key_orders:
                if set(order) == set(rec):
                    rec = {k: rec[k] for k in order}
                    break
            out.append(rec)
        return out

    def json_frame(self, path: str) -> pd.DataFrame:
        """Drop-in replacement for ``pandas.read_json(path)``.

        For every file a notebook reads, the table stores the frame
        ``read_json`` produced, together with its column order and dtypes,
        so this returns that frame unchanged.  (``read_json`` parses doubles
        with its own routine, which disagrees with ``json.loads`` in the last
        bit for some values; the published figures came through
        ``read_json``, so that is what is preserved.)
        """
        import io
        import json as _json

        key = self._flat_key(path)
        flat_schema = self.schema.get("flat_json", {})
        kind = flat_schema.get("kinds", {}).get(key, "array")
        spec = flat_schema.get("types_by_file", {}).get(key, {})

        if kind == "frame":
            d = self.flat_json
            sel = d[d["file"] == key]
            if sel.empty:
                raise FileNotFoundError(
                    f"no consolidated_results/flat_json.csv rows for {path!r}"
                )
            sel = sel.sort_values("order")
            cols = spec.get("columns", [])
            dtypes = spec.get("dtypes", {})
            out = sel[cols].reset_index(drop=True)
            for col in cols:
                want = dtypes.get(col)
                if want == "object":
                    # Lists were JSON-encoded on the way in.
                    out[col] = [
                        _json.loads(v) if isinstance(v, str)
                        and v[:1] in "[{" else v
                        for v in out[col]
                    ]
                elif want and str(out[col].dtype) != want:
                    try:
                        out[col] = out[col].astype(want)
                    except (TypeError, ValueError):
                        pass
            return out

        recs = self.json_records(path)
        if not recs:
            raise FileNotFoundError(
                f"no consolidated_results/flat_json.csv rows for {path!r}"
            )
        if kind == "lines":
            text = "\n".join(_json.dumps(r) for r in recs)
            return pd.read_json(io.StringIO(text), lines=True)
        if kind == "object":
            text = _json.dumps(recs[0])
        else:
            text = _json.dumps(recs)
        return pd.read_json(io.StringIO(text))

    def json_available(self, path: str) -> bool:
        """Whether *path* can be read, from disk *or* from derived.

        Drop-in for the ``os.path.exists(f)`` guards around the flat
        benchmark JSON files.
        """
        if os.path.isfile(path):
            return True
        d = self.flat_json
        return bool((d["file"] == self._flat_key(path)).any())


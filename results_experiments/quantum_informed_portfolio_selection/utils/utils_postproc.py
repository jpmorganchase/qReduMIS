###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
utils_postproc — Post-processing utilities for experiment results
=================================================================

Functions for computing performance metrics (success probability,
approximation ratio, optTTS) from MIS measurement counts, with
optional bootstrap confidence intervals.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import os
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd


def _fmt_p(x: float) -> str:
    """Format a probability: .2f unless <0.01, then .2e."""
    if x < 0.01 and x > 0:
        return f"{x:.2e}"
    return f"{x:.2f}"

def compute_metrics(G, gt_size, counts, n_bootstrap=0, seed=42, p_d=0.99):
    """
    Compute success probability and expected approximation ratio,
    optionally with bootstrap 95% confidence intervals.

    Parameters
    ----------
    G : nx.Graph
        The graph (kernel).
    gt_size : int
        Ground truth MIS size alpha(G).
    counts : list[dict]
        List of {"nodes": [...], "count": N}.
    n_bootstrap : int
        If > 0, resample individual shots B times and return 95% CIs.
    seed : int
        RNG seed for reproducibility.
    p_d : float
        Desired success probability used in the optTTS formula
        optTTS = log(1 - p_d) / log(1 - p_success)  (default 0.99).

    Returns
    -------
    dict with keys:
        p_success, approx_ratio, n_success, total_shots, valid_shots
        If n_bootstrap > 0, also:
        p_success_ci, approx_ratio_ci  (each a (lo, hi) tuple)
    """
    # ── Expand counts into per-shot arrays ────────────────────────────
    shot_sizes = []    # IS size per shot
    shot_valid = []    # 1 if valid IS, else 0
    shot_success = []  # 1 if valid IS of size == gt_size

    for e in counts:
        nodes = e["nodes"]
        cnt = e["count"]
        sz = len(nodes)
        is_valid = not any(
            G.has_edge(u, v)
            for i, u in enumerate(nodes) for v in nodes[i+1:]
        )
        for _ in range(cnt):
            shot_sizes.append(sz)
            shot_valid.append(1 if is_valid else 0)
            shot_success.append(1 if (is_valid and sz == gt_size) else 0)

    shot_sizes = np.array(shot_sizes)
    shot_valid = np.array(shot_valid)
    shot_success = np.array(shot_success)
    total_shots = len(shot_sizes)

    # ── Point estimates ───────────────────────────────────────────────
    n_success = int(shot_success.sum())
    valid_shots = int(shot_valid.sum())
    valid_weighted_size = int((shot_sizes * shot_valid).sum())

    p_success = n_success / total_shots if total_shots else 0
    approx_ratio = (valid_weighted_size / valid_shots) / gt_size if valid_shots else 0

    # ── optTTS = log(1 - p_d) / log(1 - p_success) ────────────────────
    opt_tts = np.log(1 - p_d) / np.log(1 - p_success) if p_success > 0 else np.inf

    result = {
        "p_success": p_success,
        "approx_ratio": approx_ratio,
        "opt_tts": opt_tts,
        "n_success": n_success,
        "total_shots": total_shots,
        "valid_shots": valid_shots,
    }

    # ── Bootstrap CIs ────────────────────────────────────────────────
    if n_bootstrap > 0:
        rng = np.random.default_rng(seed)
        boot_ps = np.empty(n_bootstrap)
        boot_ar = np.empty(n_bootstrap)
        boot_tts = np.empty(n_bootstrap)

        for b in range(n_bootstrap):
            idx = rng.choice(total_shots, size=total_shots, replace=True)
            b_success = shot_success[idx]
            b_valid = shot_valid[idx]
            b_sizes = shot_sizes[idx]

            ps_b = b_success.sum() / total_shots
            boot_ps[b] = ps_b
            boot_tts[b] = np.log(1 - p_d) / np.log(1 - ps_b) if ps_b > 0 else np.inf
            v = b_valid.sum()
            if v > 0:
                boot_ar[b] = ((b_sizes * b_valid).sum() / v) / gt_size
            else:
                boot_ar[b] = 0.0

        result["p_success_ci"] = (
            float(np.percentile(boot_ps, 2.5)),
            float(np.percentile(boot_ps, 97.5)),
        )
        result["approx_ratio_ci"] = (
            float(np.percentile(boot_ar, 2.5)),
            float(np.percentile(boot_ar, 97.5)),
        )
        # For optTTS CI, use finite resamples only
        finite_tts = boot_tts[np.isfinite(boot_tts)]
        if len(finite_tts) > 0:
            result["opt_tts_ci"] = (
                float(np.percentile(finite_tts, 2.5)),
                float(np.percentile(finite_tts, 97.5)),
            )
        else:
            result["opt_tts_ci"] = (np.inf, np.inf)
        result["_boot_ps"] = boot_ps
        result["_boot_ar"] = boot_ar
        result["_boot_tts"] = boot_tts

    return result


# ══════════════════════════════════════════════════════════════════════════
# qReduMIS postprocessing
# ══════════════════════════════════════════════════════════════════════════

def postprocess_qredumis(
    output_dir: str,
    instance: str,
    n_cshots: int = 20,
    p_d: float = 0.99,
    quantum_shots: int = 1,
    n_bootstrap: int = 0,
    seed: int = 42,
    verbose: bool = True,
    plot: bool = False,
    save_fig: str | None = None,
) -> dict:
    """
    Postprocess qReduMIS pipeline results for a single instance.

    Collects per-cshot trajectories across all available iterations and
    computes figures of merit: success probability, expected approximation
    ratio, and optTTS.  Optionally bootstraps 95% CIs over the cshots.

    Parameters
    ----------
    output_dir : str
        Pipeline output directory (contains iteration_0/, iteration_1/, ...,
        ground_truth/).
    instance : str
        Instance filename, e.g.
        "graph_unweighted_dax_N85_seed0_thres0.24.graphml".
    n_cshots : int
        Number of classical shots.
    p_d : float
        Desired probability for optTTS (default 0.99).
    quantum_shots : int
        Number of quantum shots per QPU call.  The runtime t_f used in the
        optTTS / practical-TTS formulas is expressed in **total quantum
        shots** = (QPU calls to optimal) * quantum_shots, rather than in
        QPU calls.  Default 1 (i.e. t_f counted in QPU calls).
    n_bootstrap : int
        If > 0, resample cshots with replacement B times for 95% CIs.
    seed : int
        RNG seed for bootstrap reproducibility.
    verbose : bool
        Print summary tables and evolution.
    plot : bool
        If True, show a 2-panel figure (|W| per cshot, QPU calls to optimal).
    save_fig : str or None
        If given, save the figure to this path (implies plot=True).

    Returns
    -------
    dict with keys:
        df             -- per-cshot DataFrame
        p_success      -- point estimate
        mean_ar        -- point estimate
        opt_tts        -- point estimate
        opt_tf         -- QPU calls at which optTTS is achieved
        practical_tts  -- fixed-cost TTS
        available_iters, GT_MIS, n_cshots, p_d
        If n_bootstrap > 0, also:
            p_success_ci, mean_ar_ci, opt_tts_ci  (lo, hi) tuples
            _boot_ps, _boot_ar, _boot_tts  arrays
    """
    # ── Load ground truth ─────────────────────────────────────────────
    gt_path = os.path.join(output_dir, "ground_truth", f"{instance}.json")
    with open(gt_path) as f:
        GT_MIS = json.load(f)["ground_truth_mis_size"]

    # ── Discover available iterations ─────────────────────────────────
    available_iters = sorted(
        int(d.replace("iteration_", ""))
        for d in os.listdir(output_dir)
        if d.startswith("iteration_")
        and os.path.isdir(os.path.join(output_dir, d))
    )
    MAX_ITER = max(available_iters)

    # ── Collect per-cshot trajectory ──────────────────────────────────
    records = []
    for c in range(n_cshots):
        cshot_dir_name = f"{instance}_cshot{c}"
        history = []
        qpu_calls = 0
        first_optimal_qpu = np.inf

        for it in available_iters:
            cshot_path = os.path.join(
                output_dir, f"iteration_{it}", cshot_dir_name
            )
            if not os.path.isdir(cshot_path):
                break

            files = os.listdir(cshot_path)

            if "optimal_found.json" in files:
                with open(os.path.join(cshot_path, "optimal_found.json")) as f:
                    info = json.load(f)
                status = "optimal_found"
                used_qpu = False
            elif "fully_reducible.json" in files:
                with open(os.path.join(cshot_path, "fully_reducible.json")) as f:
                    info = json.load(f)
                status = "fully_reducible"
                used_qpu = False
            elif "after.json" in files:
                with open(os.path.join(cshot_path, "after.json")) as f:
                    info = json.load(f)
                status = "completed"
                used_qpu = True
            else:
                continue

            if used_qpu:
                qpu_calls += 1

            W_size = len(info["W"])
            S_size = len(info["S"])

            if W_size >= GT_MIS and np.isinf(first_optimal_qpu):
                first_optimal_qpu = qpu_calls

            history.append({
                "iteration": it,
                "status": status,
                "W_size": W_size,
                "S_size": S_size,
                "qpu_calls_cum": qpu_calls,
                "used_qpu": used_qpu,
            })

        if history:
            final = history[-1]
            records.append({
                "cshot": c,
                "final_iter": final["iteration"],
                "final_W": final["W_size"],
                "final_S": final["S_size"],
                "final_status": final["status"],
                "total_qpu_calls": qpu_calls,
                "is_optimal": final["W_size"] >= GT_MIS,
                "approx_ratio": final["W_size"] / GT_MIS,
                "qpu_calls_to_optimal": first_optimal_qpu,
                "history": history,
            })

    df = pd.DataFrame(records)

    # ── Figures of merit ──────────────────────────────────────────────
    n_optimal = int(df["is_optimal"].sum())
    p_success = n_optimal / len(df)
    mean_ar = df["approx_ratio"].mean()

    # optTTS (rank-based estimator)
    success_mask = np.isfinite(df["qpu_calls_to_optimal"].values)
    success_rts = df.loc[success_mask, "qpu_calls_to_optimal"].values.astype(float)
    n_total = len(df)

    opt_tf = np.inf
    if len(success_rts) == 0:
        opt_tts = np.inf
    else:
        # t_f measured in total quantum shots = QPU calls * quantum_shots
        sorted_rt = np.sort(success_rts) * quantum_shots
        ranks = np.arange(1, len(sorted_rt) + 1)
        ps = (ranks - 0.5) / n_total
        tts = sorted_rt * np.log(1 - p_d) / np.log(1 - ps)
        best_idx = int(np.argmin(tts))
        opt_tts = tts[best_idx]
        opt_tf = sorted_rt[best_idx]

    # Practical TTS
    if p_success > 0:
        # avg cost in total quantum shots = mean QPU calls * quantum_shots
        avg_cost = (
            df.loc[df["is_optimal"], "qpu_calls_to_optimal"].mean()
            * quantum_shots
        )
        # p_success == 1 gives log(0) = -inf and a TTS of 0; silence the
        # expected divide-by-zero warning instead of printing it.
        with np.errstate(divide="ignore"):
            practical_tts = avg_cost * np.log(1 - p_d) / np.log(1 - p_success)
    else:
        avg_cost = np.inf
        practical_tts = np.inf

    result = {
        "df": df,
        "GT_MIS": GT_MIS,
        "available_iters": available_iters,
        "n_cshots": n_cshots,
        "p_d": p_d,
        "quantum_shots": quantum_shots,
        "p_success": p_success,
        "n_optimal": n_optimal,
        "mean_ar": mean_ar,
        "opt_tts": opt_tts,
        "opt_tf": opt_tf,
        "practical_tts": practical_tts,
    }

    # ── Bootstrap CIs over cshots ─────────────────────────────────────
    if n_bootstrap > 0:
        rng = np.random.default_rng(seed)
        is_opt_vec = df["is_optimal"].values.astype(float)
        ar_vec = df["approx_ratio"].values
        qpu_opt_vec = df["qpu_calls_to_optimal"].values

        boot_ps = np.empty(n_bootstrap)
        boot_ar = np.empty(n_bootstrap)
        boot_tts = np.empty(n_bootstrap)

        for b in range(n_bootstrap):
            idx = rng.choice(n_cshots, size=n_cshots, replace=True)
            boot_ps[b] = is_opt_vec[idx].mean()
            boot_ar[b] = ar_vec[idx].mean()
            # optTTS from resampled cshots
            sample = qpu_opt_vec[idx]
            fin = sample[np.isfinite(sample)]
            if len(fin) == 0:
                boot_tts[b] = np.inf
            else:
                # t_f in total quantum shots = QPU calls * quantum_shots
                srt = np.sort(fin) * quantum_shots
                ranks = np.arange(1, len(srt) + 1)
                ps_b = (ranks - 0.5) / n_cshots
                tts_b = srt * np.log(1 - p_d) / np.log(1 - ps_b)
                boot_tts[b] = tts_b.min()

        result["p_success_ci"] = (
            float(np.percentile(boot_ps, 2.5)),
            float(np.percentile(boot_ps, 97.5)),
        )
        result["mean_ar_ci"] = (
            float(np.percentile(boot_ar, 2.5)),
            float(np.percentile(boot_ar, 97.5)),
        )
        finite_tts = boot_tts[np.isfinite(boot_tts)]
        if len(finite_tts) > 0:
            result["opt_tts_ci"] = (
                float(np.percentile(finite_tts, 2.5)),
                float(np.percentile(finite_tts, 97.5)),
            )
        else:
            result["opt_tts_ci"] = (np.inf, np.inf)
        result["_boot_ps"] = boot_ps
        result["_boot_ar"] = boot_ar
        result["_boot_tts"] = boot_tts

    # ── Print summary ─────────────────────────────────────────────────
    if verbose:
        print(f"Ground truth (kernel MIS): {GT_MIS}")
        print(f"Available iterations: {available_iters}  (max = {MAX_ITER})")
        print(f"\n{'='*65}")
        print(f"  Figures of merit  (cshots={n_cshots}, p_d={p_d}, "
              f"quantum_shots={quantum_shots})")
        print(f"{'='*65}")
        print(f"  p_S          = {n_optimal}/{n_cshots} = {_fmt_p(p_success)}", end="")
        if "p_success_ci" in result:
            lo, hi = result["p_success_ci"]
            print(f"   95% CI [{_fmt_p(lo)}, {_fmt_p(hi)}]")
        else:
            print()
        print(f"  <AR>         = {mean_ar:.2f}", end="")
        if "mean_ar_ci" in result:
            lo, hi = result["mean_ar_ci"]
            print(f"   95% CI [{lo:.2f}, {hi:.2f}]")
        else:
            print()
        tts_s = f"{opt_tts:.2f}" if np.isfinite(opt_tts) else "inf"
        print(f"  optTTS       = {tts_s}", end="")
        if "opt_tts_ci" in result:
            lo, hi = result["opt_tts_ci"]
            lo_s = f"{lo:.2f}" if np.isfinite(lo) else "inf"
            hi_s = f"{hi:.2f}" if np.isfinite(hi) else "inf"
            print(f"   95% CI [{lo_s}, {hi_s}]")
        else:
            print()
        print(f"  practical TTS= {practical_tts:.2f}")
        print(f"{'='*65}")

        cols = [
            "cshot", "final_iter", "final_W", "total_qpu_calls",
            "qpu_calls_to_optimal", "is_optimal", "approx_ratio",
            "final_status",
        ]
        print(f"\nPer-cshot summary:")
        print(df[cols].to_string(index=False))

        print(f"\n{'-'*65}")
        print("Evolution across iterations:")
        for it in available_iters:
            w_at_it = []
            for _, row in df.iterrows():
                for h in row["history"]:
                    if h["iteration"] == it:
                        w_at_it.append(h["W_size"])
                        break
                else:
                    prev = [hh for hh in row["history"] if hh["iteration"] < it]
                    if prev:
                        w_at_it.append(prev[-1]["W_size"])
            if w_at_it:
                n_opt = sum(1 for w in w_at_it if w >= GT_MIS)
                cum_qpu = sum(
                    h["qpu_calls_cum"]
                    for _, r in df.iterrows()
                    for h in r["history"]
                    if h["iteration"] == it
                )
                print(
                    f"  After iter {it}: "
                    f"{n_opt}/{len(w_at_it)} optimal, "
                    f"mean |W| = {np.mean(w_at_it):.2f}, "
                    f"min |W| = {min(w_at_it)}, "
                    f"total QPU = {cum_qpu}"
                )

    # ── Plot ───────────────────────────────────────────────────────────
    if plot or save_fig:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(16, 5))

        # Panel 1: |W| per cshot
        ax = axes[0]
        bar_colors = [
            "tab:green" if row["is_optimal"] else "tab:red"
            for _, row in df.iterrows()
        ]
        ax.bar(df["cshot"], df["final_W"], color=bar_colors,
               edgecolor="k", linewidth=0.5)
        ax.axhline(GT_MIS, color="black", linewidth=1.5, linestyle="--",
                   label=f"GT = {GT_MIS}")
        ax.set_xlabel("cshot")
        ax.set_ylabel("|W| (incumbent IS size)")
        ax.set_title(f"Final |W| per cshot  (p_S = {p_success:.2f})")
        ax.legend()
        ax.set_xticks(range(n_cshots))
        ax.set_ylim(0, GT_MIS + 2)

        # Panel 2: QPU calls to optimal
        ax = axes[1]
        qpu_opt = df["qpu_calls_to_optimal"].copy()
        qpu_opt_plot = qpu_opt.replace(np.inf, MAX_ITER + 1)
        bar_colors2 = [
            "tab:green" if np.isfinite(q) else "tab:red"
            for q in qpu_opt.values
        ]
        ax.bar(df["cshot"], qpu_opt_plot, color=bar_colors2,
               edgecolor="k", linewidth=0.5)
        ax.set_xlabel("cshot")
        ax.set_ylabel("QPU calls to optimal")
        tts_label = f"{opt_tts:.2f}" if np.isfinite(opt_tts) else "inf"
        ax.set_title(f"QPU calls to solution  (optTTS = {tts_label})")
        ax.set_xticks(range(n_cshots))
        for i, q in enumerate(qpu_opt.values):
            if np.isinf(q):
                ax.text(i, MAX_ITER + 1 + 0.1, "\u221e", ha="center",
                        fontsize=12, fontweight="bold", color="red")

        plt.tight_layout()
        if save_fig:
            plt.savefig(save_fig, dpi=300, bbox_inches="tight")
        plt.show()

    return result
###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
TTS (Time-to-Solution) Estimation Utilities
============================================

Based on the operational definitions from:
  "qReduMIS: A Quantum-Informed Reduction Algorithm for the
   Maximum Independent Set Problem" (arXiv:2503.12551),
   Section II — Alternative Operational Definition.

Key formulas implemented
------------------------
Annealing-type optTTS (Section II, Eqs. 8–10):
    TTS(tf)  = tf · ln(1 − pd) / ln(1 − pS(tf))              [Eq. 8]
    pS(tf)   = (# trials with runtime(t) ≤ tf) / M            [Eq. 10]
    optTTS   = ln(1−pd) · min_{tf} tf / ln(1 − pS(tf))        [Eq. 6]

    Convention (from Sec. I): for sorted successful runtimes
    t1 ≤ t2 ≤ … ≤ t_Msuccess, use pS(ti) = (i − 0.5) / M.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import numpy as np
from typing import Optional


# ── Annealing-type TTS ──────────────────────────────────────────────────────


def compute_opt_tts(
    success_runtimes: np.ndarray,
    n_total: int,
    pd: float = 0.99,
) -> dict:
    """Compute optimal TTS via the annealing-type approach (Sec. II).

    Uses the convention pS(ti) = (i − 0.5) / M, where *i* is the
    rank in the sorted successful runtimes and *M* is the total
    number of trials.

    Parameters
    ----------
    success_runtimes : array-like
        Runtimes of *successful* trials only (need not be sorted).
    n_total : int
        Total number of trials (successful + failed).
    pd : float
        Desired probability (default 0.99).

    Returns
    -------
    dict
        opt_tts   – optimal TTS value
        opt_tf    – tf that achieves optTTS
        tts_curve – array of TTS(ti) for each successful trial
        tf_values – sorted runtimes of successful trials
        ps_values – corresponding pS(ti) values
    """
    sorted_rt = np.sort(np.asarray(success_runtimes, dtype=float))
    M = n_total
    n_success = len(sorted_rt)

    if n_success == 0:
        return dict(
            opt_tts=np.inf,
            opt_tf=np.inf,
            tts_curve=np.array([]),
            tf_values=np.array([]),
            ps_values=np.array([]),
        )

    ranks = np.arange(1, n_success + 1)
    ps = (ranks - 0.5) / M
    tts = sorted_rt * np.log(1 - pd) / np.log(1 - ps)

    best = int(np.argmin(tts))
    return dict(
        opt_tts=tts[best],
        opt_tf=sorted_rt[best],
        tts_curve=tts,
        tf_values=sorted_rt,
        ps_values=ps,
    )


# ── Bootstrap helpers ────────────────────────────────────────────────────────


def bootstrap_opt_tts(
    runtimes: np.ndarray,
    successes: np.ndarray,
    n_boot: int = 10_000,
    pd: float = 0.99,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Bootstrap the optimal TTS by resampling trials.

    Parameters
    ----------
    runtimes : array, shape (n_trials,)
        Runtime (cost) of every trial.
    successes : array, shape (n_trials,)
        Boolean — True if the trial found the optimal solution.
    n_boot : int
        Number of bootstrap resamples.
    pd : float
        Desired probability.
    rng : numpy Generator
        PRNG (default: seed 42).

    Returns
    -------
    np.ndarray, shape (n_boot,)
        Bootstrapped optTTS values.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    runtimes = np.asarray(runtimes, dtype=float)
    successes = np.asarray(successes, dtype=bool)
    n = len(runtimes)

    boot_tts = np.full(n_boot, np.inf)
    for b in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        s_rt = runtimes[idx][successes[idx]]
        result = compute_opt_tts(s_rt, n, pd)
        boot_tts[b] = result["opt_tts"]
    return boot_tts

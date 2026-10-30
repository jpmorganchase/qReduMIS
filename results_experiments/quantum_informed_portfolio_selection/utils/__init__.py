###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
utils — Helper modules for reproducing paper figures
=====================================================

This package contains utility functions for:

- **solver_baseline**: Exact MIS solver via Google OR-Tools (ground truth).
- **tts_utils**: Time-to-solution (TTS) estimation formulas.
- **opt_tts_estimator**: General optTTS estimator for multiple method types.
- **mis_degeneracy**: Efficient independent set counting via backtracking.
- **utils_db**: SQLite database helpers for emulator experiment results.
- **utils_po**: Portfolio optimization data loading and thresholding.
- **utils_postproc**: Post-processing metrics (success prob., approx. ratio).
- **derived**: Readers for the tables in ``consolidated_results/``.

SPDX-License-Identifier: Apache-2.0
"""

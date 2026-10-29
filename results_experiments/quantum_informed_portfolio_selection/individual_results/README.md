# Individual experiment results

This file is the small, directly read hardware input needed to reproduce the
DAX figure. 

## DAX hardware measurements

| File | Contents and consumer |
| --- | --- |
| [`hardware_counts/dax/dax_measurement_counts_raw.json`](hardware_counts/dax/dax_measurement_counts_raw.json) | Raw DAX hardware measurement outcomes (node sets and their counts), before MIS repair; read by the DAX Helios notebook. |

The Helios results of Fig. 3 and Table `tab:performance_results` are point
estimates with 95% bootstrap CIs computed from the raw per-shot hardware
results (not part of this release); `notebooks/performance_PSP-MIS_Helios.ipynb`
lists them directly.

Other strings in notebooks beginning with `results/` or `data/` can be
*historical lookup keys* for the [`../consolidated_results/`](../consolidated_results/)
tables, not additional files to download; see the
[parent README](../README.md#paths-that-are-keys-not-files).

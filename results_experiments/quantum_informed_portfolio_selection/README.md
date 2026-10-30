# Reproducing the Figures — End-to-End Pipeline for Quantum-Informed Portfolio Selection

This folder contains notebooks, data, and helper modules for reproducing the
figures listed below. Figure 15 (the ReduMIS+SA comparison) is not included:
its notebook and dedicated results have been removed. Each notebook keeps only
the cells needed for the paper figures and tables it reproduces.

> **End-to-End Pipeline for Quantum-Informed Portfolio Selection**
> R. Yalovetzky, M. J. A. Schuetz, Z. He, J. Shen, Y. Sun, R. Raymond,
> S. Sahay, K. Perla, R. S. Andrist, G. Salton, H. G. Katzgraber,
> R. Bongiovanni, N. Kumar, R. Otter (2026)

All paths are relative to this directory.

---

## Quick Start

Python 3.11 is required (as for the qReduMIS package).

```bash
# 1. Install the qReduMIS package and the notebook dependencies (Poetry)
cd <repository_root>
python3 -m pip install poetry   # or `pipx install poetry`
poetry install --with paper     # if `poetry` is not found: python3 -m poetry install --with paper

# 2a. Open the notebooks in VS Code or JupyterLab and select the Poetry
#     environment as kernel (its location: `poetry env info --path`), or
# 2b. execute a notebook headless:
poetry run jupyter nbconvert --to notebook --execute --inplace \
    results_experiments/quantum_informed_portfolio_selection/notebooks/<notebook>.ipynb
```

Without Poetry, install the same pinned versions with pip:

```bash
cd <repository_root>
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .     # the qReduMIS package and its core dependencies
pip install -r results_experiments/quantum_informed_portfolio_selection/requirements.txt
```

Kernels must start in `notebooks/`, which is the default for Jupyter,
VS Code and `nbconvert`.

Every notebook defines `SAVE_FIGURES` near the top; it is `False` in the
shipped notebooks. Set it to `True` to write the figures as PNG files to
`figures/`, which is created on demand.

**The notebooks ship executed**: every notebook carries the text output and
the plots of a full reference run, so the figures can be inspected without
running anything. No separate figure files are shipped.

The shipped outputs were produced in a fresh environment installed with the
pip commands above (Python 3.11.9, numpy 1.23.5, scipy 1.14.1,
matplotlib 3.7.1, pandas 2.3.3, networkx 2.8.8). With other library
versions the printed numbers stay the same, but plot rendering can differ
slightly.

---

## Figure in paper → Notebook Mapping

### Main Text

| Fig | Description | Notebook |
|-----|-------------|----------|
| 1 | End-to-end pipeline diagram | hand-drawn schematic — not included, see paper |
| 2 | qReduMIS algorithm schematic | hand-drawn schematic — not included, see paper |
| 3 | Helios hardware results (success probability, AR) across 4 indices — also Table `tab:performance_results` | `notebooks/performance_PSP-MIS_Helios.ipynb` |
| 4 | DAX frozen-node signal from QAOA measurements | `notebooks/performance_PSP-MIS_DAX_Helios.ipynb` |
| 5 | optTTS scaling: QAOA vs qReduMIS (p=2, p=6) — also Table `tab:individual-fits` | `notebooks/performance_systematic_PSP-MIS_optTTS.ipynb` |
| 6 | Expected approximation ratio vs kernel size | `notebooks/performance_systematic_PSP-MIS_optTTS.ipynb` |

### Appendix

| Fig | Description | Notebook |
|-----|-------------|----------|
| 7 | Market graph testbed (kernel size vs input size) | `notebooks/market_graph_generator.ipynb` |
| 8 | Testbed: kernel size & density per kernel-size interval — also Table `tab:num_seeds_mkt_emulator` | `notebooks/performance_systematic_PSP-MIS_optTTS.ipynb` |
| 9 | Heatmap: fraction of instances with optTTS = ∞ | `notebooks/performance_systematic_PSP-MIS_optTTS.ipynb` |
| 10 | Success probability box plot (p=2, p=6) | `notebooks/performance_systematic_PSP-MIS_optTTS.ipynb` |
| 11 | QPU calls to solution distribution | `notebooks/performance_systematic_PSP-MIS_optTTS.ipynb` |
| 12 | Quantum shots sweep (N=30, seed=63) | `notebooks/performance_PSP-MIS_vs_qshots.ipynb` |
| 13 | Hardness vs correlation threshold (N=22) | `notebooks/performance_PSP-MIS_vs_hardness.ipynb` |
| 14 | Performance metrics vs hardness parameter H | `notebooks/performance_PSP-MIS_vs_hardness.ipynb` |
| 15 | ReduMIS+SA optTTS comparison | not included in this release |
| 16 | 3-regular (noiseless simulator): success prob. & quantum calls | `notebooks/performance_3regulargraphs_emulator_2.ipynb` |
| 17 | 3-regular: success prob., noisy emulator vs noiseless simulator | `notebooks/performance_3regulargraphs_emulator.ipynb` |
| 18 | 3-regular: QPU calls of qReduMIS on the emulator | `notebooks/performance_3regulargraphs_emulator.ipynb` |

Figures 3–14 and 16–18 are produced by the notebooks listed above and are
embedded in them; with `SAVE_FIGURES = True` they are also written to
`figures/` under the paper's file names. Figure 15 is not
reproduced by this release. Figures 1–2 are hand-drawn schematics, so no
notebook here regenerates them — see the paper.

---

## Directory Structure

```
quantum_informed_portfolio_selection/
│
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
│
├── notebooks/                          # Figure-generating notebooks (see table above)
│   ├── market_graph_generator.ipynb                  # Fig 7
│   ├── performance_3regulargraphs_emulator.ipynb     # Figs 17–18
│   ├── performance_3regulargraphs_emulator_2.ipynb   # Fig 16
│   ├── performance_PSP-MIS_DAX_Helios.ipynb          # Fig 4
│   ├── performance_PSP-MIS_Helios.ipynb              # Fig 3 + Table performance_results (published numbers)
│   ├── performance_PSP-MIS_vs_hardness.ipynb         # Figs 13–14
│   ├── performance_PSP-MIS_vs_qshots.ipynb           # Fig 12
│   └── performance_systematic_PSP-MIS_optTTS.ipynb   # Figs 5, 6, 8–11 + Tables individual-fits, num_seeds_mkt_emulator
│
├── utils/                              # Helper Python modules
│   ├── __init__.py
│   ├── solver_baseline.py              # Exact MIS solver (OR-Tools)
│   ├── tts_utils.py                    # TTS formulas (Eqs. 8–10 from paper)
│   ├── opt_tts_estimator.py            # General optTTS estimator
│   ├── mis_degeneracy.py               # Independent set counting (backtracking)
│   ├── derived.py                      # Readers for the consolidated_results/ tables
│   ├── utils_db.py                     # SQLite DB helpers for emulator results
│   ├── utils_po.py                     # Portfolio data loading & thresholding
│   └── utils_postproc.py               # Metrics: success prob., approx. ratio
│
├── consolidated_results/               # Consolidated result tables (see "Data Formats")
│   ├── iterations.csv                  # One row per pipeline iteration
│   ├── counts.csv                      # One row per distinct measured solution
│   ├── benchmarks.csv                  # benchmark_*.db records, flattened
│   ├── flat_json.csv                   # 3-regular benchmark result JSONs, flattened
│   └── schema.json                     # Column types CSV cannot carry on its own
│
├── problem_instances/                  # The graph instances the notebooks open
│   ├── market/                         # Main market testbed
│   │   └── graphs_N{26,28,…,38,44}/    #   graph_unweighted_{seed}.graphml
│   ├── market_extra/                   # Additional market instances, same layout
│   ├── density_sweep_N22/              # N=22 threshold sweep (+ generation_summary.json)
│   ├── density_sweep_N22_extra/        # Second, finer threshold sweep
│   ├── hardware/                       # DAX graph (Fig 4)
│   ├── registries/                     # Instance list & ground truths
│   │   ├── ground_truth_testbed.json
│   │   └── instances_March4.json
│   └── (port5.txt)                     # Not shipped: download it yourself from OR-Library (Fig 7 only)
│
├── individual_results/                 # Individually stored experiment results
│   ├── README.md                       # Purpose and consumer of each result file
│   └── hardware_counts/dax/            # DAX hardware measurement counts (Fig 4)
│       └── dax_measurement_counts_raw.json
```

For the meaning and consumer of **every file in `individual_results/`**, see the
[individual results file guide](individual_results/README.md).

**Both result directories feed the figure notebooks.** `consolidated_results/`
holds tables that combine many experimental runs and are queried via
`utils.derived.DerivedData`; `individual_results/` holds individual files
opened directly by notebooks (hardware data).
Strings such as `results/emulator_nikkei/...` are historical table keys,
not references to either renamed directory.

### Portfolio benchmark data provenance

The market graphs are built from the `port5` benchmark (NIKKEI 225, 225
assets) of
[J. E. Beasley's OR-Library portfolio test problems](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/portinfo.html),
introduced in Chang, Meade, Beasley and Sharaiha, *Heuristics for cardinality
constrained portfolio optimisation*, Computers & Operations Research 27 (2000),
1271–1302.

The data file is **not contained** with this release, and nothing in the
release downloads it. To run `notebooks/market_graph_generator.ipynb`
(Figure 7), download `port5.txt` yourself from the OR-Library page above
(direct link: <https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/port5.txt>)
and save it as `problem_instances/port5.txt` (git-ignored). Without it, the
notebook stops with these instructions. The OR-Library file was checked to
yield exactly the returns, standard deviations and correlation matrix used
for the published results.

**The market-graph instances used in the paper are contained**, so
`port5.txt` is not needed to reproduce the results:
`problem_instances/market/` and `problem_instances/market_extra/` hold the 73
market graphs (`N = 26 … 44`) as
`graphs_N{N}/graph_unweighted_{seed}.graphml`, and
`problem_instances/registries/` holds their ground-truth MIS sizes and kernel
sizes. The other notebooks read these files to reproduce the figures and
tables, and you can also use them as inputs for your own qReduMIS runs:

```python
import networkx as nx
G = nx.read_graphml("problem_instances/market/graphs_N26/graph_unweighted_4.graphml")
```

`port5.txt` is only needed to reproduce Figure 7 or to sample new market
graphs.

### Paths that are keys, not files

The raw per-run output of the emulator pipelines (per-iteration JSONs,
measurement-count JSONs and SQLite benchmark databases) is **not** shipped:
it was consolidated into `consolidated_results/` and removed. The notebooks
still address it by its original directory names, so
you will see strings like

```python
_D.db_records("data/data_3regular/results_emulator_qaoa_db_17Sep/benchmark_qaoa_3regular_graphs.db")
_D.json_frame("data/data_3regular/results/benchmark_qaoa_3regular_graphs_2025-09-11_p2.json")
```

These are **record keys into the `consolidated_results/` tables, not paths on disk** — the
directories they name no longer exist. In particular there is no `data/`
directory in this release: every string beginning `data/` is a key. The
shipped inputs all live under `problem_instances/`.


---

## Scope of This Release

This is a reproduction-focused release: it ships only what the figure
notebooks read. The ReduMIS+SA notebook and its dedicated results (Figure 15)
are not included. Raw per-run pipeline output is consolidated into
`consolidated_results/` (see "Data Formats") and removed.

The file set was determined at runtime, not by static inspection: every
notebook was executed with an audit hook that logged each file it opened and
each record it looked up in the consolidated tables. Everything that was not
observed was removed, and re-running all notebooks on the trimmed tree
reproduces every printed number and, in the same environment, every saved
figure byte-for-byte.

Concretely:

- `problem_instances/` holds only the graphs that are opened: 73 market
  graphs in `market/` and `market_extra/` (`N = 26 … 44`), 307 density-sweep
  graphs (plus their `generation_summary.json`), the DAX graph in `hardware/`,
  and the two registries the notebooks read (the OR-Library `port5.txt`
  is not shipped; see "Portfolio benchmark data provenance");
- `consolidated_results/` holds only the table rows that are looked up
  (about 12.5k iteration, 44k count, 11k benchmark and 18k flat-JSON rows,
  the last from 36 source files);
- `individual_results/` holds the DAX hardware file listed in its README.

No separate figure files are shipped; the plots are embedded in the executed
notebooks. All figure-generating notebooks live directly in `notebooks/`. 

---

## Data Formats

### Consolidated result tables (`consolidated_results/*.csv`)

The emulator and baseline pipelines wrote one small file per
(iteration, instance, classical shot), plus a measurement-count JSON per
instance and a SQLite database per run. For this paper that amounted to
~112,000 files totalling ~92 MB, of which the notebooks only ever read a
handful of scalars and short node lists. The 3-regular benchmark runs added
another 133 result JSONs (~14 MB) in 13 different schemas. Everything was
folded into plain-text CSV tables and the raw files were removed; the tables
were then cut down to the rows the notebooks look up. Only post-processed
artefacts are released.

Read the tables with `pandas.read_csv`.

| Table | One row per | Key columns |
|---|---|---|
| `iterations.csv` | pipeline iteration | `tree, run, N, seed, cshot, top, iteration, n_input, reduction_factor, kernel_size, q_kernel_size, len_S, len_W, len_R, has_quantum_selected, has_quantum_kernel, is_last` |
| `counts.csv` | distinct measured solution | `tree, run, N, seed, p, order, size, count, nodes` |
| `benchmarks.csv` | `benchmark_*.db` record | `tree, run, db, order, N, seed, p, mis, pmis, baseline, cshot, atom positions MIS, num iteration` |
| `flat_json.csv` | record of a 3-regular benchmark result JSON | `file, order` plus the union of the source files' own fields |

Notes:

- `tree` + `run` (and `file` in `flat_json.csv`) identify the run a row
  belongs to, by the original output path of that run. These are labels, not
  directories in this release (see "Paths that are keys, not files").
- `is_last` marks the last iteration of each trial
  (`tree, run, N, seed, cshot`), i.e. the row with the trial's final
  `|W|` / `|S|`.
- `len_S`, `len_W`, `len_R` are set sizes; the node lists are not included.
- `order` is a row's position in its original file; sort by it to recover
  the original record order.
- `counts.nodes` holds the measured node ids as a space-separated string.
- List-valued fields such as `atom positions MIS` are JSON-encoded strings.
- `schema.json` records the column types and orders CSV cannot store
  (e.g. integer columns with missing values). `utils/derived.py` applies it
  automatically; with plain `pandas.read_csv` you get the raw values.
- Read with `pandas.read_csv(..., float_precision="round_trip")` to get the
  floats exactly as written.


## Citation

```bibtex
@article{yalovetzky2026pipeline,
  author  = {Yalovetzky, R. and Schuetz, M. J. A. and He, Z. and Shen, J.
             and Sun, Y. and Raymond, R. and Sahay, S. and Perla, K.
             and Andrist, R. S. and Salton, G. and Katzgraber, H. G.
             and Bongiovanni, R. and Kumar, N. and Otter, R.},
  title   = {End-to-End Pipeline for Quantum-Informed Portfolio Selection},
  year    = {2026}
}
```

---

## License

SPDX-License-Identifier: Apache-2.0

Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC

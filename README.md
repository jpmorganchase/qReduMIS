# Code for the quantum-informed Reduction Algorithm for the MIS problem (qReduMIS)

qReduMIS is a hybrid classical–quantum algorithm for the **Maximum Independent
Set (MIS)** problem. It pairs a *classical reducer* with a *quantum informer*
that selects nodes to freeze/remove, unlocking further classical reduction of
the kernel graph left over from the previous reduction step.

This repository contains the algorithm library together with the results
reported in two scholarly papers:

1. **qReduMIS**, introduced with a quantum-annealing informer and applied to
   unit-disk MIS graphs —
   *"Quantum-informed reduction algorithm for the maximum independent set
   problem"*, Phys. Rev. Res. **8**, 033296 (2026)
   ([arXiv:2503.12551](https://arxiv.org/abs/2503.12551)).
   Reproduction material: [`results_experiments/quantum_informed_mis/`](results_experiments/quantum_informed_mis/).

2. **Quantum-informed portfolio selection**, extending qReduMIS to the Quantum
   Approximate Optimization Algorithm (QAOA) on universal quantum computers and
   applying it end-to-end to portfolio selection over market graphs built from
   real open-source market data
   ([arXiv:2607.01037](https://arxiv.org/abs/2607.01037)).
   Reproduction material: [`results_experiments/quantum_informed_portfolio_selection/`](results_experiments/quantum_informed_portfolio_selection/).

## Citation

If you use this code, please cite the relevant paper(s). These entries are the
canonical ones for the repository; the per-paper folders under
`results_experiments/` repeat only their own.

**1 — qReduMIS (Phys. Rev. Research, 2026)**

```bibtex
@article{schuetz2026qredumis,
  title = {Quantum-informed reduction algorithm for the maximum independent set problem},
  author = {Schuetz, Martin J. A. and Yalovetzky, Romina and Andrist, Ruben S. and Salton, Grant and Sun, Yue and Raymond, Rudy and Chakrabarti, Shouvanik and Acharya, Atithi and Shaydulin, Ruslan and Pistoia, Marco and Katzgraber, Helmut G.},
  journal = {Phys. Rev. Res.},
  volume = {8},
  issue = {3},
  pages = {033296},
  numpages = {13},
  year = {2026},
  month = {Sep},
  publisher = {American Physical Society},
  doi = {10.1103/nh3b-1wv5},
  url = {https://link.aps.org/doi/10.1103/nh3b-1wv5}
}
```

**2 — Quantum-informed portfolio selection (2026)**

```bibtex
@article{yalovetzky2026quantum,
  title = {Quantum-Informed Portfolio Selection: An End-to-End Pipeline Validated on Trapped-Ion Hardware with Real Market Data},
  author = {Yalovetzky, Romina and Schuetz, Martin J. A. and He, Zichang and Shen, Jiayu and Sun, Yue and Raymond, Rudy and Sahay, Shauna and Perla, Kishore and Andrist, Ruben S. and Salton, Grant and others},
  journal = {arXiv preprint arXiv:2607.01037},
  year = {2026}
}
```

## Organization of the repository

Each folder below has its own `README.md` with further detail:

| Path | Contents |
| ---- | -------- |
| [`qReduMIS_package/`](qReduMIS_package/) | The installable `qredumis` package — installation, examples and tests |
| [`qReduMIS_package/qReduMIS/`](qReduMIS_package/qReduMIS/) | Library overview and API reference, including how to implement your own informer |
| [`results_experiments/quantum_informed_mis/`](results_experiments/quantum_informed_mis/) | Data and notebooks reproducing paper 1 |
| [`results_experiments/quantum_informed_portfolio_selection/`](results_experiments/quantum_informed_portfolio_selection/) | Data and notebooks reproducing paper 2 |

## Getting started

```bash
pip install poetry
poetry install
```

See [`qReduMIS_package/README.md`](qReduMIS_package/README.md) for usage, the
available informers, and how to run the tests.

SPDX-License-Identifier: Apache-2.0 @ Copyright 2025: Amazon Web Services, Inc.
Developed as part of an engagement with JPMorgan Chase & Co.

----

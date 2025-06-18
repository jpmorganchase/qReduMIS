# Code for paper "qReduMIS: A Quantum-Informed Reduction Algorithm for the Maximum Independent Set Problem"

This repository contains the package of the qReduMIS algorithm, which is a
quantum-informed reduction algorithm for the Maximum Independent Set (MIS)
problem ([arXiv:2503.12551](https://arxiv.org/abs/2503.12551)). qReduMIS is a
hybrid classical-quantum algorithm, which leverages a classical reducer and a
quantum informer which informs of nodes to remove in order to unlock the
classical reduction of the kernel graph (resulted from the previous classical
reduction).

## Citing the work
```
@article{schuetz2025qredumis,
  title={qReduMIS: A Quantum-Informed Reduction Algorithm for the Maximum Independent Set Problem},
  author={Schuetz, Martin JA and Yalovetzky, Romina and Andrist, Ruben S and Salton, Grant and Sun, Yue and Raymond, Rudy and Chakrabarti, Shouvanik and Acharya, Atithi and Shaydulin, Ruslan and Pistoia, Marco and others},
  journal={arXiv preprint arXiv:2503.12551},
  year={2025}
}
```

## Organization of repository:

This repository contains both the package of the algorithm qReduMIS introduced
in the scholarly paper as well as the main results discussed in it. This
repository is divided into two folders below. In each of these folders there are
README.md giving more details.

* `qReduMIS_package/`: contains the code package of the algorithm
* `results_experiments/`: contains the main results from the paper

SPDX-License-Identifier: Apache-2.0 @ Copyright 2025: Amazon Web Services, Inc.
Developed as part of an engagement with JPMorgan Chase & Co.

----

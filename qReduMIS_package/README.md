# qReduMIS — Python package

The installable `qredumis` package: a quantum-informed reduction algorithm for
the **Maximum Independent Set (MIS)** problem. This is the implementation behind
both qReduMIS papers — the original quantum-annealing formulation
([Phys. Rev. Res. 8, 033296](https://link.aps.org/doi/10.1103/nh3b-1wv5),
[arXiv:2503.12551](https://arxiv.org/abs/2503.12551)) and its QAOA extension
applied to portfolio selection
([arXiv:2607.01037](https://arxiv.org/abs/2607.01037)).

> **Citing this work** — BibTeX entries for both papers are in the
> [repository README](../README.md#citation).

## Contents of this folder
  * `examples/`: a runnable example script (`script.py`) and an annotated notebook (`example.ipynb`), with sample input data and results.
  * `qReduMIS/`: the package source code — see [`qReduMIS/README.md`](qReduMIS/README.md) for the library/API overview
  * `tests/`: the test suite
  * [`../results_experiments/`](../results_experiments/): scripts, data and notebooks to reproduce the paper results

## Features

qReduMIS is a hybrid classical–quantum algorithm. It pairs a **classical reducer**
(in `qReduMIS/solver/classical_reducer/`) with a pluggable **informer** (in
`qReduMIS/solver/informers/`). The solver, `MISSolver`
(`qReduMIS/mis_solver.py`), alternates classical reductions with informer calls
on the remaining *kernel* graph until it collapses.

Every informer implements the same interface
(`qReduMIS/solver/informers/base.py`) and plays two roles: (a) select nodes to
freeze/remove to unlock the next classical reduction, and (b) track the largest
independent set seen so far. The frozen-node selection logic is shared across all
informers in `qReduMIS/solver/informers/selection.py`.

Available informers:

  * **QAOAInformer** (`solver/informers/quantum/qaoa/`) — depth-`p` QAOA on a local
    Qiskit Aer simulator.
  * **QuantumAnnealingInformer** (`solver/informers/quantum/quantumannealing/`) —
    Rydberg-atom analog computation. The backend system (`backend_system/`)
    abstracts hardware/simulator access via `BackendFactory`:
      * **Simulator**: Braket `LocalSimulator("braket_ahs")`.
      * **Aquila**: QuEra's Aquila QPU via AWS Braket.
  * **SAInformer** (`solver/informers/classical/sa/`) — a compiled C++
    simulated-annealing solver. This one requires building the executable first;
    see [`qReduMIS/solver/informers/classical/sa/README.md`](qReduMIS/solver/informers/classical/sa/README.md).


## Requirements

This package requires Python 3.11.

To set up the environment, from this directory run:

1. `pip install poetry`
2. `poetry install`

This installs everything needed to run all three informers (including `qiskit`,
`qiskit-aer` and `amazon-braket-sdk`). To also reproduce the paper notebooks,
install the optional group:

```
poetry install --with paper
```

The SA informer additionally needs its C++ binary compiled once:

```
cd qReduMIS/solver/informers/classical/sa/_cpp && make
```

## How to use it?

Run the end-to-end example (from this directory):

```
poetry run python examples/script.py
```

For an annotated walkthrough covering every informer and the Rydberg backends,
open `examples/example.ipynb`; `qReduMIS/example.ipynb` is a shorter variant.

Minimal graph-based usage:

```python
import networkx as nx
from qReduMIS import MISSolver
from qReduMIS.solver.informers.quantum.qaoa import QAOAInformer

G = nx.erdos_renyi_graph(n=20, p=0.25, seed=42)
informer = QAOAInformer(selection_strategy="inset", num_shots=1000, p=2)
solver = MISSolver(informer=informer, top_k_solutions=2, max_iteration_limit=10)
solution, n_iter = solver.solve(G, seed_graph=0, cshot=0)
print(f"MIS size = {len(solution)}")
```

Swap the informer object to change backend — the solver code stays the same.
For the Rydberg quantum-annealing informer, which operates on atom positions and
selects a Braket backend via `BackendFactory`, see the corresponding section of
`examples/example.ipynb`.

### Configuration

Default hyperparameters live in `qReduMIS/configurations.ini`:

  * `[quantum] schedule` — path to the Rydberg drive schedule (absolute, or
    relative to the package root). A sample schedule ships with the package.
  * `[qaoa] p`, `qaoa_params`, `num_shots` — QAOA defaults, overridden by any
    argument passed explicitly to `QAOAInformer(...)`.

To run tests:

```
poetry run pytest tests/
```

See `qReduMIS/README.md` for the full library overview, including how to
implement your own informer.

SPDX-License-Identifier: Apache-2.0 @ Copyright 2025: Amazon Web Services, Inc.
Developed as part of an engagement with JPMorgan Chase & Co. 

----

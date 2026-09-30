# Simulated-Annealing (SA) informer

This folder contains a classical **simulated-annealing** informer for qReduMIS.
It implements the same [`Informer`](../../base.py) interface as the quantum
informers, so it can be plugged straight into
[`MISSolver`](../../../../mis_solver.py):

```python
from qReduMIS import MISSolver
from qReduMIS.solver.informers.classical.sa import SAInformer

solver = MISSolver(informer=SAInformer(selection_strategy="inset"))
solution, n_iters = solver.solve(G, seed_graph=0, cshot=0)
```

The informer plays the same two roles as a quantum informer:

1. **Frozen-node selection** — pick nodes that appear consistently across
   high-quality SA solutions and freeze them (remove them and their neighbours)
   to unlock further classical reduction.
2. **Incumbent tracking** — keep the largest independent set found across all
   SA calls.

## Contents

| Path | Purpose |
| ---- | ------- |
| `informer.py` | Python wrapper: METIS I/O, `sa_solver` invocation, `SAInformer`. |
| `_cpp/sa_solver.cc` | C++ SA solver; emits all replica solutions as JSON. |
| `_cpp/independent_set.h`, `_cpp/markov_chain.h`, `_cpp/instance.h`, `_cpp/state.h`, `_cpp/random.h` | SA solver headers. |
| `_cpp/Makefile` | Builds the `sa_solver` binary (into `_cpp/`). |
| `tests/test_sa_informer.py` | Unit tests for the informer. |
| `tests/data/kernel_1_atoms_L17_seed46.metis` | Small sample kernel used by the tests. |

## Dependencies 

This informer requires a pseudo-random number generator and for this, these two files are required: pcg_random.hpp and pcg_extras.hpp

These files are used unmodified by the simulated-annealing (SA) informer's
C++ solver as its pseudo-random number generator. They are from: 

PCG Random Number Generation for C++
Copyright 2014-2022 Melissa O'Neill <oneill@pcg-random.org>,
                     and the PCG Project contributors.
SPDX-License-Identifier: (Apache-2.0 OR MIT)
Homepage: http://www.pcg-random.org/

## Building the solver

The Python wrapper shells out to a compiled `sa_solver` binary that lives in
the `_cpp/` subfolder. Build it once with:

```bash
cd qReduMIS/solver/informers/classical/sa/_cpp
make          # produces ./sa_solver
```

This requires a C++11 compiler (`g++` / Apple Clang). Verify the build:

```bash
./sa_solver ../tests/data/kernel_1_atoms_L17_seed46.metis 10 32 10 5000 0 | python3 -m json.tool
```

You should see a JSON object with a `"solutions"` array (one entry per replica)
and a `"best_size"` field.

## `sa_solver` CLI

```
sa_solver [metis_file] [replicas] [steps] [b_min] [b_max] [seed]
```

| Argument | Meaning | Default |
| -------- | ------- | ------- |
| `metis_file` | Graph in METIS 4.0 format | — |
| `replicas` | Independent SA runs | 10000 |
| `steps` | Annealing sweeps per replica | 32 |
| `b_min` | Starting inverse temperature | 10 |
| `b_max` | Final inverse temperature | 5000 |
| `seed` | RNG seed | 0 |

These map directly to the `SAInformer(replicas=..., steps=..., b_min=..., b_max=...)`
constructor arguments.

## Running the tests

```bash
poetry run pytest qReduMIS/solver/informers/classical/sa/tests/test_sa_informer.py
```

Tests that need the compiled binary are skipped automatically if `sa_solver`
has not been built.

# Code for paper "qReduMIS: A Quantum-Informed Reduction Algorithm for the Maximum Independent Set Problem"

This repository contains the package of the qReduMIS algorithm, which is a quantum-informed reduction algorithm for the Maximum Independent Set (MIS) problem (arXiv:2503.12551).

## Citing the work
```
@article{schuetz2025qredumis,
  title={qReduMIS: A Quantum-Informed Reduction Algorithm for the Maximum Independent Set Problem},
  author={Schuetz, Martin JA and Yalovetzky, Romina and Andrist, Ruben S and Salton, Grant and Sun, Yue and Raymond, Rudy and Chakrabarti, Shouvanik and Acharya, Atithi and Shaydulin, Ruslan and Pistoia, Marco and others},
  journal={arXiv preprint arXiv:2503.12551},
  year={2025}
}
```

## This repository is divided into the folders:
  * examples/: it contains an example script.py and some input data in input_data/ in order to run the package
  * qReduMIS/: it contains the code of the package 
  * tests/: it contains some tests for the package

## Features

qReduMIS is a hybrid classical-quantum algorithm, which leverages a classical reducer (contained in qReduMIS/solver/classical_reducer/) and a quantum informer (contained in qReduMIS/solver/quantum_informer/) which informs of nodes to remove in order to unlock the classical reduction of the kernel graph. 

The quantum informer plays two roles: (a) select nodes to remove and inform the next classical reduction and (b) keep track of an incumbent solution, for which keeps track of the largest solution identified by the backend. For (a) the code is in qReduMIS/solver/quantum_informer/quantum_selection.py and for (b) in qReduMIS/solver/quantum_informer/quantum_solver.py which contains:

  * QuantumSolver Class: the core class responsible for orchestrating the quantum computation process. It interfaces with quantum backends to run experiments and processes the results to find the maximum independent set.

We also have the backend system in qReduMIS/solver/quantum_informer/backend_system/, which is utilized to connect and run experiments. It contains: 

  * Backend System: a flexible backend system that supports multiple quantum computing platforms, including simulators and real quantum devices. The BackendFactory class in backend_generator.py allows for easy selection and instantiation of different backends based on user requirements. The subclasses implemented are for Rydberg-atom backens:

    * RydbergAtomBackend: a specialized backend for simulating quantum experiments using Rydberg atoms. It includes methods for setting up the Hamiltonian corresponding to the input problem graph, checking   connectivity, and executing quantum programs.
      * Simulator: It utilizes the Braket LocalSimulator to simulate the behavior of Rydberg atoms in quantum computations
      * Aquila: It utilizes AWS Braket for connecting to QuEra's Aquila quantum machine 


## Requirements 

This package requires Python 3.9. 

Then follow the following steps to set up environment. In this directory do: 

1. pip install poetry 
3. poetry install  

To run example module do below. 

1. cd examples 
2. poetry run python script.py

To run tests: 
poetry run pytest tests/

## How to use it? 

Set up the configuration.ini file indicating the path to the schedule to be used in case of running with a Rydberg-based quantum backend. 
For this, edit qReduMIS/configurations.ini

Refer to examples/script.py on how to import and use MISSolver()

SPDX-License-Identifier: Apache-2.0 @ Copyright 2025: Amazon Web Services, Inc.
Developed as part of an engagement with JPMorgan Chase & Co. 

----
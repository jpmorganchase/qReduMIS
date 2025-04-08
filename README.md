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

## Features
* QuantumSolver Class: The core class responsible for orchestrating the quantum computation process. It interfaces with quantum backends to run experiments and processes the results to find the maximum independent set.

* Backend System: A flexible backend system that supports multiple quantum computing platforms, including simulators and real quantum devices. The BackendFactory class allows for easy selection and instantiation of different backends based on user requirements.

  * RydbergAtomBackend: A specialized backend for simulating quantum experiments using Rydberg atoms. It includes methods for setting up Hamiltonians, checking connectivity, and executing quantum programs.
    * Simulator: It utilizes the Braket LocalSimulator to simulate the behavior of Rydberg atoms in quantum computations
    * Aquila: It utilizes AWS Braket for connecting to QuEra's Aquila quantum machine 


## Requirements 

This package requires Python 3.9. 

Then follow the following steps to set up environment:

1. pip install poetry 
2. cd qReduMIS 
3. poetry install  

To run example module do:

1. cd examples 
2. poetry run python script.py

To run tests: 
poetry run pytest tests/

## How to use it? 

Set up the configuration.ini file indicating the path to the schedule to be used in case of running with a Rydberg-based quantum backend. 
For this, edit qReduMIS/configurations.ini

Refer to example module on how to import and use MISSolver()

SPDX-License-Identifier: Apache-2.0 @ Copyright 2025: Amazon Web Services, Inc.
Developed as part of an engagement with JPMorgan Chase & Co. 

----
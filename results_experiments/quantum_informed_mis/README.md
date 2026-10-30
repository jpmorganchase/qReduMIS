# This folder contains the main code utilized for paper "qReduMIS: A Quantum-Informed Reduction Algorithm for the Maximum Independent Set Problem"

## Citing the work
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

The experimental results correspond to random unit-disk instances with the
Union-Jack connectivity (radius=sqrt(2)) for a density fixed to 0.8. We took
different values of L and seeds (refer to `generator/generate.py`).

For each instance, we compare the results of the PMIS we obtain from three
different methods:
1. QAA
2. qReduMIS: we selected 20 classical shots, no limitation in the depth (a.k.a.
   classical iterations) and the technique used was "in-set"
3. randomReduMIS: replace the quantum component that gives the node with high
   probability to be inset by a random pick. We performed this for the same
   number of classical iterations than in qReduMIS

Some notes:
* The ground truth MIS was calculated using the sweeping line algorithm and they
  can be found in `qpo/testbed_instances/`.
* The postprocessing of the counts from both the TN simulator and hardware (for
  both QAA and qReduMIS) was the same: we performed fixup with removal and
  addition
* When reporting results on hardware, we also performed a postprocessing that
  accounts for loading errors
* For all the executions on backend (both TN and hardware) we utilized the same
  annealing schedule and ran 1000 shots

## In order to reproduce the results shown in the paper in this folder it can be found everything needed. Particularly to get the plot:

* refer to `reproduce_paper_extensive.ipynb` for the extensive benchmark
  performed (main Figure 3)
* also refer to `reproduce_paper_table.ipynb` to reproduce the results for the
  four instances that we focused on Table 1.

Note that for this you may require to install some packages included in
`requirements.txt` and use Python 3.9

## This folder also contains more code and results that were used through the project:

* `baseline_results`: folder contains the results obtained using the baseline
  solver (sweeping line algorithm). The name of the json files refer to the
  length of the grid (L) and the seed utilized. All of these problems are random
  MIS instances on UJ connectivity with density = 0.8. For each instance, the
  json is of the form:
  ```json
  {
    "|MIS|": 1,
    "D_(MIS)": 3,
    "candidates MIS": [
      {"nodes": [2]},
      {"nodes": [1]},
      {"nodes": [0]}
    ],
    "|MIS|-1": 0,
    "D_(MIS-1)": 1
  }
  ```
  With this, we utilized the MIS solution as baseline and we calculate the
  hardness parameter for these instances.

* `main_results_extensive/`: folder contains the main json files that contain
  results from the extensive benchmark performed on hardware

* `raw_results/`: this folder contains the raw results obtained from the
  experiments on the hardware
  * `QAA/`: contains the results of the standard QAA implementation.
    * `QAA/QAA_hardware`: contains the results on hardware.
      * for the instances in Table 1 in paper, their results are in the folders
        `atoms_BMW2023_HP{hp}/` where hp is the hardness parameter.
      * `testbed_*`: contain the results for the extensive benchmark

  * `QAA_TN/`: contains the results on the TN simulator for the four instances
    we show on the paper in Table 1 in the folders `atoms_BMW2023_HP{hp}/` and
    in folder `testbed_spacing5.45_cutoff10` contains for all the instances used
    in the extensive benchmark. Please note that the spacing utilized and cutoff
    used in the simulator is on the name.

  * `qReduMIS/`: contains the results of the qReduMIS algorithm:
    * `experiments_hardware/`: contains those instances from the extensive
      testbed that we executed on hardware. Note that the rest of the instances
      did not require quantum backend (i.e., were fully reducible). In the
      folders of the form `atoms_L{L}_seed{seed}` it can be found the raw counts
      as well as the postprocessed counts from the quantum backend, contained in
      a folder indicating the number of the classical shot (`cshot{c}/`). At the
      root of the folder of the problem instance it can be found the results
      from the qReduMIS algorithm inside the json files of the form
      `atoms_L{L}_seed{seed}_results_qReduMIS_cshot{c}.json` and on the ones of
      the form `atoms_L{L}_seed{seed}_results_qReduMIS_cshot{c}_job_info.json`
      it can be found some information of the jobs.

    * `experiments_TN/`: contains the results obtained from the TN simulator.
      * the folders contain fist the date and then the ones of Table 1 start
        with `atoms_BMW2023*`. The results of the extensive benchmark are
        contains in the ones that contain in the name `testebed_instances`.

    * `qReduMIS_table_hardware/`: contains the results on the hardware for the
      four instances in table 1. Please note that we have executed with two
      criteria: inset and outset. Similarly as in folder
      `experiments_hardware/` we have folders with raw and postprocessed counts
      as well as json files at the root of the folders corresponding to the
      overall results of the qReduMIS algorithm.

* `schedules/`: contains the schedule utilized for the experiments and some
  Python code to get these json files

* `testbed_instances/`: contains all the problem instances utilized for the
  paper:
  * `table_instances/`: contains the instances utilized in Table 1
  * `all_buckets/` and `testbed_instances_hardware_hard/` contain all the
    instances for the extensive benchmark. Please note that we put in
    `testbed_instances_hardware_hard/` those instances that were executed on the
    quantum hardware for qReduMIS. `all_buckets/` is divided into subfolders as
    we parallelize the runs for the TN simulator.

SPDX-License-Identifier: Apache-2.0 @ Copyright 2025: Amazon Web Services, Inc.
Developed as part of an engagement with JPMorgan Chase & Co.

----

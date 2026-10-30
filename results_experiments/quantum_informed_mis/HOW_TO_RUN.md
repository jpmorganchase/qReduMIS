In order to reproduce the results of QAA and qReduMIS using the tensor network
simulator follow these steps:

1. `git clone https://github.com/amazon-braket/amazon-braket-simulator-v2-python.git`

2. `git checkout feature/ahs_tn_simulator`

3. In `amazon-braket-simulator-v2-python` do: `pip install -e`.
   If you get the following error, run again:
   ```
   ERROR: Could not install packages due to an OSError:
   [Errno 16] Device or resource busy: '.nfs27e3a5477781f5cb00000013'
   ```

4. `python3 src/braket/ahs_tn_simulator/runner.py`

5. If you encounter an issue with the path of Julia:
   ```
   ERROR: Unable to load dependent library <your-env>/julia_env/pyjuliapkg/install/lib/julia/libjulia-codegen.so.1.10
   Message:/lib64/libstdc++.so.6: version `GLIBCXX_3.4.26' not found (required by <your-env>/julia_env/pyjuliapkg/install/lib/julia/libjulia-codegen.so.1.10)
   ```

   Please try doing:
   ```bash
   export
   LD_PRELOAD=$HOME/simenv/julia_env/pyjuliapkg/install/lib/julia/libstdc++.so.6
   ```

The .sh to run are: `run_experiments.sh` and `run_experiments_smothness.sh`,
where you can change the schedules to run.

In order to reproduce results on hardware, we utilized the hybrid jobs feature
of AWS Braket.

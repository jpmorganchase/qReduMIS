###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""
utils_db — SQLite database helpers for experiment results
=========================================================

Provides utilities to load qReduMIS and QAOA experiment results stored
in SQLite databases (as produced by the Quantinuum emulator pipeline)
and to post-process qReduMIS results by comparing against baseline
MIS solutions.

SPDX-License-Identifier: Apache-2.0
"""

import os
import sqlite3
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt


def make_df_from_db(file):
    """Load a ``benchmark_*.db`` ``results`` table into a DataFrame.

    The released repository ships the consolidated ``consolidated_results/`` tables
    instead of the SQLite files, so when *file* is missing the same records
    are served from ``consolidated_results/benchmarks.csv``.  The returned frame is
    identical either way.
    """
    if not os.path.exists(file):
        from utils.derived import DerivedData

        df = DerivedData().db_frame(file)
        if df.empty:
            raise FileNotFoundError(
                f"{file} not found, and consolidated_results/benchmarks.csv has no "
                "records for it"
            )
        return df

    # Read-only: opening a database read-write creates -shm/-wal scratch
    # files next to it, which would pollute the released tree.
    conn = sqlite3.connect(f"file:{file}?mode=ro", uri=True)
    df = pd.read_sql('SELECT result_json FROM results', conn)

    result_expanded = pd.json_normalize(df['result_json'].apply(json.loads))

    conn.close()

    return result_expanded

def post_process_qredumis(df_qredumis, df_qaoa):
    """
    df_qaoa: it contains the baseline 
    """
    Ns = list(set(df_qredumis['N']))

    pmis_list=[]
    sizes=[]
    seeds=[]

    for N in Ns: 
        seeds_list=list(set(df_qredumis[(df_qredumis['N']==N)]['seed']))
        for seed in seeds_list:
            sub_df = df_qredumis[(df_qredumis['N']==N) & (df_qredumis['seed']==seed)]
            cshots = sub_df.shape[0]
            baseline = df_qaoa[(df_qaoa['N']==N) & (df_qaoa['seed']==seed)]['baseline'].iloc[0]
            pmis = sub_df.apply(lambda row: len(row['atom positions MIS'])==baseline, axis=1).sum()/cshots
            pmis_list.append(pmis)
            sizes.append(N)
            seeds.append(seed)

    df_qredumis = pd.DataFrame()
    df_qredumis['N']=sizes
    df_qredumis['seed']= seeds
    df_qredumis['pmis']=pmis_list

    
    return df_qredumis
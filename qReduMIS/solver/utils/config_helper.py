###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import configparser

def read_config():
    import os
    print(os.getcwd())
    config = configparser.ConfigParser()
    config.read("qReduMIS/configurations.ini")

    return config

###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
import os
import configparser

def read_config():

    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Navigate up to the package root directory
    package_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    
    # Construct the path to the configurations.ini file
    config_path = os.path.join(package_root, 'configurations.ini')
    
    config = configparser.ConfigParser()
    config.read(config_path)

    return config

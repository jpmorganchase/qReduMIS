###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

import os
import configparser
from configparser import ConfigParser
from typing import Optional, Tuple


def read_config() -> ConfigParser:
    """
    Reads the configuration from a 'configurations.ini' file located in the package root directory.

    Returns:
        ConfigParser: A ConfigParser object containing the configuration data.
    """
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Navigate up to the package root directory
    package_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    # Construct the path to the configurations.ini file
    config_path = os.path.join(package_root, "configurations.ini")

    config = configparser.ConfigParser()
    config.read(config_path)

    return config


def get_s3_folder() -> Optional[Tuple[str, str]]:
    """
    Resolves the Amazon Braket S3 result destination for QPU submissions.

    Braket writes the results of every QPU task to an S3 bucket owned by the
    caller's own AWS account, so this value is deliberately **not** hardcoded:
    a bucket belonging to someone else is unusable (and publishing one would
    disclose that account's identifier).

    The location is resolved in the following order:

    1. The ``AWS_BRAKET_S3_BUCKET`` / ``AWS_BRAKET_S3_PREFIX`` environment
       variables.
    2. The ``bucket`` / ``prefix`` keys of the ``[braket]`` section in
       ``configurations.ini``.

    Returns:
        Optional[Tuple[str, str]]: ``(bucket, prefix)`` when configured, or
        ``None`` when no destination has been set. ``None`` is expected for
        local-simulator runs, which never upload results to S3.
    """
    bucket = os.environ.get("AWS_BRAKET_S3_BUCKET")
    prefix = os.environ.get("AWS_BRAKET_S3_PREFIX")

    if not bucket:
        config = read_config()
        if config.has_section("braket"):
            bucket = config.get("braket", "bucket", fallback="") or None
            prefix = prefix or config.get("braket", "prefix", fallback="") or None

    if not bucket:
        return None

    return (bucket, prefix or "qredumis")

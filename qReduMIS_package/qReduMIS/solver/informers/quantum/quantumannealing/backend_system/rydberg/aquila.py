###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################

from boto3 import Session
from braket.aws import AwsDevice, AwsSession
from qReduMIS.solver.informers.quantum.quantumannealing.backend_system.rydberg.rydberg_backend import (
    RydbergAtomBackend,
)


class Aquila(RydbergAtomBackend):
    """QuEra Aquila QPU backend accessed via AWS Braket."""

    def __init__(self):
        """Configure the Braket S3 result location and set up the device."""
        super().__init__()
        # ``s3_folder`` is resolved by ``RydbergAtomBackend`` from the
        # AWS_BRAKET_S3_BUCKET environment variable or configurations.ini.
        # Aquila is a real QPU, so a destination bucket in the caller's own
        # AWS account is mandatory.
        if self.s3_folder is None:
            raise ValueError(
                "No Amazon Braket S3 destination configured. Braket writes QPU "
                "results to a bucket in your own AWS account, so one must be "
                "provided before running on Aquila.\n"
                "Set it with:\n"
                "    export AWS_BRAKET_S3_BUCKET=amazon-braket-<region>-<your-account-id>\n"
                "    export AWS_BRAKET_S3_PREFIX=qredumis   # optional\n"
                "or add a [braket] section with 'bucket'/'prefix' keys to "
                "configurations.ini."
            )

        self.setup_device()

    def setup_device(self):
        """Resolve the Aquila ``AwsDevice`` in us-east-1 and store it as the device."""
        # QuEra's Aquila is only offered in us-east-1, which is why the region
        # is also part of the device ARN below. Pinning it here is deliberate
        # rather than a leftover local setting: Braket would otherwise fall back
        # to the caller's default region and raise NoRegionError for anyone who
        # has not configured one. It is a public region name, not account data.
        boto_session = Session(region_name="us-east-1")
        aws_session = AwsSession(boto_session=boto_session)
        aquila = AwsDevice(
            "arn:aws:braket:us-east-1::device/qpu/quera/Aquila", aws_session
        )
        self.device = aquila
        self.backend_id = "Aquila"

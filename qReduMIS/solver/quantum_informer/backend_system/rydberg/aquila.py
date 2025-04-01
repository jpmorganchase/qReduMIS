###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
from boto3 import Session
from braket.aws import AwsDevice, AwsSession
from qredumis.solver.backend_system.rydberg.rydberg_backend import RydbergAtomBackend


class Aquila(RydbergAtomBackend):
    
    def __init__(self):
        super().__init__()
        self.my_bucket = "amazon-braket-us-east-1-231197392483"
        self.bucket_prefix = "hello_quera"  # change prefix
        self.s3_folder = (self.my_bucket, self.bucket_prefix)

        self.setup_device()

    def setup_device(self):
        boto_session = Session(region_name="us-east-1")
        aws_session = AwsSession(boto_session=boto_session)
        aquila = AwsDevice("arn:aws:braket:us-east-1::device/qpu/quera/Aquila",aws_session)
        self.device= aquila
        self.backend_id = 'Aquila'

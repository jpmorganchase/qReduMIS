###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""base_backend.py: Abstract class of Backend"""
import time
import tracemalloc
from abc import ABC, abstractmethod


class Backend(ABC):
    """
    Abstract base class for all backends. A backend is utilized to run the inform the next reduction.
    """

    def __init__(self):
        self.device = None
        self.backend_id = None

    @abstractmethod
    def setup_device(self):
        """
        Abstract method for setting up devide. Must be implemented by inherited classes
        """

    @abstractmethod
    def get_counts_from_result(self, result):
        """
        Abstract method to get the counts from results. Must be implemented by inherited classes
        """
        pass

    @abstractmethod
    def get_results(self, task, iteration):
        """
        Abstract method to retrieve and process results from quantum backend. Must be implemented by inherited classes
        """
        pass

    @abstractmethod
    def execute(self, ahs_program, num_shots: int):
        """
        Abstract method to execute experiment on given backend
        """
        pass

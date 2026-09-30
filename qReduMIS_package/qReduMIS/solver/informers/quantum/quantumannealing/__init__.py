###############################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc. - Contributions from JPMC
###############################################################################
"""Rydberg-atom (Braket / Aquila / local) informer for qReduMIS.

Requires the optional ``amazon-braket-sdk`` extra.  Imports inside this
sub-package may fail with ``ModuleNotFoundError: No module named 'braket'``
if the extra is not installed.
"""

# Lazy imports kept out of the package __init__ on purpose so that
# ``import qReduMIS`` works without the Braket extra.

__all__ = []

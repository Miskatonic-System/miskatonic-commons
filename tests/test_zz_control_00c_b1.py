# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""CONTROL 00C-B1: deliberately failing required check. Never merge."""


def test_control_b1_deliberate_failure():
    assert False, "WO-COMMONS-PUBLICATION-FENCE-00C control B1: required check must fail"

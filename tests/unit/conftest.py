# Copyright 2026 Canonical
# See LICENSE file for licensing details.

"""Shared fixtures for the unit tests."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def no_subprocess():
    """Fail loudly if a test reaches a real subprocess call.

    Unit tests must mock out the Geonames methods that touch the machine
    (for example, an unmocked _run_subprocess_command would run indexer or
    import scripts against the real filesystem of whoever runs the tests).
    Tests that intentionally patch subprocess.run (e.g. via
    @patch("geonames.subprocess.run")) still work, since their own patch is
    applied after this one.
    """
    with patch(
        "subprocess.run",
        side_effect=AssertionError(
            "unit test attempted to run a real subprocess; mock the Geonames method"
        ),
    ):
        yield

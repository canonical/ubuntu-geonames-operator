# Copyright 2025 andersson123
# See LICENSE file for licensing details.

"""Unit tests for the charm.

These tests only cover behaviour that does not require internet access, and
that does not attempt to manipulate the underlying machine.
"""

from subprocess import CalledProcessError
from unittest.mock import patch

import pytest
from charmlibs.apt import PackageError, PackageNotFoundError
from ops.testing import ActiveStatus, BlockedStatus, Context, State

from charm import UbuntuGeonamesCharm


@pytest.fixture
def ctx():
    return Context(UbuntuGeonamesCharm)


@pytest.fixture
def base_state():
    return State(leader=True)


@patch("charm.Geonames.install")
def test_install_success(install_mock, ctx, base_state):
    install_mock.return_value = None

    out = ctx.run(ctx.on.install(), base_state)

    assert out.unit_status == ActiveStatus()
    assert install_mock.called


@patch("charm.Geonames.install")
def test_upgrade_success(install_mock, ctx, base_state):
    install_mock.return_value = None

    out = ctx.run(ctx.on.upgrade_charm(), base_state)

    assert out.unit_status == ActiveStatus()
    assert install_mock.called


@patch("charm.Geonames.install")
@pytest.mark.parametrize(
    "exception",
    [
        PackageError,
        PackageNotFoundError,
        CalledProcessError(1, "foo"),
        TimeoutError,
        OSError,
    ],
)
def test_install_blocks_on_environment_setup_failure(install_mock, exception, ctx, base_state):
    install_mock.side_effect = exception

    out = ctx.run(ctx.on.install(), base_state)

    assert out.unit_status == BlockedStatus(
        "Failed to set up the environment. Check `juju debug-log` for details."
    )


@patch("charm.Geonames.install")
def test_upgrade_blocks_on_environment_setup_failure(install_mock, ctx, base_state):
    install_mock.side_effect = CalledProcessError(1, "foo")

    out = ctx.run(ctx.on.upgrade_charm(), base_state)

    assert out.unit_status == BlockedStatus(
        "Failed to set up the environment. Check `juju debug-log` for details."
    )

#!/usr/bin/env python3
# Copyright 2025 andersson123
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charmed Operator for the geonames service."""

import logging
import shutil
from subprocess import CalledProcessError

import ops
from charmlibs.apt import PackageError, PackageNotFoundError
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer as IngressRequirer

from geonames import Geonames

logger = logging.getLogger(__name__)


class UbuntuGeonamesCharm(ops.CharmBase):
    """Charm the geonames service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.ingress = IngressRequirer(self, port=80, strip_prefix=True, relation_name="ingress")

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.upgrade_charm, self._on_install)

        self._geonames = Geonames()

    def _on_install(self, event: ops.EventBase):
        """Set up the geonames environment on install and upgrade."""
        self.unit.status = ops.MaintenanceStatus("Setting up environment")
        try:
            self._geonames.install()
        except (
            CalledProcessError,
            PackageError,
            PackageNotFoundError,
            TimeoutError,
            IOError,
            OSError,
            shutil.Error,
        ):
            self.unit.status = ops.BlockedStatus(
                "Failed to set up the environment. Check `juju debug-log` for details."
            )
            return
        self.unit.set_ports(80)
        self.unit.status = ops.ActiveStatus("Done!")


if __name__ == "__main__":  # pragma: nocover
    ops.main(UbuntuGeonamesCharm)  # type: ignore

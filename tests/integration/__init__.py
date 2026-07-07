# Copyright 2025 Canonical
# See LICENSE file for licensing details.

APPNAME = "ubuntu-geonames"

def address(juju):
    """Report the IP address of the application."""
    return juju.status().apps[APPNAME].units[f"{APPNAME}/0"].public_address

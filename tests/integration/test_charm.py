# Copyright 2025 Canonical
# See LICENSE file for licensing details.

import jubilant
import requests

from . import APPNAME, address


def test_service_state_after_deploy(juju: jubilant.Juju, ubuntu_geonames_charm):
    """Deploy the charm via jubilant and wait until application is active."""
    juju.deploy(ubuntu_geonames_charm, app=APPNAME)

    # Allow plenty of time for downloading datasets and populating database
    juju.wait(jubilant.all_active, timeout=5400)


def test_api_endpoint(juju: jubilant.Juju):
    """Check that the geonames api resolves locations."""
    response = requests.get(f"http://{address(juju)}/?query=paris", timeout=60)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

terraform {
  required_version = ">= 1.0"
  required_providers {
    juju = {
      version = "0.15.0"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}

resource "juju_application" "apache2" {
  name = "apache2"
  model = var.model_name
  trust = true
  charm {
    name = "apache2"
    channel = "latest/stable"
    base = local.base
  }
  constraints = "arch=amd64 cores=2 mem=4096M root-disk=51200M"
  units = 1
  config = {
    enable_modules = "include cgi proxy proxy_http remoteip wsgi"
    mpm_type = "prefork"
  }
}

resource "juju_application" "ubuntu_geonames" {
  name = "ubuntu-geonames"
  model = var.model_name
  charm {
    name = "ubuntu-geonames"
    channel = "latest/edge"
    base = local.base
  }
  units = 0
}

resource "juju_integration" "apache2-ubuntu-geonames" {
  model = var.model_name
  application {
    name = juju_application.apache2.name
    endpoint = "apache-website"
  }
  application {
    name = juju_application.ubuntu_geonames.name
    endpoint = "website"
  }
  lifecycle {
    replace_triggered_by = [
      juju_application.apache2.name,
      juju_application.apache2.model,
      juju_application.apache2.constraints,
      juju_application.apache2.placement,
      juju_application.apache2.charm.name,
      juju_application.ubuntu_geonames.name,
      juju_application.ubuntu_geonames.model,
      juju_application.ubuntu_geonames.constraints,
      juju_application.ubuntu_geonames.placement,
      juju_application.ubuntu_geonames.charm.name,
    ]
  }
}

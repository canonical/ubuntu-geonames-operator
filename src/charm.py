#!/usr/bin/env python3
# Copyright 2025 andersson123
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following tutorial that will help you
develop a new k8s charm using the Operator Framework:

https://juju.is/docs/sdk/create-a-minimal-kubernetes-charm
"""

import logging
import os
import pwd
import shutil
import subprocess
import time
from pathlib import Path
from typing import cast

import ops
import pygit2

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]

# change to path perhaps
REPO_REMOTE = "https://git.launchpad.net/~andersson123/ubuntu-geonames"
REPO_LOCATION = Path("/home/ubuntu/ubuntu-geonames/")
REPO_BRANCH = "charm-and-modernise"


class UnixUser:
    """Class representation of a unix user."""

    def __init__(self, username):
        self.username = username
        pwnam = pwd.getpwnam(username)
        self.uid = pwnam.pw_uid
        self.gid = pwnam.pw_gid

    def __enter__(self):
        """__enter__ method for use with `with` statement"""
        os.setresgid(self.gid, self.gid, os.getgid())
        os.setresuid(self.uid, self.uid, os.getuid())

    def __exit__(self, exc_type, exc_val, exc_tb):
        """__exit__ method for use with `with` statement"""
        _, _, suid = os.getresuid()
        _, _, sgid = os.getresgid()
        os.setresuid(suid, suid, suid)
        os.setresgid(sgid, sgid, sgid)


class UbuntuGeonamesCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.install, self._on_install)

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event.
        - installs binary packages
        - clones this repo
        - Sets up postgresql db, user, password
        - runs import-geonames.sh
        - sphinxsearch - installed by installs binary packages
            - replace /etc/sphinxsearch/sphinx.conf with sphinx.conf from repo
            - sudo indexer geonames
            - enables sphinxsearch
            - restarts the systemd unit
        - sets up systemd unit for geoname flask app to be run by apache
        - restarts apache
        """
        binaries = cast(list, self.model.config["binary-packages"].split(" "))  # pyright: ignore
        logger.info(f"installing binaries '{binaries}'")
        self._install_binaries(binaries)
        logger.info("Cloning repo...")
        self._clone_ubuntu_geonames()
        logger.info("Waiting for postgres service to be ready...")
        if not self._wait_for_postgres_to_be_ready():
            return
        logger.info("Setting up postgres credentials...")
        self._postgres_db_and_creds_setup()
        logger.info("Running import-geonames.sh...")
        self._run_import_geonames()
        logger.info("Setting up sphinxsearch config...")
        self._setup_sphinx_conf()
        logger.info("Setting up geonames indexes")
        self._geonames_indexes()
        logger.info("Enabling sphinxsearch...")
        self._enable_sphinxsearch()
        logger.info("Starting sphinxsearch...")
        self._run_subprocess_command("sudo systemctl restart sphinxsearch.service")
        logger.info("Writing apache config for geoname app...")
        self._write_apache_config()
        logger.info("Hacky, setting ~ permissions so apache can search under ~")
        self._run_subprocess_command("sudo setfacl -m u:www-data:rw /home/ubuntu/")
        logger.info("Restarting apache...")
        self._run_subprocess_command("sudo systemctl restart apache2.service")
        self.unit.status = ops.ActiveStatus("Done!")

    def _write_apache_config(self):
        conf_file_name = "geonames-apache2.conf"
        cfg_dir = Path("/etc/apache2")
        sites_enabled_dir = cfg_dir / "sites-enabled"
        cfg_fp = sites_enabled_dir / conf_file_name
        repo_cfg_fp = REPO_LOCATION / conf_file_name
        shutil.copy(repo_cfg_fp, cfg_fp)

    def _enable_sphinxsearch(self):
        sphinxsearch_enable = "START=yes"
        sphinxsearch_default = Path("/etc/default/sphinxsearch")
        sphinxsearch_default.write_text(sphinxsearch_enable)

    def _geonames_indexes(self):
        idx_command = "sudo indexer geonames"
        self._run_subprocess_command(idx_command)

    def _setup_sphinx_conf(self):
        sphinx_conf_dir = Path("/etc/sphinxsearch/")
        conf_file_name = "sphinx.conf"
        for cfg_file in sphinx_conf_dir.glob("**/*"):
            if cfg_file.is_file():
                if "conf" in cfg_file.name:
                    cfg_file.rename(cfg_file.with_suffix(".bkp"))
        existing_conf_file = REPO_LOCATION / conf_file_name
        to_conf_file = sphinx_conf_dir / conf_file_name
        shutil.copy(existing_conf_file, to_conf_file)

    def _clone_ubuntu_geonames(self):
        with UnixUser("ubuntu"):
            try:
                pygit2.clone_repository(
                    REPO_REMOTE,
                    str(REPO_LOCATION),
                    checkout_branch=REPO_BRANCH,
                )
            except ValueError:
                # already cloned
                pass

    def _run_subprocess_command(self, command: str):
        try:
            logger.info(f"Running the following command '{command}'")
            subprocess.run(command, check=True, shell=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.info(f"Failed to run '{command}' with '{e}'")
            return False

    def _install_binaries(self, binaries: list[str]):
        self._run_subprocess_command(f"sudo apt install -y {' '.join(binaries)}")

    def _wait_for_postgres_to_be_ready(self, timeout: int = 120):
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self._run_subprocess_command("sudo pg_isready"):
                return True
        logger.info(f"Postgres service not loading in '{timeout}' seconds")
        return False

    def _run_command_as_postgres_user(self, bash_command: str):
        prefix = "sudo -u postgres"
        full_cmd = f"{prefix} {bash_command}"
        self._run_subprocess_command(full_cmd)

    def _run_psql_command(self, psql_command: str):
        psql_prefix = "psql -c"
        full_cmd = f"""{psql_prefix} "{psql_command}" """
        self._run_command_as_postgres_user(full_cmd)

    def _postgres_db_and_creds_setup(self):
        postgres_cmds = [
            "create database geonames",
            "create user geouser",
            "alter user geouser with encrypted password 'geopw'",
            "grant all privileges on database geonames to geouser",
        ]
        for cmd in postgres_cmds:
            self._run_psql_command(cmd)

    def _run_import_geonames(self):
        full_path = REPO_LOCATION / "import-geonames.sh"
        self._run_subprocess_command(str(full_path))


if __name__ == "__main__":  # pragma: nocover
    ops.main(UbuntuGeonamesCharm)  # type: ignore

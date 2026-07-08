#!/usr/bin/env python3
# Copyright 2026 Canonical
# See LICENSE file for licensing details.

"""Representation of the geonames service."""

import logging
import os
import pwd
import shutil
import subprocess
import time
from pathlib import Path

from charmlibs import apt
from charmlibs.apt import PackageError, PackageNotFoundError

logger = logging.getLogger(__name__)

# Debian packages needed to run the geonames service.
PACKAGES = [
    "apache2",
    "libapache2-mod-wsgi-py3",
    "unzip",
    "git",
    "postgresql",
    "sphinxsearch",
    "python3-psycopg2",
    "python3-flask",
    "python3-pymysql",
]

REPO_LOCATION = Path("/home/ubuntu/ubuntu-geonames/")

POSTGRES_READY_TIMEOUT = 120


class UnixUser:
    """Class representation of a unix user."""

    def __init__(self, username):
        self.username = username
        pwnam = pwd.getpwnam(username)
        self.uid = pwnam.pw_uid
        self.gid = pwnam.pw_gid

    def __enter__(self):
        """Switch the effective user and group to this user."""
        os.setresgid(self.gid, self.gid, os.getgid())
        os.setresuid(self.uid, self.uid, os.getuid())

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the original effective user and group."""
        _, _, suid = os.getresuid()
        _, _, sgid = os.getresgid()
        os.setresuid(suid, suid, suid)
        os.setresgid(sgid, sgid, sgid)


class Geonames:
    """Represent a geonames instance in the workload."""

    def __init__(self):
        self.env = os.environ.copy()
        juju_http_proxy = self.env.get("JUJU_CHARM_HTTP_PROXY")
        juju_https_proxy = self.env.get("JUJU_CHARM_HTTPS_PROXY")
        if juju_http_proxy:
            self.env["HTTP_PROXY"] = juju_http_proxy
            self.env["http_proxy"] = juju_http_proxy
        if juju_https_proxy:
            self.env["HTTPS_PROXY"] = juju_https_proxy
            self.env["https_proxy"] = juju_https_proxy

    def _run_subprocess_command(self, command: str, check: bool = False) -> bool:
        """Run a shell command. If check is True, raise on failure; otherwise log and return False."""
        try:
            logger.info("Running the following command '%s'", command)
            subprocess.run(command, check=True, shell=True, env=self.env)
            return True
        except subprocess.CalledProcessError as e:
            logger.info("Failed to run '%s' with '%s'", command, e)
            if check:
                raise
            return False

    def _install_packages(self):
        """Install the Debian packages needed."""
        try:
            apt.update()
            logger.debug("Apt index refreshed.")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to update package cache: %s", e)
            raise

        for p in PACKAGES:
            try:
                apt.add_package(p)
                logger.debug("Package %s installed", p)
            except PackageNotFoundError:
                logger.error("Failed to find package %s in package cache", p)
                raise
            except PackageError as e:
                logger.error("Failed to install %s: %s", p, e)
                raise

    def _copy_files(self):
        """Copy the geonames application files to the target location."""
        os.makedirs(REPO_LOCATION, exist_ok=True)
        charm_dir = Path(__file__).parent
        files_to_copy = [
            "geoname.py",
            "geoname.wsgi",
        ]
        for f in files_to_copy:
            shutil.copy(charm_dir / f, REPO_LOCATION / f)
        self._run_subprocess_command(f"chown -R ubuntu:ubuntu {REPO_LOCATION}")

    def _wait_for_postgres(self, timeout: int = POSTGRES_READY_TIMEOUT):
        """Block until PostgreSQL is accepting connections."""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self._run_subprocess_command("pg_isready"):
                return
        logger.error("Postgres service not loading in '%s' seconds", timeout)
        raise TimeoutError(f"Postgres not ready after {timeout} seconds")

    def _run_command_as_postgres_user(self, bash_command: str):
        self._run_subprocess_command(f"sudo -u postgres {bash_command}")

    def _run_psql_command(self, psql_command: str):
        self._run_command_as_postgres_user(f'psql -c "{psql_command}" ')

    def _setup_postgres(self):
        """Create the geonames database, user and grants."""
        postgres_cmds = [
            "create database geonames",
            "create user geouser",
            "alter user geouser with encrypted password 'geopw'",
            "grant all privileges on database geonames to geouser",
        ]
        for cmd in postgres_cmds:
            self._run_psql_command(cmd)

        self._run_command_as_postgres_user(
            'psql -d geonames -c "GRANT ALL ON SCHEMA public TO geouser;"'
        )

    def _run_import(self):
        """Run import-geonames.sh, which downloads and populates the database."""
        import_script = Path(__file__).parent / "import-geonames.sh"
        self._run_subprocess_command(f"bash {import_script}", check=True)

    def _setup_sphinx_conf(self):
        """Replace the packaged sphinxsearch config with the repository's."""
        sphinx_conf_dir = Path("/etc/sphinxsearch/")
        conf_file_name = "sphinx.conf"
        for cfg_file in sphinx_conf_dir.glob("**/*"):
            if cfg_file.is_file() and "conf" in cfg_file.name:
                cfg_file.rename(cfg_file.with_suffix(".bkp"))
        charm_dir = Path(__file__).parent
        shutil.copy(charm_dir / conf_file_name, sphinx_conf_dir / conf_file_name)

    def _build_indexes(self):
        logger.info("Running 'indexer --rotate geonames'")
        proc = subprocess.run("indexer --rotate geonames", shell=True, env=self.env)
        if proc.returncode not in (0, 2):
            raise subprocess.CalledProcessError(proc.returncode, "indexer --rotate geonames")

    def _enable_sphinxsearch(self):
        Path("/etc/default/sphinxsearch").write_text("START=yes")

    def _write_apache_config(self):
        """Install the geonames Apache site and disable the default one."""
        self._run_subprocess_command("a2enmod wsgi")
        self._run_subprocess_command("rm -f /etc/apache2/sites-enabled/000-default.conf")
        conf_file_name = "geonames-apache2.conf"
        sites_enabled_dir = Path("/etc/apache2/sites-enabled")
        charm_dir = Path(__file__).parent
        shutil.copy(charm_dir / conf_file_name, sites_enabled_dir / conf_file_name)

    def install(self):
        """Install and configure the geonames environment.

        Installs binary packages, clones the repository, sets up PostgreSQL,
        imports the geonames data, configures and enables sphinxsearch, then
        installs the Apache site and restarts the services.
        """
        logger.info("Installing packages %s", PACKAGES)
        self._install_packages()
        logger.info("Copying application files...")
        self._copy_files()
        logger.info("Waiting for postgres service to be ready...")
        self._wait_for_postgres()
        logger.info("Setting up postgres credentials...")
        self._setup_postgres()
        logger.info("Running import-geonames.sh...")
        self._run_import()
        logger.info("Setting up sphinxsearch config...")
        self._setup_sphinx_conf()
        logger.info("Setting up geonames indexes")
        self._build_indexes()
        logger.info("Enabling sphinxsearch...")
        self._enable_sphinxsearch()
        logger.info("Starting sphinxsearch...")
        self._run_subprocess_command("systemctl restart sphinxsearch.service")
        logger.info("Writing apache config for geoname app...")
        self._write_apache_config()
        # Apache serves the app from under ~ubuntu and needs traversal permission.
        self._run_subprocess_command("chmod a+rx /home/ubuntu/")
        logger.info("Restarting apache...")
        self._run_subprocess_command("systemctl restart apache2.service")

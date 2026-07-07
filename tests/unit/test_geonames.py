# Copyright 2025 andersson123
# See LICENSE file for licensing details.

from subprocess import CalledProcessError
from unittest.mock import MagicMock, call, patch

import pytest
from charmlibs.apt import PackageError, PackageNotFoundError

import geonames


@pytest.fixture
def geonames_instance():
    return geonames.Geonames()


@patch("geonames.subprocess.run")
def test_run_subprocess_command_returns_true_on_success(mock_run, geonames_instance):
    assert geonames_instance._run_subprocess_command("true") is True
    mock_run.assert_called_once_with("true", check=True, shell=True)


@patch("geonames.subprocess.run")
def test_run_subprocess_command_returns_false_on_failure(mock_run, geonames_instance):
    mock_run.side_effect = CalledProcessError(1, "false")
    assert geonames_instance._run_subprocess_command("false") is False


@patch("geonames.apt")
def test_install_packages_updates_cache_then_installs_all(mock_apt, geonames_instance):
    geonames_instance._install_packages()

    mock_apt.update.assert_called_once()
    assert mock_apt.add_package.call_count == len(geonames.PACKAGES)
    mock_apt.add_package.assert_has_calls([call(p) for p in geonames.PACKAGES])


@patch("geonames.apt")
def test_install_packages_raises_when_update_fails(mock_apt, geonames_instance):
    mock_apt.update.side_effect = CalledProcessError(1, "apt update")
    with pytest.raises(CalledProcessError):
        geonames_instance._install_packages()


@patch("geonames.apt")
def test_install_packages_raises_when_package_not_found(mock_apt, geonames_instance):
    mock_apt.add_package.side_effect = PackageNotFoundError("not found")
    with pytest.raises(PackageNotFoundError):
        geonames_instance._install_packages()


@patch("geonames.apt")
def test_install_packages_raises_when_package_error(mock_apt, geonames_instance):
    mock_apt.add_package.side_effect = PackageError("install failed")
    with pytest.raises(PackageError):
        geonames_instance._install_packages()


@patch("geonames.pygit2")
@patch("geonames.UnixUser")
def test_clone_repo_clones_as_ubuntu_user(mock_unix_user, mock_pygit2, geonames_instance):
    geonames_instance._clone_repo()

    mock_unix_user.assert_called_once_with("ubuntu")
    mock_pygit2.clone_repository.assert_called_once_with(
        geonames.REPO_REMOTE,
        str(geonames.REPO_LOCATION),
        checkout_branch=geonames.REPO_BRANCH,
    )


@patch("geonames.pygit2")
@patch("geonames.UnixUser")
def test_clone_repo_ignores_already_cloned(mock_unix_user, mock_pygit2, geonames_instance):
    mock_pygit2.clone_repository.side_effect = ValueError("exists")
    geonames_instance._clone_repo()


def test_wait_for_postgres_returns_when_ready(geonames_instance):
    geonames_instance._run_subprocess_command = MagicMock(return_value=True)
    geonames_instance._wait_for_postgres(timeout=5)
    geonames_instance._run_subprocess_command.assert_called_once_with("pg_isready")


def test_wait_for_postgres_raises_timeout_when_never_ready(geonames_instance):
    geonames_instance._run_subprocess_command = MagicMock(return_value=False)
    with pytest.raises(TimeoutError):
        geonames_instance._wait_for_postgres(timeout=0)


def test_setup_postgres_runs_expected_psql_commands(geonames_instance):
    geonames_instance._run_subprocess_command = MagicMock(return_value=True)

    geonames_instance._setup_postgres()

    ran = [c.args[0] for c in geonames_instance._run_subprocess_command.call_args_list]
    assert any("create database geonames" in cmd for cmd in ran)
    assert any("create user geouser" in cmd for cmd in ran)
    assert any("GRANT ALL ON SCHEMA public TO geouser" in cmd for cmd in ran)
    assert all(cmd.startswith("sudo -u postgres") for cmd in ran)


def test_run_import_invokes_import_script(geonames_instance):
    geonames_instance._run_subprocess_command = MagicMock(return_value=True)

    geonames_instance._run_import()

    command = geonames_instance._run_subprocess_command.call_args.args[0]
    assert command.startswith("bash ")
    assert command.endswith("import-geonames.sh")


@patch("geonames.shutil")
@patch("geonames.Path")
def test_setup_sphinx_conf_backs_up_and_copies_repo_config(
    mock_path, mock_shutil, geonames_instance
):
    conf_dir = MagicMock()
    existing = MagicMock()
    existing.is_file.return_value = True
    existing.name = "sphinx.conf"
    conf_dir.glob.return_value = [existing]
    mock_path.return_value = conf_dir

    geonames_instance._setup_sphinx_conf()

    existing.rename.assert_called_once()
    mock_shutil.copy.assert_called_once()


@patch("geonames.Path")
def test_enable_sphinxsearch_writes_start_flag(mock_path, geonames_instance):
    default_file = MagicMock()
    mock_path.return_value = default_file

    geonames_instance._enable_sphinxsearch()

    mock_path.assert_called_once_with("/etc/default/sphinxsearch")
    default_file.write_text.assert_called_once_with("START=yes")


@patch("geonames.shutil")
def test_write_apache_config_enables_wsgi_and_installs_site(mock_shutil, geonames_instance):
    geonames_instance._run_subprocess_command = MagicMock(return_value=True)

    geonames_instance._write_apache_config()

    ran = [c.args[0] for c in geonames_instance._run_subprocess_command.call_args_list]
    assert "a2enmod wsgi" in ran
    assert "rm -f /etc/apache2/sites-enabled/000-default.conf" in ran
    mock_shutil.copy.assert_called_once()


def test_install_orchestrates_all_setup_steps(geonames_instance):
    geonames_instance._install_packages = MagicMock()
    geonames_instance._clone_repo = MagicMock()
    geonames_instance._wait_for_postgres = MagicMock()
    geonames_instance._setup_postgres = MagicMock()
    geonames_instance._run_import = MagicMock()
    geonames_instance._setup_sphinx_conf = MagicMock()
    geonames_instance._build_indexes = MagicMock()
    geonames_instance._enable_sphinxsearch = MagicMock()
    geonames_instance._write_apache_config = MagicMock()
    geonames_instance._run_subprocess_command = MagicMock(return_value=True)

    geonames_instance.install()

    geonames_instance._install_packages.assert_called_once()
    geonames_instance._clone_repo.assert_called_once()
    geonames_instance._wait_for_postgres.assert_called_once()
    geonames_instance._setup_postgres.assert_called_once()
    geonames_instance._run_import.assert_called_once()
    geonames_instance._setup_sphinx_conf.assert_called_once()
    geonames_instance._build_indexes.assert_called_once()
    geonames_instance._enable_sphinxsearch.assert_called_once()
    geonames_instance._write_apache_config.assert_called_once()
    geonames_instance._run_subprocess_command.assert_any_call(
        "systemctl restart sphinxsearch.service"
    )
    geonames_instance._run_subprocess_command.assert_any_call("chmod a+rx /home/ubuntu/")
    geonames_instance._run_subprocess_command.assert_any_call("systemctl restart apache2.service")


def test_install_propagates_package_failure(geonames_instance):
    geonames_instance._install_packages = MagicMock(side_effect=PackageError("boom"))

    with pytest.raises(PackageError):
        geonames_instance.install()

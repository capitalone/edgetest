"""Testing the core module."""

import platform
from pathlib import Path
from unittest.mock import PropertyMock, call, patch

import pytest

from edgetest.core import TestPackage


@patch.object(Path, "cwd")
def test_init(mock_path, tmpdir, plugin_manager):
    """Test init."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    tester_upgrade = TestPackage(
        hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade"]
    )
    tester_lower = TestPackage(
        hook=plugin_manager.hook, envname="myenv_lower", lower=["mylower"]
    )

    for tester in (tester_upgrade, tester_lower):
        assert tester.hook == plugin_manager.hook
        assert tester.basedir == Path(str(location)) / ".edgetest"
        assert tester.package_dir == "."
        assert not tester.setup_status
        assert not tester.status

    assert tester_upgrade.envname == "myenv"
    assert tester_upgrade.upgrade == ["myupgrade"]
    assert tester_upgrade.lower is None

    assert tester_lower.envname == "myenv_lower"
    assert tester_lower.upgrade is None
    assert tester_lower.lower == ["mylower"]

    with pytest.raises(ValueError):
        _tester_error = TestPackage(
            hook=plugin_manager.hook,
            envname="myenv",
            upgrade=["myupgrade"],
            lower=["mylower"],
        )


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_basic_setup(mock_popen, mock_path, tmpdir, plugin_manager):
    """Test creating a basic environment."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    tester = TestPackage(
        hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade"]
    )

    assert tester.basedir == Path(str(location)) / ".edgetest"

    tester.setup()

    env_loc = Path(str(location)) / ".edgetest" / "myenv"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python"
    else:
        py_loc = env_loc / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            ("uv", "pip", "install", f"--python={py_loc!s}", "."),
            stdout=-1,
            stderr=-1,
            universal_newlines=True,
        ),
    ]
    assert tester.setup_status


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_basic_setup_create_environment_error(
    mock_popen, mock_path, tmpdir, plugin_manager_environment_error
):
    """Test failure in environment creation."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    tester = TestPackage(
        hook=plugin_manager_environment_error.hook,
        envname="myenv",
        upgrade=["myupgrade"],
    )

    assert tester.basedir == Path(str(location)) / ".edgetest"

    tester.setup()
    assert not tester.setup_status


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_basic_setup_upgrade_error(
    mock_popen, mock_path, tmpdir, plugin_manager_upgrade_error
):
    """Test failure in environment creation."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    tester = TestPackage(
        hook=plugin_manager_upgrade_error.hook,
        envname="myenv",
        upgrade=["myupgrade"],
    )

    assert tester.basedir == Path(str(location)) / ".edgetest"

    tester.setup()
    assert not tester.setup_status


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_basic_setup_lower_error(
    mock_popen, mock_path, tmpdir, plugin_manager_lower_error
):
    """Test failure in environment creation."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    tester = TestPackage(
        hook=plugin_manager_lower_error.hook,
        envname="myenv",
        lower=["mylower"],
    )

    assert tester.basedir == Path(str(location)) / ".edgetest"

    tester.setup()
    assert not tester.setup_status


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_setup_extras(mock_popen, mock_path, tmpdir, plugin_manager):
    """Test creating an environment with extra installations."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    tester = TestPackage(
        hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade"]
    )

    assert tester.basedir == Path(str(location)) / ".edgetest"

    tester.setup(extras=["tests", "complete"])

    env_loc = str(Path(str(location)) / ".edgetest" / "myenv")
    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            ("uv", "pip", "install", f"--python={py_loc!s}", ".[tests, complete]"),
            stdout=-1,
            stderr=-1,
            universal_newlines=True,
        ),
    ]

    assert tester.setup_status


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_setup_pip_deps(mock_popen, mock_path, tmpdir, plugin_manager):
    """Test creating an environment with pip dependencies."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    tester = TestPackage(
        hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade"]
    )

    assert tester.basedir == Path(str(location)) / ".edgetest"

    tester.setup(deps=["-r requirements.txt", "otherpkg"])

    env_loc = str(Path(str(location)) / ".edgetest" / "myenv")

    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            (
                "uv",
                "pip",
                "install",
                f"--python={py_loc!s}",
                "-r",
                "requirements.txt",
                "otherpkg",
            ),
            stdout=-1,
            stderr=-1,
            universal_newlines=True,
        ),
        call(
            ("uv", "pip", "install", f"--python={py_loc}", "."),
            stdout=-1,
            stderr=-1,
            universal_newlines=True,
        ),
    ]

    assert tester.setup_status


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_setup_pip_deps_error(mock_popen, mock_path, tmpdir, plugin_manager):
    """Test creating an environment with pip dependencies."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=1)

    tester = TestPackage(
        hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade"]
    )

    assert tester.basedir == Path(str(location)) / ".edgetest"

    tester.setup(deps=["-r requirements.txt", "otherpkg"])

    env_loc = str(Path(str(location)) / ".edgetest" / "myenv")

    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            (
                "uv",
                "pip",
                "install",
                f"--python={py_loc!s}",
                "-r",
                "requirements.txt",
                "otherpkg",
            ),
            stdout=-1,
            stderr=-1,
            universal_newlines=True,
        ),
    ]

    assert not tester.setup_status


@patch.object(Path, "cwd")
@patch("edgetest.core.Popen", autospec=True)
def test_run_tests(mock_popen, mock_path, tmpdir, plugin_manager):
    """Test running basic tests."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    tester = TestPackage(
        hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade"]
    )

    env_loc = str(Path(str(location)) / ".edgetest" / "myenv")
    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    # If environment not setup successfully, then there should be an error
    with pytest.raises(RuntimeError):
        tester.run_tests(command="pytest tests -m 'not integration'")

    # Manually specify that environment was setup successfully
    tester.setup_status = True
    out = tester.run_tests(command="pytest tests -m 'not integration'")
    assert out == 0
    assert mock_popen.call_args_list == [
        call(
            (f"{py_loc}", "-m", "pytest", "tests", "-m", "not integration"),
            universal_newlines=True,
        )
    ]

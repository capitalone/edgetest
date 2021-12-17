"""Testing the core module."""

import platform
from pathlib import Path
from unittest.mock import PropertyMock, call, patch

import pytest

from edgetest.core import TestPackage


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

    assert tester._basedir == Path(str(location)) / ".edgetest"

    tester.setup()

    env_loc = Path(str(location)) / ".edgetest" / "myenv"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python"
    else:
        py_loc = env_loc / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            (f"{str(py_loc)}", "-m", "pip", "install", "."),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (
                f"{str(py_loc)}",
                "-m",
                "pip",
                "install",
                "myupgrade",
                "--upgrade",
            ),
            stdout=-1,
            universal_newlines=True,
        ),
    ]


@patch.object(Path, "cwd")
@patch("edgetest.utils.Popen", autospec=True)
def test_basic_setup_error(mock_popen, mock_path, tmpdir, plugin_manager):
    """Test failure in environment creation."""
    location = tmpdir.mkdir("mydir")
    mock_path.return_value = Path(str(location))
    mock_popen.return_value.communicate.return_value = ("output", "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=1)

    tester = TestPackage(
        hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade"]
    )

    assert tester._basedir == Path(str(location)) / ".edgetest"

    with pytest.raises(RuntimeError):
        tester.setup()


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

    assert tester._basedir == Path(str(location)) / ".edgetest"

    tester.setup(extras=["tests", "complete"])

    env_loc = str(Path(str(location)) / ".edgetest" / "myenv")
    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            (f"{py_loc}", "-m", "pip", "install", ".[tests, complete]"),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (f"{py_loc}", "-m", "pip", "install", "myupgrade", "--upgrade"),
            stdout=-1,
            universal_newlines=True,
        ),
    ]


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

    assert tester._basedir == Path(str(location)) / ".edgetest"

    tester.setup(deps=["-r requirements.txt", "otherpkg"])

    env_loc = str(Path(str(location)) / ".edgetest" / "myenv")

    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            (
                f"{py_loc}",
                "-m",
                "pip",
                "install",
                "-r",
                "requirements.txt",
                "otherpkg",
            ),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (f"{py_loc}", "-m", "pip", "install", "."),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (f"{py_loc}", "-m", "pip", "install", "myupgrade", "--upgrade"),
            stdout=-1,
            universal_newlines=True,
        ),
    ]


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

    out = tester.run_tests(command="pytest tests -m 'not integration'")

    assert out == 0
    assert mock_popen.call_args_list == [
        call(
            (f"{py_loc}", "-m", "pytest", "tests", "-m", "not integration"),
            universal_newlines=True,
        )
    ]

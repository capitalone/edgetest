"""Test the CLI."""

import platform
from pathlib import Path
from unittest.mock import PropertyMock, call, patch

from click.testing import CliRunner

from edgetest.interface import cli

CURR_DIR = Path(__file__).resolve().parent

REQS = """
myupgrade
"""

SETUP_CFG = """
[edgetest.envs.myenv]
upgrade =
    myupgrade
command =
    pytest tests -m 'not integration'
"""

SETUP_CFG_REQS = """
[options]
install_requires =
    myupgrade<=0.1.5
"""

SETUP_CFG_REQS_UPGRADE = "[options]\ninstall_requires = \n\tmyupgrade<=0.2.0\n\n"

SETUP_CFG_EXTRAS = """
[options.extras_require]
myextra =
    myupgrade<=0.1.5

[edgetest.envs.myenv]
upgrade =
    myupgrade
extras =
    myextra
command =
    pytest tests -m 'not integration'
"""

SETUP_CFG_EXTRAS_UPGRADE = """[options.extras_require]
myextra = \n\tmyupgrade<=0.2.0

[edgetest.envs.myenv]
upgrade = \n\tmyupgrade
extras = \n\tmyextra
command = \n\tpytest tests -m 'not integration'

"""

PIP_LIST = """
[{"name": "myupgrade", "version": "0.2.0"}]
"""

TABLE_OUTPUT = """

=============  ===============  ===================  =================
Environment    Passing tests    Upgraded packages    Package version
=============  ===============  ===================  =================
myenv          True             myupgrade            0.2.0
=============  ===============  ===================  =================
"""

TABLE_OUTPUT_NOTEST = """

=============  ===============  ===================  =================
Environment    Passing tests    Upgraded packages    Package version
=============  ===============  ===================  =================
myenv          False            myupgrade            0.2.0
=============  ===============  ===================  =================
"""

TABLE_OUTPUT_REQS = """

================  ===============  ===================  =================
Environment       Passing tests    Upgraded packages    Package version
================  ===============  ===================  =================
myupgrade         True             myupgrade            0.2.0
all-requirements  True             myupgrade            0.2.0
================  ===============  ===================  =================
"""


@patch("edgetest.lib.EnvBuilder", autospec=True)
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_basic(mock_popen, mock_cpopen, mock_builder):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG)

        result = runner.invoke(cli, ["--config=setup.cfg"])

    assert result.exit_code == 0

    env_loc = Path(loc) / ".edgetest" / "myenv"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python"
    else:
        py_loc = env_loc / "bin" / "python"

    mock_builder.return_value.create.assert_called_with(env_loc)
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
        call(
            (f"{str(py_loc)}", "-m", "pip", "list", "--format", "json"),
            stdout=-1,
            universal_newlines=True,
        ),
    ]
    assert mock_cpopen.call_args_list == [
        call(
            (
                f"{str(py_loc)}",
                "-m",
                "pytest",
                "tests",
                "-m",
                "not integration",
            ),
            universal_newlines=True,
        )
    ]

    assert result.output == TABLE_OUTPUT


@patch("edgetest.lib.EnvBuilder", autospec=True)
@patch("edgetest.core.Popen", autospect=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_reqs(mock_popen, mock_cpopen, mock_builder):
    """Test running tests based on the requirements file."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("requirements.txt", "w") as outfile:
            outfile.write(REQS)

        result = runner.invoke(cli)

    if platform.system() == "Windows":
        py_myupgrade_loc = Path(loc) / ".edgetest" / "myupgrade" / "Scripts" / "python"
        py_allreq_loc = (
            Path(loc) / ".edgetest" / "all-requirements" / "Scripts" / "python"
        )
    else:
        py_myupgrade_loc = Path(loc) / ".edgetest" / "myupgrade" / "bin" / "python"
        py_allreq_loc = Path(loc) / ".edgetest" / "all-requirements" / "bin" / "python"

    assert result.exit_code == 0

    assert mock_builder.return_value.create.call_args_list == [
        call(env_dir=Path(loc) / ".edgetest" / "myupgrade"),
        call(env_dir=Path(loc) / ".edgetest" / "all-requirements"),
    ]

    assert mock_popen.call_args_list == [
        call(
            (f"{str(py_myupgrade_loc)}", "-m", "pip", "install", "."),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (
                f"{str(py_myupgrade_loc)}",
                "-m",
                "pip",
                "install",
                "myupgrade",
                "--upgrade",
            ),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (
                f"{str(py_allreq_loc)}",
                "-m",
                "pip",
                "install",
                ".",
            ),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (
                f"{str(py_allreq_loc)}",
                "-m",
                "pip",
                "install",
                "myupgrade",
                "--upgrade",
            ),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (
                f"{str(py_myupgrade_loc)}",
                "-m",
                "pip",
                "list",
                "--format",
                "json",
            ),
            stdout=-1,
            universal_newlines=True,
        ),
        call(
            (
                f"{str(py_allreq_loc)}",
                "-m",
                "pip",
                "list",
                "--format",
                "json",
            ),
            stdout=-1,
            universal_newlines=True,
        ),
    ]
    assert mock_cpopen.call_args_list == [
        call(
            (f"{str(py_myupgrade_loc)}", "-m", "pytest"),
            universal_newlines=True,
        ),
        call(
            (f"{str(py_allreq_loc)}", "-m", "pytest"),
            universal_newlines=True,
        ),
    ]

    assert result.output == TABLE_OUTPUT_REQS


@patch("edgetest.lib.EnvBuilder", autospec=True)
@patch("edgetest.core.Popen", autospect=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_setup_reqs_update(mock_popen, mock_cpopen, mock_builder):
    """Test running tests and updating requirements in a ``setup.cfg`` file."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG_REQS)

        result = runner.invoke(cli, ["--config=setup.cfg", "--export"])

        with open("setup.cfg") as infile:
            out = infile.read()

    assert result.exit_code == 0

    assert out == SETUP_CFG_REQS_UPGRADE


@patch("edgetest.lib.EnvBuilder", autospec=True)
@patch("edgetest.core.Popen", autospect=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_setup_extras_update(mock_popen, mock_cpopen, mock_builder):
    """Test running tests and updating extra installation requirements in a ``setup.cfg`` file."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG_EXTRAS)

        result = runner.invoke(cli, ["--config=setup.cfg", "--export"])

        print(result.output)

        with open("setup.cfg") as infile:
            out = infile.read()

    assert result.exit_code == 0

    assert out == SETUP_CFG_EXTRAS_UPGRADE


@patch("edgetest.core.Popen", autospect=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_nosetup(mock_popen, mock_cpopen):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG)

        result = runner.invoke(cli, ["--config=setup.cfg", "--nosetup"])

    assert result.exit_code == 0

    env_loc = str(Path(loc) / ".edgetest" / "myenv")
    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    assert mock_popen.call_args_list == [
        call(
            (f"{py_loc}", "-m", "pip", "list", "--format", "json"),
            stdout=-1,
            universal_newlines=True,
        ),
    ]
    assert mock_cpopen.call_args_list == [
        call(
            (f"{py_loc}", "-m", "pytest", "tests", "-m", "not integration"),
            universal_newlines=True,
        )
    ]

    assert (
        result.output == f"""Using existing environment for myenv...\n{TABLE_OUTPUT}"""
    )


@patch("edgetest.lib.EnvBuilder", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_notest(mock_popen, mock_builder):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG)

        result = runner.invoke(cli, ["--config=setup.cfg", "--notest"])

    assert result.exit_code == 0

    env_loc = Path(loc) / ".edgetest" / "myenv"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python"
    else:
        py_loc = env_loc / "bin" / "python"

    mock_builder.return_value.create.assert_called_with(env_loc)
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
        call(
            (f"{str(py_loc)}", "-m", "pip", "list", "--format", "json"),
            stdout=-1,
            universal_newlines=True,
        ),
    ]

    assert result.output == f"""Skipping tests for myenv\n{TABLE_OUTPUT_NOTEST}"""

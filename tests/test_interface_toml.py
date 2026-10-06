"""Test the CLI."""

import os
import platform
from pathlib import Path
from unittest.mock import PropertyMock, call, patch

import pytest
from click.testing import CliRunner
from uv import find_uv_bin

from edgetest.interface import cli

CURR_DIR = Path(__file__).resolve().parent

REQS = """
myupgrade
"""

SETUP_TOML = """
[edgetest.envs.myenv]
upgrade = ["myupgrade"]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_TOOL = """
[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_COOLDOWN = """[edgetest]
exclude_newer = "3 days"

[edgetest.envs.myenv]
upgrade = ["myupgrade"]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_LOWER = """[project]
dependencies = [
  "myupgrade<=0.1.5",
  "mylower<=0.1,>=0.0.1"
]

[edgetest.envs.myenv_lower]
lower = [ "mylower" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_LOWER_TOOL = """
[project]
dependencies = [
  "myupgrade<=0.1.5",
  "mylower<=0.1,>=0.0.1"
]

[[tool.edgetest.env]]
name = "myenv_lower"
lower = [ "mylower" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_UPGRADE_THEN_LOWER = """[project]
dependencies = [
  "myupgrade<=0.1.5",
  "mylower<=0.1,>=0.0.1"
]

[edgetest.envs.myenv]
upgrade = [ "myupgrade" ]
command = "pytest tests -m 'not integration'"

[edgetest.envs.myenv_lower]
lower = [ "mylower" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_UPGRADE_THEN_LOWER_TOOL = """[project]
dependencies = [
  "myupgrade<=0.1.5",
  "mylower<=0.1,>=0.0.1"
]

[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]
command = "pytest tests -m 'not integration'"

[[tool.edgetest.env]]
name = "myenv_lower"
lower = [ "mylower" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_LOWER_THEN_UPGRADE = """[project]
dependencies = [
  "myupgrade<=0.1.5",
  "mylower<=0.1,>=0.0.1"
]

[edgetest.envs.myenv_lower]
lower = [ "mylower" ]
command = "pytest tests -m 'not integration'"

[edgetest.envs.myenv]
upgrade = [ "myupgrade" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_LOWER_THEN_UPGRADE_TOOL = """[project]
dependencies = [
  "myupgrade<=0.1.5",
  "mylower<=0.1,>=0.0.1"
]

[[tool.edgetest.env]]
name = "myenv_lower"
lower = [ "mylower" ]
command = "pytest tests -m 'not integration'"

[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_REQS = """[project]
dependencies = ["myupgrade<=0.1.5"]
"""

SETUP_TOML_REQS_UPGRADE = """[project]
dependencies = ["myupgrade<=0.2.0"]
"""

SETUP_TOML_EXTRAS = """[project]
optional-dependencies.myextra = [ "myupgrade<=0.1.5" ]

[edgetest.envs.myenv]
upgrade = [ "myupgrade" ]
extras = [ "myextra" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_EXTRAS_TOOL = """[project]
optional-dependencies.myextra = [ "myupgrade<=0.1.5" ]

[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]
extras = [ "myextra" ]
command = "pytest tests -m 'not integration'"
"""


SETUP_TOML_EXTRAS_UPGRADE = """[project]
optional-dependencies.myextra = [ "myupgrade<=0.2.0" ]

[edgetest.envs.myenv]
upgrade = [ "myupgrade" ]
extras = [ "myextra" ]
command = "pytest tests -m 'not integration'"
"""

SETUP_TOML_EXTRAS_UPGRADE_TOOL = """[project]
optional-dependencies.myextra = [ "myupgrade<=0.2.0" ]

[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]
extras = [ "myextra" ]
command = "pytest tests -m 'not integration'"
"""

PIP_LIST = """
[{"name": "myupgrade", "version": "0.2.0"}]
"""

TABLE_OUTPUT = """

=============  ==================  ===============  ===================  ==================  =================
Environment    Setup successful    Passing tests    Upgraded packages    Lowered packages    Package version
=============  ==================  ===============  ===================  ==================  =================
myenv          True                True             myupgrade                                0.2.0
=============  ==================  ===============  ===================  ==================  =================
"""

TABLE_OUTPUT_LOWER = """

=============  ==================  ===============  ===================  ==================  =================
Environment    Setup successful    Passing tests    Upgraded packages    Lowered packages    Package version
=============  ==================  ===============  ===================  ==================  =================
myenv_lower    True                True                                  mylower             0.0.1
=============  ==================  ===============  ===================  ==================  =================
"""

TABLE_OUTPUT_NOTEST = """

=============  ==================  ===============  ===================  ==================  =================
Environment    Setup successful    Passing tests    Upgraded packages    Lowered packages    Package version
=============  ==================  ===============  ===================  ==================  =================
myenv          True                False            myupgrade                                0.2.0
=============  ==================  ===============  ===================  ==================  =================
"""

TABLE_OUTPUT_NOTEST_LOWER = """

=============  ==================  ===============  ===================  ==================  =================
Environment    Setup successful    Passing tests    Upgraded packages    Lowered packages    Package version
=============  ==================  ===============  ===================  ==================  =================
myenv_lower    True                False                                 mylower             0.0.1
=============  ==================  ===============  ===================  ==================  =================
"""

TABLE_OUTPUT_REQS = """

================  ==================  ===============  ===================  ==================  =================
Environment       Setup successful    Passing tests    Upgraded packages    Lowered packages    Package version
================  ==================  ===============  ===================  ==================  =================
myupgrade         True                True             myupgrade                                0.2.0
all-requirements  True                True             myupgrade                                0.2.0
================  ==================  ===============  ===================  ==================  =================
"""


@pytest.mark.parametrize("toml_source", [SETUP_TOML, SETUP_TOML_TOOL])
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_basic(mock_popen, mock_cpopen, toml_source):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(toml_source)

        result = runner.invoke(cli, ["--config=pyproject.toml"])

    assert result.exit_code == 0

    env_loc = Path(loc) / ".edgetest" / "myenv"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python.exe"
    else:
        py_loc = env_loc / "bin" / "python"

    uv_ = find_uv_bin()
    assert mock_popen.call_args_list == [
        call(
            (uv_, "venv", str(env_loc)),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "sync", "--inexact", f"--python={py_loc!s}"),
            stdout=-1,
            stderr=-1,
            env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(env_loc)},
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "install",
                f"--python={py_loc!s}",
                "myupgrade",
                "--upgrade",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "pip", "list", f"--python={py_loc!s}", "--format", "json"),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
    ]
    assert mock_cpopen.call_args_list == [
        call(
            (
                f"{py_loc!s}",
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


@pytest.mark.parametrize("ignore_cooldown", [True, False])
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_basic_cooldown(mock_popen, mock_cpopen, ignore_cooldown):
    """Test creating a basic environment with dependency cooldowns."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML_COOLDOWN)

        if ignore_cooldown:
            result = runner.invoke(
                cli, ["--config=pyproject.toml", "--ignore-cooldown"]
            )
        else:
            result = runner.invoke(cli, ["--config=pyproject.toml"])

    assert result.exit_code == 0

    env_loc = Path(loc) / ".edgetest" / "myenv"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python.exe"
    else:
        py_loc = env_loc / "bin" / "python"

    # Upgrade installation argument depends on the parameterization
    uv_ = find_uv_bin()
    upgrade_callargs_ = [
        uv_,
        "pip",
        "install",
        f"--python={py_loc!s}",
        "myupgrade",
        "--upgrade",
    ]
    if not ignore_cooldown:
        upgrade_callargs_.append("--exclude-newer=3 days")

    assert mock_popen.call_args_list == [
        call(
            (uv_, "venv", str(env_loc)),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "sync", "--inexact", f"--python={py_loc!s}"),
            stdout=-1,
            stderr=-1,
            env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(env_loc)},
            universal_newlines=True,
        ),
        call(
            tuple(upgrade_callargs_),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "pip", "list", f"--python={py_loc!s}", "--format", "json"),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
    ]
    assert mock_cpopen.call_args_list == [
        call(
            (
                f"{py_loc!s}",
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


@pytest.mark.parametrize("toml_source", [SETUP_TOML_LOWER, SETUP_TOML_LOWER_TOOL])
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_basic_lower(mock_popen, mock_cpopen, toml_source):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(toml_source)

        result = runner.invoke(cli, ["--config=pyproject.toml"])

    assert result.exit_code == 0

    env_loc = Path(loc) / ".edgetest" / "myenv_lower"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python.exe"
    else:
        py_loc = env_loc / "bin" / "python"

    uv_ = find_uv_bin()
    assert mock_popen.call_args_list == [
        call(
            (uv_, "venv", str(env_loc)),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "sync", "--inexact", f"--python={py_loc!s}"),
            stdout=-1,
            stderr=-1,
            env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(env_loc)},
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "install",
                f"--python={py_loc!s}",
                "mylower==0.0.1",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
    ]
    assert mock_cpopen.call_args_list == [
        call(
            (
                f"{py_loc!s}",
                "-m",
                "pytest",
                "tests",
                "-m",
                "not integration",
            ),
            universal_newlines=True,
        )
    ]

    assert result.output == TABLE_OUTPUT_LOWER


@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_reqs(mock_popen, mock_cpopen):
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
        py_myupgrade_loc = (
            Path(loc) / ".edgetest" / "myupgrade" / "Scripts" / "python.exe"
        )
        py_allreq_loc = (
            Path(loc) / ".edgetest" / "all-requirements" / "Scripts" / "python.exe"
        )
    else:
        py_myupgrade_loc = Path(loc) / ".edgetest" / "myupgrade" / "bin" / "python"
        py_allreq_loc = Path(loc) / ".edgetest" / "all-requirements" / "bin" / "python"

    assert result.exit_code == 0

    uv_ = find_uv_bin()
    assert mock_popen.call_args_list == [
        call(
            (uv_, "venv", str(Path(loc) / ".edgetest" / "myupgrade")),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "sync", "--inexact", f"--python={py_myupgrade_loc!s}"),
            stdout=-1,
            stderr=-1,
            env={
                **os.environ,
                "UV_PROJECT_ENVIRONMENT": str(Path(loc) / ".edgetest" / "myupgrade"),
            },
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "install",
                f"--python={py_myupgrade_loc!s}",
                "myupgrade",
                "--upgrade",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "venv", str(Path(loc) / ".edgetest" / "all-requirements")),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "sync",
                "--inexact",
                f"--python={py_allreq_loc!s}",
            ),
            stdout=-1,
            stderr=-1,
            env={
                **os.environ,
                "UV_PROJECT_ENVIRONMENT": str(
                    Path(loc) / ".edgetest" / "all-requirements"
                ),
            },
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "install",
                f"--python={py_allreq_loc!s}",
                "myupgrade",
                "--upgrade",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "list",
                f"--python={py_myupgrade_loc!s}",
                "--format",
                "json",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "list",
                f"--python={py_allreq_loc!s}",
                "--format",
                "json",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
    ]
    assert mock_cpopen.call_args_list == [
        call(
            (f"{py_myupgrade_loc!s}", "-m", "pytest"),
            universal_newlines=True,
        ),
        call(
            (f"{py_allreq_loc!s}", "-m", "pytest"),
            universal_newlines=True,
        ),
    ]

    assert result.output == TABLE_OUTPUT_REQS


@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_setup_reqs_update(mock_popen, mock_cpopen):
    """Test running tests and updating requirements in a ``pyproject.toml`` file."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML_REQS)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--export"])

        with open("pyproject.toml") as infile:
            out = infile.read()

    assert result.exit_code == 0

    assert out == SETUP_TOML_REQS_UPGRADE


@pytest.mark.parametrize(
    "toml_source, toml_output",
    [
        (SETUP_TOML_EXTRAS, SETUP_TOML_EXTRAS_UPGRADE),
        (SETUP_TOML_EXTRAS_TOOL, SETUP_TOML_EXTRAS_UPGRADE_TOOL),
    ],
)
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_setup_extras_update(mock_popen, mock_cpopen, toml_source, toml_output):
    """Test running tests and updating extra installation requirements in a ``pyproject.toml`` file."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(toml_source)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--export"])

        with open("pyproject.toml") as infile:
            out = infile.read()

    assert result.exit_code == 0

    assert out == toml_output


@pytest.mark.parametrize(
    "toml_source",
    [SETUP_TOML_UPGRADE_THEN_LOWER, SETUP_TOML_UPGRADE_THEN_LOWER_TOOL],
)
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_export_with_lower_env_after_upgrade_env(
    mock_popen, mock_cpopen, toml_source
):
    """Upgrades must survive when a ``lower`` env is declared after the upgrade env.

    A lower-bound env reports no upgrades of its own, so exporting from only the
    last tester silently dropped every widened pin.
    """
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open("pyproject.toml", "w") as outfile:
            outfile.write(toml_source)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--export"])

        with open("pyproject.toml") as infile:
            out = infile.read()

    assert result.exit_code == 0
    assert '"myupgrade<=0.2.0"' in out
    assert '"myupgrade<=0.1.5"' not in out
    assert '"mylower<=0.1,>=0.0.1"' in out


@pytest.mark.parametrize(
    "toml_source",
    [SETUP_TOML_UPGRADE_THEN_LOWER, SETUP_TOML_UPGRADE_THEN_LOWER_TOOL],
)
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_export_blocked_when_any_env_fails(mock_popen, mock_cpopen, toml_source):
    """No pin may be widened while any environment is red.

    A widened upper bound claims the package works at that version across the
    whole configured matrix. If one env fails, the claim is unproven, so the
    export must not happen regardless of which env failed or whether another
    env produced upgrades.
    """
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    # First env (upgrade) passes, second env (lower) fails.
    type(mock_cpopen.return_value).returncode = PropertyMock(side_effect=[0, 0, 1, 1])
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open("pyproject.toml", "w") as outfile:
            outfile.write(toml_source)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--export"])

        with open("pyproject.toml") as infile:
            out = infile.read()

    assert result.exit_code == 0
    assert '"myupgrade<=0.1.5"' in out
    assert '"myupgrade<=0.2.0"' not in out


@pytest.mark.parametrize(
    "toml_source",
    [SETUP_TOML_UPGRADE_THEN_LOWER, SETUP_TOML_UPGRADE_THEN_LOWER_TOOL],
)
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_export_blocked_when_first_env_fails(mock_popen, mock_cpopen, toml_source):
    """A failure in the first env must block export even when the last env passes.

    ``testers[-1].status`` alone lets a partially verified matrix through when
    the failure is not in the last env.
    """
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    # First env (upgrade) fails, second env (lower) passes.
    type(mock_cpopen.return_value).returncode = PropertyMock(side_effect=[1, 1, 0, 0])
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open("pyproject.toml", "w") as outfile:
            outfile.write(toml_source)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--export"])

        with open("pyproject.toml") as infile:
            out = infile.read()

    assert result.exit_code == 0
    assert '"myupgrade<=0.1.5"' in out
    assert '"myupgrade<=0.2.0"' not in out


@pytest.mark.parametrize(
    "toml_source",
    [SETUP_TOML_LOWER_THEN_UPGRADE, SETUP_TOML_LOWER_THEN_UPGRADE_TOOL],
)
@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_export_blocked_when_upgrade_env_passes_last(
    mock_popen, mock_cpopen, toml_source
):
    """The scenario the old ``testers[-1]`` gate actually got wrong.

    The lower env fails FIRST and the passing upgrade env runs LAST, so
    ``testers[-1].status`` is ``True`` and the old gate widens the pin while
    an earlier env is red. The ``all()`` gate must block the export.

    Unlike the other ``blocked_when`` tests, this one fails under the old
    gate: the last tester is green and *does* carry an upgrade, so the old
    code writes ``myupgrade<=0.2.0``.
    """
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    # First env (lower) fails, second env (upgrade) passes.
    type(mock_cpopen.return_value).returncode = PropertyMock(side_effect=[1, 1, 0, 0])
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem():
        with open("pyproject.toml", "w") as outfile:
            outfile.write(toml_source)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--export"])

        with open("pyproject.toml") as infile:
            out = infile.read()

    assert result.exit_code == 0
    assert '"myupgrade<=0.1.5"' in out
    assert '"myupgrade<=0.2.0"' not in out


@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_nosetup(mock_popen, mock_cpopen):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--nosetup"])

    assert result.exit_code == 0

    env_loc = str(Path(loc) / ".edgetest" / "myenv")
    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python.exe"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    uv_ = find_uv_bin()
    assert mock_popen.call_args_list == [
        call(
            (uv_, "pip", "list", f"--python={py_loc}", "--format", "json"),
            stdout=-1,
            stderr=-1,
            env=None,
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


@patch("edgetest.core.Popen", autospec=True)
@patch("edgetest.utils.Popen", autospec=True)
def test_cli_nosetup_lower(mock_popen, mock_cpopen):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)
    mock_cpopen.return_value.communicate.return_value = ("output", "error")
    type(mock_cpopen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML_LOWER)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--nosetup"])

    assert result.exit_code == 0

    env_loc = str(Path(loc) / ".edgetest" / "myenv_lower")
    if platform.system() == "Windows":
        py_loc = Path(env_loc) / "Scripts" / "python.exe"
    else:
        py_loc = Path(env_loc) / "bin" / "python"

    assert mock_cpopen.call_args_list == [
        call(
            (f"{py_loc}", "-m", "pytest", "tests", "-m", "not integration"),
            universal_newlines=True,
        )
    ]

    assert (
        result.output
        == f"""Using existing environment for myenv_lower...\n{TABLE_OUTPUT_LOWER}"""
    )


@patch("edgetest.utils.Popen", autospec=True)
def test_cli_notest(mock_popen):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--notest"])

    assert result.exit_code == 0

    env_loc = Path(loc) / ".edgetest" / "myenv"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python.exe"
    else:
        py_loc = env_loc / "bin" / "python"

    uv_ = find_uv_bin()
    assert mock_popen.call_args_list == [
        call(
            (uv_, "venv", str(env_loc)),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "sync", "--inexact", f"--python={py_loc!s}"),
            stdout=-1,
            stderr=-1,
            env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(env_loc)},
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "install",
                f"--python={py_loc!s}",
                "myupgrade",
                "--upgrade",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "pip", "list", f"--python={py_loc!s}", "--format", "json"),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
    ]

    assert result.output == f"""Skipping tests for myenv\n{TABLE_OUTPUT_NOTEST}"""


@patch("edgetest.utils.Popen", autospec=True)
def test_cli_notest_lower(mock_popen):
    """Test creating a basic environment."""
    mock_popen.return_value.communicate.return_value = (PIP_LIST, "error")
    type(mock_popen.return_value).returncode = PropertyMock(return_value=0)

    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML_LOWER)

        result = runner.invoke(cli, ["--config=pyproject.toml", "--notest"])

    assert result.exit_code == 0

    env_loc = Path(loc) / ".edgetest" / "myenv_lower"
    if platform.system() == "Windows":
        py_loc = env_loc / "Scripts" / "python.exe"
    else:
        py_loc = env_loc / "bin" / "python"

    uv_ = find_uv_bin()
    assert mock_popen.call_args_list == [
        call(
            (uv_, "venv", str(env_loc)),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
        call(
            (uv_, "sync", "--inexact", f"--python={py_loc!s}"),
            stdout=-1,
            stderr=-1,
            env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(env_loc)},
            universal_newlines=True,
        ),
        call(
            (
                uv_,
                "pip",
                "install",
                f"--python={py_loc!s}",
                "mylower==0.0.1",
            ),
            stdout=-1,
            stderr=-1,
            env=None,
            universal_newlines=True,
        ),
    ]

    assert (
        result.output
        == f"""Skipping tests for myenv_lower\n{TABLE_OUTPUT_NOTEST_LOWER}"""
    )

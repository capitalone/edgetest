"""Default virtual environment hook."""

import logging
import platform
from pathlib import Path
from typing import Dict, List

import click
import pluggy

from edgetest.utils import _run_command

LOG = logging.getLogger(__name__)

hookimpl = pluggy.HookimplMarker("edgetest")


@hookimpl(trylast=True)
def path_to_python(basedir: str, envname: str) -> str:
    """Return the path to the python executable."""
    if platform.system() == "Windows":
        return str(Path(basedir) / envname / "Scripts" / "python.exe")
    else:
        return str(Path(basedir) / envname / "bin" / "python")


@hookimpl(trylast=True)
def create_environment(basedir: str, envname: str, conf: Dict):
    """Create the virtual environment for testing.

    Creates an environment using ``uv``.

    Parameters
    ----------
    basedir : str
        The base directory location for the environment.
    envname : str
        The name of the virtual environment.
    conf : dict
        Ignored.

    Raises
    ------
    RuntimeError
        Error raised if the environment cannot be created.
    """
    try:
        callargs_ = ["uv", "venv", str(Path(basedir, envname))]
        if (py_version := conf.get("python_version")) is not None:
            callargs_.append(f"--python={py_version}")
        if Path(basedir, envname).is_dir():
            callargs_.append("--clear")
        _run_command(*callargs_)
    except Exception as err:
        raise RuntimeError(f"Unable to create {envname} in {basedir}") from err


@hookimpl(trylast=True)
def run_update(basedir: str, envname: str, upgrade: List, conf: Dict):
    """Update packages from upgrade list.

    Parameters
    ----------
    basedir : str
        The base directory location for the environment.
    envname : str
        The name of the virtual environment.
    upgrade : list
        The list of packages to upgrade
    conf : dict
        Ignored.

    Raises
    ------
    RuntimeError
        Error raised if the packages cannot be updated.
    """
    python_path = path_to_python(basedir, envname)
    try:
        _run_command(
            "uv", "pip", "install", f"--python={python_path}", *upgrade, "--upgrade"
        )
    except Exception as err:
        raise RuntimeError(f"Unable to pip upgrade: {upgrade}") from err


@hookimpl(trylast=True)
def run_install_lower(basedir: str, envname: str, lower: List[str], conf: Dict):
    """Install lower bounds of packages provided.

    Parameters
    ----------
    basedir : str
        The base directory location for the environment.
    envname : str
        Environment to install into.
    lower : List[str]
        Lower bounds of packages to install.
    conf : Dict
        The configuration dictionary for the environment. This is useful if you
        want to add configuration arguments for additional dependencies that can
        only be installed through the environment manager (e.g. Conda).
    """
    python_path = path_to_python(basedir, envname)
    try:
        _run_command("uv", "pip", "install", f"--python={python_path}", *lower)
    except Exception as err:
        raise RuntimeError(f"Unable to pip install: {lower}") from err


@hookimpl(tryfirst=True)
def post_run_hook(testers: List, conf: Dict):
    """Refresh ``uv.lock`` based on the test output."""
    ctx = click.get_current_context()
    if not ctx.params["export"]:
        LOG.info(
            "Skipping ``uv lock --upgrade`` as the requirements have not been updated."
        )
    elif (
        testers[-1].status and (Path(ctx.params["config"]).parent / "uv.lock").is_file()
    ):
        # uv.lock exists already and the last tester passed
        try:
            _run_command("uv", "lock", "--upgrade")
        except RuntimeError:
            LOG.info("Unable to update the ``uv.lock`` file.")
    else:
        LOG.info(
            "Skpping ``uv.lock`` refresh as the tests didn't pass and/or we couldn't find an existing ``uv.lock`` file."
        )

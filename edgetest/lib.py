"""Default virtual environment hook."""

import platform
from pathlib import Path
from typing import Dict, List
from venv import EnvBuilder

import pluggy

from edgetest.utils import _run_command

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

    Creates an environment using ``venv``.

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
    builder = EnvBuilder(with_pip=False)
    try:
        builder.create(env_dir=Path(basedir, envname))
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

"""Default virtual environment hook."""

import platform
from pathlib import Path
from typing import Dict, List
from venv import EnvBuilder

import pluggy

from .utils import _run_command

hookimpl = pluggy.HookimplMarker("edgetest")


@hookimpl(trylast=True)
def path_to_python(basedir: str, envname: str) -> str:
    """Return the path to the python executable."""
    if platform.system() == "Windows":
        return str(Path(basedir) / envname / "Scripts" / "python")
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
    builder = EnvBuilder(with_pip=True)
    try:
        builder.create(env_dir=Path(basedir, envname))
    except Exception:
        raise RuntimeError(f"Unable to create {envname} in {basedir}")


@hookimpl(trylast=True)
def run_update(basedir: str, envname: str, upgrade: List):
    """Update packages from upgrade list.

    Parameters
    ----------
    basedir : str
        The base directory location for the environment.
    envname : str
        The name of the virtual environment.
    upgrade : list
        The list of packages to upgrade

    Raises
    ------
    RuntimeError
        Error raised if the packages cannot be updated.
    """
    python_path = path_to_python(basedir, envname)
    try:
        _run_command(
            python_path,
            "-m",
            "pip",
            "install",
            *upgrade,
            "--upgrade",
        )
    except Exception:
        raise RuntimeError(f"Unable to pip upgrade: {upgrade}")

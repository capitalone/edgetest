"""Hook specifications for edgetest."""

from typing import Dict, List

import pluggy

from edgetest.schema import Schema

hookspec = pluggy.HookspecMarker("edgetest")


@hookspec
def addoption(schema: Schema):
    """Modify the schema for custom options.

    You can add environment-level options through ``add_envoption`` or global
    configuration options through ``add_globaloption``.
    """


@hookspec
def pre_run_hook(conf: Dict):
    """Pre-setup and test hook.

    Parameters
    ----------
    conf : Dict
        The entire configuration dictionary.
    """


@hookspec(firstresult=True)
def path_to_python(basedir: str, envname: str) -> str:
    """Return the path to the python executable.

    Parameters
    ----------
    basedir : str
        The base directory location for the environment.
    envname : str
        The name of the virtual environment.

    Returns
    -------
    str
        The path to the python executable for the environment. For installations
        via ``pip``, we'll be running ``python -m pip install ...``, where ``python``
        is the python executable for the environment.
    """


@hookspec(firstresult=True)
def create_environment(basedir: str, envname: str, conf: Dict):
    """Create the virtual environment for testing.

    Parameters
    ----------
    basedir : str
        The base directory location for the environment.
    envname : str
        The name of the virtual environment.
    conf : dict
        The configuration dictionary for the environment. This is useful if you
        want to add configuration arguments for additional dependencies that can
        only be installed through the environment manager (e.g. Conda).

    Raises
    ------
    RuntimeError
        Error raised if the environment cannot be created.
    """


@hookspec(firstresult=True)
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
        The configuration dictionary for the environment. This is useful if you
        want to add configuration arguments for additional dependencies that can
        only be installed through the environment manager (e.g. Conda).

    Raises
    ------
    RuntimeError
        Error raised if the packages cannot be updated.
    """


@hookspec(firstresult=True)
def run_install_lower(basedir: str, envname: str, lower: Dict[str, str], conf: Dict):
    """Install lower bounds of packages provided.

    Parameters
    ----------
    basedir : str
        The base directory location for the environment.
    envname : str
        Environment to install into.
    lower_bounds : Dict[str, str]
        Lower bounds of packages to install.
    conf : Dict
        The configuration dictionary for the environment. This is useful if you
        want to add configuration arguments for additional dependencies that can
        only be installed through the environment manager (e.g. Conda).
    """


@hookspec
def post_run_hook(testers: List, conf: Dict):
    """Post testing hook.

    For executing code after the environment set up and testing.

    Parameters
    ----------
    testers : list
        The list of ``TestPackage`` objects.
    conf : dict
        The entire configuration dictionary.
    """

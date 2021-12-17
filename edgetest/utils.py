"""Utility functions."""

import os
from configparser import ConfigParser
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Dict, List, Optional, Tuple

from packaging.specifiers import SpecifierSet
from pkg_resources import parse_requirements

from .logger import get_logger

LOG = get_logger(__name__)


def _run_command(*args) -> Tuple[str, int]:
    """Run a command using ``subprocess.Popen``.

    Parameters
    ----------
    *args
        Arguments for the command.

    Returns
    -------
    str
        The output
    int
        The exit code

    Raises
    ------
    RuntimeError
        Error raised when the command is not successfully executed.
    """
    LOG.debug(f"Running the following command: \n\n {' '.join(args)}")
    popen = Popen(args, stdout=PIPE, universal_newlines=True)
    out, _ = popen.communicate()
    if popen.returncode:
        raise RuntimeError(
            f"Unable to run the following command: \n\n {' '.join(args)}"
        )

    return out, popen.returncode


@contextmanager
def pushd(new_dir: str):
    """Create a context manager for running commands in sub-directories.

    Parameters
    ----------
    new_dir : str
        The relative directory to run the command in.
    """
    curr_dir = Path.cwd()
    os.chdir(curr_dir / new_dir)
    try:
        yield
    finally:
        os.chdir(curr_dir)


def convert_requirements(requirements: str, conf: Optional[Dict] = None) -> Dict:
    """Generate environments for a newline-separate list of package requirements.

    This function will generate one environment per entry with an additional environment
    that upgrades all requirements simultaneously.

    Parameters
    ----------
    requirements : str
        The requirements string.
    conf : dict, optional (default None)
        An existing configuration to edit.

    Returns
    -------
    Dict
        A configuration dictionary.
    """
    conf = {"envs": []} if conf is None else conf
    pkgs = [pkg.project_name for pkg in parse_requirements(requirements)]
    for pkg in pkgs:
        conf["envs"].append({})
        conf["envs"][-1]["name"] = pkg
        conf["envs"][-1]["upgrade"] = pkg
    # Create an environment with all requirements upgraded
    conf["envs"].append({})
    conf["envs"][-1]["name"] = "all-requirements"
    conf["envs"][-1]["upgrade"] = "\n".join(pkgs)

    return conf


def gen_requirements_config(fname_or_buf: str, **options) -> Dict:
    """Generate a configuration file from package requirements.

    This function will convert the package installation requirements to a configuration
    file with one environment per requirement.

    Parameters
    ----------
    fname_or_buf : str
        Path to the requirements file to parse using ``pkg_resources.parse_requirements``
        or the string representing the requirements file.
    **options
        Options to apply to each test environment.

    Returns
    -------
    Dict
        The configuration file.
    """
    # First, get the requirements
    if Path(fname_or_buf).is_file():
        with open(fname_or_buf) as infile:
            cfg = infile.read()
    else:
        cfg = fname_or_buf
    output = convert_requirements(requirements=cfg)
    for index in range(len(output["envs"])):
        output["envs"][index].update(options)

    return output


def parse_cfg(filename: str = "setup.cfg", requirements: Optional[str] = None) -> Dict:
    """Generate a configuration from a ``.ini`` style file.

    This function can operate in two ways. First, it can look for sections that
    start with ``edgetest`` and build a configuration. Suppose
    you have ``setup.cfg`` as follows:

    .. code-block:: ini

        [edgetest.envs.pandas]
        upgrade =
            pandas

    This will result in a configuration that has one testing environment, named
    ``pandas``, that upgrades the ``pandas`` package.

    If you don't have any sections that start with ``edgetest.envs``, we will look for
    the PEP 517-style ``setup.cfg`` install requirements (the ``install_requires`` key
    within the ``options`` section). To set global defaults for you environments, use
    the ``edgetest`` section:

    .. code-block:: ini

        [edgetest]
        extras =
            tests
        command =
            pytest tests -m "not integration"

        [edgetest.envs.pandas]
        upgrade =
            pandas

    For this single environment file, the above configuration is equivalent to

    .. code-block:: ini

        [edgetest.envs.pandas]
        extras =
            tests
        command =
            pytest tests -m "not integration"
        upgrade =
            pandas

    Parameters
    ----------
    filename : str, optional (default "setup.cfg")
        The name of the configuration file to read. Defaults to ``setup.cfg``.
    requirements : str, optional (default None)
        An optional path to the requirements text file. If there are no PEP-517
        style dependencies or coded environments in the edgetest configuration, this
        function will look for dependencies in the requirements file.

    Returns
    -------
    Dict
        A configuration dictionary for ``edgetest``.
    """
    # Read in the configuration file
    config = ConfigParser()
    config.read(filename)
    # Parse
    output: Dict = {"envs": []}
    # Get any global options if necessary
    options = dict(config["edgetest"]) if "edgetest" in config else {}
    # Next, create the sections
    for section in config.sections():
        if not section.startswith("edgetest."):
            continue
        # Look for the special ``envs`` key
        section_name = section.split(".")
        if section_name[1] == "envs":
            output["envs"].append(dict(config[section]))
            output["envs"][-1]["name"] = section_name[2]
        else:
            output[section_name[1]] = dict(config[section])
    if len(output["envs"]) == 0:
        if config.get("options", "install_requires"):
            output = convert_requirements(
                requirements=config["options"]["install_requires"], conf=output
            )
        elif requirements:
            req_conf = gen_requirements_config(fname_or_buf=requirements)
            output["envs"] = req_conf["envs"]
        else:
            raise ValueError("Please supply a valid list of environments to create.")
    # Apply global environment options (without overwriting)
    for idx in range(len(output["envs"])):
        output["envs"][idx] = dict(
            list(options.items()) + list(output["envs"][idx].items())
        )

    return output


def upgrade_requirements(
    fname_or_buf: str, upgraded_packages: List[Dict[str, str]]
) -> str:
    """Create an upgraded requirements file.

    Parameters
    ----------
    fname_or_buf : str
        Path to the requirements file to parse using ``pkg_resources.parse_requirements``
        or the string representing the requirements file.
    upgraded_packages : list
        A list of packages upgraded in the testing procedure.

    Returns
    -------
    str
        The string file representing the new requirements file.
    """
    # Get the existing file
    try:
        if Path(fname_or_buf).is_file():
            with open(fname_or_buf) as infile:
                cfg = infile.read()
        else:
            cfg = fname_or_buf
    except OSError:
        # Filename too long for the is_file() function
        cfg = fname_or_buf
    pkgs = [pkg for pkg in parse_requirements(cfg)]
    upgrades = {pkg["name"]: pkg["version"] for pkg in upgraded_packages}

    for pkg in pkgs:
        if pkg.project_name not in upgrades:
            continue
        # Replace the spec
        specs = deepcopy(pkg.specs)
        for index, value in enumerate(specs):
            if value[0] == "<=":
                pkg.specs[index] = ("<=", upgrades[pkg.project_name])
            elif value[0] == "<":
                pkg.specs[index] = ("!=", value[1])
                pkg.specs.append(("<=", upgrades[pkg.project_name]))
            elif value[0] == "==":
                pkg.specs = [(">=", value[1]), ("<=", upgrades[pkg.project_name])]
        pkg.specifier = SpecifierSet(",".join("".join(spec) for spec in pkg.specs))  # type: ignore

    return "\n".join(str(pkg) for pkg in pkgs)


def upgrade_setup_cfg(
    upgraded_packages: List[Dict[str, str]], filename: str = "setup.cfg"
) -> ConfigParser:
    """Upgrade the ``setup.cfg`` file.

    Parameters
    ----------
    upgraded_packages : List[Dict[str, str]]
        A list of packages upgraded in the testing procedure.
    filename : str, optional (default "setup.cfg")
        The name of the configuration file to read. Defaults to ``setup.cfg``.

    Returns
    -------
    ConfigParser
        The updated configuration file.
    """
    parser = ConfigParser()
    parser.read(filename)
    if "options" in parser and parser.get("options", "install_requires"):
        LOG.info(f"Updating the requirements in {filename}")
        upgraded = upgrade_requirements(
            fname_or_buf=parser["options"]["install_requires"].lstrip(),
            upgraded_packages=upgraded_packages,
        )
        parser["options"]["install_requires"] = "\n" + upgraded
    # Update the extras, if necessary
    if "options.extras_require" in parser:
        for extra, dependencies in parser.items("options.extras_require"):
            upgraded = upgrade_requirements(
                fname_or_buf=dependencies,
                upgraded_packages=upgraded_packages,
            )
            parser["options.extras_require"][extra] = "\n" + upgraded

    return parser

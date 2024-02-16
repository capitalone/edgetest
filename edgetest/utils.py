"""Utility functions."""

import os
from configparser import ConfigParser
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any, Dict, List, Optional, Tuple, Union

from packaging.specifiers import SpecifierSet
from pkg_resources import parse_requirements
from tomlkit import TOMLDocument, load
from tomlkit.container import Container
from tomlkit.items import Array, Item, String, Table

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


def _convert_toml_array_to_string(item: Union[Item, Any]) -> str:
    if isinstance(item, Array):
        return "\n".join(item)
    elif isinstance(item, String):
        return str(item)
    else:
        raise ValueError


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
            if (
                "lower" in output["envs"][-1]
                and "options" in config
                and "install_requires" in config["options"]
            ):
                output["envs"][-1]["lower"] = get_lower_bounds(
                    config.get("options", "install_requires"),
                    output["envs"][-1]["lower"],
                )
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


def parse_toml(
    filename: str = "pyproject.toml", requirements: Optional[str] = None
) -> Dict:
    """Generate a configuration from a ``.toml`` style file.

    This function can operate in two ways. First, it will look for tables that
    start with ``edgetest`` and build a configuration. Suppose
    you have ``pyproject.toml`` as follows:

    .. code-block:: toml

        [edgetest.envs.pandas]
        upgrade = [
            "pandas"
        ]

    This will result in a configuration that has one testing environment, named
    ``pandas``, that upgrades the ``pandas`` package.

    If you don't have any tables that start with ``edgetest.envs``, we will look for
    the installation requirements (the ``dependencies`` key within the ``project`` section).
    To set global defaults for you environments, use the ``edgetest`` table:

    .. code-block:: toml

        [edgetest]
        extras = [
            "tests"
        ]
        command = "pytest tests -m 'not integration'"

        [edgetest.envs.pandas]
        upgrade = [
            "pandas"
        ]

    For this single environment file, the above configuration is equivalent to

    .. code-block:: toml

        [edgetest.envs.pandas]
        extras = [
            "tests"
        ]
        command = "pytest tests -m 'not integration'"
        upgrade = [
            "pandas"
        ]

    Parameters
    ----------
    filename : str, optional (default "pyproject.toml")
        The name of the toml file to read. Defaults to ``pyproject.toml``.
    requirements : str, optional (default None)
        An optional path to the requirements text file. If there are no TOML
        style dependencies or coded environments in the edgetest configuration, this
        function will look for dependencies in the requirements file.

    Returns
    -------
    Dict
        A configuration dictionary for ``edgetest``.
    """
    options: Union[Item, Container, dict]
    # Read in the configuration file
    config: TOMLDocument = load(open(filename))
    # Parse
    output: Dict = {"envs": []}
    # Get any global options if necessary. First scan through and pop out any Tables
    temp_config = deepcopy(config)
    if "edgetest" in config:
        for j in config["edgetest"].items():  # type: ignore
            if isinstance(config["edgetest"][j[0]], Table):  # type: ignore
                _ = temp_config["edgetest"].pop(  # type: ignore
                    j[0], None
                )  # remove Tables from the temp config
            else:
                temp_config["edgetest"][j[0]] = _convert_toml_array_to_string(  # type: ignore
                    temp_config["edgetest"][j[0]]  # type: ignore
                )
        options = temp_config["edgetest"]
    else:
        options = {}

    # Check envs exists and any other Tables
    if "edgetest" in config:
        for section in config["edgetest"]:  # type: ignore
            if section == "envs":
                for env in config["edgetest"]["envs"]:  # type: ignore
                    for item in config["edgetest"]["envs"][env]:  # type: ignore
                        # If an Array then decompose to a string format
                        config["edgetest"]["envs"][env][  # type: ignore
                            item
                        ] = _convert_toml_array_to_string(
                            config["edgetest"]["envs"][env][item]  # type: ignore
                        )
                    output["envs"].append(dict(config["edgetest"]["envs"][env]))  # type: ignore
                    output["envs"][-1]["name"] = env
                    if (
                        "lower" in output["envs"][-1]
                        and "project" in config
                        and "dependencies" in config["project"]  # type: ignore
                    ):
                        output["envs"][-1]["lower"] = get_lower_bounds(
                            dict(config["project"])["dependencies"],  # type: ignore
                            output["envs"][-1]["lower"],
                        )
            elif isinstance(config["edgetest"][section], Table):  # type: ignore
                output[section] = dict(config["edgetest"][section])  # type: ignore

    if len(output["envs"]) == 0:
        if config.get("project").get("dependencies"):  # type: ignore
            output = convert_requirements(
                requirements="\n".join(config["project"]["dependencies"]),  # type: ignore
                conf=output,  # type: ignore # noqa: E501
            )
        elif requirements:
            req_conf = gen_requirements_config(fname_or_buf=requirements)
            output["envs"] = req_conf["envs"]
        else:
            raise ValueError("Please supply a valid list of environments to create.")

    # Apply global environment options (without overwriting)
    for idx in range(len(output["envs"])):
        output["envs"][idx] = dict(
            list(options.items()) + list(output["envs"][idx].items())  # type: ignore
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


def upgrade_pyproject_toml(
    upgraded_packages: List[Dict[str, str]], filename: str = "pyproject.toml"
) -> TOMLDocument:
    """Upgrade the ``pyproject.toml`` file.

    Parameters
    ----------
    upgraded_packages : List[Dict[str, str]]
        A list of packages upgraded in the testing procedure.
    filename : str, optional (default "pyproject.toml")
        The name of the configuration file to read. Defaults to ``pyproject.toml``.

    Returns
    -------
    TOMLDocument
        The updated TOMLDocument.
    """
    parser: TOMLDocument = load(open(filename))
    if "project" in parser and parser.get("project").get("dependencies"):  # type: ignore
        LOG.info(f"Updating the requirements in {filename}")
        upgraded = upgrade_requirements(
            fname_or_buf="\n".join(parser["project"]["dependencies"]),  # type: ignore
            upgraded_packages=upgraded_packages,
        )
        parser["project"]["dependencies"] = upgraded.split("\n")  # type: ignore
    # Update the extras, if necessary
    if parser.get("project").get("optional-dependencies"):  # type: ignore
        for extra, dependencies in parser["project"]["optional-dependencies"].items():  # type: ignore # noqa: E501
            upgraded = upgrade_requirements(
                fname_or_buf="\n".join(dependencies),
                upgraded_packages=upgraded_packages,
            )
            parser["project"]["optional-dependencies"][extra] = upgraded.split("\n")  # type: ignore

    return parser


def _isin_case_dashhyphen_ins(a: str, vals: List[str]) -> bool:
    """Run isin check that is case and dash/hyphen insensitive.

    Paramaters
    ----------
    a : str
        String value to check for membership against ``vals``.
    vals : list of str
        List of strings to check ``a`` against.

    Returns
    -------
    bool
        Return ``True`` if ``a`` in vals, otherwise ``False``.
    """
    for b in vals:
        if a.replace("_", "-").lower() == b.replace("_", "-").lower():
            return True
    return False


def get_lower_bounds(requirements: str, lower: str) -> str:
    r"""Get lower bounds of requested packages from installation requirements.

    Parses through the project ``requirements`` and the newline-delimited
    packages requested in ``lower`` to find the lower bounds.

    Parameters
    ----------
    requirements : str
        Project setup requirements,
        e.g. ``"pandas>=1.5.1,<=1.4.2\nnumpy>=1.22.1,<=1.25.4"``
    lower : str
        Newline-delimited packages requested,
         e.g. ``"pandas\nnumpy"``.

    Returns
    -------
    str
        The packages along with the lower bound, e.g. ``"pandas==1.5.1\nnumpy==1.22.1"``.
    """
    all_lower_bounds = {
        pkg.project_name + (f"[{','.join(pkg.extras)}]" if pkg.extras else ""): dict(
            pkg.specs
        ).get(">=")
        for pkg in parse_requirements(requirements)
    }

    lower_with_bounds = ""
    for pkg_name, lower_bound in all_lower_bounds.items():
        # TODO: Parse through extra requirements as well to get lower bounds
        if lower_bound is None:
            LOG.warning(
                "Requested %s lower bound, but did not find in install requirements.",
                pkg_name,
            )
        elif _isin_case_dashhyphen_ins(pkg_name, lower.split("\n")):
            lower_with_bounds += f"{pkg_name}=={lower_bound}\n"

    return lower_with_bounds

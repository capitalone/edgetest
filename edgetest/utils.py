"""Utility functions."""

import os
import re
import warnings
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE, Popen

import tomlkit
from packaging.requirements import Requirement
from packaging.specifiers import Specifier
from tomlkit.items import Table

from edgetest.logger import get_logger

LOG = get_logger(__name__)


def _run_command(*args, env: dict[str, str] | None = None) -> tuple[str, int]:
    """Run a command using ``subprocess.Popen``.

    Parameters
    ----------
    *args
        Arguments for the command.
    env : dict, optional (default None)
        Additional environment variables to set on top of the current
        environment. Passed to ``Popen`` merged with ``os.environ``;
        replacing the whole environment breaks subprocesses on Windows
        (e.g. ``python.exe`` fails to boot without ``SystemRoot``/``PATH``).

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
    if env is not None:
        env = {**os.environ, **env}
    popen = Popen(args, stdout=PIPE, stderr=PIPE, env=env, universal_newlines=True)
    out, err = popen.communicate()
    if popen.returncode:
        raise RuntimeError(
            f"Unable to run the following command: \n\n {' '.join(args)} \n\n"
            f"Returned the following stdout: \n\n {out} \n\n"
            f"Returned the following stderr: \n\n {err} \n\n"
        ) from None

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


def convert_requirements(requirements: str, conf: dict | None = None) -> dict:
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
    dict
        A configuration dictionary.
    """
    conf = {"envs": []} if conf is None else conf
    pkgs = [
        Requirement(val).name
        for val in requirements.splitlines()
        if not (val.strip().startswith("#") or val.strip() == "")
    ]
    for pkg in pkgs:
        conf["envs"].append({})
        conf["envs"][-1]["name"] = pkg
        conf["envs"][-1]["upgrade"] = pkg
    # Create an environment with all requirements upgraded
    conf["envs"].append({})
    conf["envs"][-1]["name"] = "all-requirements"
    conf["envs"][-1]["upgrade"] = "\n".join(pkgs)

    return conf


def gen_requirements_config(fname_or_buf: str, **options) -> dict:
    """Generate a configuration file from package requirements.

    This function will convert the package installation requirements to a configuration
    file with one environment per requirement.

    Parameters
    ----------
    fname_or_buf : str
        Path to the requirements file to parse using ``packaging.requirements.Requirement``
        or the string representing the requirements file.
    **options
        Options to apply to each test environment.

    Returns
    -------
    dict
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


def parse_toml(
    filename: str = "pyproject.toml", requirements: str | None = None
) -> dict:
    """Generate a configuration from a ``.toml`` style file.

    This function will look for a table that starts with either ``edgetest``
    or ``tool.edgetest``:

    .. tabs::

        .. tab:: legacy

            .. code-block:: toml

                [edgetest.envs.pandas]
                upgrade = [ "pandas" ]

        .. tab:: ``tool``-style

            .. code-block:: toml

                [[tool.edgetest.env]]
                name = "pandas"
                upgrade = [ "pandas" ]

    This will result in a configuration that has one testing environment, named
    ``pandas``, that upgrades the ``pandas`` package.

    If you don't have any tables that start with ``edgetest.envs`` or entries under the
    name ``tool.edgetest.env``, we will look for the installation requirements (the ``dependencies``
    key within the ``project`` section). To set the global defaults for your environments, use
    the ``edgetest`` or ``tool.edgetest`` table:

    .. tabs::

        .. tab:: legacy

            .. code-block:: toml

                [edgetest]
                extras = [ "tests" ]
                command = "pytest tests -m 'not integration'"

                [edgetest.envs.pandas]
                upgrade = [ "pandas" ]

        .. tab:: ``tool``-style

            .. code-block:: toml

                [tool.edgetest]
                extras = [ "tests" ]
                command = "pytest tests -m 'not integration'"

                [[tool.edgetest.env]]
                name = "pandas"
                upgrade = [ "pandas" ]

    For this single environment file, the above configuration is equivalent to

    .. tabs::

        .. tab:: legacy

            .. code-block:: toml

                [edgetest.envs.pandas]
                extras = [
                    "tests"
                ]
                command = "pytest tests -m 'not integration'"
                upgrade = [
                    "pandas"
                ]

        .. tab:: ``tool``-style

                [[tool.edgetest.env]]
                name = "pandas"
                extras = [ "tests" ]
                command = "pytest tests -m 'not integration'"
                upgrade = [ "pandas" ]

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
    dict
        A configuration dictionary for ``edgetest``.
    """
    options: dict
    # Read in the configuration file
    with open(filename) as buf:
        config: tomlkit.TOMLDocument = tomlkit.load(buf)
    # Check for ``[tool.edgetest]`` or ``[edgetest]``
    config_: Table
    if (config_ := config.get("tool", tomlkit.table()).get("edgetest")) is not None:
        output, options = _parse_toml_tool(config_)
    elif "edgetest" in config:
        warnings.warn(
            (
                "The [edgetest] configuration format has been deprecated. Please "
                "use [tool.edgetest] and [[tool.edgetest.env]] in the future."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        config_ = config.get("edgetest", tomlkit.table())
        output, options = _parse_toml_classic(config_)
    else:
        output = {"envs": []}
        options = {}

    for idx, env in enumerate(output["envs"]):
        if (
            "lower" in env
            and "project" in config
            and "dependencies" in config.get("project", tomlkit.array())
        ):
            output["envs"][idx]["lower"] = get_lower_bounds(
                config.get("project", tomlkit.table())
                .get("dependencies", tomlkit.array())
                .unwrap(),
                output["envs"][idx]["lower"],
            )

    if len(output["envs"]) == 0:
        if config.get("project").get("dependencies"):  # type: ignore
            output = convert_requirements(
                requirements="\n".join(config["project"]["dependencies"]),  # type: ignore
                conf=output,  # type: ignore
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


def _parse_toml_classic(config: Table) -> tuple[dict, dict]:
    """Generate a configuration from a ``.toml`` style file.

    This function is used to parse the classic ``edgetest`` table format.

    Parameters
    ----------
    config : Table
        The contents of ``[tool.edgetest]`` in the source TOML document.

    Returns
    -------
    dict
        A configuration dictionary for ``edgetest``.
    dict
        Global configuration options for ``edgetest``.
    """
    options = {
        key: value.unwrap()
        for key, value in config.items()
        if not isinstance(value, Table)
    }

    output: dict = {"envs": []}
    for section in config:
        if section == "envs":
            for name, env in config.get("envs", tomlkit.table()).unwrap().items():
                output["envs"].append({**env, "name": name})
        elif isinstance(config[section], Table):
            output[section] = config[section].unwrap()

    return output, options


def _parse_toml_tool(config: Table) -> tuple[dict, dict]:
    """Generate a configuration from a ``.toml`` style configuration.

    This function is used to parse the newer ``tool.edgetest`` table format.

    Parameters
    ----------
    config : Table
        The contents of ``[tool.edgetest]`` in the source TOML document.

    Returns
    -------
    Dict
        A basic configuration dictionary for ``edgetest``.
    Dict
        Global configuration options for ``edgetest``.
    """
    # Get any global options, if provided. First scan through and pop out any Tables
    options = {
        key: value.unwrap()
        for key, value in config.items()
        if key != "env" and not isinstance(value, Table)
    }

    output: dict = {"envs": []}
    for section in config:
        if section == "env":
            output["envs"] = config["env"].unwrap()
        elif isinstance(config[section], Table):
            output[section] = config[section].unwrap()

    return output, options


def _split_inline_comment(line: str) -> tuple[str, str]:
    """Split a line into its code part and its trailing comment.

    Quote-aware: a ``#`` inside a quoted string is not a comment. The returned
    comment includes the ``#`` and any whitespace preceding it, so
    ``code + comment == line`` exactly.

    Parameters
    ----------
    line : str
        A single line from a requirements-style file.

    Returns
    -------
    tuple[str, str]
        ``(code, comment)``; ``comment`` is ``""`` when there is no comment.
    """
    in_single = in_double = False
    for index, char in enumerate(line):
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
        elif char == "#" and not in_single and not in_double:
            return line[:index], line[index:]
    return line, ""


def _split_marker(text: str) -> tuple[str, str]:
    """Split requirement text into specifiers and environment marker.

    Quote-aware: a ``;`` inside a quoted string is not a marker separator.

    Parameters
    ----------
    text : str
        Requirement text after the name and extras.

    Returns
    -------
    tuple[str, str]
        ``(specs, marker)`` where ``marker`` starts with ``;`` or is ``""``.
    """
    in_single = in_double = False
    for index, char in enumerate(text):
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
        elif char == ";" and not in_single and not in_double:
            return text[:index], text[index:]
    return text, ""


def _widen_specifier(spec: str, tested: str) -> list[str]:
    """Widen a single specifier so it admits ``tested``, never tighten it.

    A specifier already satisfied by ``tested`` is returned unchanged. Only
    violated bounds are widened, preserving the operator's intent:

    - ``<X`` / ``<=X`` violated -> ``<=tested`` (no synthesized ``!=``)
    - ``==X`` / ``===X`` / ``~=X`` violated -> ``>=X,<=tested``
    - ``>X`` / ``>=X`` violated -> ``>=tested``
    - ``!=`` is a user-authored exclusion and is never modified.

    Parameters
    ----------
    spec : str
        A single specifier, e.g. ``"<2.6"``.
    tested : str
        The version that was tested and passed.

    Returns
    -------
    list[str]
        One or more specifiers replacing ``spec``.
    """
    specifier = Specifier(spec)
    if specifier.contains(tested):
        return [spec]
    operator, version = specifier.operator, specifier.version
    if operator in ("<", "<="):
        return [f"<={tested}"]
    if operator in ("==", "===", "~="):
        return [f">={version}", f"<={tested}"]
    if operator in (">", ">="):
        return [f">={tested}"]
    return [spec]


def _upgrade_requirement_line(line: str, new_version: str) -> str:
    """Rewrite one requirement line, touching only the violated specifier span.

    Preserves the line's leading indentation, the original order and spacing of
    specifiers, extras, the environment marker, and any trailing inline comment.
    If no specifier needs widening the original line is returned byte-identical.

    Parameters
    ----------
    line : str
        A single requirement line (may carry a trailing comment).
    new_version : str
        The version that was tested and passed.

    Returns
    -------
    str
        The rewritten line, or the original line when nothing needs to change.
    """
    code, comment = _split_inline_comment(line)
    leading = code[: len(code) - len(code.lstrip())]
    trailing_ws = code[len(code.rstrip()) :]
    stripped = code.strip()
    if not stripped:
        return line
    requirement = Requirement(stripped)
    if requirement.url is not None:
        # Direct references (pkg @ url) have no specifier span to widen.
        return line
    head_match = re.match(
        r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
        r"(?P<ws>\s*)"
        r"(?P<extras>\[[^\]]*\])?",
        stripped,
    )
    if head_match is None:  # pragma: no cover - Requirement already validated
        return line
    head = head_match.group(0)
    specs_str, marker = _split_marker(stripped[len(head) :])
    if not specs_str.strip():
        return line

    out_parts: list[str] = []
    changed = False
    for element in specs_str.split(","):
        lead_ws = element[: len(element) - len(element.lstrip())]
        trail_ws = element[len(element.rstrip()) :]
        spec = element.strip()
        if not spec:
            out_parts.append(element)
            continue
        new_specs = _widen_specifier(spec, new_version)
        if new_specs != [spec]:
            changed = True
        out_parts.append(lead_ws + ",".join(new_specs) + trail_ws)
    if not changed:
        return line
    return leading + head + ",".join(out_parts) + marker + trailing_ws + comment


def upgrade_requirements(
    fname_or_buf: str, upgraded_packages: list[dict[str, str]]
) -> str:
    """Create an upgraded requirements file.

    Parameters
    ----------
    fname_or_buf : str
        Path to the requirements file to parse using ``packaging.requirements.Requirement``
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
    upgrades = {pkg["name"]: pkg["version"] for pkg in upgraded_packages}

    out_lines: list[str] = []
    for raw_line in cfg.splitlines(keepends=True):
        eol = raw_line[len(raw_line.rstrip("\r\n")) :]
        line = raw_line.rstrip("\r\n")
        code, _ = _split_inline_comment(line)
        stripped = code.strip()
        if stripped.startswith("#") or stripped == "":
            out_lines.append(raw_line)
            continue
        try:
            name = Requirement(stripped).name
        except Exception:
            # Option lines (-r, --hash, ...) and anything unparseable pass through
            out_lines.append(raw_line)
            continue
        # Match case- and dash/underscore-insensitively, like the rest of edgetest
        match = next(
            (pkg for pkg in upgrades if _isin_case_dashhyphen_ins(name, [pkg])),
            None,
        )
        if match is None:
            out_lines.append(raw_line)
            continue
        out_lines.append(_upgrade_requirement_line(line, upgrades[match]) + eol)

    return "".join(out_lines)


def upgrade_pyproject_toml(
    upgraded_packages: list[dict[str, str]], filename: str = "pyproject.toml"
) -> tomlkit.TOMLDocument:
    """Upgrade the ``pyproject.toml`` file.

    Parameters
    ----------
    upgraded_packages : list[dict[str, str]]
        A list of packages upgraded in the testing procedure.
    filename : str, optional (default "pyproject.toml")
        The name of the configuration file to read. Defaults to ``pyproject.toml``.

    Returns
    -------
    TOMLDocument
        The updated TOMLDocument.
    """
    with open(filename) as buf:
        parser: tomlkit.TOMLDocument = tomlkit.load(buf)
    if "project" in parser and parser.get("project").get("dependencies"):  # type: ignore
        LOG.info(f"Updating the requirements in {filename}")
        upgraded = upgrade_requirements(
            fname_or_buf="\n".join(parser["project"]["dependencies"]),  # type: ignore
            upgraded_packages=upgraded_packages,
        )
        parser["project"]["dependencies"] = upgraded.split("\n")  # type: ignore
    # Update the extras, if necessary
    if parser.get("project").get("optional-dependencies"):  # type: ignore
        for extra, dependencies in parser["project"]["optional-dependencies"].items():  # type: ignore
            upgraded = upgrade_requirements(
                fname_or_buf="\n".join(dependencies),
                upgraded_packages=upgraded_packages,
            )
            parser["project"]["optional-dependencies"][extra] = upgraded.split("\n")  # type: ignore

    return parser


def _isin_case_dashhyphen_ins(a: str, vals: list[str]) -> bool:
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
    return any(a.replace("_", "-").lower() == b.replace("_", "-").lower() for b in vals)


def get_lower_bounds(requirements: str | list[str], lower: str | list[str]) -> str:
    r"""Get lower bounds of requested packages from installation requirements.

    Parses through the project ``requirements`` and the newline-delimited
    packages requested in ``lower`` to find the lower bounds.

    Parameters
    ----------
    requirements : str or list
        Project setup requirements,
        e.g. ``"pandas>=1.5.1,<=1.4.2\nnumpy>=1.22.1,<=1.25.4"``
    lower : str | list[str]
        Newline-delimited packages requested,
         e.g. ``"pandas\nnumpy"``.

    Returns
    -------
    str
        The packages along with the lower bound, e.g. ``"pandas==1.5.1\nnumpy==1.22.1"``.
    """
    if isinstance(requirements, str):
        pkgs = [
            Requirement(val)
            for val in requirements.splitlines()
            if not (val.strip().startswith("#") or val.strip() == "")
        ]
    elif isinstance(requirements, list):
        pkgs = [Requirement(val) for val in requirements]
    all_lower_bounds: dict[str, str] = {}
    for pkg in pkgs:
        full_name = pkg.name + (f"[{','.join(pkg.extras)}]" if pkg.extras else "")
        for spec in pkg.specifier:
            if spec.operator == ">=":
                all_lower_bounds[full_name] = spec.version
                break

    lower_with_bounds = ""
    lower_ = lower.split("\n") if isinstance(lower, str) else lower
    for pkg_name, lower_bound in all_lower_bounds.items():
        # TODO: Parse through extra requirements as well to get lower bounds
        if lower_bound is None:
            LOG.warning(
                "Requested %s lower bound, but did not find in install requirements.",
                pkg_name,
            )
        elif _isin_case_dashhyphen_ins(pkg_name, lower_):
            lower_with_bounds += f"{pkg_name}=={lower_bound}\n"

    return lower_with_bounds

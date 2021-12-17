"""Core module."""

import json
import shlex
from pathlib import Path
from subprocess import Popen
from typing import Dict, List, Optional

from pluggy._hooks import _HookRelay

from .logger import get_logger
from .utils import _run_command, pushd

LOG = get_logger(__name__)


class TestPackage:
    """Run test commands with bleeding edge dependencies.

    Parameters
    ----------
    hook : _HookRelay
        The hook object from ``pluggy``.
    envname : str
        The name of the conda environment to create/use.
    upgrade : list
        The list of packages to upgrade
    package_dir : str, optional (default None)
        The location of the local package to install and test.

    Attributes
    ----------
    _basedir : str
        The base directory location for each environment
    status : bool
        A boolean status indicator for whether or not the tests passed. Only populated
        after ``run_tests`` has been executed.
    """

    def __init__(
        self,
        hook: _HookRelay,
        envname: str,
        upgrade: List[str],
        package_dir: Optional[str] = None,
    ):
        """Init method."""
        self.hook = hook
        self._basedir = Path(Path.cwd(), ".edgetest")
        self._basedir.mkdir(exist_ok=True)
        self.envname = envname
        self.upgrade = upgrade
        self.package_dir = package_dir or "."

        self.status: bool = False

    @property
    def python_path(self) -> str:
        """Get the path to the python executable.

        Returns
        -------
        str
            The path to the python executable.
        """
        return self.hook.path_to_python(basedir=self._basedir, envname=self.envname)  # type: ignore

    def setup(
        self,
        extras: Optional[List[str]] = None,
        deps: Optional[List[str]] = None,
        **options,
    ) -> None:
        """Set up the testing environment.

        Parameters
        ----------
        extras : list, optional (default None)
            The list of extra installations to include.
        deps : list, optional (default None)
            A list of additional dependencies to install via ``pip``
        **options
            Additional options for ``self.hook.create_environment``.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            This error will be raised if any part of the set up process fails.
        """
        # Create the conda environment
        LOG.info(f"Creating the following environment: {self.envname}...")
        self.hook.create_environment(
            basedir=self._basedir, envname=self.envname, conf=options
        )
        LOG.info(f"Successfully created {self.envname}")

        # Install the local package
        with pushd(self.package_dir):
            pkg = "."
            if extras:
                pkg += f"[{', '.join(extras)}]"
            if deps:
                LOG.info(
                    f"Installing specified additional dependencies into {self.envname}..."
                )
                split = [shlex.split(dep) for dep in deps]
                _run_command(
                    self.python_path,
                    "-m",
                    "pip",
                    "install",
                    *[itm for lst in split for itm in lst],
                )
            LOG.info(f"Installing the local package into {self.envname}...")
            _run_command(self.python_path, "-m", "pip", "install", pkg)
            LOG.info(f"Successfully installed the local package into {self.envname}...")

        # Upgrade package(s)
        LOG.info(
            f"Upgrading the following packages in {self.envname}: {', '.join(self.upgrade)}"
        )
        _run_command(
            self.python_path,
            "-m",
            "pip",
            "install",
            *self.upgrade,
            "--upgrade",
        )
        LOG.info(f"Successfully upgraded packages in {self.envname}")

    def upgraded_packages(self) -> List[Dict[str, str]]:
        """Get the list of upgraded packages for the test environment.

        Parameters
        ----------
        None

        Returns
        -------
        List
            The output of ``pip list --format json``, filtered to the packages upgraded
            for this environment.
        """
        # Get the version for the upgraded package(s)
        out, _ = _run_command(self.python_path, "-m", "pip", "list", "--format", "json")
        outjson = json.loads(out)

        return [pkg for pkg in outjson if pkg.get("name", "") in self.upgrade]

    def run_tests(self, command: str) -> int:
        """Run the tests in the package directory.

        Parameters
        ----------
        command : str
            The test command

        Returns
        -------
        int
            The exit code
        """
        with pushd(self.package_dir):
            popen = Popen(
                (self.python_path, "-m", *shlex.split(command)), universal_newlines=True
            )
            popen.communicate()

        self.status = bool(popen.returncode == 0)

        return popen.returncode

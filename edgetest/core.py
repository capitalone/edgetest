"""Core module."""

import json
import shlex
from pathlib import Path
from subprocess import Popen
from typing import Dict, List, Optional

from pluggy._hooks import _HookRelay

from edgetest.logger import get_logger
from edgetest.utils import _isin_case_dashhyphen_ins, _run_command, pushd

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
    lower : list
        The list of packages to install lower bounds alongside the lower bound value.
        E.g. ``["pandas==1.5.2"]``.
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

    # Tell pytest this isn't for tests
    __test__ = False

    def __init__(
        self,
        hook: _HookRelay,
        envname: str,
        upgrade: Optional[List[str]] = None,
        lower: Optional[List[str]] = None,
        package_dir: Optional[str] = None,
    ):
        """Init method."""
        self.hook = hook
        self.envname = envname

        if (upgrade is None and lower is None) or (
            upgrade is not None and lower is not None
        ):
            raise ValueError("Exactly one of upgrade and lower must be provided.")
        self.upgrade = upgrade
        self.lower = lower
        self.package_dir = package_dir or "."

        self.setup_status: bool = False
        self.status: bool = False

    @property
    def basedir(self) -> Path:
        """Base directory.

        Returns
        -------
        Path
            Base directory for execution.
        """
        _basedir = Path.cwd() / ".edgetest"
        _basedir.mkdir(exist_ok=True)

        return _basedir

    @property
    def python_path(self) -> str:
        """Get the path to the python executable.

        Returns
        -------
        str
            The path to the python executable.
        """
        return self.hook.path_to_python(basedir=self.basedir, envname=self.envname)  # type: ignore

    def setup(
        self,
        extras: Optional[List[str]] = None,
        deps: Optional[List[str]] = None,
        skip: bool = False,
        **options,
    ) -> None:
        """Set up the testing environment.

        Parameters
        ----------
        extras : list, optional (default None)
            The list of extra installations to include.
        deps : list, optional (default None)
            A list of additional dependencies to install via ``pip``
        skip : bool, optional (default False)
            Whether to skip setup as a pre-made environment has already been
            created.
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
        if skip:
            self.setup_status = True
            return
        # Create the conda environment
        try:
            LOG.info(f"Creating the following environment: {self.envname}...")
            self.hook.create_environment(
                basedir=self.basedir, envname=self.envname, conf=options
            )
            LOG.info(f"Successfully created {self.envname}")
        except RuntimeError:
            LOG.exception(
                "Could not create the following environment: %s", self.envname
            )
            self.setup_status = False
            return

        # Install the local package
        with pushd(self.package_dir):
            pkg = "."
            if extras:
                pkg += f"[{', '.join(extras)}]"
            if deps:
                LOG.info(
                    "Installing specified additional dependencies into %s: %s",
                    self.envname,
                    ", ".join(deps),
                )
                split = [shlex.split(dep) for dep in deps]
                try:
                    _run_command(
                        "uv",
                        "pip",
                        "install",
                        f"--python={self.python_path}",
                        *[itm for lst in split for itm in lst],
                    )
                except RuntimeError:
                    LOG.exception(
                        "Unable to install specified additional dependencies in %s",
                        self.envname,
                    )
                    self.setup_status = False
                    return
                LOG.info(
                    f"Successfully installed specified additional dependencies into {self.envname}"
                )

            LOG.info(f"Installing the local package into {self.envname}...")
            try:
                _run_command(
                    "uv", "pip", "install", f"--python={self.python_path}", pkg
                )
                LOG.info(
                    f"Successfully installed the local package into {self.envname}..."
                )
            except RuntimeError:
                LOG.exception(
                    "Unable to install the local package into %s", self.envname
                )
                self.setup_status = False
                return

        if self.upgrade:
            # Upgrade package(s)
            LOG.info(
                f"Upgrading the following packages in {self.envname}: {', '.join(self.upgrade)}"
            )
            try:
                self.hook.run_update(
                    basedir=self.basedir,
                    envname=self.envname,
                    upgrade=self.upgrade,
                    conf=options,
                )
                self.setup_status = True
            except RuntimeError:
                self.setup_status = False
                LOG.exception("Unable to upgrade packages in %s", self.envname)
                return
            LOG.info("Successfully upgraded packages in %s", self.envname)
        else:
            # Install lower bounds of package(s)
            LOG.info(
                "Installing lower bounds of packages in %s: %s",
                {self.envname},
                ", ".join(self.lower),  # type:ignore
            )
            try:
                self.hook.run_install_lower(
                    basedir=self.basedir,
                    envname=self.envname,
                    lower=self.lower,
                    conf=options,
                )
                self.setup_status = True
            except RuntimeError:
                self.setup_status = False
                LOG.exception(
                    "Unable to install lower bounds of packages in %s", self.envname
                )
                return
            LOG.info(
                f"Successfully installed lower bounds of packages in {self.envname}"
            )

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
        if self.upgrade is None:
            return []
        # Get the version for the upgraded package(s)
        out, _ = _run_command(
            "uv", "pip", "list", f"--python={self.python_path}", "--format", "json"
        )
        outjson = json.loads(out)

        upgrade_wo_extras = [pkg.split("[")[0] for pkg in self.upgrade]
        return [
            pkg
            for pkg in outjson
            if _isin_case_dashhyphen_ins(pkg.get("name", ""), upgrade_wo_extras)
        ]

    def lowered_packages(self) -> List[Dict[str, str]]:
        """Get list of lowered packages for the test environment.

        Returns
        -------
        List[Dict[str, str]]
            List of lowered packages and their versions
        """
        if self.lower is None:
            return []
        packages_split = (pkg_str.split("==") for pkg_str in self.lower)
        return [
            {"name": pkg_info[0], "version": pkg_info[1]} for pkg_info in packages_split
        ]

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
        if not self.setup_status:
            raise RuntimeError("Environment setup failed. Cannot run tests.")
        with pushd(self.package_dir):
            popen = Popen(
                (self.python_path, "-m", *shlex.split(command)), universal_newlines=True
            )
            popen.communicate()

        self.status = bool(popen.returncode == 0)

        return popen.returncode

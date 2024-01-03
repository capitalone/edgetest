"""Set up a fake hook for testing purposes."""

import platform
from pathlib import Path
from typing import Dict, List

import pluggy
import pytest

from edgetest import hookspecs

hookimpl = pluggy.HookimplMarker("edgetest")


class FakeHook:
    """Create a series of fake hooks."""

    @hookimpl
    def path_to_python(self, basedir: str, envname: str) -> str:
        """Return the path to the python executable."""
        # return str(Path(basedir, envname, "bin", "python"))
        if platform.system() == "Windows":
            return str(Path(basedir) / envname / "Scripts" / "python")
        else:
            return str(Path(basedir) / envname / "bin" / "python")

    @hookimpl
    def create_environment(self, basedir: str, envname: str, conf: Dict):
        """Create the virtual environment for testing."""
        pass

    @hookimpl
    def run_update(self, basedir: str, envname: str, upgrade: List):
        """Update packages from upgrade list."""
        pass

    @hookimpl
    def run_install_lower(basedir: str, envname: str, lower: Dict[str, str]):
        """Install lower bounds of packages from lower list."""
        pass


class FakeHookEnvironmentError:
    """Create a series of fake hooks that raise errors."""

    @hookimpl
    def path_to_python(self, basedir: str, envname: str) -> str:
        """Return the path to the python executable."""
        # return str(Path(basedir, envname, "bin", "python"))
        if platform.system() == "Windows":
            return str(Path(basedir) / envname / "Scripts" / "python")
        else:
            return str(Path(basedir) / envname / "bin" / "python")

    @hookimpl
    def create_environment(self, basedir: str, envname: str, conf: Dict):
        """Create the virtual environment for testing."""
        raise RuntimeError("Could not create virtual environment.")

    @hookimpl
    def run_update(self, basedir: str, envname: str, upgrade: List):
        """Update packages from upgrade list."""
        pass

    @hookimpl
    def run_install_lower(basedir: str, envname: str, lower: Dict[str, str]):
        """Install lower bounds of packages from lower list."""
        pass


class FakeHookUpdateError:
    """Create a series of fake hooks that raise errors."""

    @hookimpl
    def path_to_python(self, basedir: str, envname: str) -> str:
        """Return the path to the python executable."""
        # return str(Path(basedir, envname, "bin", "python"))
        if platform.system() == "Windows":
            return str(Path(basedir) / envname / "Scripts" / "python")
        else:
            return str(Path(basedir) / envname / "bin" / "python")

    @hookimpl
    def create_environment(self, basedir: str, envname: str, conf: Dict):
        """Create the virtual environment for testing."""
        pass

    @hookimpl
    def run_update(self, basedir: str, envname: str, upgrade: List):
        """Update packages from upgrade list."""
        raise RuntimeError("Could not update packages.")

    @hookimpl
    def run_install_lower(basedir: str, envname: str, lower: Dict[str, str]):
        """Install lower bounds of packages from lower list."""
        pass


class FakeHookLowerError:
    """Create a series of fake hooks that raise errors."""

    @hookimpl
    def path_to_python(self, basedir: str, envname: str) -> str:
        """Return the path to the python executable."""
        # return str(Path(basedir, envname, "bin", "python"))
        if platform.system() == "Windows":
            return str(Path(basedir) / envname / "Scripts" / "python")
        else:
            return str(Path(basedir) / envname / "bin" / "python")

    @hookimpl
    def create_environment(self, basedir: str, envname: str, conf: Dict):
        """Create the virtual environment for testing."""
        pass

    @hookimpl
    def run_update(self, basedir: str, envname: str, upgrade: List):
        """Update packages from upgrade list."""
        pass

    @hookimpl
    def run_install_lower(basedir: str, envname: str, lower: Dict[str, str]):
        """Install lower bounds of packages from lower list."""
        raise RuntimeError("Could not install lower bounds of packages.")



@pytest.fixture
def plugin_manager():
    """The plugin manager for our fake hook."""
    pm = pluggy.PluginManager("edgetest")
    pm.add_hookspecs(hookspecs)
    pm.register(FakeHook())

    return pm

@pytest.fixture
def plugin_manager_environment_error():
    """The plugin manager for our fake hook that raises errors."""
    pm = pluggy.PluginManager("edgetest")
    pm.add_hookspecs(hookspecs)
    pm.register(FakeHookEnvironmentError())

    return pm

@pytest.fixture
def plugin_manager_upgrade_error():
    """The plugin manager for our fake hook that raises errors."""
    pm = pluggy.PluginManager("edgetest")
    pm.add_hookspecs(hookspecs)
    pm.register(FakeHookUpdateError())

    return pm

@pytest.fixture
def plugin_manager_lower_error():
    """The plugin manager for our fake hook that raises errors."""
    pm = pluggy.PluginManager("edgetest")
    pm.add_hookspecs(hookspecs)
    pm.register(FakeHookLowerError())

    return pm
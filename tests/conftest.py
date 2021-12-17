"""Set up a fake hook for testing purposes."""

import platform
from pathlib import Path
from typing import Dict

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


@pytest.fixture
def plugin_manager():
    """The plugin manager for our fake hook."""
    pm = pluggy.PluginManager("edgetest")
    pm.add_hookspecs(hookspecs)
    pm.register(FakeHook())

    return pm

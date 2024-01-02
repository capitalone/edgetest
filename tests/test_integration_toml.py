"""Create a fake package and test."""
import configparser
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from tomlkit import load

from edgetest.interface import cli

SETUP_TOML = """
[project]
name = "toy_package"
version = "0.1.0"
description = "Fake description"
requires-python = ">=3.7.0"
dependencies = ["pandas<=1.2.0"]

[project.optional-dependencies]
tests = ["pytest"]

[edgetest]
extras = ["tests"]
"""

SETUP_TOML_LOWER = """
[project]
name = "toy_package"
version = "0.1.0"
description = "Fake description"
requires-python = ">=3.7.0"
dependencies = ["pandas<=1.2.0,>=1.0.0"]

[project.optional-dependencies]
tests = ["pytest"]

[edgetest]
extras = ["tests"]

[edgetest.envs.lower_env]
lower = ["pandas"]
"""

SETUP_TOML_DASK = """
[project]
name = "toy_package"
version = "0.1.0"
description = "Fake description"
requires-python = ">=3.7.0"
dependencies = ["Scikit_Learn>=1.0,<=1.2.0", "Dask[dataframe]<=2022.1.0,>=2021.6.1"]

[project.optional-dependencies]
tests = ["pytest"]

[edgetest.envs.core]
extras = ["tests"]
upgrade = ["scikit-learn", "dask[dataframe]"]

[edgetest.envs.lower_env]
extras = ["tests"]
lower = ["scikit-learn", "dask[dataframe]"]
"""


SETUP_PY = """
from setuptools import setup

setup()
"""

MODULE_CODE = """
def main() -> str:
    print("Hello world")
"""

TEST_CODE = """
from toy_package import main

def test_func():
    main()
"""

PY_VER = f"python{sys.version_info.major}.{sys.version_info.minor}"


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
@pytest.mark.integration
def test_toy_package():
    """Test using edgetest with a toy package."""
    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML)
        with open("setup.py", "w") as outfile:
            outfile.write(SETUP_PY)
        # Make a directory for the module
        Path(loc, "toy_package").mkdir()
        with open(Path(loc, "toy_package", "__init__.py"), "w") as outfile:
            outfile.write(MODULE_CODE)
        # Make a directory for the tests
        Path(loc, "tests").mkdir()
        with open(Path(loc, "tests", "test_main.py"), "w") as outfile:
            outfile.write(TEST_CODE)

        # Run the CLI
        result = runner.invoke(cli, ["--config=pyproject.toml"])

        assert result.exit_code == 0
        assert Path(loc, ".edgetest").is_dir()
        assert Path(loc, ".edgetest", "pandas").is_dir()
        assert "pandas" in result.stdout

        if not sys.platform == "win32":
            assert Path(
                loc, ".edgetest", "pandas", "lib", PY_VER, "site-packages", "pandas"
            ).is_dir()


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
@pytest.mark.integration
def test_toy_package_lower():
    """Test using edgetest with a toy package."""
    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML_LOWER)
        with open("setup.py", "w") as outfile:
            outfile.write(SETUP_PY)
        # Make a directory for the module
        Path(loc, "toy_package").mkdir()
        with open(Path(loc, "toy_package", "__init__.py"), "w") as outfile:
            outfile.write(MODULE_CODE)
        # Make a directory for the tests
        Path(loc, "tests").mkdir()
        with open(Path(loc, "tests", "test_main.py"), "w") as outfile:
            outfile.write(TEST_CODE)

        # Run the CLI
        result = runner.invoke(cli, ["--config=pyproject.toml"])

        assert result.exit_code == 0
        assert Path(loc, ".edgetest").is_dir()
        assert Path(loc, ".edgetest", "lower_env").is_dir()
        assert "pandas" in result.stdout

        if not sys.platform == "win32":
            assert Path(
                loc, ".edgetest", "lower_env", "lib", PY_VER, "site-packages", "pandas"
            ).is_dir()


@pytest.mark.integration
def test_toy_package_dask():
    """Test using edgetest with a toy package."""
    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML_DASK)
        with open("setup.py", "w") as outfile:
            outfile.write(SETUP_PY)
        # Make a directory for the module
        Path(loc, "toy_package").mkdir()
        with open(Path(loc, "toy_package", "__init__.py"), "w") as outfile:
            outfile.write(MODULE_CODE)
        # Make a directory for the tests
        Path(loc, "tests").mkdir()
        with open(Path(loc, "tests", "test_main.py"), "w") as outfile:
            outfile.write(TEST_CODE)

        # Run the CLI
        result = runner.invoke(cli, ["--config=pyproject.toml", "--export"])

        assert result.exit_code == 0
        assert Path(loc, ".edgetest").is_dir()

        for envname in ("core", "lower_env"):
            assert Path(loc, ".edgetest", envname).is_dir()

            if not sys.platform == "win32":
                assert Path(
                    loc, ".edgetest", envname, "lib", PY_VER, "site-packages", "dask"
                ).is_dir()
                assert Path(
                    loc, ".edgetest", envname, "lib", PY_VER, "site-packages", "pandas"
                ).is_dir()
                assert Path(
                    loc, ".edgetest", envname, "lib", PY_VER, "site-packages", "sklearn"
                ).is_dir()

        config = load(open("pyproject.toml"))

        assert "Scikit_Learn" in config["project"]["dependencies"][0]
        assert "Dask" in config["project"]["dependencies"][1]
        assert config["edgetest"]["envs"]["core"]["extras"] == ["tests"]
        assert config["edgetest"]["envs"]["core"]["upgrade"] == [
            "scikit-learn",
            "dask[dataframe]",
        ]
        assert config["edgetest"]["envs"]["lower_env"]["extras"] == ["tests"]
        assert config["edgetest"]["envs"]["lower_env"]["lower"] == [
            "scikit-learn",
            "dask[dataframe]",
        ]
        assert "dask" in result.stdout
        assert "scikit-learn" in result.stdout

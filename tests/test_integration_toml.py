"""Create a fake package and test."""

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
dependencies = ["polars<=1.0.0"]

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
dependencies = ["polars>=1.0.0,<=1.5.0"]

[project.optional-dependencies]
tests = ["pytest"]

[edgetest]
extras = ["tests"]

[edgetest.envs.lower_env]
lower = ["polars"]
"""

SETUP_TOML_EXTRAS = """
[project]
name = "toy_package"
version = "0.1.0"
description = "Fake description"
requires-python = ">=3.7.0"
dependencies = ["Scikit_Learn>=1.3.2,<=1.4.0", "Polars[pyarrow]>=1.0.0,<=1.5.0"]

[project.optional-dependencies]
tests = ["pytest"]

[edgetest.envs.core]
extras = ["tests"]
upgrade = ["scikit-learn", "polars[pyarrow]"]

[edgetest.envs.lower_env]
extras = ["tests"]
lower = ["scikit-learn", "polars[pyarrow]"]
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
        assert Path(loc, ".edgetest", "polars").is_dir()
        assert "polars" in result.stdout

        if sys.platform != "win32":
            assert Path(
                loc, ".edgetest", "polars", "lib", PY_VER, "site-packages", "polars"
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
        assert "polars" in result.stdout

        if sys.platform != "win32":
            assert Path(
                loc, ".edgetest", "lower_env", "lib", PY_VER, "site-packages", "polars"
            ).is_dir()


@pytest.mark.integration
def test_toy_package_extras():
    """Test using edgetest with a toy package."""
    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("pyproject.toml", "w") as outfile:
            outfile.write(SETUP_TOML_EXTRAS)
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

            if sys.platform != "win32":
                assert Path(
                    loc, ".edgetest", envname, "lib", PY_VER, "site-packages", "polars"
                ).is_dir()
                assert Path(
                    loc, ".edgetest", envname, "lib", PY_VER, "site-packages", "pyarrow"
                ).is_dir()
                assert Path(
                    loc, ".edgetest", envname, "lib", PY_VER, "site-packages", "sklearn"
                ).is_dir()

        with open("pyproject.toml") as buf:
            config = load(buf)

        assert "Scikit_Learn" in config["project"]["dependencies"][0]
        assert "Polars[pyarrow]" in config["project"]["dependencies"][1]
        assert config["edgetest"]["envs"]["core"]["extras"] == ["tests"]
        assert config["edgetest"]["envs"]["core"]["upgrade"] == [
            "scikit-learn",
            "polars[pyarrow]",
        ]
        assert config["edgetest"]["envs"]["lower_env"]["extras"] == ["tests"]
        assert config["edgetest"]["envs"]["lower_env"]["lower"] == [
            "scikit-learn",
            "polars[pyarrow]",
        ]
        assert "polars" in result.stdout
        assert "scikit-learn" in result.stdout

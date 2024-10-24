"""Create a fake package and test."""

import configparser
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from edgetest.interface import cli

SETUP_CFG = """
[metadata]
name = toy_package
version = 0.1.0
description = Fake description
python_requires =
    >=3.7.0

[options]
zip_safe = False
include_package_data = True
packages = find:
install_requires =
    polars<=1.0.0

[options.extras_require]
tests =
    pytest

[edgetest]
extras =
    tests
"""

SETUP_CFG_LOWER = """
[metadata]
name = toy_package
version = 0.1.0
description = Fake description
python_requires =
    >=3.7.0

[options]
zip_safe = False
include_package_data = True
packages = find:
install_requires =
    polars>=1.0.0,<=1.5.0

[options.extras_require]
tests =
    pytest

[edgetest]
extras =
    tests

[edgetest.envs.lower_env]
lower =
    polars
"""


SETUP_CFG_EXTRAS = """
[metadata]
name = toy_package
version = 0.1.0
description = Fake description
python_requires =
    >=3.7.0

[options]
zip_safe = False
include_package_data = True
packages = find:
install_requires =
    scikit-learn>=1.3.2,<=1.4.0
    polars[pyarrow]>=1.0.0,<=1.5.0

[options.extras_require]
tests =
    pytest

[edgetest.envs.core]
extras =
    tests
upgrade =
    Scikit_Learn
    Polars[PyArrow]

[edgetest.envs.lower_env]
extras =
    tests
lower =
    scikit_Learn
    Polars[pyArrow]
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
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG)
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
        result = runner.invoke(cli, ["--config=setup.cfg"])

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
    """Test lower bounds with a toy package."""
    runner = CliRunner()

    with runner.isolated_filesystem() as loc:
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG_LOWER)
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
        result = runner.invoke(cli, ["--config=setup.cfg"])

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
        with open("setup.cfg", "w") as outfile:
            outfile.write(SETUP_CFG_EXTRAS)
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
        result = runner.invoke(cli, ["--config=setup.cfg", "--export"])

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

        config = configparser.ConfigParser()
        config.read("setup.cfg")

        assert "scikit-learn" in config["options"]["install_requires"]
        assert "polars[pyarrow]" in config["options"]["install_requires"]
        assert config["edgetest.envs.core"]["extras"] == "\ntests"
        assert (
            config["edgetest.envs.core"]["upgrade"] == "\nScikit_Learn\nPolars[PyArrow]"
        )
        assert config["edgetest.envs.lower_env"]["extras"] == "\ntests"
        assert (
            config["edgetest.envs.lower_env"]["lower"]
            == "\nscikit_Learn\nPolars[pyArrow]"
        )
        assert "polars" in result.stdout
        assert "scikit-learn" in result.stdout

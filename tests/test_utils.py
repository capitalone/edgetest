"""Test utility functions."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from edgetest.schema import BASE_SCHEMA, EdgetestValidator, Schema
from edgetest.utils import (
    _isin_case_dashhyphen_ins,
    gen_requirements_config,
    get_lower_bounds,
    parse_toml,
    upgrade_pyproject_toml,
)

REQS = """
mydep1>=0.1.0,<=0.2.0
mydep2<=0.10.0
"""


TOML_NOREQS = """
[edgetest.envs.myenv]
upgrade = [
    "myupgrade"
]
command = "pytest tests -m 'not integration'"

[edgetest.envs.myenv_lower]
lower = ["mylower"]
command = "pytest tests -m 'not integration'"
"""


TOML_NOREQS_TOOL = """
[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]
command = "pytest tests -m 'not integration'"

[[tool.edgetest.env]]
name = "myenv_lower"
lower = [ "mylower" ]
command = "pytest tests -m 'not integration'"
"""


TOML_REQS = """
[project]
dependencies = [
    "myupgrade"
]
"""

TOML_REQS_DEFAULTS = """
[project]
dependencies = [
    "myupgrade"
]
[edgetest]
extras = ["tests"]
command = "pytest tests -m 'not integration'"
"""


TOML_REQS_DEFAULTS_TOOL = """
[project]
dependencies = [ "myupgrade" ]

[tool.edgetest]
extras = [ "tests" ]
command = "pytest tests -m 'not integration'"
"""


TOML_REQS_COOLDOWN = """
[project]
dependencies = [
    "myupgrade"
]

[edgetest]
extras = ["tests"]
command = "pytest tests -m 'not integration'"
exclude_newer = "3 days"
"""


TOML_REQS_COOLDOWN_TOOL = """
[project]
dependencies = [ "myupgrade" ]

[tool.edgetest]
extras = [ "tests" ]
command = "pytest tests -m 'not integration'"
exclude_newer = "3 days"
"""


TOML_NOREQS_DEFAULTS = """
[edgetest]
extras = ["tests"]
command = "pytest tests -m 'not integration'"

[edgetest.envs.myenv]
upgrade = ["myupgrade"]
command = "pytest tests"

[edgetest.envs.myenv_lower]
lower = ["mylower"]
command = "pytest tests"
"""

TOML_NOREQS_DEFAULTS_TOOL = """
[tool.edgetest]
extras = [ "tests" ]
command = "pytest tests -m 'not integration'"

[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]
command = "pytest tests"

[[tool.edgetest.env]]
name = "myenv_lower"
lower = [ "mylower" ]
command = "pytest tests"
"""


TOML_CUSTOM = """
[edgetest]
extras = ["tests"]
command = "pytest tests -m 'not integration'"

[edgetest.custom]
mycustom = "mykey"

[edgetest.envs.myenv]
upgrade = ["myupgrade"]

[edgetest.envs.myenv_lower]
lower = ["mylower"]
"""


TOML_CUSTOM_TOOL = """
[tool.edgetest]
extras = [ "tests" ]
command = "pytest tests -m 'not integration'"

[tool.edgetest.custom]
mycustom = "mykey"

[[tool.edgetest.env]]
name = "myenv"
upgrade = [ "myupgrade" ]

[[tool.edgetest.env]]
name = "myenv_lower"
lower = [ "mylower" ]
"""


TOML_REQS_UPGRADE = """
[project]
dependencies = [
    "pandas<=1.0.0,>=1.0.0",
    "numpy<=1.0.0,>=1.0.0",
]
[project.optional-dependencies]
tests = [
    "pytest<=1.0.0,>=1.0.0",
]
"""

REQS_NORMAL = """
pandas>=1.0.0,<=2.0
numpy<=0.24,>=0.01
"""


def test_get_lower_bounds():
    """Test getting lower bound from reqs."""
    assert (
        get_lower_bounds(REQS_NORMAL, "pandas\nnumpy\n")
        == "pandas==1.0.0\nnumpy==0.01\n"
    )
    assert get_lower_bounds(REQS_NORMAL, "pandas") == "pandas==1.0.0\n"
    assert get_lower_bounds(REQS_NORMAL, "") == ""
    assert get_lower_bounds(REQS, "mydep2") == ""


@patch("edgetest.utils.Path")
def test_parse_reqs(mock_pathlib):
    """Test creating a configuration from requirements."""
    mock_pathlib.return_value.is_file.return_value = True
    with patch("edgetest.utils.open", mock_open(read_data=REQS)):
        cfg = gen_requirements_config("filename")

    assert cfg == {
        "envs": [
            {"name": "mydep1", "upgrade": "mydep1"},
            {"name": "mydep2", "upgrade": "mydep2"},
            {"name": "all-requirements", "upgrade": "mydep1\nmydep2"},
        ]
    }
    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(cfg)


@pytest.mark.parametrize("toml_source", [TOML_NOREQS, TOML_NOREQS_TOOL])
def test_parse_toml(tmpdir, toml_source):
    """Test parsing a config with no install requirements."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "myconfig.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(toml_source)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {
                "name": "myenv",
                "upgrade": ["myupgrade"],
                "command": "pytest tests -m 'not integration'",
            },
            {
                "name": "myenv_lower",
                "lower": ["mylower"],
                "command": "pytest tests -m 'not integration'",
            },
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(toml)


@pytest.mark.parametrize(
    "toml_source", [TOML_NOREQS_DEFAULTS, TOML_NOREQS_DEFAULTS_TOOL]
)
def test_parse_toml_default(tmpdir, toml_source):
    """Test parsing a config with no install requirements and defaults."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "myconfig.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(toml_source)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {
                "name": "myenv",
                "upgrade": ["myupgrade"],
                "extras": ["tests"],
                "command": "pytest tests",
            },
            {
                "name": "myenv_lower",
                "lower": ["mylower"],
                "extras": ["tests"],
                "command": "pytest tests",
            },
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(toml)


def test_parse_toml_reqs(tmpdir):
    """Test parsing a TOML style config."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "pyproject.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(TOML_REQS)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {"name": "myupgrade", "upgrade": "myupgrade"},
            {"name": "all-requirements", "upgrade": "myupgrade"},
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(toml)


@pytest.mark.parametrize("toml_source", [TOML_REQS_DEFAULTS, TOML_REQS_DEFAULTS_TOOL])
def test_parse_toml_reqs_default(tmpdir, toml_source):
    """Test parsing a TOML style config with default arguments."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "pyproject.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(toml_source)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {
                "name": "myupgrade",
                "upgrade": "myupgrade",
                "extras": ["tests"],
                "command": "pytest tests -m 'not integration'",
            },
            {
                "name": "all-requirements",
                "upgrade": "myupgrade",
                "extras": ["tests"],
                "command": "pytest tests -m 'not integration'",
            },
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(toml)


@pytest.mark.parametrize("toml_source", [TOML_REQS_COOLDOWN, TOML_REQS_COOLDOWN_TOOL])
def test_parse_toml_cooldown(tmpdir, toml_source):
    """Test parsing a config with a dependency cooldown."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "myconfig.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(toml_source)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {
                "name": "myupgrade",
                "upgrade": "myupgrade",
                "extras": ["tests"],
                "command": "pytest tests -m 'not integration'",
                "exclude_newer": "3 days",
            },
            {
                "name": "all-requirements",
                "upgrade": "myupgrade",
                "extras": ["tests"],
                "command": "pytest tests -m 'not integration'",
                "exclude_newer": "3 days",
            },
        ]
    }


@pytest.mark.parametrize("toml_source", [TOML_CUSTOM, TOML_CUSTOM_TOOL])
def test_parse_custom_toml(tmpdir, toml_source):
    """Test parsing a custom configuration."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "pyproject.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(toml_source)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "custom": {"mycustom": "mykey"},
        "envs": [
            {
                "name": "myenv",
                "upgrade": ["myupgrade"],
                "extras": ["tests"],
                "command": "pytest tests -m 'not integration'",
            },
            {
                "name": "myenv_lower",
                "lower": ["mylower"],
                "extras": ["tests"],
                "command": "pytest tests -m 'not integration'",
            },
        ],
    }

    schema = Schema()
    schema.add_globaloption(
        "custom", {"type": "dict", "schema": {"mycustom": {"type": "string"}}}
    )

    validator = EdgetestValidator(schema=schema.schema)

    assert validator.validate(toml)


def test_upgrade_pyproject_toml(tmpdir):
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "pyproject.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(TOML_REQS_UPGRADE)

    assert upgrade_pyproject_toml(
        upgraded_packages=[
            {"name": "pandas", "version": "2.0.0"},
            {"name": "numpy", "version": "3.0.0"},
            {"name": "pytest", "version": "4.0.0"},
        ],
        filename=conf_loc,
    ) == {
        "project": {
            "dependencies": ["pandas<=2.0.0,>=1.0.0", "numpy<=3.0.0,>=1.0.0"],
            "optional-dependencies": {"tests": ["pytest<=4.0.0,>=1.0.0"]},
        }
    }


def test_isin_case_dashhyphen_ins():
    vals = ["pandas", "python-dateutil"]

    assert _isin_case_dashhyphen_ins("pandas", vals)
    assert _isin_case_dashhyphen_ins("Pandas", vals)
    assert not _isin_case_dashhyphen_ins("Panda$", vals)
    assert _isin_case_dashhyphen_ins("python-dateutil", vals)
    assert _isin_case_dashhyphen_ins("Python_Dateutil", vals)
    assert not _isin_case_dashhyphen_ins("Python_Dateut1l", vals)
    assert not _isin_case_dashhyphen_ins("pandaspython-dateutil", vals)

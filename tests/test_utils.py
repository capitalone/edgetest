"""Test utility functions."""

from pathlib import Path
from unittest.mock import mock_open, patch

from edgetest.schema import BASE_SCHEMA, EdgetestValidator, Schema
from edgetest.utils import gen_requirements_config, parse_cfg, parse_toml

REQS = """
mydep1>=0.1.0,<=0.2.0
mydep2<=0.10.0
"""

CFG_NOREQS = """
[edgetest.envs.myenv]
upgrade =
    myupgrade
command =
    pytest tests -m 'not integration'
"""

CFG_REQS = """
[options]
install_requires =
    myupgrade
"""

CFG_REQS_DEFAULTS = """
[options]
install_requires =
    myupgrade

[edgetest]
extras =
    tests
command =
    pytest tests -m 'not integration'
"""

CFG_NOREQS_DEFAULTS = """
[edgetest]
extras =
    tests
command =
    pytest tests -m 'not integration'

[edgetest.envs.myenv]
upgrade =
    myupgrade
command =
    pytest tests
"""

CFG_CUSTOM = """
[edgetest]
extras =
    tests
command =
    pytest tests -m 'not integration'

[edgetest.custom]
mycustom = mykey

[edgetest.envs.myenv]
upgrade =
    myupgrade
"""


TOML_NOREQS = """
[edgetest.envs.myenv]
upgrade = [
    "myupgrade"
]
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

TOML_NOREQS_DEFAULTS = """
[edgetest]
extras = ["tests"]
command = "pytest tests -m 'not integration'"

[edgetest.envs.myenv]
upgrade = ["myupgrade"]
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
"""


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


def test_parse_cfg(tmpdir):
    """Test parsing a config with no install requirements."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "myconfig.ini")
    with open(conf_loc, "w") as outfile:
        outfile.write(CFG_NOREQS)

    cfg = parse_cfg(filename=conf_loc)

    assert cfg == {
        "envs": [
            {
                "name": "myenv",
                "upgrade": "\nmyupgrade",
                "command": "\npytest tests -m 'not integration'",
            }
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(cfg)


def test_parse_cfg_default(tmpdir):
    """Test parsing a config with no install requirements and defaults."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "myconfig.ini")
    with open(conf_loc, "w") as outfile:
        outfile.write(CFG_NOREQS_DEFAULTS)

    cfg = parse_cfg(filename=conf_loc)

    assert cfg == {
        "envs": [
            {
                "name": "myenv",
                "upgrade": "\nmyupgrade",
                "extras": "\ntests",
                "command": "\npytest tests",
            }
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(cfg)


def test_parse_cfg_reqs(tmpdir):
    """Test parsing a PEP-517 style config."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "setup.cfg")
    with open(conf_loc, "w") as outfile:
        outfile.write(CFG_REQS)

    cfg = parse_cfg(filename=conf_loc)

    assert cfg == {
        "envs": [
            {"name": "myupgrade", "upgrade": "myupgrade"},
            {"name": "all-requirements", "upgrade": "myupgrade"},
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(cfg)


def test_parse_cfg_reqs_default(tmpdir):
    """Test parsing a PEP-517 style config with default arguments."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "setup.cfg")
    with open(conf_loc, "w") as outfile:
        outfile.write(CFG_REQS_DEFAULTS)

    cfg = parse_cfg(filename=conf_loc)

    assert cfg == {
        "envs": [
            {
                "name": "myupgrade",
                "upgrade": "myupgrade",
                "extras": "\ntests",
                "command": "\npytest tests -m 'not integration'",
            },
            {
                "name": "all-requirements",
                "upgrade": "myupgrade",
                "extras": "\ntests",
                "command": "\npytest tests -m 'not integration'",
            },
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(cfg)


def test_parse_custom_cfg(tmpdir):
    """Test parsing a custom configuration."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "setup.cfg")
    with open(conf_loc, "w") as outfile:
        outfile.write(CFG_CUSTOM)

    cfg = parse_cfg(filename=conf_loc)

    assert cfg == {
        "custom": {"mycustom": "mykey"},
        "envs": [
            {
                "name": "myenv",
                "upgrade": "\nmyupgrade",
                "extras": "\ntests",
                "command": "\npytest tests -m 'not integration'",
            }
        ],
    }

    schema = Schema()
    schema.add_globaloption(
        "custom", {"type": "dict", "schema": {"mycustom": {"type": "string"}}}
    )

    validator = EdgetestValidator(schema=schema.schema)

    assert validator.validate(cfg)


def test_parse_toml(tmpdir):
    """Test parsing a config with no install requirements."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "myconfig.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(TOML_NOREQS)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {
                "name": "myenv",
                "upgrade": "myupgrade",
                "command": "pytest tests -m 'not integration'",
            }
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(toml)


def test_parse_toml_default(tmpdir):
    """Test parsing a config with no install requirements and defaults."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "myconfig.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(TOML_NOREQS_DEFAULTS)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {
                "name": "myenv",
                "upgrade": "myupgrade",
                "extras": "tests",
                "command": "pytest tests",
            }
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


def test_parse_toml_reqs_default(tmpdir):
    """Test parsing a TOML style config with default arguments."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "pyproject.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(TOML_REQS_DEFAULTS)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "envs": [
            {
                "name": "myupgrade",
                "upgrade": "myupgrade",
                "extras": "tests",
                "command": "pytest tests -m 'not integration'",
            },
            {
                "name": "all-requirements",
                "upgrade": "myupgrade",
                "extras": "tests",
                "command": "pytest tests -m 'not integration'",
            },
        ]
    }

    validator = EdgetestValidator(schema=BASE_SCHEMA)

    assert validator.validate(toml)


def test_parse_custom_toml(tmpdir):
    """Test parsing a custom configuration."""
    location = tmpdir.mkdir("mylocation")
    conf_loc = Path(str(location), "pyproject.toml")
    with open(conf_loc, "w") as outfile:
        outfile.write(TOML_CUSTOM)

    toml = parse_toml(filename=conf_loc)

    assert toml == {
        "custom": {"mycustom": "mykey"},
        "envs": [
            {
                "name": "myenv",
                "upgrade": "myupgrade",
                "extras": "tests",
                "command": "pytest tests -m 'not integration'",
            }
        ],
    }

    schema = Schema()
    schema.add_globaloption(
        "custom", {"type": "dict", "schema": {"mycustom": {"type": "string"}}}
    )

    validator = EdgetestValidator(schema=schema.schema)

    assert validator.validate(toml)

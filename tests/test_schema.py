"""Test modifying and adjusting the schema."""

from edgetest.schema import EdgetestValidator, Schema


def test_add_envoption():
    """Test adding an environment option."""
    schema = Schema()
    schema.add_envoption(
        "mylist", {"type": "list", "schema": {"schema": {"type": "string"}}}
    )

    conf = {"envs": [{"name": "myenv", "upgrade": "\nmypackage", "mylist": ["heyo"]}]}

    validator = EdgetestValidator(schema=schema.schema)

    assert validator.validate(conf)

    conf = {
        "envs": [{"name": "myenv", "upgrade": "\nmypackage", "mylist": "not a list"}]
    }

    assert not validator.validate(conf)


def test_add_global_option():
    """Test adding a global option to the schema."""
    schema = Schema()
    schema.add_globaloption("title", {"type": "string"})

    conf = {"title": "My title", "envs": [{"name": "myenv", "upgrade": "\nmyupgrade"}]}

    validator = EdgetestValidator(schema=schema.schema)

    assert validator.validate(conf)

    conf = {"title": 3, "envs": [{"name": "myenv", "upgrade": "\nmyupgrade"}]}

    assert not validator.validate(conf)

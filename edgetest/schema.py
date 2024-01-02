"""Define the Cerberus schema for the testing configuration."""

from typing import Dict, List

from cerberus import Validator

BASE_SCHEMA = {
    "envs": {
        "type": "list",
        "required": True,
        "schema": {
            "type": "dict",
            "schema": {
                "name": {"type": "string", "coerce": "strip", "required": True},
                "upgrade": {
                    "type": "list",
                    "schema": {
                        "type": "string",
                    },
                    "coerce": "listify",
                    "required": True,
                    "excludes": "lower",
                },
                "lower": {
                    "type": "list",
                    "schema": {"type": "string"},
                    "coerce": "listify",
                    "required": True,
                    "excludes": "upgrade",
                },
                "extras": {
                    "type": "list",
                    "schema": {"type": "string"},
                    "coerce": "listify",
                    "default": None,
                    "nullable": True,
                },
                "deps": {
                    "type": "list",
                    "schema": {"type": "string"},
                    "coerce": "listify",
                    "default": None,
                    "nullable": True,
                },
                "command": {"type": "string", "coerce": "strip", "default": "pytest"},
                "package_dir": {"type": "string", "coerce": "strip", "default": "."},
            },
        },
    }
}


class Schema:
    """An editable schema."""

    schema = BASE_SCHEMA

    def add_envoption(self, option: str, schema: Dict):
        """Add an environment-level option.

        Parameters
        ----------
        option : str
            The name of the option. This will be the key in the key-value pair.
        schema : dict
            The schema for the option.

        Examples
        --------
        >>> Schema().add_envoption("command", {"type": "string", "default": "pytest"})
        """
        self.schema["envs"]["schema"]["schema"][option] = schema  # type: ignore

    def add_globaloption(self, option: str, schema: Dict):
        """Add a global option.

        Parameters
        ----------
        option : str
            The name of the option. This will be the key in the key-value pair.
        schema : dict
            The schema for the option.

        Examples
        --------
        >>> Schema().add_globaloption("print_message", {"type": "string"})
        """
        self.schema[option] = schema


class EdgetestValidator(Validator):
    """Custom validator for coercing lists from ``.ini`` style files."""

    def _normalize_coerce_listify(self, value: str) -> List:
        """Coerce a value into a list.

        Parameters
        ----------
        value : str
            The original value for the field.

        Returns
        -------
        list
            The newline-separated list.
        """
        if isinstance(value, str):
            return value.strip().splitlines()
        else:
            return value

    def _normalize_coerce_strip(self, value: str) -> str:
        """Remove leading and trailing spaces.

        Parameters
        ----------
        value : str
            The original value for the field.

        Returns
        -------
        str
            The stripped string.
        """
        return value.strip()

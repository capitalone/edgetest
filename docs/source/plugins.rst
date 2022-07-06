Extending edgetest through plugins
==================================

``edgetest`` uses `pluggy <https://pluggy.readthedocs.io/en/latest/>`_ to implement a simple plugin
framework that allows for additional functionality. We expose the following hooks:

+---------------------------------------------------------+----------------------------------------------+
| Hook                                                    | Description                                  |
|                                                         |                                              |
+=========================================================+==============================================+
| :py:meth:`edgetest.hookspecs.addoption`                 | | This hook allows the user to add global or |
|                                                         | | environment-level hooks to the             |
|                                                         | | configuration schema.                      |
+---------------------------------------------------------+----------------------------------------------+
| :py:meth:`edgetest.hookspecs.pre_run_hook`              | | This hook allows the user to execute any   |
|                                                         | | necessary set up code before creating the  |
|                                                         | | virtual environment(s).                    |
+---------------------------------------------------------+----------------------------------------------+
| :py:meth:`edgetest.hookspecs.path_to_python` [#f1]_     | | This hook returns the path to the python   |
|                                                         | | executable.                                |
+---------------------------------------------------------+----------------------------------------------+
| :py:meth:`edgetest.hookspecs.create_environment` [#f1]_ | This hook creates the virtual environment.   |
+---------------------------------------------------------+----------------------------------------------+
| :py:meth:`edgetest.hookspecs.run_update` [#f1]_         | | This hook runs the environment update.     |
|                                                         | | As an example, you could implement updates |
|                                                         | | via `pip`, `conda`, or some other package  |
|                                                         | | manager.                                   |
+---------------------------------------------------------+----------------------------------------------+
| :py:meth:`edgetest.hookspecs.post_run_hook`             | | This hook executes code after the testing  |
|                                                         | | has completed. Commonly used for creating  |
|                                                         | | notifications.                             |
+---------------------------------------------------------+----------------------------------------------+

.. rubric:: Footnotes

.. [#f1]

    Only one plugin can be used at a time.

Example
-------

Suppose you want to create a plugin that uses ``conda`` to create your virtual
environments. The typical naming convention for a plugin is ``<host>-<plugin>``,
so let's name our package ``edgetest-conda``. First, let's create the hooks:

``edgetest-conda/edgetest_conda/plugin.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's create the hooks. First, we want to create a hook for :py:meth:`edgetest.hookspecs.addoption`
so we can add two sections to our environment configuration: ``conda_install``
and ``python_version``.

.. code-block:: python

    import pluggy
    from edgetest.schema import Schema

    hookimpl = pluggy.HookimplMarker("edgetest")

    @hookimpl
    def addoption(schema: Schema):
        """Add an environment-level variable for conda installation options.
        Parameters
        ----------
        schema : Schema
            The schema class.
        """
        schema.add_envoption(
            "conda_install",
            {
                "type": "list",
                "schema": {"type": "string"},
                "coerce": "listify",
                "default": None,
                "nullable": True,
            },
        )
        schema.add_envoption(
            "python_version", {"type": "string", "default": "3.7", "coerce": str}
        )

Here, we're using :py:meth:`edgetest.schema.Schema.add_envoption`` to create a new
Cerberus validated section to the configuration file. Next, we'll create a hook
for :py:meth:`edgetest.hookspecs.create_environment` to let conda handle environment
creation.

.. code-block:: python

    from pathlib import Path
    from typing import Dict

    from edgetest.logger import get_logger
    from edgetest.utils import _run_command

    LOG = get_logger(__name__)

    @hookimpl
    def create_environment(basedir: Path, envname: str, conf: Dict):
        """Create the conda environment.
        Parameters
        ----------
        basedir : Path
            The base directory location for the environment.
        envname : str
            The name of the virtual environment.
        conf : dict
            The configuration dictionary for the environment. We will look for ``conda_install``.
        Raises
        ------
        RuntimeError
            Error raised if the environment cannot be created.
        """
        _run_command(
            "conda",
            "create",
            "-p",
            str(basedir / envname),
            f"python={conf['python_version']}",
            "--yes",
        )

        # Install any conda packages
        if conf.get("conda_install"):
            LOG.info(f"Installing conda packages for {envname}")
            _run_command(
                "conda",
                "install",
                "-p",
                str(basedir / envname),
                *conf["conda_install"],
                "--yes",
            )
            LOG.info(f"Successfully installed conda packages for {envname}")

``edgetest-conda/setup.cfg``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini
    :emphasize-lines: 11-13

    [metadata]
    name = edgetest-conda
    ...

    [options]
    packages = find:
    ...
    install_requires =
        edgetest>=2021.11.0

    [options.entry_points]
    edgetest =
        conda = edgetest_conda.plugin

The ``options.entry_points`` section here creates the link between ``edgetest`` and your plugin.

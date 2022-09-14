Advanced Usage
==============

Configuration file
------------------

Suppose you want to test upgrades for a subset of your dependencies. Instead of letting ``edgetest``
parse your requirements file, you can create a configuration file:

.. code-block:: ini

    [edgetest.envs.pandas]
    upgrade =
        pandas

Then run

.. code-block:: console

    $ edgetest -c edgetest.cfg

This command will

1. Create your virtual environment (as in the standard case),
2. Install the local package,
3. Upgrade ``pandas``, and
4. Run the ``pytest`` in the environment.


.. important::

    This configuration file can be a standalone file which is distinct from the ``setup.cfg`` or ``pyproject.toml``
    configurations. Just note it must have a ``edgetest.envs`` otherwise it expects a PEP 517-style ``setup.cfg``



``setup.cfg`` and ``pyproject.toml`` Configuration
--------------------------------------------------

You can also specify your testing environment through ``setup.cfg`` or ``pyproject.toml``:

.. tabs::

    .. tab:: .cfg

        .. code-block:: ini

            [edgetest.envs.pandas]
            upgrade =
                pandas

    .. tab:: .toml

        .. code-block:: toml

            [edgetest.envs.pandas]
            upgrade = [
                "pandas"
            ]

If you're using a `PEP-517 <https://setuptools.pypa.io/en/latest/userguide/declarative_config.html>`_
or `PEP-621 <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html>`_ style installation configuration
your requirements might look like this:

.. tabs::

    .. tab:: .cfg

        .. code-block:: ini

            [options]
            install_requires =
                pandas

    .. tab:: .toml

        .. code-block:: toml

            [project]
            dependencies = [
                "pandas",
            ]

To point to ``setup.cfg`` or ``pyproject.toml``, supply the location of the file as your ``--config``:

.. tabs::

    .. tab:: .cfg

        .. code-block:: console

            $ edgetest -c path/to/setup.cfg

    .. tab:: .toml

        .. code-block:: console

            $ edgetest -c path/to/pyproject.toml

.. important::

    Using ``setup.cfg`` or ``pyproject.toml`` will allow you to upgrade optional installations.


Installing extras
-----------------

To install extras with your local package in the virtual environment(s), modify your configuration or CLI
call as follows:

.. tabs::

    .. tab:: .cfg

        Add an ``extras`` list to your environment:

        .. code-block:: ini

            [edgetest.envs.pandas]
            upgrade =
                pandas
            extras =
                tests

    .. tab:: .toml

        Add an ``extras`` list to your environment:

        .. code-block:: toml

            [edgetest.envs.pandas]
            upgrade = ["myupgrade"]
            extras = ["tests"]

    .. tab:: Requirements parsing

        Add ``--extras`` to the CLI call:

        .. code-block:: console

            $ edgetest --extras tests --extras complete

        The above command will install ``.[tests, complete]``.


Modifying the test command
--------------------------

To customize your test command, modify the configuration or CLI call as follows:

.. tabs::

    .. tab:: .cfg

        Add a ``command`` key to your environment:

        .. code-block:: ini

            [edgetest.envs.pandas]
            upgrade =
                pandas
            extras =
                tests
            command =
                pytest tests -m 'not integration'

    .. tab:: .toml

        Add a ``command`` key to your environment:

        .. code-block:: toml

            [edgetest.envs.pandas]
            upgrade = ["myupgrade"]
            extras = ["tests"]
            command = "pytest tests -m 'not integration'"

    .. tab:: Requirements parsing

        Add ``--command`` to your CLI call:

        .. code-block:: console

            $ edgetest \
                --extras tests \
                --extras complete \
                --command 'pytest tests -m "not integration"'


Additional dependencies
-----------------------

Suppose your testing requires an additional library that is not included in your ``extras``. You
can specify additional dependencies to be installed via ``pip``.

To specify additional ``pip`` dependencies, modify as follows:

.. tabs::

    .. tab:: .cfg

        Add a ``deps`` list:

        .. code-block:: ini

            [edgetest.envs.pandas]
            upgrade =
                pandas
            extras =
                tests
            command =
                pytest tests -m "not integration"
            deps =
                scikit-learn

    .. tab:: .toml

        Add a ``deps`` list:

        .. code-block:: toml

            [edgetest.envs.pandas]
            upgrade = ["myupgrade"]
            extras = ["tests"]
            command = "pytest tests -m 'not integration'"
            deps = ["scikit-learn"]

    .. tab:: Requirements parsing

        Add a ``deps`` argument to your CLI call; this argument accepts multiple values.

        .. code-block:: console

            $ edgetest \
                --extras tests \
                --extras complete \
                --command 'pytest tests -m "not integration"' \
                --deps scikit-learn

In both cases, ``scikit-learn`` will be installed with the following command:

.. code-block:: console

    $ .edgetest/pandas/bin/python -m pip install scikit-learn


Default arguments
-----------------

If you have default arguments you want to pass to each environment in your configuration,
you can specify those under the ``edgetest`` section of your configuration:

.. tabs::

    .. tab:: .cfg

        .. code-block:: ini

            [edgetest]
            extras =
                tests
            command =
                pytest tests -m 'not integration'

            [edgetest.envs.pandas]
            upgrade =
                pandas

            [edgetest.envs.numpy]
            upgrade =
                numpy

        .. important::

            You can combine your configuration file with ``requirements.txt``. If you have the following
            configuration file:

            .. code-block:: ini

                [options]
                install_requires =

                [edgetest]
                extras =
                    tests
                command =
                    pytest tests -m 'not integration'

            and the following requirements file:

            .. code-block:: text

                pandas>=0.25.1,<=1.0.0
                scikit-learn>=0.23.0,<=0.24.2


            the following CLI call

            .. code-block:: console

                $ edgetest -c edgetest.cfg -r requirements.txt

            will apply the default arguments to each environment.


    .. tab:: .toml

        .. code-block:: toml

            [edgetest]
            extras = ["tests"]
            command = "pytest tests -m 'not integration'"

            [edgetest.envs.pandas]
            upgrade = ["pandas"]

            [edgetest.envs.numpy]
            upgrade = ["numpy"]


Multiple packages
-----------------

Suppose you have multiple local packages you want to test. You can include the ``package_dir``
in your testing project directory:

.. tabs::

    .. tab:: .cfg

        .. code-block:: ini

            [edgetest.envs.pandas]
            package_dir = ../mypackage
            upgrade =
                pandas

            [edgetest.envs.numpy]
            package_dir = ../myotherpackage
            upgrade =
                numpy

        After running

        .. code-block:: console

            $ edgetest -c path/to/edgetest.cfg

    .. tab:: .toml

        .. code-block:: toml

            [edgetest.envs.pandas]
            package_dir = "../mypackage"
            upgrade = ["pandas"]

            [edgetest.envs.numpy]
            package_dir = "../myotherpackage"
            upgrade = ["numpy"]

        After running

        .. code-block:: console

            $ edgetest -c path/to/edgetest.toml

your end output should look something like this:

.. code-block:: text

    ============= =============== =================== =================
     Environment   Passing tests   Upgraded packages   Package version
    ------------- --------------- ------------------- -----------------
     pandas        True            pandas              1.2.4
     numpy         True            numpy               1.20.2
    ============= =============== =================== =================

.. important::

    Testing multiple local packages is only supported with the configuration file syntax.


Running a single environment
----------------------------

To run ``edgetest`` for a single environment, supply ``--environment`` or ``-e``:

.. code-block:: console

    $ edgetest -e pandas


Exporting an upgraded requirements file
---------------------------------------

You can use the ``--export`` flag to overwrite your input requirements file with the
upgraded version as well. This feature will update the ``--requirements`` argument
file (default ``requirements.txt``) with the upgraded packages from your **last**
test environment if the tests pass. In the requirements file,

* any ``<=`` constraint will be updated,
* any ``==`` constraint will be changed to ``>=`` and ``<=``, and
* any ``<`` constraint will use ``!=`` to exclude the upper version but include the new maximum.

For instance, ``snowflake-connector-python[pandas]>=2.2.8,<2.3.9`` might be replaced with
``snowflake-connector-python[pandas]!=2.3.9,<=2.4.3,>=2.2.8``. To use this functionality,

.. tabs::

    .. tab:: Configuration file

        Include the correct ``--requirements`` filepath and use ``--export``:

        .. code-block:: console

            $ edgetest \
                -c path/to/config.yaml \
                --requirements requirements.txt \
                --export

        .. important::

            This will overwrite your current ``setup.cfg`` file with the updated requirements
            if you are using PEP-517.

            .. code-block:: console

                $ edgetest -c path/to/setup.cfg --export

    .. tab:: Requirements parsing

        For a standard requirements file, the last environment will be ``all-requirements``.
        So, if your tests pass with all requirements upgraded, the requirements file will
        be updated.

        .. code-block:: console

            $ edgetest \
                --extras tests \
                --extras complete \
                --command 'pytest tests -m "not integration"' \
                --deps scikit-learn \
                --export

Using plugins
-------------

``edgetest`` is built on a plugin framework that allows for extensibility and modularity
(see details :doc:`here <plugins>`). Below we have listed the plugins that are built
and maintained by the ``edgetest`` developer team:

+--------------------------------------------------------------------------+--------------------------------------------------------------------+
| Plugin                                                                   | Description                                                        |
|                                                                          |                                                                    |
+==========================================================================+====================================================================+
| `edgetest-conda <https://github.com/capitalone/edgetest-conda>`_         | | Uses ``conda`` or ``mamba`` for environment creation instead of  |
|                                                                          | | ``venv``.                                                        |
+--------------------------------------------------------------------------+--------------------------------------------------------------------+
| `edgetest-hub <https://github.com/capitalone/edgetest-hub>`_             | | Creates a pull request in your GitHub repository with the        |
|                                                                          | | dependency updates.                                              |
+--------------------------------------------------------------------------+--------------------------------------------------------------------+
| `edgetest-pip-tools <https://github.com/capitalone/edgetest-pip-tools>`_ | | Refreshes a locked requirements file based on the updated        |
|                                                                          | | dependency pins.                                                 |
+--------------------------------------------------------------------------+--------------------------------------------------------------------+

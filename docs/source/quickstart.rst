Quick Start
===========

Install
-------

Installation from PyPI:

.. code-block:: console

    $ python -m pip install edgetest

Installation from conda-forge:

.. code-block:: console

    $ conda install -c conda-forge edgetest

Usage
-----

``edgetest`` allows multi-package, bleeding edge dependency testing. Suppose you have a local package,
``mypackage``, with the following ``requirements.txt`` file [#f1]_:

.. code-block:: text

    pandas>=0.25.1,<=1.0.0
    ...

``edgetest`` allows you to test your package against the latest version of ``pandas``. If you run

.. code-block:: console

    $ edgetest

from within the root directory of ``mypackage``, ``edgetest`` will

1. Create a virtual environment in the ``.edgetest`` folder,
2. Install the local ``mypackage`` with the following command:

   .. code-block:: console

      $ .edgetest/pandas/bin/python -m pip install .

3. Upgrade ``pandas`` using the following command:

   .. code-block:: console

      $ .edgetest/pandas/bin/python -m pip install pandas --upgrade

4. Run a generic test command:

   .. code-block:: console

      $ .edgetest/pandas/bin/python -m pytest

5. Repeat steps 1-5 for any other packages in your ``requirements.txt``.
6. Repeat steps 1-5 for a single environment with all packages in ``requirements.txt`` upgraded.

.. important::

    Remember to add ``.edgetest/`` to your ``.gitignore`` to avoid committing entire conda
    environments to Github.

After you run the command, you should get a console output similar to the following:

.. code-block:: text

    ================== =============== =================== =================
     Environment        Passing tests   Upgraded packages   Package version
    ------------------ --------------- ------------------- -----------------
     pandas             True            pandas              1.2.4
     ...                ...             ...                 ...
     all-requirements   True            pandas              1.2.4
     all-requirements   ...             ...                 ...
    ================== =============== =================== =================

.. rubric:: Footnotes

.. [#f1]

    If you are not using a ``requirements.txt`` file, you can specify the filename with ``-r``:

    .. code-block:: console

        $ edgetest -r path/to/file.txt

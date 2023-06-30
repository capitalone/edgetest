# Bleeding edge dependency testing

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/edgetest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![PyPI version](https://badge.fury.io/py/edgetest.svg)](https://badge.fury.io/py/edgetest)
[![Anaconda-Server Badge](https://anaconda.org/conda-forge/edgetest/badges/version.svg)](https://anaconda.org/conda-forge/edgetest)
![PyPI - Downloads](https://img.shields.io/pypi/dm/edgetest)

[Full Documentation](https://capitalone.github.io/edgetest/)

`edgetest` is a `tox`-inspired python library that will loop through your project's dependencies, and check if your
project is compatible with the latest version of each dependency. It does this by:

* creating a virtual environment,
* installing your local package into the environment,
* upgrading specified dependency package(s), and
* running your test command.

For example, if you depend on ``pandas>=0.25.1,<=1.0.0``, ``edgetest`` will test your project against the most current
pandas version (say ``1.3.4``), so you know if you can safely update your dependency to ``pandas>=0.25.1,<=1.3.4`` or not.


`edgetest` works with the following types of projects:

- `pyproject.toml`
- `setup.cfg`
- and `requirements.txt`


Table Of Contents
-----------------

- [Install](#install)
- [Getting Started](#getting-started)
- [Options](#options)
- [Plugins](#plugins)
- [Contributing](#contributing)
- [License](#license)
- [Roadmap](#roadmap)

Install
-------

Create a ``conda`` environment with Python 3.8+ and install from PyPI:

```console
$ python -m pip install edgetest
```

or conda-forge:

```console
$ conda install -c conda-forge edgetest
```

Getting Started
---------------

``edgetest`` allows multi-package, bleeding edge dependency testing. Suppose you have a package, ``mypackage``, with
the following ``requirements.txt``:

```
pandas>=0.25.1,<=1.0.0
...
```

``edgetest`` allows you to test your package against the latest version of ``pandas``. If you run

```console
$ edgetest
```

the package will

1. Create a virtual environment in the ``.edgetest`` folder,
2. Install the local ``mypackage``: ``.edgetest/pandas/bin/python -m pip install .``,
3. Upgrade ``pandas``: ``.edgetest/pandas/bin/python -m pip install pandas --upgrade``,
4. Run ``.edgetest/pandas/bin/python -m pytest``, and
5. Repeat steps 1-4 for all packages in ``requirements.txt``.

After you run the command, you should get console output similar to the following:

```
============= =============== =================== =================
 Environment   Passing tests   Upgraded packages   Package version
------------- --------------- ------------------- -----------------
 pandas        True            pandas              1.3.4
============= =============== =================== =================
```

Options
-------

See the [advanced usage](https://capitalone.github.io/edgetest/usage.html) page.


Plugins
-------

Current plugins include:

| Plugin                 | Description                                                                  |
|------------------------|------------------------------------------------------------------------------|
| [edgetest-conda](https://github.com/capitalone/edgetest-conda)     | Uses conda or mamba for environment creation instead of venv.                |
| [edgetest-hub](https://github.com/capitalone/edgetest-hub)       | Creates a pull request in your GitHub repository with the dependency updates.|
| [edgetest-pip-tools](https://github.com/capitalone/edgetest-pip-tools) | Refreshes a locked requirements file based on the updated dependency pins.   |


Contributing
------------

See our [developer documentation](https://capitalone.github.io/edgetest/developer.html).

We welcome and appreciate your contributions! Before we can accept any contributions, we ask that you please be sure to
sign the [Contributor License Agreement (CLA)](https://cla-assistant.io/capitalone/edgetest)

This project adheres to the [Open Source Code of Conduct](https://developer.capitalone.com/resources/code-of-conduct/).
By participating, you are expected to honor this code.


License
-------

Apache-2.0


Roadmap
-------

Roadmap details can be found [here](https://capitalone.github.io/edgetest/roadmap.html).

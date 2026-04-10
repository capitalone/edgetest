Release Guide
=============

Overview
--------

Starting in 2026 we've modified our git workflow.

``main`` will be the core branch where all features will get merged into and
production ready code will also exist. When a release is ready to be made releases/tags will be use
to point to the commit where the release should be made from.

In the past we had used ``dev``, in conjunction with ``main``, but there were some issues
with diverging branches and new rulesets which make the ``main`` only branching strategy
easier to manage.

Each release on ``main`` should be tagged properly to denote a "version" that will have the
corresponding artifact on PyPI for users to ``pip install``.


``gh-pages`` is where official documentation will go. After each release you should
build the docs and push the HTML to the pages branch. When first setting up the
repo you want to make sure your gh-pages is a orphaned branch since it is
disconnected and independent from the code: ``git checkout --orphan gh-pages``.

To build the documentation, run ``make sphinx``. To push, run ``make ghpages``.


TLDR;
-----

* Each feature should have its own branch.
* Each feature branch should be squash merged into ``main``
* Before a release, bump the version using ``bumpver``.
* Create a release from ``main`` via Releases and Tags
* Build and push docs ``gh-pages``. (automated via actions)
* Build and push version to PyPI. (automated via actions)


.. note::

    ``main``, and ``gh-pages`` should be protected in the GitHub UI
    so they aren't accidentally deleted.

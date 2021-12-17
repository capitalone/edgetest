Release Guide
=============

Overview
--------

As part of the on going maintenance of the project having a standardized release
procedure for our repos is key. We follows as pared down version of git-flow
which can be read in more detail `here. <https://nvie.com/posts/a-successful-git-branching-model/>`_
We use ``bumpver`` to automate calendar versioning. To run ``bumpver`` and update
your branch in preparation for an upcoming release, run ``bumpver update``. This
will update all necessary files and commit them using ``git``.

``dev`` is the default branch where most people will work with day to day.
All features must be squash merged into this branch. The reason we squash merge
is to prevent the dev branch from being polluted with endless commit messages
when people are developing. Squashing collapses all the commits into one single
new commit. It will also make it much easier to back out changes if something breaks.

``main`` is where official releases will go. Each release on ``main`` should
be tagged properly to denote a "version" that will have the corresponding artifact
on PyPI for users to ``pip install``.


``gh-pages`` is where official documentation will go. After each release you should
build the docs and push the HTML to the pages branch. When first setting up the
repo you want to make sure your gh-pages is a orphaned branch since it is
disconnected and independent from the code: ``git checkout --orphan gh-pages``.

To build the documentation, run ``make sphinx``. To push, run ``make ghpages``.


TLDR;
-----

* Each feature should have its own branch.
* Each feature branch should be squash merged into ``dev``
* Before a release, bump the version using ``bumpver``.
* Merge  ``dev`` into ``main`` via a regular "merge commits"
* Build and push docs ``gh-pages``.
* Build and push version to PyPI.


.. note::

    ``main``, ``dev``, and ``gh-pages`` should be protected in the GitHub UI
    so they aren't accidentally deleted.

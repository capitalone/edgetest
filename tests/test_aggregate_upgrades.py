"""Tests for aggregating upgrades across environments (#160, #161, #162).

Covers ``aggregate_upgrades``: only passing envs contribute, and when two
passing envs upgraded the same package to different versions the lower
tested version wins, so a pin never moves to a version some env never
installed.
"""

import logging
from types import SimpleNamespace

from edgetest.utils import aggregate_upgrades


def _tester(status: bool, upgrades: list[dict[str, str]]) -> SimpleNamespace:
    """Build a stand-in for ``TestPackage`` with a canned upgrade list."""
    return SimpleNamespace(status=status, upgraded_packages=lambda: list(upgrades))


class TestAggregateUpgrades:
    def test_only_passing_envs_contribute(self):
        testers = [
            _tester(True, [{"name": "pkg", "version": "2.0"}]),
            _tester(False, [{"name": "other", "version": "9.9"}]),
        ]
        assert aggregate_upgrades(testers) == [{"name": "pkg", "version": "2.0"}]

    def test_no_passing_envs_returns_empty(self):
        testers = [_tester(False, [{"name": "pkg", "version": "2.0"}])]
        assert aggregate_upgrades(testers) == []

    def test_lower_version_wins_when_envs_disagree(self):
        testers = [
            _tester(True, [{"name": "pkg", "version": "2.1"}]),
            _tester(True, [{"name": "pkg", "version": "2.0"}]),
        ]
        assert aggregate_upgrades(testers) == [{"name": "pkg", "version": "2.0"}]

    def test_lower_version_wins_regardless_of_env_order(self):
        forward = [
            _tester(True, [{"name": "pkg", "version": "2.0"}]),
            _tester(True, [{"name": "pkg", "version": "2.1"}]),
        ]
        backward = list(reversed(forward))
        assert aggregate_upgrades(forward) == aggregate_upgrades(backward)
        assert aggregate_upgrades(forward) == [{"name": "pkg", "version": "2.0"}]

    def test_same_version_in_two_envs_is_not_a_conflict(self):
        testers = [
            _tester(True, [{"name": "pkg", "version": "2.0"}]),
            _tester(True, [{"name": "pkg", "version": "2.0"}]),
        ]
        assert aggregate_upgrades(testers) == [{"name": "pkg", "version": "2.0"}]

    def test_dash_underscore_names_collide(self):
        testers = [
            _tester(True, [{"name": "python-dateutil", "version": "3.1"}]),
            _tester(True, [{"name": "python_dateutil", "version": "3.0"}]),
        ]
        out = aggregate_upgrades(testers)
        assert len(out) == 1
        assert out[0]["version"] == "3.0"

    def test_conflict_is_logged(self, caplog):
        testers = [
            _tester(True, [{"name": "pkg", "version": "2.1"}]),
            _tester(True, [{"name": "pkg", "version": "2.0"}]),
        ]
        with caplog.at_level(logging.WARNING):
            aggregate_upgrades(testers)
        assert "disagree" in caplog.text

    def test_multiple_packages_tracked_independently(self):
        testers = [
            _tester(
                True, [{"name": "a", "version": "1.5"}, {"name": "b", "version": "0.9"}]
            ),
            _tester(True, [{"name": "a", "version": "1.2"}]),
        ]
        out = {p["name"]: p["version"] for p in aggregate_upgrades(testers)}
        assert out == {"a": "1.2", "b": "0.9"}

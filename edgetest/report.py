"""Generate rST reports."""

from typing import Any, List

from tabulate import tabulate

from .core import TestPackage


def gen_report(testers: List[TestPackage]) -> Any:
    """Generate a rST report.

    Parameters
    ----------
    testers : list
        A list of ``TestPackage`` objects.

    Returns
    -------
    Any
        The report.
    """
    headers = ["Environment", "Passing tests", "Upgraded packages", "Package version"]
    rows: List[List] = []
    for env in testers:
        upgraded = env.upgraded_packages()
        for pkg in upgraded:
            rows.append([env.envname, env.status, pkg["name"], pkg["version"]])

    return tabulate(rows, headers=headers, tablefmt="rst")

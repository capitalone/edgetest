"""Generate rST reports."""

from typing import Any, List

from tabulate import tabulate

from .core import TestPackage

VALID_OUTPUTS = ["rst", "github"]


def gen_report(testers: List[TestPackage], output_type: str = "rst") -> Any:
    """Generate a rST report.

    Parameters
    ----------
    testers : list
        A list of ``TestPackage`` objects.

    output_type : str
        A valid output type of ``rst`` or ``github``

    Returns
    -------
    Any
        The report.
    """
    if output_type not in VALID_OUTPUTS:
        raise ValueError(f"Invalid output_type provided: {output_type}")

    headers = ["Environment", "Passing tests", "Upgraded packages", "Package version"]
    rows: List[List] = []
    for env in testers:
        upgraded = env.upgraded_packages()
        for pkg in upgraded:
            rows.append([env.envname, env.status, pkg["name"], pkg["version"]])

    return tabulate(rows, headers=headers, tablefmt=output_type)

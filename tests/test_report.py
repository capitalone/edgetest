from unittest.mock import patch

import pytest

from edgetest.core import TestPackage
from edgetest.report import gen_report


@patch("edgetest.report.tabulate", autospec=True)
@patch("edgetest.core.TestPackage.upgraded_packages", autospec=True)
def test_report(mock_test_package, mock_tabulate, plugin_manager):
    """Test gen_report function"""

    tester_list = [
        TestPackage(hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade1"]),
        TestPackage(hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade2"]),
    ]
    gen_report(tester_list)
    mock_tabulate.assert_called_with(
        [],
        headers=[
            "Environment",
            "Passing tests",
            "Upgraded packages",
            "Package version",
        ],
        tablefmt="rst",
    )

    gen_report(tester_list, output_type="github")
    mock_tabulate.assert_called_with(
        [],
        headers=[
            "Environment",
            "Passing tests",
            "Upgraded packages",
            "Package version",
        ],
        tablefmt="github",
    )

    with pytest.raises(ValueError) as e:
        gen_report(tester_list, output_type="bad")

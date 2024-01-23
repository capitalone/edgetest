from unittest.mock import patch

import pytest

from edgetest.core import TestPackage
from edgetest.report import gen_report


@patch("edgetest.report.tabulate", autospec=True)
@patch("edgetest.core.TestPackage.upgraded_packages", autospec=True)
@patch("edgetest.core.TestPackage.lowered_packages", autospec=True)
def test_report(
    mock_test_package_lowered, mock_test_package, mock_tabulate, plugin_manager
):
    """Test gen_report function"""

    tester_list = [
        TestPackage(hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade1"]),
        TestPackage(hook=plugin_manager.hook, envname="myenv", upgrade=["myupgrade2"]),
        TestPackage(hook=plugin_manager.hook, envname="myenv_lower", lower=["mylower"]),
    ]

    expected_headers = [
        "Environment",
        "Setup successful",
        "Passing tests",
        "Upgraded packages",
        "Lowered packages",
        "Package version",
    ]
    gen_report(tester_list)
    mock_tabulate.assert_called_with([], headers=expected_headers, tablefmt="rst")

    gen_report(tester_list, output_type="github")
    mock_tabulate.assert_called_with([], expected_headers, tablefmt="github")

    with pytest.raises(ValueError):
        gen_report(tester_list, output_type="bad")

from pathlib import Path
from unittest.mock import patch

import pytest

from edgetest.lib import (
    create_environment,
    path_to_python,
    run_install_lower,
    run_update,
)


@patch("edgetest.lib.platform", autospec=True)
def test_path_to_python(mock_platform):
    mock_platform.system.return_value = "Windows"
    assert path_to_python("test", "test") == str(
        Path("test") / "test" / "Scripts" / "python.exe"
    )

    mock_platform.system.return_value = "Unix"
    assert path_to_python("test", "test") == str(
        Path("test") / "test" / "bin" / "python"
    )

    mock_platform.system.side_effect = RuntimeError()
    with pytest.raises(RuntimeError):
        path_to_python("test", "test")


@patch("edgetest.lib.EnvBuilder", autospec=True)
def test_create_environment(mock_env_builder):
    create_environment("test", "test", {})
    mock_env_builder.assert_called_with(with_pip=False)
    mock_env_builder().create.assert_called_with(env_dir=Path("test", "test"))

    mock_env_builder().create.side_effect = RuntimeError()
    with pytest.raises(RuntimeError):
        create_environment("test", "test", {})


@patch("edgetest.lib._run_command", autospec=True)
def test_run_update(mock_run):
    python_path = path_to_python("test", "test")
    run_update("test", "test", ["1", "2"], {"test": "test"})
    mock_run.assert_called_with(
        "uv", "pip", "install", f"--python={python_path}", "1", "2", "--upgrade"
    )

    mock_run.side_effect = RuntimeError()
    with pytest.raises(RuntimeError):
        run_update("test", "test", ["1", "2"], {"test": "test"})


@patch("edgetest.lib._run_command", autospec=True)
def test_run_install_lower(mock_run):
    python_path = path_to_python("test", "test")
    run_install_lower("test", "test", ["package1==1", "package2==2"], {"test": "test"})
    mock_run.assert_called_with(
        "uv",
        "pip",
        "install",
        f"--python={python_path}",
        "package1==1",
        "package2==2",
    )

    mock_run.side_effect = RuntimeError()
    with pytest.raises(RuntimeError):
        run_install_lower(
            "test", "test", ["package1==1", "package2==2"], {"test": "test"}
        )

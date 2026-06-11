from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from uv import find_uv_bin

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


@patch("edgetest.lib._run_command", autospec=True)
def test_create_environment(mock_run):
    create_environment("test", "test", {})
    uv_ = find_uv_bin()
    mock_run.assert_called_with(uv_, "venv", str(Path("test", "test")))

    create_environment("test", "test", {"python_version": "3.10"})

    mock_run.assert_called_with(uv_, "venv", str(Path("test", "test")), "--python=3.10")

    mock_run.side_effect = RuntimeError()
    with pytest.raises(RuntimeError):
        create_environment("test", "test", {"python_version": "3.10"})


@pytest.mark.parametrize("ignore_cooldown", [True, False])
@patch("edgetest.lib.click.get_current_context")
@patch("edgetest.lib._run_command", autospec=True)
def test_run_update(mock_run, mock_ctx, ignore_cooldown):
    mock_ctx.return_value = SimpleNamespace(params={"ignore_cooldown": ignore_cooldown})
    python_path = path_to_python("test", "test")
    run_update("test", "test", ["1", "2"], {"exclude_newer": "3 days"})

    uv_ = find_uv_bin()
    if ignore_cooldown:
        mock_run.assert_called_with(
            uv_, "pip", "install", f"--python={python_path}", "1", "2", "--upgrade"
        )
    else:
        mock_run.assert_called_with(
            uv_,
            "pip",
            "install",
            f"--python={python_path}",
            "1",
            "2",
            "--upgrade",
            "--exclude-newer=3 days",
        )

    mock_run.side_effect = RuntimeError()
    with pytest.raises(RuntimeError):
        run_update("test", "test", ["1", "2"], {"test": "test"})


@patch("edgetest.lib._run_command", autospec=True)
def test_run_install_lower(mock_run):
    python_path = path_to_python("test", "test")
    run_install_lower("test", "test", ["package1==1", "package2==2"], {"test": "test"})

    uv_ = find_uv_bin()
    mock_run.assert_called_with(
        uv_,
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

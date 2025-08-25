"""Tests for virtual environment detection."""

from pathlib import Path

from pyenvsearch.core.venv import VirtualEnvDetector, VirtualEnvInfo


def test_venv_detector_init():
    """Test that VirtualEnvDetector can be initialized."""
    detector = VirtualEnvDetector()
    assert detector is not None
    assert detector.python_executable is not None
    assert detector.python_version is not None


def test_detect_returns_venv_info():
    """Test that detect() returns a VirtualEnvInfo object."""
    detector = VirtualEnvDetector()
    result = detector.detect()

    assert isinstance(result, VirtualEnvInfo)
    assert result.python_version is not None
    assert result.python_executable is not None
    assert isinstance(result.site_packages, list)
    assert result.env_type in ["system", "venv", "conda", "pyenv", "poetry", "uv"]


def test_venv_info_to_dict():
    """Test VirtualEnvInfo serialization."""
    info = VirtualEnvInfo(
        path=Path("/test/path"),
        is_active=True,
        python_version="3.13.0",
        python_executable="/usr/bin/python3",
        site_packages=[Path("/test/site-packages")],
        env_type="venv",
        uv_managed=False,
    )

    result = info.to_dict()
    assert isinstance(result, dict)
    assert result["path"] == "/test/path"
    assert result["is_active"] is True
    assert result["python_version"] == "3.13.0"
    assert result["site_packages"] == ["/test/site-packages"]


def test_venv_info_format_human():
    """Test VirtualEnvInfo human formatting."""
    info = VirtualEnvInfo(
        path=Path("/test/path"),
        is_active=True,
        python_version="3.13.0",
        python_executable="/usr/bin/python3",
        site_packages=[Path("/test/site-packages")],
        env_type="venv",
        uv_managed=False,
    )

    result = info.format_human()
    assert isinstance(result, str)
    assert "Virtual Environment Information" in result
    assert "/test/path" in result
    assert "3.13.0" in result

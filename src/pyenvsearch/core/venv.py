"""Virtual environment detection and analysis."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class VirtualEnvInfo:
    """Information about a detected virtual environment."""

    path: Path | None
    is_active: bool
    python_version: str
    python_executable: str
    site_packages: list[Path]
    env_type: str  # 'venv', 'conda', 'pyenv', 'system', 'unknown'
    uv_managed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path) if self.path else None,
            "is_active": self.is_active,
            "python_version": self.python_version,
            "python_executable": self.python_executable,
            "site_packages": [str(p) for p in self.site_packages],
            "env_type": self.env_type,
            "uv_managed": self.uv_managed,
        }

    def format_human(self) -> str:
        """Format for human-readable output."""
        lines = []
        lines.append("Virtual Environment Information:")
        lines.append("=" * 35)

        if self.path:
            lines.append(f"Environment Path: {self.path}")
        else:
            lines.append("Environment Path: Not detected (using system Python)")

        lines.append(f"Active: {'Yes' if self.is_active else 'No'}")
        lines.append(f"Python Version: {self.python_version}")
        lines.append(f"Python Executable: {self.python_executable}")
        lines.append(f"Environment Type: {self.env_type}")
        lines.append(f"UV Managed: {'Yes' if self.uv_managed else 'No'}")

        if self.site_packages:
            lines.append(f"\nSite Packages ({len(self.site_packages)}):")
            for i, pkg_path in enumerate(self.site_packages, 1):
                lines.append(f"  {i}. {pkg_path}")
        else:
            lines.append("\nSite Packages: None found")

        return "\n".join(lines)


class VirtualEnvDetector:
    """Detects and analyzes virtual environments."""

    COMMON_VENV_NAMES = [".venv", "venv", ".env", "env", "virtualenv"]

    def __init__(self):
        self.python_executable = sys.executable
        self.python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    def detect(self) -> VirtualEnvInfo:
        """Detect the current virtual environment setup."""
        # Check if we're in a virtual environment
        venv_path = self._detect_venv_path()
        is_active = self._is_venv_active()
        env_type = self._determine_env_type(venv_path)
        site_packages = self._find_site_packages()
        uv_managed = self._is_uv_managed()

        return VirtualEnvInfo(
            path=venv_path,
            is_active=is_active,
            python_version=self.python_version,
            python_executable=self.python_executable,
            site_packages=site_packages,
            env_type=env_type,
            uv_managed=uv_managed,
        )

    def _detect_venv_path(self) -> Path | None:
        """Detect the path to the virtual environment."""
        # Check VIRTUAL_ENV environment variable
        venv_env = os.environ.get("VIRTUAL_ENV")
        if venv_env:
            return Path(venv_env)

        # Check if we're running from a virtual environment
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            return Path(sys.prefix)

        # Look for common virtual environment directories
        current_dir = Path.cwd()
        for parent in [current_dir] + list(current_dir.parents):
            for venv_name in self.COMMON_VENV_NAMES:
                venv_path = parent / venv_name
                if self._is_valid_venv(venv_path):
                    return venv_path

        return None

    def _is_valid_venv(self, path: Path) -> bool:
        """Check if a path is a valid virtual environment."""
        if not path.exists() or not path.is_dir():
            return False

        # Check for Python executable
        python_paths = [
            path / "bin" / "python",
            path / "bin" / "python3",
            path / "Scripts" / "python.exe",  # Windows
            path / "Scripts" / "python3.exe",  # Windows
        ]

        return any(p.exists() for p in python_paths)

    def _is_venv_active(self) -> bool:
        """Check if a virtual environment is currently active."""
        return (
            os.environ.get("VIRTUAL_ENV") is not None
            or hasattr(sys, "real_prefix")
            or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        )

    def _determine_env_type(self, venv_path: Path | None) -> str:
        """Determine the type of environment."""
        if not venv_path:
            return "system"

        # Check for UV management
        if self._is_uv_managed():
            return "uv"

        # Check for conda
        if "conda" in str(venv_path).lower() or os.environ.get("CONDA_DEFAULT_ENV"):
            return "conda"

        # Check for pyenv
        if "pyenv" in str(venv_path).lower() or os.environ.get("PYENV_VERSION"):
            return "pyenv"

        # Check for Poetry
        if ".poetry" in str(venv_path) or (venv_path.parent / "pyproject.toml").exists():
            pyproject = venv_path.parent / "pyproject.toml"
            if pyproject.exists():
                try:
                    content = pyproject.read_text()
                    if "[tool.poetry]" in content:
                        return "poetry"
                except OSError:
                    pass

        return "venv"

    def _find_site_packages(self) -> list[Path]:
        """Find all site-packages directories."""
        site_packages = []

        for path in sys.path:
            path_obj = Path(path)
            if path_obj.exists() and "site-packages" in str(path_obj):
                site_packages.append(path_obj)

        return site_packages

    def _is_uv_managed(self) -> bool:
        """Check if this is a UV-managed environment."""
        # Check for UV-specific markers
        current_dir = Path.cwd()

        # Look for uv.lock or .python-version files
        for parent in [current_dir] + list(current_dir.parents):
            if (parent / "uv.lock").exists() or (parent / ".python-version").exists():
                return True

        # Check if uv is in the path or environment variables
        return (
            os.environ.get("UV_PROJECT_ENVIRONMENT") is not None
            or "uv" in os.environ.get("PATH", "").lower()
        )

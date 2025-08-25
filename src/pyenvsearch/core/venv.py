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

    # Order matters - prefer .venv (uv/modern convention) over legacy names
    COMMON_VENV_NAMES = [".venv", "venv", ".env", "env", "virtualenv"]

    # Project markers that indicate a project root
    PROJECT_MARKERS = [
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "uv.lock",
        ".git",
        ".hg",
        ".svn",
    ]

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

    def _find_project_root(self, start_path: Path | None = None) -> Path | None:
        """Find the project root by looking for project markers."""
        current_dir = start_path or Path.cwd()

        # Don't search above these boundaries
        boundaries = [Path.home(), Path("/")]

        for parent in [current_dir] + list(current_dir.parents):
            # Stop at boundaries
            if parent in boundaries:
                break

            # Stop after going up too far (safety limit)
            if len(parent.parts) < len(current_dir.parts) - 5:
                break

            # Check for project markers
            for marker in self.PROJECT_MARKERS:
                if (parent / marker).exists():
                    return parent

        return current_dir  # Fallback to current directory

    def _detect_tool_type(self, project_root: Path) -> str:
        """Detect which tool manages this project."""
        # uv project
        if (project_root / "uv.lock").exists():
            return "uv"

        # Poetry project
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if "[tool.poetry]" in content:
                    return "poetry"
                elif "[tool.uv]" in content or "requires-python" in content:
                    return "uv"
            except (OSError, UnicodeDecodeError):
                pass

        # Legacy markers
        if (project_root / "Pipfile").exists():
            return "pipenv"
        if (project_root / "requirements.txt").exists():
            return "pip"

        return "unknown"

    def _find_poetry_venv(self, project_root: Path) -> Path | None:
        """Find Poetry-managed virtual environment."""
        # First check for in-project .venv
        local_venv = project_root / ".venv"
        if self._is_valid_venv(local_venv):
            return local_venv

        # Then check Poetry's cache directory
        poetry_cache = Path.home() / ".cache" / "pypoetry" / "virtualenvs"
        if poetry_cache.exists():
            project_name = project_root.name
            # Poetry creates names like "projectname-hash-py3.x"
            for venv_dir in poetry_cache.iterdir():
                if venv_dir.is_dir() and venv_dir.name.startswith(project_name):
                    if self._is_valid_venv(venv_dir):
                        return venv_dir

        return None

    def _detect_venv_path(self) -> Path | None:
        """Detect the path to the virtual environment with intelligent tool-aware search."""
        project_root = self._find_project_root()
        tool_type = self._detect_tool_type(project_root)

        # Tool-specific search strategies
        if tool_type == "poetry":
            venv_path = self._find_poetry_venv(project_root)
            if venv_path:
                return venv_path

        # Search for local project venvs (uv, manual venv, etc.)
        search_paths = [project_root]

        # For non-project directories, also search current directory
        current_dir = Path.cwd()
        if current_dir != project_root:
            search_paths.append(current_dir)

        for search_dir in search_paths:
            for venv_name in self.COMMON_VENV_NAMES:
                venv_path = search_dir / venv_name
                if self._is_valid_venv(venv_path):
                    return venv_path

        # Check currently active environment (VIRTUAL_ENV, sys.prefix)
        venv_env = os.environ.get("VIRTUAL_ENV")
        if venv_env:
            venv_path = Path(venv_env)
            if self._is_valid_venv(venv_path):
                return venv_path

        # Check if we're running from a virtual environment
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            return Path(sys.prefix)

        return None

    def _is_valid_venv(self, path: Path) -> bool:
        """Check if a path is a valid virtual environment."""
        if not path.exists() or not path.is_dir():
            return False

        # Resolve symlinks consistently for cross-platform reliability
        resolved_path = path.resolve()

        # Check for Python executable (Unix/Linux/macOS)
        python_unix_paths = [
            resolved_path / "bin" / "python",
            resolved_path / "bin" / "python3",
        ]

        # Check for Python executable (Windows)
        python_windows_paths = [
            resolved_path / "Scripts" / "python.exe",
            resolved_path / "Scripts" / "python3.exe",
        ]

        has_python = any(p.exists() for p in python_unix_paths + python_windows_paths)

        if not has_python:
            return False

        # Additional validation - check for site-packages or lib directory
        has_site_packages = (
            any((resolved_path / "lib").glob("python*/site-packages"))
            or (resolved_path / "Lib" / "site-packages").exists()
            or (resolved_path / "lib").exists()  # At least lib directory should exist
            or (resolved_path / "Lib").exists()  # Windows variant
        )

        return has_site_packages

    def _is_venv_active(self) -> bool:
        """Check if a virtual environment is currently active."""
        self._detect_venv_path()

        # If we detected a local project venv, it's not necessarily "active"
        # since we might be running from a different environment (like UV tool)
        # Just check if any virtual environment is active
        return (
            os.environ.get("VIRTUAL_ENV") is not None
            or hasattr(sys, "real_prefix")
            or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        )

    def _determine_env_type(self, venv_path: Path | None) -> str:
        """Determine the type of environment."""
        if not venv_path:
            return "system"

        # Use the improved tool detection
        project_root = self._find_project_root()
        tool_type = self._detect_tool_type(project_root)

        # If we detected a specific tool type, use it
        if tool_type != "unknown":
            return tool_type

        # Check for conda
        if "conda" in str(venv_path).lower() or os.environ.get("CONDA_DEFAULT_ENV"):
            return "conda"

        # Check for pyenv
        if "pyenv" in str(venv_path).lower() or os.environ.get("PYENV_VERSION"):
            return "pyenv"

        # Check for Poetry in the venv path itself (centralized Poetry venvs)
        if ".poetry" in str(venv_path) or "pypoetry" in str(venv_path):
            return "poetry"

        return "venv"

    def _find_site_packages(self) -> list[Path]:
        """Find all site-packages directories, prioritizing detected virtual environment."""
        site_packages = []

        # First, check if we have a detected virtual environment
        detected_venv = self._detect_venv_path()
        if detected_venv:
            # Look for site-packages in the detected venv
            possible_site_packages = [
                detected_venv
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages",
                detected_venv / "Lib" / "site-packages",  # Windows
            ]

            # Also check for any python* directory under lib
            lib_dir = detected_venv / "lib"
            if lib_dir.exists():
                for python_dir in lib_dir.glob("python*"):
                    if python_dir.is_dir():
                        site_pkg = python_dir / "site-packages"
                        if site_pkg.exists():
                            possible_site_packages.append(site_pkg)

            for site_pkg in possible_site_packages:
                if site_pkg.exists() and site_pkg not in site_packages:
                    site_packages.append(site_pkg)

        # Then add current sys.path site-packages as fallback
        for path in sys.path:
            path_obj = Path(path)
            if (
                path_obj.exists()
                and "site-packages" in str(path_obj)
                and path_obj not in site_packages
            ):
                site_packages.append(path_obj)

        return site_packages

    def _is_uv_managed(self) -> bool:
        """Check if this is a UV-managed environment."""
        project_root = self._find_project_root()

        # Primary indicators of UV management
        if (project_root / "uv.lock").exists():
            return True

        # Check pyproject.toml for UV configuration
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if "[tool.uv]" in content or "requires-python" in content:
                    return True
            except (OSError, UnicodeDecodeError):
                pass

        # Check for .python-version (weaker indicator, but UV-related)
        if (project_root / ".python-version").exists():
            return True

        # Check environment variables
        return (
            os.environ.get("UV_PROJECT_ENVIRONMENT") is not None
            or os.environ.get("UV_PYTHON") is not None
        )

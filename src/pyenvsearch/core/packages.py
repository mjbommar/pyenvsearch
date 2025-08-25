"""Package location and analysis functionality."""

import importlib.util
import pkgutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .venv import VirtualEnvDetector


@dataclass
class PackageInfo:
    """Information about a Python package."""

    name: str
    version: str | None = None
    location: Path | None = None
    is_namespace: bool = False
    submodules: list[str] = field(default_factory=list)
    distribution_info: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "location": str(self.location) if self.location else None,
            "is_namespace": self.is_namespace,
            "submodules": self.submodules,
            "distribution_info": str(self.distribution_info) if self.distribution_info else None,
        }

    def format_human(self) -> str:
        """Format for human-readable output."""
        lines = []
        lines.append(f"Package: {self.name}")
        lines.append("=" * (len(self.name) + 9))

        if self.version:
            lines.append(f"Version: {self.version}")

        if self.location:
            lines.append(f"Location: {self.location}")
        else:
            lines.append("Location: Not found")

        lines.append(f"Namespace Package: {'Yes' if self.is_namespace else 'No'}")

        if self.distribution_info:
            lines.append(f"Distribution Info: {self.distribution_info}")

        if self.submodules:
            lines.append(f"\nSubmodules ({len(self.submodules)}):")
            for submodule in sorted(self.submodules):
                lines.append(f"  - {submodule}")

        return "\n".join(lines)


@dataclass
class TableOfContents:
    """Table of contents for a package."""

    package_name: str
    structure: dict[str, Any] = field(default_factory=dict)
    total_modules: int = 0
    total_classes: int = 0
    total_functions: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "package_name": self.package_name,
            "structure": self.structure,
            "total_modules": self.total_modules,
            "total_classes": self.total_classes,
            "total_functions": self.total_functions,
        }

    def format_human(self) -> str:
        """Format for human-readable output."""
        lines = []
        lines.append(f"Table of Contents: {self.package_name}")
        lines.append("=" * (len(self.package_name) + 19))
        lines.append(f"Total Modules: {self.total_modules}")
        lines.append(f"Total Classes: {self.total_classes}")
        lines.append(f"Total Functions: {self.total_functions}")
        lines.append("")

        def format_structure(structure: dict[str, Any], indent: str = "") -> list[str]:
            result = []
            for key, value in sorted(structure.items()):
                if isinstance(value, dict):
                    if "type" in value:
                        # This is a leaf node with type information
                        type_info = value.get("type", "unknown")
                        if type_info == "class":
                            result.append(f"{indent}📁 {key} (class)")
                        elif type_info == "function":
                            result.append(f"{indent}⚡ {key} (function)")
                        elif type_info == "module":
                            result.append(f"{indent}📄 {key} (module)")
                        else:
                            result.append(f"{indent}❓ {key} ({type_info})")
                    else:
                        # This is a directory/package
                        result.append(f"{indent}📦 {key}/")
                        result.extend(format_structure(value, indent + "  "))
            return result

        lines.extend(format_structure(self.structure))
        return "\n".join(lines)


class PackageFinder:
    """Finds and analyzes Python packages."""

    def __init__(self):
        self.venv_detector = VirtualEnvDetector()
        self.venv_info = self.venv_detector.detect()
        self.site_packages = self._find_site_packages()

    def _find_site_packages(self) -> list[Path]:
        """Find site-packages directories, prioritizing detected virtual environment."""
        site_packages = []

        # First, use the detected virtual environment's site-packages
        if self.venv_info.site_packages:
            site_packages.extend(self.venv_info.site_packages)

        # Also include current sys.path for fallback
        for path_str in sys.path:
            path = Path(path_str)
            if path.exists() and "site-packages" in str(path) and path not in site_packages:
                site_packages.append(path)

        return site_packages

    def find_package(self, package_name: str) -> PackageInfo:
        """Find information about a specific package."""
        # If we have a detected virtual environment, use its Python to find packages
        if (
            self.venv_info.path
            and self.venv_info.path != Path(sys.prefix)
            and self.venv_info.site_packages
        ):
            return self._find_package_in_venv(package_name)

        # Fall back to current interpreter
        return self._find_package_current(package_name)

    def _find_package_current(self, package_name: str) -> PackageInfo:
        """Find package using current interpreter."""
        # Try to find the package spec
        spec = importlib.util.find_spec(package_name)

        if spec is None:
            return PackageInfo(
                name=package_name,
                location=None,
            )

        # Get basic package information
        location = None
        if spec.origin:
            location = Path(spec.origin).parent
        elif spec.submodule_search_locations:
            # Namespace package or regular package with submodules
            location = Path(spec.submodule_search_locations[0])

        # Check if it's a namespace package
        is_namespace = spec.submodule_search_locations is not None and spec.origin is None

        # Get version information
        version = self._get_package_version(package_name)

        # Find submodules
        submodules = self._find_submodules(package_name)

        # Find distribution info
        dist_info = self._find_distribution_info(package_name)

        return PackageInfo(
            name=package_name,
            version=version,
            location=location,
            is_namespace=is_namespace,
            submodules=submodules,
            distribution_info=dist_info,
        )

    def _find_package_in_venv(self, package_name: str) -> PackageInfo:
        """Find package in the detected virtual environment."""
        # First try to find via distribution info (handles name mismatches)
        actual_package_name = self._find_actual_package_name(package_name)
        if actual_package_name != package_name:
            # Recursive call with correct name
            result = self._find_package_in_venv(actual_package_name)
            if result.location:
                # Update the name back to what user requested
                result.name = package_name
                return result

        # Search in the detected virtual environment's site-packages
        for site_pkg in self.venv_info.site_packages:
            # Check for editable installs (.pth files)
            editable_result = self._check_editable_installs(package_name, site_pkg)
            if editable_result:
                return editable_result

            # Check for normal package directory
            package_path = site_pkg / package_name
            if package_path.is_dir():
                # Check for __init__.py to confirm it's a package
                init_file = package_path / "__init__.py"
                is_namespace = not init_file.exists()

                version = self._get_package_version_from_path(package_name, site_pkg)
                submodules = self._find_submodules_from_path(package_path)
                dist_info = self._find_distribution_info_from_path(package_name, site_pkg)

                return PackageInfo(
                    name=package_name,
                    version=version,
                    location=package_path,
                    is_namespace=is_namespace,
                    submodules=submodules,
                    distribution_info=dist_info,
                )

            # Look for package as single .py file
            py_file = site_pkg / f"{package_name}.py"
            if py_file.is_file():
                version = self._get_package_version_from_path(package_name, site_pkg)
                dist_info = self._find_distribution_info_from_path(package_name, site_pkg)

                return PackageInfo(
                    name=package_name,
                    version=version,
                    location=py_file.parent,
                    is_namespace=False,
                    submodules=[],
                    distribution_info=dist_info,
                )

        # Package not found in virtual environment
        return PackageInfo(
            name=package_name,
            location=None,
        )

    def _find_actual_package_name(self, requested_name: str) -> str:
        """Find the actual package name from distribution info (handles name mismatches)."""
        for site_pkg in self.venv_info.site_packages:
            # Look through all .dist-info directories
            for dist_info in site_pkg.glob("*.dist-info"):
                if not dist_info.is_dir():
                    continue

                # Check METADATA file for package name mappings
                metadata_file = dist_info / "METADATA"
                if metadata_file.exists():
                    try:
                        content = metadata_file.read_text(encoding="utf-8", errors="ignore")
                        lines = content.split("\n")

                        # Look for Name: field and top_level.txt
                        package_name = None
                        for line in lines:
                            if line.startswith("Name:"):
                                package_name = line.split(":", 1)[1].strip()
                                break

                        # Check if this matches our requested name (case insensitive)
                        if package_name and package_name.lower().replace(
                            "-", "_"
                        ) == requested_name.lower().replace("-", "_"):
                            # Check top_level.txt for actual import name
                            top_level_file = dist_info / "top_level.txt"
                            if top_level_file.exists():
                                try:
                                    top_level_content = top_level_file.read_text().strip()
                                    if top_level_content:
                                        return top_level_content.split("\n")[0]  # First module name
                                except (OSError, UnicodeDecodeError):
                                    pass

                            # Fall back to package name with underscore conversion
                            return package_name.replace("-", "_")

                    except (OSError, UnicodeDecodeError):
                        continue

        return requested_name  # No mapping found

    def _check_editable_installs(self, package_name: str, site_pkg: Path) -> PackageInfo | None:
        """Check for editable installs via .pth files."""
        # Look for .pth files that might point to editable installs
        for pth_file in site_pkg.glob("*.pth"):
            if not pth_file.is_file():
                continue

            try:
                content = pth_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.strip().split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Check if this path contains our package
                    potential_path = Path(line)
                    if potential_path.exists():
                        # Look for package in this path
                        package_path = potential_path / package_name
                        if (
                            package_path.is_dir()
                            or (potential_path / f"{package_name}.py").exists()
                        ):
                            # Found editable install
                            version = self._get_editable_version(potential_path, package_name)
                            is_namespace = (
                                not (package_path / "__init__.py").exists()
                                if package_path.is_dir()
                                else False
                            )
                            submodules = (
                                self._find_submodules_from_path(package_path)
                                if package_path.is_dir()
                                else []
                            )

                            return PackageInfo(
                                name=package_name,
                                version=version,
                                location=package_path if package_path.exists() else potential_path,
                                is_namespace=is_namespace,
                                submodules=submodules,
                                distribution_info=None,  # Editable installs might not have dist-info
                            )
            except (OSError, UnicodeDecodeError):
                continue

        return None

    def _get_editable_version(self, project_path: Path, package_name: str) -> str | None:
        """Get version from editable install (usually from pyproject.toml or setup.py)."""
        # Check pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                import re

                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    return version_match.group(1)
            except (OSError, UnicodeDecodeError):
                pass

        # Check setup.py (basic pattern matching, no execution)
        setup_py = project_path / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                import re

                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    return version_match.group(1)
            except (OSError, UnicodeDecodeError):
                pass

        # Check package __init__.py for __version__
        package_init = project_path / package_name / "__init__.py"
        if package_init.exists():
            try:
                content = package_init.read_text()
                import re

                version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    return version_match.group(1)
            except (OSError, UnicodeDecodeError):
                pass

        return "dev"  # Default for editable installs

    def _get_package_version_from_path(self, package_name: str, site_packages: Path) -> str | None:
        """Get package version by reading from distribution info in specific site-packages."""
        # Look for .dist-info directories
        for dist_info in site_packages.glob(f"{package_name}*.dist-info"):
            if dist_info.is_dir():
                metadata_file = dist_info / "METADATA"
                if metadata_file.exists():
                    try:
                        content = metadata_file.read_text()
                        for line in content.split("\n"):
                            if line.startswith("Version:"):
                                return line.split(":", 1)[1].strip()
                    except (OSError, UnicodeDecodeError):
                        pass

        # Fall back to egg-info
        for egg_info in site_packages.glob(f"{package_name}*.egg-info"):
            if egg_info.is_dir():
                metadata_file = egg_info / "PKG-INFO"
                if metadata_file.exists():
                    try:
                        content = metadata_file.read_text()
                        for line in content.split("\n"):
                            if line.startswith("Version:"):
                                return line.split(":", 1)[1].strip()
                    except (OSError, UnicodeDecodeError):
                        pass

        return None

    def _find_submodules_from_path(self, package_path: Path) -> list[str]:
        """Find submodules by exploring package directory."""
        submodules = []
        if not package_path.is_dir():
            return submodules

        for item in package_path.iterdir():
            if item.name.startswith("_"):
                continue

            if item.is_file() and item.suffix == ".py":
                # It's a module
                submodules.append(f"{package_path.name}.{item.stem}")
            elif item.is_dir() and (item / "__init__.py").exists():
                # It's a subpackage
                submodules.append(f"{package_path.name}.{item.name}")

        return sorted(submodules)

    def _find_distribution_info_from_path(
        self, package_name: str, site_packages: Path
    ) -> Path | None:
        """Find distribution info in specific site-packages directory."""
        # Look for .dist-info directories
        for dist_info in site_packages.glob(f"{package_name}*.dist-info"):
            if dist_info.is_dir():
                return dist_info

        # Also check for .egg-info directories
        for egg_info in site_packages.glob(f"{package_name}*.egg-info"):
            if egg_info.is_dir():
                return egg_info

        return None

    def _get_package_version(self, package_name: str) -> str | None:
        """Get the version of a package."""
        try:
            import importlib.metadata

            return importlib.metadata.version(package_name)
        except (importlib.metadata.PackageNotFoundError, Exception):
            # Try alternative approaches
            try:
                module = importlib.import_module(package_name)
                return getattr(module, "__version__", None)
            except Exception:
                return None

    def _find_submodules(self, package_name: str) -> list[str]:
        """Find submodules of a package."""
        submodules = []
        try:
            # Import the package to get its path
            package = importlib.import_module(package_name)

            if hasattr(package, "__path__"):
                # Iterate through the package's modules
                for _importer, modname, _ispkg in pkgutil.iter_modules(
                    package.__path__, f"{package_name}."
                ):
                    submodules.append(modname)
        except (ImportError, AttributeError):
            pass

        return sorted(submodules)

    def _find_distribution_info(self, package_name: str) -> Path | None:
        """Find the distribution info directory for a package."""
        for site_pkg in self.site_packages:
            # Look for .dist-info directories
            for dist_info in site_pkg.glob(f"{package_name}*.dist-info"):
                if dist_info.is_dir():
                    return dist_info

            # Also check for .egg-info directories (older format)
            for egg_info in site_pkg.glob(f"{package_name}*.egg-info"):
                if egg_info.is_dir():
                    return egg_info

        return None

    def generate_toc(self, package_name: str, depth: int = 2) -> TableOfContents:
        """Generate a table of contents for a package."""
        toc = TableOfContents(package_name=package_name)

        # First find the package location
        package_info = self.find_package(package_name)

        if package_info.location and package_info.location.exists():
            # Use filesystem-based analysis
            toc.structure = self._build_package_structure_from_filesystem(
                package_info.location, depth
            )
            # Count totals
            self._count_items(toc.structure, toc)
        else:
            # Fall back to importlib if package is in current environment
            try:
                package = importlib.import_module(package_name)
                if hasattr(package, "__path__"):
                    toc.structure = self._build_package_structure(package_name, depth)
                    # Count totals
                    self._count_items(toc.structure, toc)
            except ImportError:
                # Package not found or not importable
                pass

        return toc

    def _build_package_structure_from_filesystem(
        self, package_path: Path, max_depth: int, current_depth: int = 0
    ) -> dict[str, Any]:
        """Build package structure by analyzing filesystem directly."""
        if current_depth >= max_depth or not package_path.is_dir():
            return {}

        structure = {}

        try:
            for item in package_path.iterdir():
                # Skip private items and non-Python files
                if item.name.startswith("_") and item.name not in ["__init__.py", "__main__.py"]:
                    continue

                if item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                    # It's a Python module - analyze it
                    module_name = item.stem
                    structure[module_name] = self._analyze_python_file(item)

                elif item.is_dir():
                    # Check if it's a Python package (has __init__.py or is namespace)
                    init_file = item / "__init__.py"
                    if init_file.exists() or any(item.glob("*.py")):
                        # It's a subpackage - recurse
                        substructure = self._build_package_structure_from_filesystem(
                            item, max_depth, current_depth + 1
                        )
                        if substructure:  # Only add if it has content
                            structure[item.name] = substructure
                        else:
                            # Empty package, just mark as package
                            structure[item.name] = {"type": "package"}

        except (OSError, PermissionError):
            pass

        return structure

    def _analyze_python_file(self, file_path: Path) -> dict[str, Any]:
        """Analyze a Python file to extract classes and functions without importing."""
        items = {"type": "module"}

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Simple regex-based analysis to avoid code execution
            import re

            # Find class definitions
            class_pattern = r"^class\s+(\w+)(?:\([^)]*\))?:"
            classes = re.findall(class_pattern, content, re.MULTILINE)

            # Find function definitions (not inside classes)
            func_pattern = r"^def\s+(\w+)\s*\("
            functions = re.findall(func_pattern, content, re.MULTILINE)

            # Add classes
            for class_name in classes:
                if not class_name.startswith("_"):
                    items[class_name] = {"type": "class"}

            # Add functions
            for func_name in functions:
                if not func_name.startswith("_"):
                    items[func_name] = {"type": "function"}

        except (OSError, UnicodeDecodeError):
            pass

        return items

    def _build_package_structure(
        self, package_name: str, max_depth: int, current_depth: int = 0
    ) -> dict[str, Any]:
        """Build the structure dictionary for a package."""
        if current_depth >= max_depth:
            return {}

        structure = {}

        try:
            package = importlib.import_module(package_name)

            if hasattr(package, "__path__"):
                # Iterate through submodules
                for _importer, modname, ispkg in pkgutil.iter_modules(
                    package.__path__, f"{package_name}."
                ):
                    # Get the simple name (without package prefix)
                    simple_name = modname.split(".")[-1]

                    if ispkg:
                        # Recursively build structure for subpackages
                        structure[simple_name] = self._build_package_structure(
                            modname, max_depth, current_depth + 1
                        )
                    else:
                        # This is a module, try to analyze it
                        try:
                            module = importlib.import_module(modname)
                            structure[simple_name] = self._analyze_module(module)
                        except Exception:
                            structure[simple_name] = {"type": "module"}
        except ImportError:
            pass

        return structure

    def _analyze_module(self, module) -> dict[str, Any]:
        """Analyze a module to extract classes and functions."""
        items = {}

        # Get all public attributes
        for name in dir(module):
            if name.startswith("_"):
                continue

            try:
                attr = getattr(module, name)

                # Check if it's a class
                if isinstance(attr, type):
                    items[name] = {"type": "class"}
                # Check if it's a function
                elif callable(attr) and hasattr(attr, "__module__"):
                    if attr.__module__ == module.__name__:  # Defined in this module
                        items[name] = {"type": "function"}
            except Exception:
                # Skip attributes that can't be accessed
                continue

        return items

    def _count_items(self, structure: dict[str, Any], toc: TableOfContents) -> None:
        """Recursively count modules, classes, and functions."""
        for _key, value in structure.items():
            if isinstance(value, dict):
                if "type" in value:
                    # This is a typed item
                    item_type = value["type"]
                    if item_type == "module":
                        toc.total_modules += 1
                        # Also count classes and functions within this module
                        for sub_key, sub_value in value.items():
                            if (
                                sub_key != "type"
                                and isinstance(sub_value, dict)
                                and "type" in sub_value
                            ):
                                sub_type = sub_value["type"]
                                if sub_type == "class":
                                    toc.total_classes += 1
                                elif sub_type == "function":
                                    toc.total_functions += 1
                    elif item_type == "class":
                        toc.total_classes += 1
                    elif item_type == "function":
                        toc.total_functions += 1
                    elif item_type == "package":
                        toc.total_modules += 1
                else:
                    # This is a directory/package, recurse
                    toc.total_modules += 1  # Count the package itself as a module
                    self._count_items(value, toc)

"""Package location and analysis functionality."""

import importlib.util
import pkgutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
        self.site_packages = self._find_site_packages()

    def _find_site_packages(self) -> list[Path]:
        """Find all site-packages directories in sys.path."""
        site_packages = []
        for path_str in sys.path:
            path = Path(path_str)
            if path.exists() and "site-packages" in str(path):
                site_packages.append(path)
        return site_packages

    def find_package(self, package_name: str) -> PackageInfo:
        """Find information about a specific package."""
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
                    # This is a leaf node
                    item_type = value["type"]
                    if item_type == "module":
                        toc.total_modules += 1
                    elif item_type == "class":
                        toc.total_classes += 1
                    elif item_type == "function":
                        toc.total_functions += 1
                else:
                    # This is a directory/package, recurse
                    toc.total_modules += 1  # Count the package itself as a module
                    self._count_items(value, toc)

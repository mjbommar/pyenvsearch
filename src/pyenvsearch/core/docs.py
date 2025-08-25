"""Documentation search functionality for LLM-friendly docs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocumentationFile:
    """Information about a documentation file."""

    path: Path
    file_type: str  # 'llms.txt', 'ai.txt', 'readme', 'docs'
    size: int
    content_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path),
            "file_type": self.file_type,
            "size": self.size,
            "content_preview": self.content_preview,
        }


@dataclass
class DocumentationResult:
    """Result of documentation search."""

    package_name: str
    package_path: Path | None = None
    found_files: list[DocumentationFile] = field(default_factory=list)
    search_locations: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "package_name": self.package_name,
            "package_path": str(self.package_path) if self.package_path else None,
            "found_files": [f.to_dict() for f in self.found_files],
            "search_locations": [str(p) for p in self.search_locations],
        }

    def format_human(self) -> str:
        """Format for human-readable output."""
        lines = []
        lines.append(f"Documentation Search: {self.package_name}")
        lines.append("=" * (len(self.package_name) + 22))

        if self.package_path:
            lines.append(f"Package Path: {self.package_path}")
        else:
            lines.append("Package Path: Not found")

        lines.append(f"Search Locations: {len(self.search_locations)}")
        for i, location in enumerate(self.search_locations, 1):
            lines.append(f"  {i}. {location}")

        if self.found_files:
            lines.append(f"\nFound Documentation Files: {len(self.found_files)}")
            lines.append("")

            # Group by type
            by_type = {}
            for doc_file in self.found_files:
                file_type = doc_file.file_type
                if file_type not in by_type:
                    by_type[file_type] = []
                by_type[file_type].append(doc_file)

            # Display by priority
            priority_order = ["llms.txt", "ai.txt", "readme", "docs"]
            for file_type in priority_order:
                if file_type in by_type:
                    files = by_type[file_type]
                    type_display = {
                        "llms.txt": "🤖 LLM-specific docs (llms.txt)",
                        "ai.txt": "🧠 AI docs (ai.txt)",
                        "readme": "📄 README files",
                        "docs": "📚 Documentation directories",
                    }
                    lines.append(f"{type_display[file_type]}:")
                    for doc_file in files:
                        size_kb = doc_file.size / 1024
                        lines.append(f"  📂 {doc_file.path} ({size_kb:.1f} KB)")
                        if doc_file.content_preview:
                            preview_lines = doc_file.content_preview.strip().split("\n")[:3]
                            for preview_line in preview_lines:
                                if preview_line.strip():
                                    lines.append(f"     │ {preview_line.strip()[:80]}")
                    lines.append("")
        else:
            lines.append("\nNo documentation files found.")

        return "\n".join(lines)


class DocumentationSearcher:
    """Searches for LLM-friendly documentation."""

    # Priority order for LLM-friendly documentation
    LLM_DOC_FILES = ["llms.txt", "ai.txt"]
    README_PATTERNS = [
        "README.md",
        "readme.md",
        "README.txt",
        "readme.txt",
        "README.rst",
        "readme.rst",
        "README",
        "readme",
    ]
    DOC_DIR_NAMES = ["docs", "doc", "documentation", "guide", "guides"]

    def __init__(self):
        pass

    def find_docs(self, package_name: str) -> DocumentationResult:
        """Find documentation for a package."""
        result = DocumentationResult(package_name=package_name)

        # First, try to find the package location
        from .packages import PackageFinder

        finder = PackageFinder()
        package_info = finder.find_package(package_name)

        if not package_info.location:
            return result

        result.package_path = package_info.location
        search_locations = self._get_search_locations(package_info.location)
        result.search_locations = search_locations

        # Search for documentation files
        for location in search_locations:
            if location.exists():
                result.found_files.extend(self._search_location(location))

        # Sort results by priority
        result.found_files = self._sort_by_priority(result.found_files)

        return result

    def _get_search_locations(self, package_path: Path) -> list[Path]:
        """Get list of locations to search for documentation."""
        locations = []

        # Start with the package directory itself
        locations.append(package_path)

        # Check parent directories (for cases where docs are in project root)
        current = package_path
        for _ in range(3):  # Check up to 3 levels up
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            locations.append(parent)
            current = parent

            # Also check if there's a pyproject.toml or setup.py
            # which would indicate this is the project root
            if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
                break

        return locations

    def _search_location(self, location: Path) -> list[DocumentationFile]:
        """Search a specific location for documentation files."""
        found_files = []

        if not location.exists() or not location.is_dir():
            return found_files

        # Search for LLM-specific documentation files
        for llm_file in self.LLM_DOC_FILES:
            file_path = location / llm_file
            if file_path.exists():
                doc_file = self._create_doc_file(file_path, llm_file.replace(".txt", ""))
                if doc_file:
                    found_files.append(doc_file)

        # Search for README files
        for readme_pattern in self.README_PATTERNS:
            file_path = location / readme_pattern
            if file_path.exists():
                doc_file = self._create_doc_file(file_path, "readme")
                if doc_file:
                    found_files.append(doc_file)

        # Search for documentation directories
        for doc_dir_name in self.DOC_DIR_NAMES:
            doc_dir = location / doc_dir_name
            if doc_dir.exists() and doc_dir.is_dir():
                doc_file = DocumentationFile(
                    path=doc_dir,
                    file_type="docs",
                    size=self._get_directory_size(doc_dir),
                    content_preview=self._get_directory_preview(doc_dir),
                )
                found_files.append(doc_file)

        return found_files

    def _create_doc_file(self, file_path: Path, file_type: str) -> DocumentationFile | None:
        """Create a DocumentationFile from a file path."""
        try:
            if not file_path.exists():
                return None

            size = file_path.stat().st_size
            content_preview = self._get_file_preview(file_path)

            return DocumentationFile(
                path=file_path, file_type=file_type, size=size, content_preview=content_preview
            )
        except Exception:
            return None

    def _get_file_preview(self, file_path: Path, max_chars: int = 500) -> str:
        """Get a preview of a file's content."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
                return content
        except Exception:
            return ""

    def _get_directory_size(self, directory: Path) -> int:
        """Get the total size of files in a directory."""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except OSError:
                        continue
        except OSError:
            pass
        return total_size

    def _get_directory_preview(self, directory: Path) -> str:
        """Get a preview of a directory's contents."""
        preview_lines = []
        try:
            # List key files in the docs directory
            files = []
            for item in directory.iterdir():
                if item.is_file():
                    files.append(f"📄 {item.name}")
                elif item.is_dir():
                    files.append(f"📁 {item.name}/")

            # Show first 10 items
            preview_lines = sorted(files)[:10]
            if len(files) > 10:
                preview_lines.append(f"... and {len(files) - 10} more items")
        except OSError:
            pass

        return "\n".join(preview_lines)

    def _sort_by_priority(self, doc_files: list[DocumentationFile]) -> list[DocumentationFile]:
        """Sort documentation files by priority."""
        priority_map = {
            "llms": 1,
            "ai": 2,
            "readme": 3,
            "docs": 4,
        }

        def get_priority(doc_file: DocumentationFile) -> int:
            return priority_map.get(doc_file.file_type, 999)

        return sorted(doc_files, key=get_priority)

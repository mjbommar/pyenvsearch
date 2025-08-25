"""Code search functionality with ast-grep and ripgrep integration."""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SearchMatch:
    """A single search match result."""

    file_path: Path
    line_number: int
    column: int | None = None
    match_text: str = ""
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": str(self.file_path),
            "line_number": self.line_number,
            "column": self.column,
            "match_text": self.match_text,
            "context_before": self.context_before,
            "context_after": self.context_after,
        }


@dataclass
class ListItem:
    """A single item in a listing (method, class, or enum)."""

    name: str
    item_type: str  # 'method', 'class', 'enum'
    file_path: Path
    line_number: int
    column: int | None = None
    module_name: str = ""
    class_name: str | None = None  # For methods: which class they belong to
    parent_class: str | None = None  # For classes: their parent class
    enum_base: str | None = None  # For enums: their base type (Enum, IntEnum, etc.)
    signature: str = ""  # Method signature or class definition
    is_private: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "item_type": self.item_type,
            "file_path": str(self.file_path),
            "line_number": self.line_number,
            "column": self.column,
            "module_name": self.module_name,
            "class_name": self.class_name,
            "parent_class": self.parent_class,
            "enum_base": self.enum_base,
            "signature": self.signature,
            "is_private": self.is_private,
        }


@dataclass
class ListResult:
    """Result of a listing operation."""

    query_type: str  # 'methods', 'classes', 'enums'
    package_name: str | None = None
    items: list[ListItem] = field(default_factory=list)
    total_found: int = 0
    limit: int = 50
    offset: int = 0
    filters: dict[str, Any] = field(default_factory=dict)
    search_paths: list[Path] = field(default_factory=list)
    tool_used: str = "python_re"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_type": self.query_type,
            "package_name": self.package_name,
            "items": [item.to_dict() for item in self.items],
            "total_found": self.total_found,
            "limit": self.limit,
            "offset": self.offset,
            "filters": self.filters,
            "search_paths": [str(p) for p in self.search_paths],
            "tool_used": self.tool_used,
        }

    def format_human(self, relative_paths: bool = False) -> str:
        """Format for human-readable output."""
        lines = []
        lines.append(f"List {self.query_type.title()}: {self.package_name or 'All Packages'}")
        lines.append(
            "="
            * (len(f"List {self.query_type.title()}: {self.package_name or 'All Packages'}") + 2)
        )

        lines.append(f"Tool Used: {self.tool_used}")
        lines.append(f"Total Found: {self.total_found}")
        lines.append(f"Showing: {len(self.items)} (offset: {self.offset}, limit: {self.limit})")

        if self.filters:
            filter_strs = []
            for key, value in self.filters.items():
                if value:
                    filter_strs.append(f"{key}={value}")
            if filter_strs:
                lines.append(f"Filters: {', '.join(filter_strs)}")

        if not self.items:
            lines.append(f"\nNo {self.query_type} found.")
            return "\n".join(lines)

        lines.append("")

        # Group by module for better organization
        by_module = {}
        for item in self.items:
            module = item.module_name or "unknown"
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(item)

        for module_name in sorted(by_module.keys()):
            items = by_module[module_name]
            lines.append(f"📦 {module_name} ({len(items)} items)")

            for item in items:
                if relative_paths:
                    # Try to make path relative to site-packages
                    try:
                        parts = item.file_path.parts
                        site_pkg_idx = -1
                        for i, part in enumerate(parts):
                            if "site-packages" in part:
                                site_pkg_idx = i
                                break
                        if site_pkg_idx >= 0 and site_pkg_idx + 1 < len(parts):
                            rel_path = Path(*parts[site_pkg_idx + 1 :])
                            location = f"{rel_path}:{item.line_number}"
                        else:
                            location = f"{item.file_path.name}:{item.line_number}"
                    except Exception:
                        location = f"{item.file_path.name}:{item.line_number}"
                else:
                    location = f"{item.file_path}:{item.line_number}"

                if item.item_type == "method":
                    if item.class_name:
                        lines.append(f"  ⚡ {item.class_name}.{item.name} → {location}")
                    else:
                        lines.append(f"  ⚡ {item.name} → {location}")
                    if item.signature:
                        lines.append(f"      {item.signature}")
                elif item.item_type == "class":
                    parent_info = f" ({item.parent_class})" if item.parent_class else ""
                    lines.append(f"  📁 {item.name}{parent_info} → {location}")
                elif item.item_type == "enum":
                    enum_info = f" ({item.enum_base})" if item.enum_base else ""
                    lines.append(f"  🏷️  {item.name}{enum_info} → {location}")
                else:
                    lines.append(f"  ❓ {item.name} → {location}")

            lines.append("")

        # Add pagination info
        if self.total_found > len(self.items) + self.offset:
            remaining = self.total_found - len(self.items) - self.offset
            lines.append(
                f"... {remaining} more results available (use --offset {self.offset + self.limit})"
            )

        return "\n".join(lines)


@dataclass
class SearchResult:
    """Result of a code search operation."""

    query: str
    search_type: str
    package_filter: str | None = None
    matches: list[SearchMatch] = field(default_factory=list)
    search_paths: list[Path] = field(default_factory=list)
    tool_used: str = "python_re"  # 'ripgrep', 'ast-grep', 'python_re'

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "search_type": self.search_type,
            "package_filter": self.package_filter,
            "matches": [m.to_dict() for m in self.matches],
            "search_paths": [str(p) for p in self.search_paths],
            "tool_used": self.tool_used,
        }

    def format_human(self, relative_paths: bool = False) -> str:
        """Format for human-readable output."""
        lines = []
        lines.append(f"Search Results: {self.query}")
        lines.append("=" * (len(self.query) + 16))
        lines.append(f"Search Type: {self.search_type}")
        lines.append(f"Tool Used: {self.tool_used}")

        if self.package_filter:
            lines.append(f"Package Filter: {self.package_filter}")

        lines.append(f"Search Paths: {len(self.search_paths)}")
        for path in self.search_paths:
            lines.append(f"  • {path}")

        if self.matches:
            lines.append(f"\nMatches Found: {len(self.matches)}")
            lines.append("")

            for i, match in enumerate(self.matches, 1):
                # Format file path
                if relative_paths:
                    try:
                        parts = match.file_path.parts
                        site_pkg_idx = -1
                        for idx, part in enumerate(parts):
                            if "site-packages" in part:
                                site_pkg_idx = idx
                                break
                        if site_pkg_idx >= 0 and site_pkg_idx + 1 < len(parts):
                            rel_path = Path(*parts[site_pkg_idx + 1 :])
                            location = f"{rel_path}:{match.line_number}"
                        else:
                            location = f"{match.file_path.name}:{match.line_number}"
                    except Exception:
                        location = f"{match.file_path.name}:{match.line_number}"
                else:
                    location = f"{match.file_path}:{match.line_number}"

                lines.append(f"{i}. {location}")

                # Show context before
                for ctx_line in match.context_before:
                    lines.append(f"   │ {ctx_line}")

                # Show the match line highlighted
                lines.append(f" ➤ │ {match.match_text}")

                # Show context after
                for ctx_line in match.context_after:
                    lines.append(f"   │ {ctx_line}")

                if i < len(self.matches):
                    lines.append("")
        else:
            lines.append(f"\nNo matches found for '{self.query}'")

        return "\n".join(lines)


class ToolDetector:
    """Detects available search tools."""

    @staticmethod
    def has_ripgrep() -> bool:
        """Check if ripgrep is available."""
        return shutil.which("rg") is not None

    @staticmethod
    def has_ast_grep() -> bool:
        """Check if ast-grep is available."""
        return shutil.which("ast-grep") is not None or shutil.which("sg") is not None

    @staticmethod
    def get_ast_grep_cmd() -> str | None:
        """Get the ast-grep command name."""
        if shutil.which("ast-grep"):
            return "ast-grep"
        elif shutil.which("sg"):
            return "sg"
        return None


class CodeSearcher:
    """Searches for code patterns using the best available tools."""

    def __init__(self):
        self.has_ripgrep = ToolDetector.has_ripgrep()
        self.has_ast_grep = ToolDetector.has_ast_grep()
        self.ast_grep_cmd = ToolDetector.get_ast_grep_cmd()

    def search(
        self,
        pattern: str,
        package: str | None = None,
        search_type: str = "regex",
        limit: int = 50,
        offset: int = 0,
        context: int = 2,
        case_insensitive: bool = False,
        comments_only: bool = False,
        strings_only: bool = False,
    ) -> SearchResult:
        """Search for a pattern in code."""
        result = SearchResult(query=pattern, search_type=search_type, package_filter=package)

        # Determine search paths
        search_paths = self._get_search_paths(package)
        result.search_paths = search_paths

        if not search_paths:
            return result

        # Choose the best search method
        search_options = {
            "context": context,
            "case_insensitive": case_insensitive,
            "comments_only": comments_only,
            "strings_only": strings_only,
        }

        if search_type == "ast" and self.has_ast_grep:
            all_matches = self._search_with_ast_grep(pattern, search_paths, search_options)
            result.tool_used = "ast-grep"
        elif search_type == "regex":
            if self.has_ripgrep:
                all_matches = self._search_with_ripgrep(pattern, search_paths, search_options)
                result.tool_used = "ripgrep"
            else:
                # Only fall back to Python RE if ripgrep is not available
                all_matches = self._search_with_python_re(pattern, search_paths, search_options)
                result.tool_used = "python_re"
        else:
            # Default to ripgrep for any unrecognized search type
            if self.has_ripgrep:
                all_matches = self._search_with_ripgrep(pattern, search_paths, search_options)
                result.tool_used = "ripgrep"
            else:
                all_matches = self._search_with_python_re(pattern, search_paths, search_options)
                result.tool_used = "python_re"

        # Apply pagination
        result.matches = all_matches[offset : offset + limit]
        return result

    def find_class(self, classname: str, package: str | None = None) -> SearchResult:
        """Find class definitions."""
        # Use AST search if available, otherwise regex
        if self.has_ast_grep:
            pattern = f"class {classname}"
            return self.search(pattern, package, "ast")
        else:
            pattern = rf"class\s+{re.escape(classname)}\b"
            return self.search(pattern, package, "regex")

    def find_method(
        self, methodname: str, package: str | None = None, classname: str | None = None
    ) -> SearchResult:
        """Find method implementations."""
        if classname and self.has_ast_grep:
            # AST search for method within specific class
            pattern = f"class {classname} {{ def {methodname} }}"
            return self.search(pattern, package, "ast")
        else:
            # Regex search for method definitions
            pattern = rf"def\s+{re.escape(methodname)}\s*\("
            return self.search(pattern, package, "regex")

    def list_methods(
        self,
        package: str,
        limit: int = 50,
        offset: int = 0,
        include_private: bool = False,
        module_filter: str | None = None,
        class_filter: str | None = None,
    ) -> ListResult:
        """List all methods in a package."""
        result = ListResult(
            query_type="methods",
            package_name=package,
            limit=limit,
            offset=offset,
            filters={
                "include_private": include_private,
                "module": module_filter,
                "class": class_filter,
            },
        )

        # Get search paths
        search_paths = self._get_search_paths(package)
        result.search_paths = search_paths

        if not search_paths:
            return result

        # Choose the best method based on available tools
        if self.has_ast_grep:
            all_items = self._list_methods_with_ast_grep(search_paths)
            result.tool_used = "ast-grep"
        elif self.has_ripgrep:
            all_items = self._list_methods_with_ripgrep(search_paths)
            result.tool_used = "ripgrep"
        else:
            all_items = self._list_methods_with_python_re(search_paths)
            result.tool_used = "python_re"

        # Apply filters and pagination
        filtered_items = self._apply_method_filters(
            all_items, include_private, module_filter, class_filter
        )
        result.total_found = len(filtered_items)
        result.items = filtered_items[offset : offset + limit]

        return result

    def list_classes(
        self,
        package: str,
        limit: int = 50,
        offset: int = 0,
        include_private: bool = False,
        module_filter: str | None = None,
        parent_filter: str | None = None,
    ) -> ListResult:
        """List all classes in a package."""
        result = ListResult(
            query_type="classes",
            package_name=package,
            limit=limit,
            offset=offset,
            filters={
                "include_private": include_private,
                "module": module_filter,
                "parent": parent_filter,
            },
        )

        # Get search paths
        search_paths = self._get_search_paths(package)
        result.search_paths = search_paths

        if not search_paths:
            return result

        # Choose the best method based on available tools
        if self.has_ast_grep:
            all_items = self._list_classes_with_ast_grep(search_paths)
            result.tool_used = "ast-grep"
        elif self.has_ripgrep:
            all_items = self._list_classes_with_ripgrep(search_paths)
            result.tool_used = "ripgrep"
        else:
            all_items = self._list_classes_with_python_re(search_paths)
            result.tool_used = "python_re"

        # Apply filters and pagination
        filtered_items = self._apply_class_filters(
            all_items, include_private, module_filter, parent_filter
        )
        result.total_found = len(filtered_items)
        result.items = filtered_items[offset : offset + limit]

        return result

    def list_enums(
        self,
        package: str,
        limit: int = 50,
        offset: int = 0,
        include_private: bool = False,
        module_filter: str | None = None,
        enum_type_filter: str | None = None,
    ) -> ListResult:
        """List all enums in a package."""
        result = ListResult(
            query_type="enums",
            package_name=package,
            limit=limit,
            offset=offset,
            filters={
                "include_private": include_private,
                "module": module_filter,
                "enum_type": enum_type_filter,
            },
        )

        # Get search paths
        search_paths = self._get_search_paths(package)
        result.search_paths = search_paths

        if not search_paths:
            return result

        # Choose the best method based on available tools
        if self.has_ast_grep:
            all_items = self._list_enums_with_ast_grep(search_paths)
            result.tool_used = "ast-grep"
        elif self.has_ripgrep:
            all_items = self._list_enums_with_ripgrep(search_paths)
            result.tool_used = "ripgrep"
        else:
            all_items = self._list_enums_with_python_re(search_paths)
            result.tool_used = "python_re"

        # Apply filters and pagination
        filtered_items = self._apply_enum_filters(
            all_items, include_private, module_filter, enum_type_filter
        )
        result.total_found = len(filtered_items)
        result.items = filtered_items[offset : offset + limit]

        return result

    def _get_search_paths(self, package: str | None = None) -> list[Path]:
        """Get paths to search in."""
        search_paths = []

        if package:
            # Search only in the specified package
            from .packages import PackageFinder

            finder = PackageFinder()
            package_info = finder.find_package(package)
            if package_info.location:
                search_paths.append(package_info.location)
        else:
            # Search in all site-packages
            from .venv import VirtualEnvDetector

            detector = VirtualEnvDetector()
            venv_info = detector.detect()
            search_paths.extend(venv_info.site_packages)

        return [p for p in search_paths if p.exists()]

    def _search_with_ripgrep(
        self, pattern: str, search_paths: list[Path], options: dict[str, Any] | None = None
    ) -> list[SearchMatch]:
        """Search using ripgrep."""
        matches = []
        options = options or {}

        for search_path in search_paths:
            try:
                cmd = [
                    "rg",
                    "--type",
                    "py",
                    "--line-number",
                    "--column",
                    "--no-heading",
                    "--no-ignore",  # Don't honor .gitignore files
                    "--hidden",  # Search hidden files/directories
                ]

                # Add context lines
                context_lines = options.get("context", 2)
                cmd.extend(["--context", str(context_lines)])

                # Add case insensitive flag
                if options.get("case_insensitive", False):
                    cmd.append("--ignore-case")

                # Add comment/string filtering
                if options.get("comments_only", False):
                    # Search for comments (lines starting with # after whitespace)
                    cmd.extend(["--regex", r"^\s*#.*" + pattern])
                elif options.get("strings_only", False):
                    # Search within string literals (simplified - matches content within quotes)
                    cmd.extend(["--regex", r'["\'].*' + pattern + r'.*["\']'])
                else:
                    cmd.append(pattern)

                cmd.append(str(search_path))

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    matches.extend(self._parse_ripgrep_output(result.stdout))

            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return matches

    def _parse_ripgrep_output(self, output: str) -> list[SearchMatch]:
        """Parse ripgrep output into SearchMatch objects."""
        matches = []
        lines = output.strip().split("\n")

        current_match = None
        for line in lines:
            # Parse ripgrep output format: file:line:col:text
            if ":" in line:
                parts = line.split(":", 3)
                if len(parts) >= 3:
                    try:
                        file_path = Path(parts[0])
                        line_num = int(parts[1])

                        # Check if this is a match line (has column number)
                        if len(parts) == 4 and parts[2].isdigit():
                            col = int(parts[2])
                            text = parts[3]

                            current_match = SearchMatch(
                                file_path=file_path,
                                line_number=line_num,
                                column=col,
                                match_text=text,
                            )
                            matches.append(current_match)
                        elif current_match and len(parts) >= 3:
                            # This is a context line
                            text = parts[-1]
                            if line_num < current_match.line_number:
                                current_match.context_before.append(text)
                            elif line_num > current_match.line_number:
                                current_match.context_after.append(text)
                    except ValueError:
                        continue

        return matches

    def _search_with_ast_grep(
        self, pattern: str, search_paths: list[Path], options: dict[str, Any] | None = None
    ) -> list[SearchMatch]:
        """Search using ast-grep."""
        matches = []

        for search_path in search_paths:
            try:
                cmd = [
                    self.ast_grep_cmd,
                    "run",
                    "--pattern",
                    pattern,
                    "--lang",
                    "python",
                    "--json",
                    str(search_path),
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0 and result.stdout.strip():
                    matches.extend(self._parse_ast_grep_output(result.stdout))

            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return matches

    def _parse_ast_grep_output(self, output: str) -> list[SearchMatch]:
        """Parse ast-grep JSON output into SearchMatch objects."""
        matches = []

        try:
            # ast-grep returns a JSON array
            data_list = json.loads(output)
            if isinstance(data_list, list):
                for data in data_list:
                    if isinstance(data, dict):
                        file_path = Path(data["path"])
                        line_num = data["range"]["start"]["line"] + 1  # ast-grep uses 0-based
                        col = data["range"]["start"]["column"]
                        text = data["text"]

                        match = SearchMatch(
                            file_path=file_path, line_number=line_num, column=col, match_text=text
                        )
                        matches.append(match)
        except (json.JSONDecodeError, KeyError):
            pass

        return matches

    def _search_with_python_re(
        self, pattern: str, search_paths: list[Path], options: dict[str, Any] | None = None
    ) -> list[SearchMatch]:
        """Search using Python's re module (fallback)."""
        matches = []
        options = options or {}

        try:
            flags = re.MULTILINE
            if options.get("case_insensitive", False):
                flags |= re.IGNORECASE

            compiled_pattern = re.compile(pattern, flags)
        except re.error:
            return matches

        for search_path in search_paths:
            matches.extend(self._search_path_with_re(compiled_pattern, search_path, options))

        return matches

    def _search_path_with_re(
        self, pattern: re.Pattern, search_path: Path, options: dict[str, Any] | None = None
    ) -> list[SearchMatch]:
        """Search a single path using compiled regex pattern."""
        matches = []

        if search_path.is_file() and search_path.suffix == ".py":
            matches.extend(self._search_file_with_re(pattern, search_path, options))
        elif search_path.is_dir():
            for py_file in search_path.rglob("*.py"):
                matches.extend(self._search_file_with_re(pattern, py_file, options))

        return matches

    def _search_file_with_re(
        self, pattern: re.Pattern, file_path: Path, options: dict[str, Any] | None = None
    ) -> list[SearchMatch]:
        """Search a single file using regex."""
        matches = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                match = pattern.search(line)
                if match:
                    # Get context lines
                    context_before = []
                    context_after = []

                    # Get 2 lines before
                    for i in range(max(0, line_num - 3), line_num - 1):
                        if i < len(lines):
                            context_before.append(lines[i].rstrip())

                    # Get 2 lines after
                    for i in range(line_num, min(len(lines), line_num + 2)):
                        if i < len(lines):
                            context_after.append(lines[i].rstrip())

                    search_match = SearchMatch(
                        file_path=file_path,
                        line_number=line_num,
                        column=match.start(),
                        match_text=line.rstrip(),
                        context_before=context_before,
                        context_after=context_after,
                    )
                    matches.append(search_match)

        except Exception:
            pass

        return matches

    def _apply_method_filters(
        self,
        items: list[ListItem],
        include_private: bool,
        module_filter: str | None,
        class_filter: str | None,
    ) -> list[ListItem]:
        """Apply filters to method list."""
        filtered = []
        for item in items:
            # Skip private methods unless requested
            if not include_private and item.is_private:
                continue

            # Filter by module
            if module_filter and not item.module_name.endswith(module_filter):
                continue

            # Filter by class
            if class_filter and item.class_name != class_filter:
                continue

            filtered.append(item)
        return sorted(filtered, key=lambda x: (x.module_name, x.class_name or "", x.name))

    def _apply_class_filters(
        self,
        items: list[ListItem],
        include_private: bool,
        module_filter: str | None,
        parent_filter: str | None,
    ) -> list[ListItem]:
        """Apply filters to class list."""
        filtered = []
        for item in items:
            # Skip private classes unless requested
            if not include_private and item.is_private:
                continue

            # Filter by module
            if module_filter and not item.module_name.endswith(module_filter):
                continue

            # Filter by parent class
            if parent_filter and item.parent_class != parent_filter:
                continue

            filtered.append(item)
        return sorted(filtered, key=lambda x: (x.module_name, x.name))

    def _apply_enum_filters(
        self,
        items: list[ListItem],
        include_private: bool,
        module_filter: str | None,
        enum_type_filter: str | None,
    ) -> list[ListItem]:
        """Apply filters to enum list."""
        filtered = []
        for item in items:
            # Skip private enums unless requested
            if not include_private and item.is_private:
                continue

            # Filter by module
            if module_filter and not item.module_name.endswith(module_filter):
                continue

            # Filter by enum type
            if enum_type_filter and item.enum_base != enum_type_filter:
                continue

            filtered.append(item)
        return sorted(filtered, key=lambda x: (x.module_name, x.name))

    def _list_methods_with_python_re(self, search_paths: list[Path]) -> list[ListItem]:
        """List methods using Python RE and AST parsing."""
        items = []

        for search_path in search_paths:
            items.extend(self._extract_methods_from_path(search_path))
        return items

    def _list_classes_with_python_re(self, search_paths: list[Path]) -> list[ListItem]:
        """List classes using Python RE and AST parsing."""
        items = []

        for search_path in search_paths:
            items.extend(self._extract_classes_from_path(search_path))
        return items

    def _list_enums_with_python_re(self, search_paths: list[Path]) -> list[ListItem]:
        """List enums using Python RE and AST parsing."""
        items = []

        for search_path in search_paths:
            items.extend(self._extract_enums_from_path(search_path))
        return items

    def _extract_methods_from_path(self, search_path: Path) -> list[ListItem]:
        """Extract methods from a file or directory using AST parsing."""
        items = []

        if search_path.is_file() and search_path.suffix == ".py":
            items.extend(self._extract_methods_from_file(search_path))
        elif search_path.is_dir():
            for py_file in search_path.rglob("*.py"):
                items.extend(self._extract_methods_from_file(py_file))

        return items

    def _extract_classes_from_path(self, search_path: Path) -> list[ListItem]:
        """Extract classes from a file or directory using AST parsing."""
        items = []

        if search_path.is_file() and search_path.suffix == ".py":
            items.extend(self._extract_classes_from_file(search_path))
        elif search_path.is_dir():
            for py_file in search_path.rglob("*.py"):
                items.extend(self._extract_classes_from_file(py_file))

        return items

    def _extract_enums_from_path(self, search_path: Path) -> list[ListItem]:
        """Extract enums from a file or directory using AST parsing."""
        items = []

        if search_path.is_file() and search_path.suffix == ".py":
            items.extend(self._extract_enums_from_file(search_path))
        elif search_path.is_dir():
            for py_file in search_path.rglob("*.py"):
                items.extend(self._extract_enums_from_file(py_file))

        return items

    def _extract_methods_from_file(self, file_path: Path) -> list[ListItem]:
        """Extract methods from a single Python file using AST."""
        import ast

        items = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            module_name = self._get_module_name_from_path(file_path)

            class MethodVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.current_class = None

                def visit_ClassDef(self, node):
                    old_class = self.current_class
                    self.current_class = node.name
                    self.generic_visit(node)
                    self.current_class = old_class

                def visit_FunctionDef(self, node):
                    is_private = node.name.startswith("_")

                    # Build method signature
                    signature = f"def {node.name}("
                    args = []
                    for arg in node.args.args:
                        args.append(arg.arg)
                    signature += ", ".join(args) + ")"

                    item = ListItem(
                        name=node.name,
                        item_type="method",
                        file_path=file_path,
                        line_number=node.lineno,
                        column=node.col_offset,
                        module_name=module_name,
                        class_name=self.current_class,
                        signature=signature,
                        is_private=is_private,
                    )
                    items.append(item)

                def visit_AsyncFunctionDef(self, node):
                    # Handle async methods the same way
                    self.visit_FunctionDef(node)

            visitor = MethodVisitor()
            visitor.visit(tree)

        except Exception:
            pass  # Skip files that can't be parsed

        return items

    def _extract_classes_from_file(self, file_path: Path) -> list[ListItem]:
        """Extract classes from a single Python file using AST."""
        import ast

        items = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            module_name = self._get_module_name_from_path(file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    is_private = node.name.startswith("_")

                    # Get parent class info
                    parent_class = None
                    if node.bases:
                        # Get the first base class name
                        if isinstance(node.bases[0], ast.Name):
                            parent_class = node.bases[0].id
                        elif isinstance(node.bases[0], ast.Attribute):
                            parent_class = node.bases[0].attr

                    item = ListItem(
                        name=node.name,
                        item_type="class",
                        file_path=file_path,
                        line_number=node.lineno,
                        column=node.col_offset,
                        module_name=module_name,
                        parent_class=parent_class,
                        signature=f"class {node.name}",
                        is_private=is_private,
                    )
                    items.append(item)

        except Exception:
            pass  # Skip files that can't be parsed

        return items

    def _extract_enums_from_file(self, file_path: Path) -> list[ListItem]:
        """Extract enums from a single Python file using AST."""
        import ast

        items = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            module_name = self._get_module_name_from_path(file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this class inherits from enum classes
                    enum_base = None
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if base.id in ("Enum", "IntEnum", "Flag", "IntFlag", "StrEnum"):
                                enum_base = base.id
                                break
                        elif isinstance(base, ast.Attribute):
                            if base.attr in ("Enum", "IntEnum", "Flag", "IntFlag", "StrEnum"):
                                enum_base = base.attr
                                break

                    if enum_base:
                        is_private = node.name.startswith("_")

                        item = ListItem(
                            name=node.name,
                            item_type="enum",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            module_name=module_name,
                            enum_base=enum_base,
                            signature=f"class {node.name}({enum_base})",
                            is_private=is_private,
                        )
                        items.append(item)

        except Exception:
            pass  # Skip files that can't be parsed

        return items

    def _get_module_name_from_path(self, file_path: Path) -> str:
        """Convert file path to module name."""
        # Try to infer module name from file path
        parts = file_path.parts

        # Look for site-packages to determine the module root
        module_parts = []
        found_site_packages = False

        for i, part in enumerate(parts):
            if "site-packages" in part:
                found_site_packages = True
                # Take parts after site-packages
                module_parts = list(parts[i + 1 :])
                break

        if not found_site_packages:
            # Fallback: use just the filename
            return file_path.stem

        # Remove .py extension and convert to module name
        if module_parts and module_parts[-1].endswith(".py"):
            module_parts[-1] = module_parts[-1][:-3]

        # Remove __init__
        if module_parts and module_parts[-1] == "__init__":
            module_parts.pop()

        return ".".join(module_parts) if module_parts else file_path.stem

    def _list_methods_with_ripgrep(self, search_paths: list[Path]) -> list[ListItem]:
        """List methods using ripgrep (stub - to be implemented)."""
        # For now, fall back to Python RE
        return self._list_methods_with_python_re(search_paths)

    def _list_classes_with_ripgrep(self, search_paths: list[Path]) -> list[ListItem]:
        """List classes using ripgrep (stub - to be implemented)."""
        # For now, fall back to Python RE
        return self._list_classes_with_python_re(search_paths)

    def _list_enums_with_ripgrep(self, search_paths: list[Path]) -> list[ListItem]:
        """List enums using ripgrep (stub - to be implemented)."""
        # For now, fall back to Python RE
        return self._list_enums_with_python_re(search_paths)

    def _list_methods_with_ast_grep(self, search_paths: list[Path]) -> list[ListItem]:
        """List methods using ast-grep with AST patterns."""
        items = []

        # Collect all Python files from search paths
        python_files = []
        for search_path in search_paths:
            if search_path.is_file() and search_path.suffix == ".py":
                python_files.append(search_path)
            elif search_path.is_dir():
                python_files.extend(search_path.rglob("*.py"))

        if not python_files:
            return items

        try:
            # Use AST pattern to find all function definitions
            # ast-grep works better with explicit file lists rather than directories
            cmd = [
                self.ast_grep_cmd,
                "run",
                "--pattern",
                "def $METHOD($$$): $$$",
                "--lang",
                "python",
                "--json",
            ] + [str(f) for f in python_files]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # Increased timeout for multiple files
            )

            if result.returncode == 0 and result.stdout.strip():
                matches = self._parse_ast_grep_json_for_methods(result.stdout, None)
                items.extend(matches)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fall back to Python RE if ast-grep fails
            items.extend(self._list_methods_with_python_re(search_paths))

        return items

    def _parse_ast_grep_json_for_methods(
        self, output: str, base_path: Path | None
    ) -> list[ListItem]:
        """Parse ast-grep JSON output for method matches."""
        import json

        items = []

        try:
            matches = json.loads(output)
            if not isinstance(matches, list):
                return items

            for match in matches:
                if not isinstance(match, dict):
                    continue

                file_path = Path(match.get("file", ""))
                # File paths from ast-grep should already be absolute when we pass explicit files
                if not file_path.is_absolute() and base_path:
                    file_path = base_path / file_path

                # Extract method name from meta variables
                meta_vars = match.get("metaVariables", {}).get("single", {})
                method_name = meta_vars.get("METHOD", {}).get("text", "")

                if not method_name:
                    continue

                # Get position info
                range_info = match.get("range", {})
                start_info = range_info.get("start", {})
                line_num = start_info.get("line", 0) + 1  # ast-grep uses 0-based line numbers
                column = start_info.get("column", 0)

                # Get module name
                module_name = self._get_module_name_from_path(file_path)

                # Determine if this is a class method by checking the surrounding context
                # For now, we'll use a simple heuristic - check if there's indentation
                is_private = method_name.startswith("_")

                # Try to extract more context from the matched text
                matched_text = match.get("text", "")
                class_name = None
                signature = (
                    matched_text.split("\n")[0].strip() if matched_text else f"def {method_name}()"
                )

                # For class methods, we'd need a more complex AST pattern or additional parsing
                # This is a limitation we'll address in a future iteration

                item = ListItem(
                    name=method_name,
                    item_type="method",
                    file_path=file_path,
                    line_number=line_num,
                    column=column,
                    module_name=module_name,
                    class_name=class_name,
                    signature=signature,
                    is_private=is_private,
                )
                items.append(item)

        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return items

    def _list_classes_with_ast_grep(self, search_paths: list[Path]) -> list[ListItem]:
        """List classes using ast-grep with AST patterns."""
        items = []

        # Collect all Python files from search paths
        python_files = []
        for search_path in search_paths:
            if search_path.is_file() and search_path.suffix == ".py":
                python_files.append(search_path)
            elif search_path.is_dir():
                python_files.extend(search_path.rglob("*.py"))

        if not python_files:
            return items

        try:
            # Search for classes with and without inheritance in one pattern
            # This pattern should match both "class Name:" and "class Name(Parent):"
            cmd = [
                self.ast_grep_cmd,
                "run",
                "--pattern",
                "class $NAME: $$$",
                "--lang",
                "python",
                "--json",
            ] + [str(f) for f in python_files]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and result.stdout.strip():
                matches = self._parse_ast_grep_json_for_classes(result.stdout, None)
                items.extend(matches)

            # Also search explicitly for classes with inheritance
            cmd_inherit = [
                self.ast_grep_cmd,
                "run",
                "--pattern",
                "class $NAME($PARENT): $$$",
                "--lang",
                "python",
                "--json",
            ] + [str(f) for f in python_files]

            result_inherit = subprocess.run(cmd_inherit, capture_output=True, text=True, timeout=60)

            if result_inherit.returncode == 0 and result_inherit.stdout.strip():
                inherit_matches = self._parse_ast_grep_json_for_classes(result_inherit.stdout, None)
                items.extend(inherit_matches)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fall back to Python RE if ast-grep fails
            items.extend(self._list_classes_with_python_re(search_paths))

        # Remove duplicates (classes found in both patterns)
        unique_items = []
        seen_classes = set()
        for item in items:
            key = (str(item.file_path), item.line_number, item.name)
            if key not in seen_classes:
                seen_classes.add(key)
                unique_items.append(item)

        return unique_items

    def _parse_ast_grep_json_for_classes(
        self, output: str, base_path: Path | None
    ) -> list[ListItem]:
        """Parse ast-grep JSON output for class matches."""
        import json

        items = []

        try:
            matches = json.loads(output)
            if not isinstance(matches, list):
                return items

            for match in matches:
                if not isinstance(match, dict):
                    continue

                file_path = Path(match.get("file", ""))
                if not file_path.is_absolute():
                    file_path = base_path / file_path

                # Extract class name from meta variables
                meta_vars = match.get("metaVariables", {}).get("single", {})
                class_name = meta_vars.get("NAME", {}).get("text", "")

                if not class_name:
                    continue

                # Extract parent class if available
                parent_class = meta_vars.get("PARENT", {}).get("text", "") or None

                # Get position info
                range_info = match.get("range", {})
                start_info = range_info.get("start", {})
                line_num = start_info.get("line", 0) + 1  # ast-grep uses 0-based line numbers
                column = start_info.get("column", 0)

                # Get module name
                module_name = self._get_module_name_from_path(file_path)

                is_private = class_name.startswith("_")

                # Build signature
                if parent_class:
                    signature = f"class {class_name}({parent_class})"
                else:
                    signature = f"class {class_name}"

                item = ListItem(
                    name=class_name,
                    item_type="class",
                    file_path=file_path,
                    line_number=line_num,
                    column=column,
                    module_name=module_name,
                    parent_class=parent_class,
                    signature=signature,
                    is_private=is_private,
                )
                items.append(item)

        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return items

    def _list_enums_with_ast_grep(self, search_paths: list[Path]) -> list[ListItem]:
        """List enums using ast-grep (stub - to be implemented)."""
        # For now, fall back to Python RE
        return self._list_enums_with_python_re(search_paths)

"""Simplified integration tests for documentation search functionality.

Tests with real packages only - no mocking.
"""

from pathlib import Path

import pytest

from pyenvsearch.core.docs import DocumentationFile, DocumentationResult, DocumentationSearcher


@pytest.fixture
def searcher():
    """Create a DocumentationSearcher instance."""
    return DocumentationSearcher()


class TestDocumentationSearch:
    """Test documentation search with real packages."""

    def test_find_docs_for_json_module(self, searcher):
        """Test finding docs for json standard library module."""
        result = searcher.find_docs("json")

        assert isinstance(result, DocumentationResult)
        assert result.package_name == "json"
        assert isinstance(result.found_files, list)
        assert isinstance(result.search_locations, list)

    def test_find_docs_for_nonexistent_package(self, searcher):
        """Test documentation search for non-existent package."""
        result = searcher.find_docs("nonexistent_package_12345")

        assert isinstance(result, DocumentationResult)
        assert result.package_name == "nonexistent_package_12345"
        assert result.package_path is None
        assert len(result.found_files) == 0

    def test_find_docs_for_pathlib(self, searcher):
        """Test documentation search for pathlib module."""
        result = searcher.find_docs("pathlib")

        assert isinstance(result, DocumentationResult)
        assert result.package_name == "pathlib"
        # Should not crash regardless of what's found

    def test_find_docs_for_pytest_if_available(self, searcher):
        """Test documentation search for pytest if available."""
        result = searcher.find_docs("pytest")

        assert isinstance(result, DocumentationResult)
        assert result.package_name == "pytest"

        # If pytest package is found, might have documentation
        if result.package_path:
            print(f"Found pytest docs: {len(result.found_files)} files")


class TestDocumentationFile:
    """Test DocumentationFile data model."""

    def test_documentation_file_creation(self):
        """Test DocumentationFile creation and properties."""
        doc_file = DocumentationFile(
            path=Path("/test/README.md"),
            file_type="readme",
            size=1024,
            content_preview="Sample README content",
        )

        assert doc_file.path == Path("/test/README.md")
        assert doc_file.file_type == "readme"
        assert doc_file.size == 1024
        assert doc_file.content_preview == "Sample README content"

    def test_documentation_file_to_dict(self):
        """Test DocumentationFile serialization."""
        doc_file = DocumentationFile(
            path=Path("/test/llms.txt"),
            file_type="llms.txt",
            size=512,
            content_preview="LLM documentation",
        )

        result = doc_file.to_dict()

        assert isinstance(result, dict)
        assert result["path"] == "/test/llms.txt"
        assert result["file_type"] == "llms.txt"
        assert result["size"] == 512
        assert result["content_preview"] == "LLM documentation"


class TestDocumentationResult:
    """Test DocumentationResult data model."""

    def test_documentation_result_creation(self):
        """Test DocumentationResult creation."""
        docs = [
            DocumentationFile(
                path=Path("/test/README.md"),
                file_type="readme",
                size=1024,
                content_preview="README content",
            )
        ]

        result = DocumentationResult(
            package_name="test_package",
            package_path=Path("/test"),
            found_files=docs,
            search_locations=[Path("/test")],
        )

        assert result.package_name == "test_package"
        assert result.package_path == Path("/test")
        assert len(result.found_files) == 1
        assert len(result.search_locations) == 1

    def test_documentation_result_to_dict(self):
        """Test DocumentationResult serialization."""
        docs = [
            DocumentationFile(
                path=Path("/test/README.md"),
                file_type="readme",
                size=1024,
                content_preview="Content",
            )
        ]

        result = DocumentationResult(
            package_name="test_package",
            package_path=Path("/test"),
            found_files=docs,
            search_locations=[Path("/test")],
        )

        dict_result = result.to_dict()

        assert isinstance(dict_result, dict)
        assert dict_result["package_name"] == "test_package"
        assert dict_result["package_path"] == "/test"
        assert len(dict_result["found_files"]) == 1
        assert len(dict_result["search_locations"]) == 1

    def test_documentation_result_format_human(self):
        """Test DocumentationResult human formatting."""
        docs = [
            DocumentationFile(
                path=Path("/test/README.md"),
                file_type="readme",
                size=1024,
                content_preview="Content",
            )
        ]

        result = DocumentationResult(
            package_name="test_package",
            package_path=Path("/test"),
            found_files=docs,
            search_locations=[Path("/test")],
        )

        formatted = result.format_human()

        assert isinstance(formatted, str)
        assert "test_package" in formatted
        # Should show some information about the documentation

    def test_documentation_result_empty(self):
        """Test DocumentationResult with no files found."""
        result = DocumentationResult(
            package_name="empty_package", package_path=None, found_files=[], search_locations=[]
        )

        formatted = result.format_human()

        assert isinstance(formatted, str)
        assert "empty_package" in formatted


class TestDocumentationSearchConstants:
    """Test DocumentationSearcher constants and configuration."""

    def test_searcher_has_constants(self, searcher):
        """Test that searcher has expected constants."""
        assert hasattr(searcher, "LLM_DOC_FILES")
        assert hasattr(searcher, "README_PATTERNS")
        assert hasattr(searcher, "DOC_DIR_NAMES")

        # Should be lists or similar containers
        assert isinstance(searcher.LLM_DOC_FILES, list | tuple)
        assert isinstance(searcher.README_PATTERNS, list | tuple)
        assert isinstance(searcher.DOC_DIR_NAMES, list | tuple)

        # Should have expected values
        assert "llms.txt" in searcher.LLM_DOC_FILES or "ai.txt" in searcher.LLM_DOC_FILES
        assert any("readme" in pattern.lower() for pattern in searcher.README_PATTERNS)


class TestErrorHandling:
    """Test error handling in documentation search."""

    def test_invalid_package_name(self, searcher):
        """Test handling of invalid package names."""
        result = searcher.find_docs("")

        # Should handle gracefully
        assert isinstance(result, DocumentationResult)
        assert result.package_name == ""

    def test_unicode_package_name(self, searcher):
        """Test handling of unicode package names."""
        result = searcher.find_docs("测试包")

        # Should handle gracefully
        assert isinstance(result, DocumentationResult)
        assert result.package_name == "测试包"

    def test_very_long_package_name(self, searcher):
        """Test handling of very long package names."""
        long_name = "a" * 1000
        result = searcher.find_docs(long_name)

        # Should handle gracefully
        assert isinstance(result, DocumentationResult)
        assert result.package_name == long_name

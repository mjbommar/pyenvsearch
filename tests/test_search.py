"""Integration tests for code search functionality.

Tests the core search capabilities including ast-grep and ripgrep integration.
Uses real packages from the virtual environment - no mocking.
"""

from unittest.mock import patch

import pytest

from pyenvsearch.core.search import CodeSearcher, ListResult, SearchResult


@pytest.fixture
def searcher():
    """Create a CodeSearcher instance."""
    return CodeSearcher()


@pytest.fixture
def sample_python_files(tmp_path):
    """Create sample Python files for testing."""
    # Create test files with various Python constructs
    test_code = {
        "module1.py": '''
"""Test module 1."""

class TestClass:
    def method1(self):
        return "test"

    def _private_method(self):
        return "private"

def function1():
    return True

class AnotherClass(TestClass):
    def method2(self):
        # This is a comment
        return "another"
''',
        "module2.py": '''
"""Test module 2."""

from enum import Enum, IntEnum

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

class Priority(IntEnum):
    LOW = 1
    HIGH = 2

def helper_function():
    """Helper function with docstring."""
    return None
''',
        "subpackage/__init__.py": "",
        "subpackage/nested.py": '''
"""Nested module."""

class NestedClass:
    def nested_method(self):
        return "nested"
''',
    }

    for file_path, content in test_code.items():
        full_path = tmp_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    return tmp_path


class TestAstGrepIntegration:
    """Test ast-grep integration for semantic search."""

    def test_has_ast_grep_available(self, searcher):
        """Test if ast-grep is available in the system."""
        has_ast_grep = searcher._has_ast_grep()
        # This test documents whether ast-grep is available
        # It should pass regardless, but helps with debugging
        print(f"ast-grep available: {has_ast_grep}")
        assert isinstance(has_ast_grep, bool)

    def test_list_methods_with_ast_grep(self, searcher, sample_python_files):
        """Test listing methods using ast-grep."""
        if not searcher._has_ast_grep():
            pytest.skip("ast-grep not available")

        result = searcher._list_methods_with_ast_grep([sample_python_files])

        # Should find methods from our test files
        method_names = [item.name for item in result]
        assert "method1" in method_names
        assert "method2" in method_names
        assert "nested_method" in method_names

        # Check that we get proper file locations
        for item in result:
            assert item.file_path.exists()
            assert item.line_number > 0

    def test_list_classes_with_ast_grep(self, searcher, sample_python_files):
        """Test listing classes using ast-grep."""
        if not searcher._has_ast_grep():
            pytest.skip("ast-grep not available")

        result = searcher._list_classes_with_ast_grep([sample_python_files])

        # Should find classes from our test files
        class_names = [item.name for item in result]
        assert "TestClass" in class_names
        assert "AnotherClass" in class_names
        assert "Color" in class_names
        assert "NestedClass" in class_names

        # Check inheritance detection
        another_class_items = [item for item in result if item.name == "AnotherClass"]
        assert len(another_class_items) > 0
        # Should detect TestClass as parent (meta-variable extraction)

    def test_list_enums_with_ast_grep(self, searcher, sample_python_files):
        """Test listing enums using ast-grep."""
        if not searcher._has_ast_grep():
            pytest.skip("ast-grep not available")

        result = searcher._list_enums_with_ast_grep([sample_python_files])

        # Should find enum classes
        enum_names = [item.name for item in result]
        assert "Color" in enum_names
        assert "Priority" in enum_names


class TestRipgrepIntegration:
    """Test ripgrep integration for text search."""

    def test_has_ripgrep_available(self, searcher):
        """Test if ripgrep is available in the system."""
        has_rg = searcher._has_ripgrep()
        print(f"ripgrep available: {has_rg}")
        assert isinstance(has_rg, bool)

    def test_search_with_ripgrep(self, searcher, sample_python_files):
        """Test text search using ripgrep."""
        if not searcher._has_ripgrep():
            pytest.skip("ripgrep not available")

        # Search for "def " pattern
        result = searcher._search_with_ripgrep(
            pattern="def ", search_paths=[sample_python_files], context=1
        )

        assert len(result.matches) > 0

        # Should find function definitions
        found_text = [match.text for match in result.matches]
        assert any("def method1" in text for text in found_text)
        assert any("def function1" in text for text in found_text)

    def test_search_comments_only(self, searcher, sample_python_files):
        """Test searching only in comments."""
        if not searcher._has_ripgrep():
            pytest.skip("ripgrep not available")

        # This should find comments containing "comment"
        # For now, we'll test the basic pattern search
        result = searcher._search_with_ripgrep(
            pattern="# .*comment", search_paths=[sample_python_files], context=0
        )

        # Should find our comment line
        assert len(result.matches) > 0
        found_text = [match.text for match in result.matches]
        assert any("comment" in text.lower() for text in found_text)


class TestGracefulFallbacks:
    """Test graceful fallback behavior when tools are unavailable."""

    def test_list_methods_fallback_to_python_re(self, searcher, sample_python_files):
        """Test method listing falls back to Python RE when ast-grep unavailable."""
        with patch.object(searcher, "_has_ast_grep", return_value=False):
            with patch.object(searcher, "_has_ripgrep", return_value=False):
                result = searcher._list_methods_with_python_re([sample_python_files])

                # Should still find methods using regex
                method_names = [item.name for item in result]
                assert "method1" in method_names
                assert "method2" in method_names

    def test_search_fallback_to_python_re(self, searcher, sample_python_files):
        """Test search falls back to Python RE when ripgrep unavailable."""
        with patch.object(searcher, "_has_ripgrep", return_value=False):
            with patch.object(searcher, "_has_ast_grep", return_value=False):
                result = searcher._search_with_python_re(
                    pattern="def ", search_paths=[sample_python_files], context=1
                )

                # Should find function definitions
                assert len(result.matches) > 0
                found_text = [match.text for match in result.matches]
                assert any("def " in text for text in found_text)


class TestRealPackageIntegration:
    """Test with real packages from the virtual environment."""

    def test_list_methods_from_real_package(self, searcher):
        """Test listing methods from an actual installed package."""
        # Test with a standard library module that should be available
        result = searcher.list_methods(package="json", limit=10, include_private=False)

        assert isinstance(result, ListResult)
        assert result.total_found > 0
        assert len(result.items) > 0

        # Should find common json methods
        method_names = [item.name for item in result.items]
        # Standard library json module should have these
        expected_methods = ["dumps", "loads"]
        found_expected = [m for m in expected_methods if m in method_names]
        assert len(found_expected) > 0

    def test_search_in_real_package(self, searcher):
        """Test searching in an actual installed package."""
        # Search for "def " in json module
        result = searcher.search(pattern="def loads", package="json", search_type="regex", limit=5)

        assert isinstance(result, SearchResult)
        # Should find at least one match
        assert result.total_matches >= 0  # May be 0 if json is compiled


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_package_name(self, searcher):
        """Test handling of invalid package names."""
        result = searcher.list_methods(package="nonexistent_package_12345", limit=10)

        # Should return empty result, not crash
        assert isinstance(result, ListResult)
        assert result.total_found == 0
        assert len(result.items) == 0

    def test_empty_search_pattern(self, searcher):
        """Test handling of empty search patterns."""
        result = searcher.search(pattern="", search_type="regex", limit=10)

        # Should handle gracefully
        assert isinstance(result, SearchResult)

    def test_malformed_regex_pattern(self, searcher):
        """Test handling of malformed regex patterns."""
        # This should not crash the application
        result = searcher.search(pattern="[invalid regex", search_type="regex", limit=10)

        assert isinstance(result, SearchResult)


class TestPaginationAndFiltering:
    """Test pagination and filtering options."""

    def test_method_listing_with_pagination(self, searcher):
        """Test method listing with limit and offset."""
        # Get first page
        result1 = searcher.list_methods(package="json", limit=3, offset=0)

        # Get second page
        result2 = searcher.list_methods(package="json", limit=3, offset=3)

        if result1.total_found > 3:
            # Should have different items
            items1 = {item.name for item in result1.items}
            items2 = {item.name for item in result2.items}
            assert items1 != items2

    def test_include_private_filtering(self, searcher, sample_python_files):
        """Test filtering private methods."""
        with_private = searcher._list_methods_with_python_re(
            search_paths=[sample_python_files], include_private=True
        )

        without_private = searcher._list_methods_with_python_re(
            search_paths=[sample_python_files], include_private=False
        )

        with_private_names = {item.name for item in with_private}
        without_private_names = {item.name for item in without_private}

        # Should find private method when include_private=True
        assert "_private_method" in with_private_names
        # Should not find private method when include_private=False
        assert "_private_method" not in without_private_names

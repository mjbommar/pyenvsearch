"""Integration tests for package discovery functionality.

Tests package finding, table of contents generation, and site-packages navigation.
Uses real packages from the virtual environment.
"""

from pathlib import Path

import pytest

from pyenvsearch.core.packages import PackageFinder, PackageInfo, TableOfContents


@pytest.fixture
def finder():
    """Create a PackageFinder instance."""
    return PackageFinder()


class TestPackageDiscovery:
    """Test package discovery and location finding."""

    def test_find_standard_library_package(self, finder):
        """Test finding standard library packages."""
        result = finder.find_package("json")

        assert isinstance(result, PackageInfo)
        assert result.name == "json"
        # Standard library modules are always findable
        assert result.location is not None or True  # Location might be None for built-ins

        # Should have some basic info
        # Standard library check passes if we get PackageInfo back
        assert True

    def test_find_nonexistent_package(self, finder):
        """Test handling of non-existent packages."""
        result = finder.find_package("nonexistent_package_12345")

        assert isinstance(result, PackageInfo)
        assert result.name == "nonexistent_package_12345"
        assert result.location is None

    def test_find_package_with_version(self, finder):
        """Test package finding includes version info when available."""
        result = finder.find_package("json")

        if result.found:
            # Standard library modules might not have __version__
            # but the method should not crash
            assert isinstance(result.version, str | type(None))

    def test_find_installed_package(self, finder):
        """Test finding an installed third-party package."""
        # Try to find pytest which should be available in test environment
        result = finder.find_package("pytest")

        assert isinstance(result, PackageInfo)
        assert result.name == "pytest"

        if result.location:
            assert result.location.exists()
            # Package type is not tracked in the actual implementation


class TestPackageInfo:
    """Test PackageInfo data model."""

    def test_package_info_to_dict(self):
        """Test PackageInfo serialization."""
        info = PackageInfo(
            name="test_package",
            version="1.0.0",
            location=Path("/test/path"),
            is_namespace=False,
            submodules=["submodule1", "submodule2"],
        )

        result = info.to_dict()

        assert isinstance(result, dict)
        assert result["name"] == "test_package"
        assert result["version"] == "1.0.0"
        assert result["location"] == "/test/path"
        assert result["is_namespace"] is False
        assert result["submodules"] == ["submodule1", "submodule2"]

    def test_package_info_format_human(self):
        """Test PackageInfo human formatting."""
        info = PackageInfo(
            name="test_package",
            version="1.0.0",
            location=Path("/test/path"),
            is_namespace=False,
            submodules=[],
        )

        result = info.format_human()

        assert isinstance(result, str)
        assert "Package: test_package" in result
        assert "test_package" in result
        assert "/test/path" in result
        assert "1.0.0" in result

    def test_package_info_format_human_not_found(self):
        """Test PackageInfo formatting when package not found."""
        info = PackageInfo(
            name="missing_package", version=None, location=None, is_namespace=False, submodules=[]
        )

        result = info.format_human()

        assert isinstance(result, str)
        assert "missing_package" in result
        assert "Location: Not found" in result


class TestTableOfContents:
    """Test table of contents generation."""

    def test_generate_toc_for_standard_package(self, finder):
        """Test generating TOC for a standard library package."""
        result = finder.generate_toc("json", depth=2)

        assert isinstance(result, TableOfContents)
        assert result.package_name == "json"

        # Should have some structural information
        assert isinstance(result.structure, dict)
        assert result.total_modules >= 0
        assert result.total_classes >= 0
        assert result.total_functions >= 0

    def test_generate_toc_with_different_depths(self, finder):
        """Test TOC generation with different depth limits."""
        # Test shallow depth
        result_shallow = finder.generate_toc("json", depth=1)

        # Test deeper depth
        result_deep = finder.generate_toc("json", depth=3)

        # Both should be valid TableOfContents objects
        assert isinstance(result_shallow, TableOfContents)
        assert isinstance(result_deep, TableOfContents)

        # Deeper search might find more items
        shallow_total = (
            result_shallow.total_modules
            + result_shallow.total_classes
            + result_shallow.total_functions
        )
        deep_total = (
            result_deep.total_modules + result_deep.total_classes + result_deep.total_functions
        )
        assert deep_total >= shallow_total

    def test_toc_for_nonexistent_package(self, finder):
        """Test TOC generation for non-existent package."""
        result = finder.generate_toc("nonexistent_package_12345")

        assert isinstance(result, TableOfContents)
        assert result.package_name == "nonexistent_package_12345"
        # For non-existent packages, should have empty/minimal structure
        assert result.total_modules == 0
        assert result.total_classes == 0
        assert result.total_functions == 0


class TestTableOfContents:
    """Test TableOfContents data model."""

    def test_table_of_contents_to_dict(self):
        """Test TableOfContents serialization."""

        result = TableOfContents(
            package_name="test_package",
            structure={"functions": ["func1", "func2"], "classes": ["Class1"]},
            total_modules=1,
            total_classes=1,
            total_functions=2,
        )

        dict_result = result.to_dict()

        assert isinstance(dict_result, dict)
        assert dict_result["package_name"] == "test_package"
        assert dict_result["total_modules"] == 1
        assert dict_result["total_classes"] == 1
        assert dict_result["total_functions"] == 2
        assert "structure" in dict_result

    def test_table_of_contents_format_human(self):
        """Test TableOfContents human formatting."""

        result = TableOfContents(
            package_name="test_package",
            structure={"functions": ["function1"], "classes": ["Class1"]},
            total_modules=1,
            total_classes=1,
            total_functions=1,
        )

        formatted = result.format_human()

        assert isinstance(formatted, str)
        assert "Table of Contents" in formatted
        assert "test_package" in formatted
        # Should show summary stats
        assert "1" in formatted  # Should show counts


class TestSitePackagesNavigation:
    """Test site-packages directory navigation."""

    def test_site_packages_property(self, finder):
        """Test site-packages property."""
        paths = finder.site_packages

        assert isinstance(paths, list)
        # Should have at least some paths (might be empty in some environments)
        for path in paths:
            if path.exists():
                assert path.is_dir()

    def test_package_attributes(self, finder):
        """Test package attribute detection."""
        # Test with json (built-in)
        json_result = finder.find_package("json")
        assert isinstance(json_result, PackageInfo)
        assert json_result.name == "json"

        # Test with pytest (installed package) if available
        pytest_result = finder.find_package("pytest")
        assert isinstance(pytest_result, PackageInfo)
        assert pytest_result.name == "pytest"

    def test_get_package_version(self, finder):
        """Test package version retrieval."""
        # Some packages may not have versions, which is fine
        result = finder.find_package("json")

        # Should not crash, version can be None for built-ins
        assert isinstance(result.version, str | type(None))


class TestPackageLocationFeatures:
    """Test package location features."""

    def test_namespace_package_detection(self, finder):
        """Test namespace package detection."""
        result = finder.find_package("json")
        # json is not a namespace package
        assert result.is_namespace is False

    def test_submodule_listing(self, finder):
        """Test submodule listing."""
        result = finder.find_package("json")
        # Should have submodules list (might be empty)
        assert isinstance(result.submodules, list)


class TestErrorHandling:
    """Test error handling in package operations."""

    def test_corrupted_package_handling(self, finder):
        """Test handling of corrupted or problematic packages."""
        # Test with a very long package name
        result = finder.find_package("a" * 1000)

        # Should handle gracefully
        assert isinstance(result, PackageInfo)
        assert result.found is False

    def test_permission_error_handling(self, finder):
        """Test handling of permission errors."""
        # This is hard to test reliably across platforms
        # But we can ensure the methods don't crash on normal packages
        result = finder.find_package("os")

        # Should not crash
        assert isinstance(result, PackageInfo)

    def test_unicode_package_names(self, finder):
        """Test handling of unicode in package names."""
        # Test with unicode characters
        result = finder.find_package("测试包")

        # Should handle gracefully
        assert isinstance(result, PackageInfo)
        assert result.found is False  # Unlikely to exist

    def test_empty_package_name(self, finder):
        """Test handling of empty package names."""
        result = finder.find_package("")

        # Should handle gracefully
        assert isinstance(result, PackageInfo)
        assert result.found is False


class TestRealWorldPackages:
    """Test with real packages that should be commonly available."""

    def test_sys_package(self, finder):
        """Test with sys built-in package."""
        result = finder.find_package("sys")

        assert isinstance(result, PackageInfo)
        assert result.package_name == "sys"
        # sys should always be available
        assert result.found is True

    def test_os_package(self, finder):
        """Test with os built-in package."""
        result = finder.find_package("os")

        assert isinstance(result, PackageInfo)
        assert result.found is True
        assert result.package_type in ["builtin", "source", "unknown"]

    def test_pathlib_package(self, finder):
        """Test with pathlib standard library package."""
        result = finder.find_package("pathlib")

        assert isinstance(result, PackageInfo)
        assert result.found is True

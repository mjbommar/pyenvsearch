"""Integration tests for CLI functionality.

Tests all CLI commands with real packages and options.
Uses subprocess to test actual command-line usage.
"""

import json
import subprocess
import sys

import pytest


@pytest.fixture
def cli_command():
    """Base command for running pyenvsearch CLI."""
    return [sys.executable, "-m", "pyenvsearch"]


class TestCLICommands:
    """Test all CLI commands with real execution."""

    def test_help_command(self, cli_command):
        """Test that help command works."""
        result = subprocess.run(cli_command + ["--help"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "pyenvsearch" in result.stdout
        assert "Available commands" in result.stdout

    def test_version_command(self, cli_command):
        """Test version command."""
        result = subprocess.run(cli_command + ["--version"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_venv_command(self, cli_command):
        """Test venv command."""
        result = subprocess.run(cli_command + ["venv"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Virtual Environment Information" in result.stdout
        assert "Python Version" in result.stdout

    def test_venv_command_json(self, cli_command):
        """Test venv command with JSON output."""
        result = subprocess.run(cli_command + ["venv", "--json"], capture_output=True, text=True)

        assert result.returncode == 0

        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "python_version" in data
        assert "python_executable" in data
        assert "env_type" in data

    def test_find_command(self, cli_command):
        """Test find command with a real package."""
        result = subprocess.run(cli_command + ["find", "json"], capture_output=True, text=True)

        assert result.returncode == 0
        # Should find the json module
        assert "json" in result.stdout.lower()

    def test_find_command_json(self, cli_command):
        """Test find command with JSON output."""
        result = subprocess.run(
            cli_command + ["find", "json", "--json"], capture_output=True, text=True
        )

        assert result.returncode == 0

        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "name" in data
        assert data["name"] == "json"

    def test_search_command(self, cli_command):
        """Test search command."""
        result = subprocess.run(
            cli_command + ["search", "def loads", "--limit", "3"],
            capture_output=True,
            text=True,
            timeout=30,  # Generous timeout for search
        )

        # Should not crash (return code 0 or 1 is acceptable)
        assert result.returncode in [0, 1]

        if result.returncode == 0:
            # If successful, should have search results format
            assert "Search Results" in result.stdout or "Total Matches" in result.stdout

    def test_search_command_with_package(self, cli_command):
        """Test search command limited to specific package."""
        result = subprocess.run(
            cli_command + ["search", "def", "--package", "json", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not crash
        assert result.returncode in [0, 1]

    def test_search_command_ast_type(self, cli_command):
        """Test search command with AST type."""
        result = subprocess.run(
            cli_command + ["search", "def $METHOD($$$): $$$", "--type", "ast", "--limit", "3"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not crash regardless of ast-grep availability
        assert result.returncode in [0, 1]

    def test_list_methods_command(self, cli_command):
        """Test list-methods command."""
        result = subprocess.run(
            cli_command + ["list-methods", "json", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Methods Found" in result.stdout or "Total Found" in result.stdout

    def test_list_methods_command_json(self, cli_command):
        """Test list-methods command with JSON output."""
        result = subprocess.run(
            cli_command + ["list-methods", "json", "--limit", "3", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "total_found" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_classes_command(self, cli_command):
        """Test list-classes command."""
        result = subprocess.run(
            cli_command + ["list-classes", "json", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Classes Found" in result.stdout or "Total Found" in result.stdout

    def test_list_classes_command_json(self, cli_command):
        """Test list-classes command with JSON output."""
        result = subprocess.run(
            cli_command + ["list-classes", "json", "--limit", "3", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "total_found" in data
        assert "items" in data

    def test_list_enums_command(self, cli_command):
        """Test list-enums command."""
        result = subprocess.run(
            cli_command + ["list-enums", "enum", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # Should show enum results or indicate none found
        assert (
            "Enums Found" in result.stdout or "Total Found" in result.stdout or "0" in result.stdout
        )

    def test_class_command(self, cli_command):
        """Test class command to find specific class."""
        result = subprocess.run(
            cli_command + ["class", "JSONDecodeError"], capture_output=True, text=True, timeout=30
        )

        # Should not crash
        assert result.returncode in [0, 1]

    def test_method_command(self, cli_command):
        """Test method command to find specific method."""
        result = subprocess.run(
            cli_command + ["method", "loads"], capture_output=True, text=True, timeout=30
        )

        # Should not crash
        assert result.returncode in [0, 1]

    def test_toc_command(self, cli_command):
        """Test table of contents command."""
        result = subprocess.run(
            cli_command + ["toc", "json", "--depth", "2"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # Should generate table of contents
        assert "Table of Contents" in result.stdout or "json" in result.stdout


class TestCLIOptions:
    """Test CLI command options and flags."""

    def test_relative_paths_option(self, cli_command):
        """Test --relative-paths option."""
        result = subprocess.run(
            cli_command + ["list-methods", "json", "--limit", "3", "--relative-paths"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        # Should not show full absolute paths like /home/user/.venv/...
        # Instead should show relative paths from site-packages
        lines = result.stdout.split("\n")
        path_lines = [line for line in lines if "/" in line and "json" in line]

        if path_lines:
            # Check that paths don't start with full system paths
            for line in path_lines:
                assert not any(
                    line.strip().startswith(prefix) for prefix in ["/home/", "/usr/", "/opt/"]
                )

    def test_include_private_option(self, cli_command):
        """Test --include-private option."""
        # Test without private methods
        result1 = subprocess.run(
            cli_command + ["list-methods", "json", "--limit", "10"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Test with private methods
        result2 = subprocess.run(
            cli_command + ["list-methods", "json", "--limit", "10", "--include-private"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result1.returncode == 0
        assert result2.returncode == 0

        # With private should potentially have more results or same
        # (depending on whether json module has private methods)

    def test_case_insensitive_search(self, cli_command):
        """Test case insensitive search option."""
        result = subprocess.run(
            cli_command + ["search", "JSON", "--case-insensitive", "--limit", "3"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not crash
        assert result.returncode in [0, 1]

    def test_context_lines_option(self, cli_command):
        """Test context lines option in search."""
        result = subprocess.run(
            cli_command + ["search", "def", "--context", "5", "--limit", "2"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not crash
        assert result.returncode in [0, 1]


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""

    def test_missing_command(self, cli_command):
        """Test CLI with no command specified."""
        result = subprocess.run(cli_command, capture_output=True, text=True)

        # Should show help and exit with error
        assert result.returncode == 1
        assert "usage:" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_invalid_command(self, cli_command):
        """Test CLI with invalid command."""
        result = subprocess.run(cli_command + ["invalid-command"], capture_output=True, text=True)

        # Should exit with error
        assert result.returncode != 0

    def test_missing_required_argument(self, cli_command):
        """Test CLI with missing required arguments."""
        result = subprocess.run(cli_command + ["find"], capture_output=True, text=True)

        # Should exit with error for missing package argument
        assert result.returncode == 2  # argparse error code

    def test_invalid_package_name(self, cli_command):
        """Test CLI with invalid package name."""
        result = subprocess.run(
            cli_command + ["find", "nonexistent_package_12345"], capture_output=True, text=True
        )

        # Should handle gracefully - either succeed with empty result or error
        # Both are acceptable behaviors
        assert result.returncode in [0, 1]

    def test_keyboard_interrupt_handling(self, cli_command):
        """Test that CLI handles KeyboardInterrupt gracefully."""
        # This is hard to test automatically, but we can check that
        # the code structure exists for handling it
        import inspect

        import pyenvsearch.main

        # Check that main() handles KeyboardInterrupt
        source = inspect.getsource(pyenvsearch.main.main)
        assert "KeyboardInterrupt" in source
        assert "130" in source  # Standard exit code for SIGINT


class TestCLIPerformance:
    """Test CLI performance characteristics."""

    def test_search_timeout_handling(self, cli_command):
        """Test that search commands complete in reasonable time."""
        import time

        start_time = time.time()
        result = subprocess.run(
            cli_command + ["search", "def", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute max
        )
        elapsed = time.time() - start_time

        # Should complete within reasonable time
        assert elapsed < 60
        assert result.returncode in [0, 1]

    def test_large_result_handling(self, cli_command):
        """Test handling of large result sets."""
        result = subprocess.run(
            cli_command + ["list-methods", "json", "--limit", "100"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0
        # Should handle large limits without issues

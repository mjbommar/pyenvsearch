"""PyEnvSearch - Python library navigation tool for developers and AI agents."""

__version__ = "0.5.0"
__author__ = "PyEnvSearch Contributors"
__description__ = "Python library navigation tool optimized for uv/uvx ecosystem"

# Enhanced object inspection - main user-facing functions
from .core.inspect import (
    AttributeInfo,
    dir_enhanced,
    enhanced_dir,
    inspect_object,
    print_object_inspection,
)

# Make the most common functions easily available
__all__ = [
    "inspect_object",
    "print_object_inspection",
    "enhanced_dir",
    "dir_enhanced",
    "AttributeInfo",
]

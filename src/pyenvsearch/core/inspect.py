"""Enhanced object inspection functionality."""

import inspect
from dataclasses import dataclass
from typing import Any


@dataclass
class AttributeInfo:
    """Information about an object attribute."""

    name: str
    type_description: str
    signature: str | None = None
    docstring_snippet: str | None = None
    value_preview: str | None = None
    is_private: bool = False
    module_origin: str | None = None

    def format_compact(self, max_width: int = 120) -> str:
        """Format as a single compact line."""

        # Name and type
        name_part = f"📋 {self.name}"
        if self.is_private:
            name_part = f"🔒 {self.name}"

        type_part = f"({self.type_description})"

        # Signature for callables
        if self.signature:
            sig_part = f" {self.signature}"
            if len(sig_part) > 50:  # Truncate long signatures
                sig_part = sig_part[:47] + "..."
            type_part += sig_part

        # Value preview for constants
        if self.value_preview:
            type_part += f" = {self.value_preview}"

        # Docstring snippet
        doc_part = ""
        if self.docstring_snippet:
            # Clean up the docstring
            doc = self.docstring_snippet.strip().replace("\n", " ").replace("\r", " ")
            # Remove extra whitespace
            doc = " ".join(doc.split())
            if len(doc) > 80:
                doc = doc[:77] + "..."
            doc_part = f" → {doc}"

        # Combine parts
        line = f"{name_part} {type_part}{doc_part}"

        # Truncate if too long
        if len(line) > max_width:
            line = line[: max_width - 3] + "..."

        return line


def get_type_description(obj: Any) -> str:
    """Get a human-readable type description."""
    if isinstance(obj, type):
        # It's a class
        if issubclass(obj, Exception):
            return "exception"
        elif hasattr(obj, "__abstractmethods__") and obj.__abstractmethods__:
            return "abstract class"
        else:
            return "class"

    elif inspect.isfunction(obj):
        return "function"

    elif inspect.ismethod(obj):
        return "method"

    elif inspect.isbuiltin(obj):
        return "builtin"

    elif isinstance(obj, property):
        return "property"

    elif isinstance(obj, classmethod | staticmethod):
        return type(obj).__name__

    elif inspect.ismodule(obj):
        return "module"

    elif callable(obj):
        return "callable"

    elif isinstance(obj, int | float | complex):
        return "number"

    elif isinstance(obj, str):
        return "string"

    elif isinstance(obj, list | tuple | set | frozenset):
        return f"{type(obj).__name__}[{len(obj)}]"

    elif isinstance(obj, dict):
        return f"dict[{len(obj)}]"

    elif hasattr(obj, "__dict__") and not callable(obj):
        return "instance"

    else:
        return type(obj).__name__


def get_signature_string(obj: Any) -> str | None:
    """Get function/method signature as string."""
    try:
        if callable(obj) and not isinstance(obj, type):
            sig = inspect.signature(obj)
            return str(sig)
    except (ValueError, TypeError):
        pass
    return None


def get_docstring_snippet(obj: Any, max_length: int = 100) -> str | None:
    """Get first line of docstring, cleaned up."""
    try:
        doc = inspect.getdoc(obj)
        if doc:
            # Get first meaningful line
            lines = [line.strip() for line in doc.split("\n") if line.strip()]
            if lines:
                first_line = lines[0]
                if len(first_line) > max_length:
                    first_line = first_line[: max_length - 3] + "..."
                return first_line
    except Exception:
        pass
    return None


def get_value_preview(obj: Any, max_length: int = 50) -> str | None:
    """Get a preview of simple values."""
    try:
        if isinstance(obj, int | float | complex | bool):
            return str(obj)
        elif isinstance(obj, str):
            if len(obj) <= max_length:
                return repr(obj)
            else:
                return repr(obj[: max_length - 5] + "...")
        elif isinstance(obj, list | tuple | set | frozenset):
            if len(obj) <= 3:
                preview = repr(obj)
                if len(preview) <= max_length:
                    return preview
            return f"{type(obj).__name__}[{len(obj)} items]"
        elif isinstance(obj, dict):
            if len(obj) <= 2:
                preview = repr(obj)
                if len(preview) <= max_length:
                    return preview
            return f"dict[{len(obj)} items]"
    except Exception:
        pass
    return None


def get_module_origin(obj: Any) -> str | None:
    """Get the module where this object was defined."""
    try:
        if hasattr(obj, "__module__"):
            return obj.__module__
    except Exception:
        pass
    return None


def inspect_object(
    obj: Any,
    show_private: bool = False,
    show_docs: bool = True,
    group_by_type: bool = True,
    max_items: int | None = None,
) -> list[AttributeInfo]:
    """Enhanced dir() that provides detailed attribute information.

    Args:
        obj: The object to inspect
        show_private: Whether to include private attributes (starting with _)
        show_docs: Whether to include docstring snippets
        group_by_type: Whether to group output by attribute type
        max_items: Maximum number of items to return (None for all)

    Returns:
        List of AttributeInfo objects with detailed information
    """
    items = []

    # Get all attribute names
    try:
        attr_names = dir(obj)
    except Exception:
        return items

    for name in attr_names:
        # Skip private attributes unless requested
        is_private = name.startswith("_")
        if is_private and not show_private:
            continue

        try:
            # Get the attribute
            attr = getattr(obj, name)

            # Get detailed information
            info = AttributeInfo(
                name=name,
                type_description=get_type_description(attr),
                signature=get_signature_string(attr),
                docstring_snippet=get_docstring_snippet(attr) if show_docs else None,
                value_preview=get_value_preview(attr),
                is_private=is_private,
                module_origin=get_module_origin(attr),
            )

            items.append(info)

        except Exception:
            # Skip attributes that can't be accessed
            continue

    # Sort items
    if group_by_type:
        # Sort by type, then by name
        items.sort(key=lambda x: (x.type_description, x.name.lower()))
    else:
        # Sort alphabetically by name
        items.sort(key=lambda x: x.name.lower())

    # Limit number of items if requested
    if max_items is not None:
        items = items[:max_items]

    return items


def print_object_inspection(
    obj: Any,
    show_private: bool = False,
    show_docs: bool = True,
    group_by_type: bool = True,
    max_items: int | None = None,
    show_summary: bool = True,
) -> None:
    """Print enhanced object inspection results.

    This is the main function that users would call from command line.
    """
    items = inspect_object(obj, show_private, show_docs, group_by_type, max_items)

    if not items:
        print("No accessible attributes found.")
        return

    # Print summary
    if show_summary:
        obj_type = get_type_description(obj)
        obj_name = getattr(obj, "__name__", str(type(obj).__name__))
        total_count = len(dir(obj)) if hasattr(obj, "__dict__") or callable(dir) else len(items)
        shown_count = len(items)

        print(f"🔍 Inspecting {obj_type}: {obj_name}")
        print(
            f"📊 Showing {shown_count} attributes"
            + (f" (of {total_count} total)" if shown_count != total_count else "")
        )
        print("=" * 80)

    # Group items by type if requested
    if group_by_type:
        current_type = None
        for item in items:
            if item.type_description != current_type:
                current_type = item.type_description
                print(f"\n📁 {current_type.upper()}:")
                print("-" * 40)
            print(f"  {item.format_compact()}")
    else:
        for item in items:
            print(item.format_compact())

    # Show truncation warning
    if max_items and len(items) == max_items:
        print(f"\n⚠️  Results truncated to {max_items} items. Use max_items=None to see all.")


# Convenience aliases for easy import
dir_enhanced = print_object_inspection
enhanced_dir = print_object_inspection

#!/usr/bin/env python3
"""PyEnvSearch CLI - Main entry point for the command-line interface."""

import argparse
import sys

from .core.docs import DocumentationSearcher
from .core.llm import LLMAnalyzer
from .core.packages import PackageFinder
from .core.search import CodeSearcher
from .core.venv import VirtualEnvDetector


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="pyenvsearch",
        description="🔍 Python library navigation tool for developers and AI agents\n"
        + "Combines traditional code search with AI-powered package analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔍 Environment & Discovery:
  pyenvsearch venv                    # Show virtual environment info
  pyenvsearch find httpx              # Find where httpx is installed
  pyenvsearch docs requests           # Find LLM-friendly documentation

🔎 Code Navigation & Search:
  pyenvsearch toc fastapi             # Generate package table of contents
  pyenvsearch search "class.*Http"    # Search for HTTP-related classes
  pyenvsearch class HttpClient        # Find specific class definitions
  pyenvsearch method get              # Find method implementations
  pyenvsearch list-classes requests   # List all classes in a package
  pyenvsearch list-methods httpx      # List all methods in a package
  pyenvsearch list-enums enum         # List all enums in a package

🤖 AI-Powered Analysis:
  pyenvsearch summarize requests      # Quick package overview
  pyenvsearch explain fastapi         # Deep technical explanation
  pyenvsearch howto pandas            # Step-by-step tutorial
  pyenvsearch api-guide numpy         # API reference & patterns
  pyenvsearch ask requests "How do I handle timeouts?"  # Ask specific questions
  pyenvsearch llm-tools               # List available AI tools

💡 Pro Tips:
  • Add --json to any command for structured output
  • Use --tool claude|gemini|codex|goose to choose AI tool
  • Perfect for AI agents exploring Python codebases
  • All searches support regex patterns and package filtering
        """,
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")

    # venv command
    venv_parser = subparsers.add_parser(
        "venv", help="Show virtual environment info and installed packages"
    )
    venv_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # find command
    find_parser = subparsers.add_parser("find", help="Find exact installation path of a package")
    find_parser.add_argument("package", help='Package name to locate (e.g., "requests", "fastapi")')
    find_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # docs command
    docs_parser = subparsers.add_parser(
        "docs", help="Find AI-optimized documentation (llms.txt, ai.txt, README)"
    )
    docs_parser.add_argument("package", help="Package name to search documentation for")
    docs_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # search command
    search_parser = subparsers.add_parser("search", help="Search for code patterns")
    search_parser.add_argument("pattern", help="Search pattern (regex or AST pattern)")
    search_parser.add_argument("--package", help="Limit search to specific package")
    search_parser.add_argument(
        "--type", choices=["regex", "ast"], default="regex", help="Search type (default: regex)"
    )
    search_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    search_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum number of results to show (default: 50)"
    )
    search_parser.add_argument(
        "--offset", type=int, default=0, help="Number of results to skip (for pagination)"
    )
    search_parser.add_argument(
        "--context", type=int, default=2, help="Lines of context around each match (default: 2)"
    )
    search_parser.add_argument(
        "--case-insensitive", action="store_true", help="Case insensitive search"
    )
    search_parser.add_argument(
        "--comments-only", action="store_true", help="Search only in comments"
    )
    search_parser.add_argument(
        "--strings-only", action="store_true", help="Search only in string literals"
    )
    search_parser.add_argument(
        "--relative-paths",
        action="store_true",
        help="Show relative paths instead of absolute paths",
    )

    # toc command
    toc_parser = subparsers.add_parser("toc", help="Generate table of contents for package")
    toc_parser.add_argument("package", help="Package name to generate TOC for")
    toc_parser.add_argument(
        "--depth", type=int, default=2, help="Maximum depth for TOC (default: 2)"
    )
    toc_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # class command
    class_parser = subparsers.add_parser("class", help="Find class definitions")
    class_parser.add_argument("classname", help="Class name to find")
    class_parser.add_argument("--package", help="Limit search to specific package")
    class_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # method command
    method_parser = subparsers.add_parser("method", help="Find method implementations")
    method_parser.add_argument("methodname", help="Method name to find")
    method_parser.add_argument("--package", help="Limit search to specific package")
    method_parser.add_argument("--class", dest="classname", help="Limit search to specific class")
    method_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # list-methods command
    list_methods_parser = subparsers.add_parser(
        "list-methods", help="List all methods in a package"
    )
    list_methods_parser.add_argument("package", help="Package name to list methods from")
    list_methods_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum number of results to show (default: 50)"
    )
    list_methods_parser.add_argument(
        "--offset", type=int, default=0, help="Number of results to skip (for pagination)"
    )
    list_methods_parser.add_argument(
        "--include-private", action="store_true", help="Include methods starting with underscore"
    )
    list_methods_parser.add_argument("--module", help="Filter to specific module within package")
    list_methods_parser.add_argument(
        "--class", dest="classname", help="Filter to methods in specific class"
    )
    list_methods_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    list_methods_parser.add_argument(
        "--relative-paths",
        action="store_true",
        help="Show relative paths instead of absolute paths",
    )

    # list-classes command
    list_classes_parser = subparsers.add_parser(
        "list-classes", help="List all classes in a package"
    )
    list_classes_parser.add_argument("package", help="Package name to list classes from")
    list_classes_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum number of results to show (default: 50)"
    )
    list_classes_parser.add_argument(
        "--offset", type=int, default=0, help="Number of results to skip (for pagination)"
    )
    list_classes_parser.add_argument(
        "--include-private", action="store_true", help="Include classes starting with underscore"
    )
    list_classes_parser.add_argument("--module", help="Filter to specific module within package")
    list_classes_parser.add_argument(
        "--parent", help="Filter to subclasses of specific parent class"
    )
    list_classes_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    list_classes_parser.add_argument(
        "--relative-paths",
        action="store_true",
        help="Show relative paths instead of absolute paths",
    )

    # list-enums command
    list_enums_parser = subparsers.add_parser("list-enums", help="List all enums in a package")
    list_enums_parser.add_argument("package", help="Package name to list enums from")
    list_enums_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum number of results to show (default: 50)"
    )
    list_enums_parser.add_argument(
        "--offset", type=int, default=0, help="Number of results to skip (for pagination)"
    )
    list_enums_parser.add_argument(
        "--include-private", action="store_true", help="Include enums starting with underscore"
    )
    list_enums_parser.add_argument("--module", help="Filter to specific module within package")
    list_enums_parser.add_argument(
        "--enum-type", help="Filter by enum base type (Enum, IntEnum, Flag, etc.)"
    )
    list_enums_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    list_enums_parser.add_argument(
        "--relative-paths",
        action="store_true",
        help="Show relative paths instead of absolute paths",
    )

    # summarize command
    summarize_parser = subparsers.add_parser(
        "summarize", help="🤖 Generate concise AI-powered package overview"
    )
    summarize_parser.add_argument(
        "package", help='Package name to summarize (e.g., "requests", "pandas")'
    )
    summarize_parser.add_argument(
        "--tool",
        choices=["claude", "gemini", "codex", "goose"],
        help="Preferred LLM tool (auto-detects if not specified)",
    )
    summarize_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # explain command
    explain_parser = subparsers.add_parser(
        "explain", help="🤖 Generate detailed technical architecture analysis"
    )
    explain_parser.add_argument("package", help="Package name to explain in depth")
    explain_parser.add_argument(
        "--tool",
        choices=["claude", "gemini", "codex", "goose"],
        help="Preferred LLM tool (auto-detects if not specified)",
    )
    explain_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # howto command
    howto_parser = subparsers.add_parser(
        "howto", help="🤖 Generate step-by-step tutorial with examples"
    )
    howto_parser.add_argument("package", help="Package name for tutorial")
    howto_parser.add_argument(
        "--task", help='Specific task or use case (e.g., "data cleaning", "async requests")'
    )
    howto_parser.add_argument(
        "--tool",
        choices=["claude", "gemini", "codex", "goose"],
        help="Preferred LLM tool (auto-detects if not specified)",
    )
    howto_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # api-guide command
    api_guide_parser = subparsers.add_parser(
        "api-guide", help="🤖 Generate comprehensive API reference and patterns"
    )
    api_guide_parser.add_argument("package", help="Package name for API guide")
    api_guide_parser.add_argument(
        "--tool",
        choices=["claude", "gemini", "codex", "goose"],
        help="Preferred LLM tool (auto-detects if not specified)",
    )
    api_guide_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # ask command
    ask_parser = subparsers.add_parser("ask", help="🤖 Ask a specific question about a package")
    ask_parser.add_argument("package", help="Package name to ask about")
    ask_parser.add_argument("question", help='Your question (e.g., "How do I handle timeouts?")')
    ask_parser.add_argument(
        "--tool",
        choices=["claude", "gemini", "codex", "goose"],
        help="Preferred LLM tool (auto-detects if not specified)",
    )
    ask_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # llm-tools command
    llm_tools_parser = subparsers.add_parser(
        "llm-tools", help="📋 List available AI tools (claude, gemini, codex, goose)"
    )
    llm_tools_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "venv":
            detector = VirtualEnvDetector()
            result = detector.detect()
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "find":
            finder = PackageFinder()
            result = finder.find_package(args.package)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "docs":
            searcher = DocumentationSearcher()
            result = searcher.find_docs(args.package)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "search":
            searcher = CodeSearcher()
            result = searcher.search(
                pattern=args.pattern,
                package=args.package,
                search_type=args.type,
                limit=args.limit,
                offset=args.offset,
                context=args.context,
                case_insensitive=getattr(args, "case_insensitive", False),
                comments_only=getattr(args, "comments_only", False),
                strings_only=getattr(args, "strings_only", False),
            )
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human(relative_paths=getattr(args, "relative_paths", False)))

        elif args.command == "toc":
            finder = PackageFinder()
            result = finder.generate_toc(args.package, depth=args.depth)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "class":
            searcher = CodeSearcher()
            result = searcher.find_class(classname=args.classname, package=args.package)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "method":
            searcher = CodeSearcher()
            result = searcher.find_method(
                methodname=args.methodname, package=args.package, classname=args.classname
            )
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "list-methods":
            searcher = CodeSearcher()
            result = searcher.list_methods(
                package=args.package,
                limit=args.limit,
                offset=args.offset,
                include_private=getattr(args, "include_private", False),
                module_filter=args.module,
                class_filter=args.classname,
            )
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human(relative_paths=getattr(args, "relative_paths", False)))

        elif args.command == "list-classes":
            searcher = CodeSearcher()
            result = searcher.list_classes(
                package=args.package,
                limit=args.limit,
                offset=args.offset,
                include_private=getattr(args, "include_private", False),
                module_filter=args.module,
                parent_filter=args.parent,
            )
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human(relative_paths=getattr(args, "relative_paths", False)))

        elif args.command == "list-enums":
            searcher = CodeSearcher()
            result = searcher.list_enums(
                package=args.package,
                limit=args.limit,
                offset=args.offset,
                include_private=getattr(args, "include_private", False),
                module_filter=args.module,
                enum_type_filter=getattr(args, "enum_type", None),
            )
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human(relative_paths=getattr(args, "relative_paths", False)))

        elif args.command == "summarize":
            analyzer = LLMAnalyzer()
            result = analyzer.summarize_package(args.package, preferred_tool=args.tool)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "explain":
            analyzer = LLMAnalyzer()
            result = analyzer.explain_package(args.package, preferred_tool=args.tool)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "howto":
            analyzer = LLMAnalyzer()
            result = analyzer.generate_howto(args.package, task=args.task, preferred_tool=args.tool)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "api-guide":
            analyzer = LLMAnalyzer()
            result = analyzer.analyze_api(args.package, preferred_tool=args.tool)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "ask":
            analyzer = LLMAnalyzer()
            result = analyzer.ask_question(args.package, args.question, preferred_tool=args.tool)
            if args.json:
                import json

                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.format_human())

        elif args.command == "llm-tools":
            analyzer = LLMAnalyzer()
            available_tools = analyzer.get_available_tools()
            if args.json:
                import json

                print(json.dumps({"available_tools": available_tools}, indent=2))
            else:
                if available_tools:
                    print("Available LLM tools:")
                    for tool in available_tools:
                        print(f"  - {tool}")
                else:
                    print("No LLM tools available. Please install claude, gemini, codex, or goose.")

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

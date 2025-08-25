"""LLM integration for intelligent package analysis.

Provides AI-powered analysis of Python packages using various LLM CLI tools.
Supports claude, gemini, codex, and goose with automatic fallback.
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .packages import PackageFinder


@dataclass
class LLMTool:
    """Configuration for an LLM CLI tool."""

    name: str
    executable: str
    prompt_args: list[str]
    supports_stdin: bool = True
    supports_file_context: bool = True
    working_dir_sensitive: bool = False
    additional_flags: list[str] = field(default_factory=list)


@dataclass
class LLMAnalysisResult:
    """Result of LLM analysis."""

    package_name: str
    analysis_type: str  # 'summary', 'explain', 'howto', 'api'
    content: str
    tool_used: str
    success: bool
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "package_name": self.package_name,
            "analysis_type": self.analysis_type,
            "content": self.content,
            "tool_used": self.tool_used,
            "success": self.success,
            "error_message": self.error_message,
        }

    def format_human(self) -> str:
        """Format for human-readable output."""
        lines = []
        lines.append(f"LLM Analysis: {self.package_name}")
        lines.append("=" * (len(self.package_name) + 14))
        lines.append(f"Analysis Type: {self.analysis_type.title()}")
        lines.append(f"Tool Used: {self.tool_used}")

        if self.success:
            lines.append("")
            lines.append(self.content)
        else:
            lines.append(f"Error: {self.error_message}")

        return "\\n".join(lines)


class LLMAnalyzer:
    """LLM-powered Python package analyzer."""

    # Available LLM tools in priority order
    AVAILABLE_TOOLS = [
        LLMTool(
            name="claude",
            executable="claude",
            prompt_args=["--print"],
            supports_stdin=True,
            supports_file_context=True,
            working_dir_sensitive=False,
        ),
        LLMTool(
            name="gemini",
            executable="gemini",
            prompt_args=["--prompt"],
            supports_stdin=False,  # Gemini seems to ignore stdin content
            supports_file_context=True,
            working_dir_sensitive=True,
        ),
        LLMTool(
            name="codex",
            executable="codex",
            prompt_args=["exec", "--skip-git-repo-check"],
            supports_stdin=False,
            supports_file_context=True,
            working_dir_sensitive=True,
        ),
        LLMTool(
            name="goose",
            executable="goose",
            prompt_args=["run", "-i", "-"],
            supports_stdin=True,
            supports_file_context=True,
            working_dir_sensitive=True,
        ),
    ]

    def __init__(self):
        self.package_finder = PackageFinder()
        self.available_tools = self._detect_available_tools()

    def _detect_available_tools(self) -> list[LLMTool]:
        """Detect which LLM tools are available on the system."""
        available = []
        for tool in self.AVAILABLE_TOOLS:
            if shutil.which(tool.executable):
                available.append(tool)
        return available

    def get_available_tools(self) -> list[str]:
        """Get list of available LLM tool names."""
        return [tool.name for tool in self.available_tools]

    def summarize_package(
        self, package_name: str, preferred_tool: str | None = None
    ) -> LLMAnalysisResult:
        """Generate a high-level summary of a Python package."""
        prompt = f"""Analyze the Python package '{package_name}' and provide a concise summary covering:

1. **Purpose**: What the package does in 1-2 sentences
2. **Key Features**: Main capabilities and components
3. **Common Use Cases**: When and why you'd use this package
4. **Installation**: How to install (pip, conda, etc.)
5. **Basic Example**: Simple code example showing typical usage

Keep it concise but informative - suitable for developers who want to quickly understand the package."""

        return self._analyze_package(package_name, "summary", prompt, preferred_tool)

    def explain_package(
        self, package_name: str, preferred_tool: str | None = None
    ) -> LLMAnalysisResult:
        """Generate detailed explanation of package architecture and design."""
        prompt = f"""Provide a detailed technical explanation of the Python package '{package_name}':

1. **Architecture**: Overall structure, main modules, and design patterns
2. **Core Components**: Key classes, functions, and their relationships
3. **API Design**: How the public API is organized and intended to be used
4. **Dependencies**: Important external dependencies and why they're used
5. **Extension Points**: How the package can be extended or customized
6. **Best Practices**: Recommended patterns when using this package

Focus on helping developers understand the package's internal structure and design philosophy."""

        return self._analyze_package(package_name, "explain", prompt, preferred_tool)

    def generate_howto(
        self, package_name: str, task: str | None = None, preferred_tool: str | None = None
    ) -> LLMAnalysisResult:
        """Generate step-by-step tutorial for using the package."""
        if task:
            prompt = f"""Create a step-by-step tutorial for using the Python package '{package_name}' to accomplish: {task}

Include:
1. **Setup**: Installation and initial configuration
2. **Step-by-Step Guide**: Clear, numbered steps with code examples
3. **Code Examples**: Complete, runnable code snippets
4. **Common Issues**: Potential problems and solutions
5. **Advanced Tips**: Pro tips for more effective usage

Make it practical and actionable for developers."""
        else:
            prompt = f"""Create a comprehensive getting-started tutorial for the Python package '{package_name}':

1. **Installation**: How to install the package
2. **Basic Setup**: Initial configuration and imports
3. **Core Concepts**: Key concepts developers need to understand
4. **Essential Examples**: 3-4 practical examples showing common operations
5. **Next Steps**: Where to go for more advanced usage
6. **Resources**: Links to docs, examples, community

Structure it as a practical tutorial that gets developers productive quickly."""

        return self._analyze_package(package_name, "howto", prompt, preferred_tool)

    def analyze_api(
        self, package_name: str, preferred_tool: str | None = None
    ) -> LLMAnalysisResult:
        """Generate API reference and usage patterns."""
        prompt = f"""Generate a comprehensive API analysis for the Python package '{package_name}':

1. **Public API**: Main classes, functions, and methods available to users
2. **Usage Patterns**: Common patterns and idioms for using the API
3. **Parameter Guide**: Important parameters and their effects
4. **Return Values**: What to expect from major functions/methods
5. **Error Handling**: Common exceptions and how to handle them
6. **API Evolution**: Notes on stability, deprecations, or version differences

Focus on practical API usage that helps developers write correct, idiomatic code."""

        return self._analyze_package(package_name, "api", prompt, preferred_tool)

    def ask_question(
        self, package_name: str, question: str, preferred_tool: str | None = None
    ) -> LLMAnalysisResult:
        """Ask a specific question about a Python package."""
        prompt = f"""Answer this specific question about the Python package '{package_name}':

**Question**: {question}

Please provide a comprehensive, practical answer that includes:
1. **Direct Answer**: Clear, specific response to the question
2. **Code Examples**: Relevant code snippets demonstrating the answer
3. **Context**: Any important background or considerations
4. **Best Practices**: Recommended approaches and common pitfalls to avoid
5. **Related Topics**: Other relevant aspects that might be helpful

Focus on being practical and actionable. If the question can't be answered about this specific package, explain why and suggest alternatives."""

        return self._analyze_package(package_name, "question", prompt, preferred_tool)

    def _analyze_package(
        self,
        package_name: str,
        analysis_type: str,
        prompt: str,
        preferred_tool: str | None = None,
    ) -> LLMAnalysisResult:
        """Execute LLM analysis of a package."""
        if not self.available_tools:
            return LLMAnalysisResult(
                package_name=package_name,
                analysis_type=analysis_type,
                content="",
                tool_used="none",
                success=False,
                error_message="No LLM tools available. Please install claude, gemini, codex, or goose.",
            )

        # Find package location for context
        package_info = self.package_finder.find_package(package_name)

        # Select tool to use
        tool = self._select_tool(preferred_tool)

        # Enhance prompt with package context
        enhanced_prompt = self._enhance_prompt_with_context(prompt, package_info)

        try:
            result = self._execute_llm_analysis(tool, enhanced_prompt, package_info)
            return LLMAnalysisResult(
                package_name=package_name,
                analysis_type=analysis_type,
                content=result,
                tool_used=tool.name,
                success=True,
            )
        except Exception as e:
            # Try fallback tools
            for fallback_tool in self.available_tools:
                if fallback_tool.name != tool.name:
                    try:
                        result = self._execute_llm_analysis(
                            fallback_tool, enhanced_prompt, package_info
                        )
                        return LLMAnalysisResult(
                            package_name=package_name,
                            analysis_type=analysis_type,
                            content=result,
                            tool_used=fallback_tool.name,
                            success=True,
                        )
                    except Exception:
                        continue

            return LLMAnalysisResult(
                package_name=package_name,
                analysis_type=analysis_type,
                content="",
                tool_used=tool.name,
                success=False,
                error_message=str(e),
            )

    def _select_tool(self, preferred_tool: str | None) -> LLMTool:
        """Select the best available LLM tool."""
        if preferred_tool:
            for tool in self.available_tools:
                if tool.name == preferred_tool:
                    return tool

        # Return first available tool (highest priority)
        return self.available_tools[0]

    def _enhance_prompt_with_context(self, base_prompt: str, package_info) -> str:
        """Enhance prompt with package location and actual source code context."""
        context_lines = [base_prompt, ""]

        if package_info.location and package_info.location.exists():
            context_lines.append(f"Package location: {package_info.location}")

            # Add actual file contents for better context
            if package_info.location.is_file() and package_info.location.suffix == ".py":
                try:
                    size = package_info.location.stat().st_size
                    if size < 50000:  # Less than 50KB
                        content = package_info.location.read_text(encoding="utf-8", errors="ignore")
                        context_lines.append("Package source code:")
                        context_lines.append("```python")
                        context_lines.append(content[:5000])  # First 5KB of content
                        context_lines.append("```")
                except (OSError, UnicodeDecodeError):
                    context_lines.append(
                        f"Package source file available at: {package_info.location}"
                    )
            elif package_info.location.is_dir():
                # Read key files for context
                context_lines.append("Package structure and key source code:")

                try:
                    # List main Python files
                    py_files = sorted(
                        [
                            f
                            for f in package_info.location.glob("*.py")
                            if not f.name.startswith("_")
                        ]
                    )[:3]
                    init_file = package_info.location / "__init__.py"

                    # Always try to read __init__.py first
                    if init_file.exists():
                        try:
                            content = init_file.read_text(encoding="utf-8", errors="ignore")
                            if content.strip():
                                context_lines.append(f"\\n--- {init_file.name} ---")
                                context_lines.append("```python")
                                context_lines.append(content[:3000])  # First 3KB
                                context_lines.append("```")
                        except (OSError, UnicodeDecodeError):
                            pass

                    # Read a few other key files
                    files_read = 1 if init_file.exists() else 0
                    for py_file in py_files:
                        if files_read >= 2:  # Limit to prevent prompt bloat
                            break
                        if py_file.name != "__init__.py":
                            try:
                                content = py_file.read_text(encoding="utf-8", errors="ignore")
                                if (
                                    content.strip() and len(content) < 10000
                                ):  # Skip very large files
                                    context_lines.append(f"\\n--- {py_file.name} ---")
                                    context_lines.append("```python")
                                    context_lines.append(content[:2000])  # First 2KB
                                    context_lines.append("```")
                                    files_read += 1
                            except (OSError, UnicodeDecodeError):
                                continue

                    # Also list directory structure
                    py_files_all = list(package_info.location.glob("*.py"))[:10]
                    if py_files_all:
                        context_lines.append("\\nAvailable Python modules:")
                        for py_file in py_files_all:
                            context_lines.append(f"  - {py_file.name}")

                except (OSError, AttributeError):
                    context_lines.append("Unable to read package structure")
        else:
            context_lines.append(f"Package '{package_info.name}' not found in current environment.")

        if package_info.version:
            context_lines.append(f"\\nPackage version: {package_info.version}")

        context_lines.append(
            "\\nPlease base your answer on the actual source code provided above, not general knowledge."
        )
        context_lines.append("")
        return "\\n".join(context_lines)

    def _execute_llm_analysis(self, tool: LLMTool, prompt: str, package_info) -> str:
        """Execute LLM analysis with the specified tool."""
        # Prepare command
        cmd = [tool.executable] + tool.prompt_args + tool.additional_flags

        # Set working directory if needed
        cwd = None
        if tool.working_dir_sensitive and package_info.location:
            if package_info.location.is_dir():
                cwd = package_info.location
            elif package_info.location.is_file():
                cwd = package_info.location.parent

        # Handle different tool interfaces
        if tool.name == "claude":
            cmd.append(prompt)
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=cwd, timeout=60, stdin=subprocess.DEVNULL
            )

        elif tool.name == "gemini":
            cmd.append(prompt)
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=cwd, timeout=60, stdin=subprocess.DEVNULL
            )

        elif tool.name == "codex":
            cmd.append(prompt)
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=cwd, timeout=60, stdin=subprocess.DEVNULL
            )

        elif tool.name == "goose":
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=60,
                # Note: goose uses input=prompt, so don't add stdin=DEVNULL
            )

        else:
            raise ValueError(f"Unknown tool: {tool.name}")

        if result.returncode != 0:
            raise RuntimeError(f"LLM tool failed: {result.stderr}")

        # Clean up output (remove tool-specific metadata)
        output = result.stdout.strip()
        output = self._clean_tool_output(tool.name, output)

        return output

    def _clean_tool_output(self, tool_name: str, output: str) -> str:
        """Remove tool-specific metadata and formatting from output."""
        lines = output.split("\\n")
        cleaned_lines = []

        if tool_name == "codex":
            # Remove codex metadata lines
            skip_patterns = [
                "[2025-",
                "--------",
                "workdir:",
                "model:",
                "provider:",
                "approval:",
                "sandbox:",
                "reasoning",
                "tokens used:",
                "exec bash",
            ]
            for line in lines:
                if not any(pattern in line for pattern in skip_patterns):
                    cleaned_lines.append(line)

        elif tool_name == "goose":
            # Remove goose session info
            skip_patterns = [
                "starting session",
                "logging to",
                "working directory:",
                "Warning:",
                "Continuing without extension",
            ]
            for line in lines:
                if not any(pattern in line for pattern in skip_patterns):
                    cleaned_lines.append(line)

        elif tool_name == "gemini":
            # Remove gemini warnings
            skip_patterns = [
                "Data collection is disabled",
                "[WARN]",
                "Skipping unreadable directory",
            ]
            for line in lines:
                if not any(pattern in line for pattern in skip_patterns):
                    cleaned_lines.append(line)
        else:
            # Claude and others - minimal cleaning
            cleaned_lines = lines

        return "\\n".join(cleaned_lines).strip()

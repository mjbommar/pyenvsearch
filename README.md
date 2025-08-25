# PyEnvSearch

🔍 **Python library navigation tool for developers and AI agents**

A powerful command-line tool designed for the modern Python ecosystem (uv/uvx) that combines traditional code search with AI-powered package analysis.

## ✨ Key Features

### 🔍 **Code Discovery & Navigation**
- **Virtual Environment Detection**: Automatically finds and analyzes virtual environments
- **Package Location Discovery**: Locates exact paths for installed packages  
- **Semantic Code Search**: Find classes, methods, enums with AST-aware search
- **High-Performance Search**: Uses ast-grep and ripgrep when available for blazing-fast search
- **Code Structure Navigation**: Generate beautiful table of contents for any package

### 🤖 **AI-Powered Analysis** 
- **Package Summaries**: Get concise overviews of any Python package
- **Technical Explanations**: Deep dive into package architecture and design
- **Step-by-Step Tutorials**: Generate how-to guides for specific tasks
- **API References**: Comprehensive usage patterns and best practices
- **Multi-LLM Support**: Works with Claude, Gemini, Codex, and Goose

### 🛠️ **Developer Experience**
- **JSON Output**: Perfect for programmatic usage and tool integration
- **LLM-Friendly Documentation**: Finds AI-optimized docs (llms.txt, ai.txt)
- **Zero Heavy Dependencies**: Minimal footprint with graceful degradation
- **uv/uvx Native**: Built for the modern Python toolchain

## 🚀 Installation

### Prerequisites
**Core functionality works with Python standard library only.** For enhanced features:

#### Optional: Performance Tools
```bash
# For blazing-fast search (highly recommended)
# macOS
brew install ripgrep ast-grep

# Ubuntu/Debian  
sudo apt install ripgrep
cargo install ast-grep-cli

# Windows
winget install BurntSushi.ripgrep.MSVC
cargo install ast-grep-cli
```

#### Optional: AI-Powered Analysis
For AI features, install at least one LLM CLI tool:
```bash
# Claude (best results) - requires subscription
npm install -g @anthropic-ai/claude

# Gemini (free tier available)  
npm install -g @google/generative-ai-cli

# Codex (OpenAI account required)
# See: https://github.com/microsoft/codex-cli

# Goose (multi-provider support)
pipx install goose-ai
```

### Install PyEnvSearch
```bash
# With uv tool (recommended for CLI usage)
uv tool install pyenvsearch

# With performance tools for blazing-fast search
uv tool install "pyenvsearch[performance]"

# With pipx (alternative CLI installer)
pipx install pyenvsearch
pipx install "pyenvsearch[performance]"

# For one-time usage (no installation)
uvx pyenvsearch --help

# Or install as regular package
uv add pyenvsearch
uv add "pyenvsearch[performance]"  # With fast search tools
pip install pyenvsearch
pip install "pyenvsearch[performance]"
```

## 📖 Usage Guide

### 🔍 Environment & Discovery
**Understand your Python environment and locate packages**

```bash
# Show virtual environment info
pyenvsearch venv

# Find where a package is installed
pyenvsearch find httpx

# Find LLM-optimized documentation
pyenvsearch docs requests
```

### 🔎 Code Navigation & Search
**Navigate and search through package code**

```bash
# Generate package table of contents  
pyenvsearch toc fastapi --depth 3

# Search for code patterns
pyenvsearch search "class.*Http" --type regex
pyenvsearch search "async def" --package httpx

# Find specific classes and methods
pyenvsearch class HttpClient
pyenvsearch method get --class HttpClient

# List all classes, methods, or enums in a package
pyenvsearch list-classes requests
pyenvsearch list-methods httpx --include-private
pyenvsearch list-enums enum --enum-type IntEnum
```

### 🤖 AI-Powered Analysis
**Get intelligent insights about any Python package**

```bash
# Quick package overview
pyenvsearch summarize requests

# Deep technical explanation  
pyenvsearch explain fastapi --tool claude

# Step-by-step tutorials
pyenvsearch howto pandas --task "data cleaning"
pyenvsearch howto sqlalchemy 

# Comprehensive API guides
pyenvsearch api-guide httpx --tool gemini

# Check available AI tools
pyenvsearch llm-tools
```

### 💾 JSON Output
**Perfect for scripts and tool integration**

```bash
# Any command with --json flag
pyenvsearch find httpx --json
pyenvsearch summarize requests --json | jq '.content'
pyenvsearch list-classes fastapi --json
```

## 🎯 Real-World Examples

### 🧪 Exploring a New Package
```bash
# Just installed a new package? Get oriented quickly:
pyenvsearch find fastapi              # Where is it?
pyenvsearch summarize fastapi         # What does it do?
pyenvsearch toc fastapi --depth 2     # How is it structured?
pyenvsearch list-classes fastapi      # What are the main classes?
```

### 🔍 Debugging & Investigation  
```bash
# Looking for specific functionality:
pyenvsearch search "ValidationError" --package pydantic
pyenvsearch method validate --package pydantic
pyenvsearch class BaseModel --package pydantic

# Need usage examples:
pyenvsearch howto pydantic --task "custom validators"
pyenvsearch api-guide pydantic
```

### 🤖 AI Agent Workflows
```bash
# Perfect for AI agents exploring codebases:
pyenvsearch venv --json | jq '.packages[]'
pyenvsearch docs requests --json      # Find AI-friendly docs
pyenvsearch explain httpx --json      # Get structured analysis
pyenvsearch search "async.*client" --json --package httpx
```

### 📊 Package Analysis Scripts
```bash
#!/bin/bash
# Analyze all installed packages
for pkg in $(pyenvsearch venv --json | jq -r '.packages[].name'); do
    echo "=== $pkg ==="
    pyenvsearch summarize "$pkg" --json | jq -r '.content'
done
```

## 🏗️ Architecture

**Built for Performance & Developer Experience:**
- **🪶 Minimal Dependencies**: Python standard library + optional performance tools
- **⚡ High Performance**: Leverages ast-grep, ripgrep when available  
- **🔄 Graceful Degradation**: Works with or without external tools
- **🎯 uv/uvx Native**: Designed for modern Python workflows
- **🤖 LLM Integration**: Multi-provider AI analysis with automatic fallback
- **📊 Structured Output**: JSON support for programmatic usage

## 🛠️ Development

### Setup
```bash
git clone <repository-url>
cd pyenvsearch
uv sync --dev
```

### Testing
```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Test specific functionality
uv run pytest tests/test_llm.py -v
```

### Code Quality
```bash
# Lint and fix issues
uvx ruff check --fix
uvx ruff format

# Type checking
uvx mypy src/

# Run all quality checks
uvx ruff check --fix && uvx ruff format && uvx mypy src/
```

### Manual Testing
```bash
# Test basic functionality
uv run python -m pyenvsearch venv
uv run python -m pyenvsearch find requests
uv run python -m pyenvsearch summarize requests

# Test with different LLM tools
uv run python -m pyenvsearch llm-tools
uv run python -m pyenvsearch summarize requests --tool claude
```

## 📋 Requirements

### Core Requirements
- **Python 3.13+** (uses modern Python features)
- **uv/uvx** (recommended package manager)

### Optional Performance Tools  
- **ripgrep** (`rg`) - Blazing fast text search
- **ast-grep** - Semantic code search and analysis

```bash
# Install performance tools (optional but recommended)
# macOS
brew install ripgrep ast-grep

# Ubuntu/Debian  
sudo apt install ripgrep
cargo install ast-grep-cli

# Windows
winget install BurntSushi.ripgrep.MSVC
cargo install ast-grep-cli
```

### LLM Tools (for AI features)
- **Claude CLI** - Best results, requires subscription
- **Gemini CLI** - Good free tier
- **Codex CLI** - OpenAI integration  
- **Goose** - Multi-provider support

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Made with ❤️ for the Python community and AI agents everywhere** 🐍🤖
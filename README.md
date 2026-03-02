# insight-blueprint

[![CI](https://github.com/etoyama/insight-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/etoyama/insight-blueprint/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

A Python MCP server for hypothesis-driven data analysis. Manage analysis designs, data catalogs, and review workflows through Claude Code or any MCP-compatible client.

## Installation

### From Source (Development)

Requires **Python 3.11+**, **uv**, and **Node.js** (for frontend build).

```bash
git clone https://github.com/etoyama/insight-blueprint.git
cd insight-blueprint
uv sync --all-extras

# Build frontend assets (required for WebUI)
poe build-frontend
```

### From PyPI

> **Note**: Not yet published. Coming soon.

```bash
# Zero-install with uvx
uvx insight-blueprint --project /path/to/analysis

# Or install permanently
uv tool install insight-blueprint
```

## Quick Start

```bash
# 1. Start the server for your analysis project
#    (from source — run from the insight-blueprint repo root)
uv run insight-blueprint --project /path/to/my-analysis

#    Or install as a global tool so you can run from anywhere:
uv tool install -e /path/to/insight-blueprint
insight-blueprint --project /path/to/my-analysis

#    (from PyPI, once published)
#    uvx insight-blueprint --project /path/to/my-analysis

# 2. The server provides MCP tools for Claude Code:
#    - create_analysis_design   — Create hypothesis documents
#    - list_analysis_designs    — Browse existing designs
#    - get_analysis_design      — Retrieve a specific design
#    - add_catalog_entry        — Register data sources
#    - search_catalog           — Search the data catalog
#    - create_review            — Start a design review

# 3. A WebUI dashboard opens automatically at http://127.0.0.1:3000
```

## Features

### MCP Tools

insight-blueprint exposes tools via the [Model Context Protocol](https://modelcontextprotocol.io/), allowing AI assistants to manage your analysis workflow:

- **Analysis Design** -- Create, update, and track hypothesis-driven analysis documents stored as YAML files
- **Data Catalog** -- Register and search data sources (CSV, API, SQL) with schema information
- **Review Workflow** -- Structured review process for analysis designs
- **Validation Rules** -- Automated quality checks on designs and catalog entries

### WebUI Dashboard

A browser-based dashboard (http://127.0.0.1:3000) provides:

- Overview of all analysis designs and their statuses
- Data catalog browser
- Review tracking

### Bundled Skills

When you run `insight-blueprint --project <path>`, skill templates are copied to `.claude/skills/` in your project:

- `/analysis-design` -- Guided workflow for creating hypothesis documents
- `/catalog-register` -- Step-by-step data source registration

Skills support both English and Japanese trigger phrases.

## CLI Options

```bash
insight-blueprint --project /path/to/project   # Specify project directory
insight-blueprint --headless                    # Suppress browser auto-open
insight-blueprint                               # Use current directory
```

## Development

```bash
poe all   # Run lint + typecheck + test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code style, and how to submit pull requests.

### Tech Stack

| Tool | Purpose |
|------|---------|
| **uv** | Package management |
| **ruff** | Linting and formatting |
| **ty** | Type checking |
| **pytest** | Testing |
| **FastMCP** | MCP server framework |
| **FastAPI** | WebUI backend |

## License

MIT

# insight-blueprint

[![PyPI](https://img.shields.io/pypi/v/insight-blueprint)](https://pypi.org/project/insight-blueprint/)
[![CI](https://github.com/etoyama/insight-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/etoyama/insight-blueprint/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/etoyama)

A Python MCP server for hypothesis-driven data analysis. Manage analysis designs, data catalogs, and review workflows through Claude Code or any MCP-compatible client.

## Quick Start

```bash
# Start the server (zero-install)
uvx insight-blueprint --project /path/to/my-analysis

# Or install permanently
uv tool install insight-blueprint
insight-blueprint --project /path/to/my-analysis

# The server provides 17 MCP tools for Claude Code.
# A WebUI dashboard opens automatically at http://127.0.0.1:3000
```

## Features

### MCP Tools

insight-blueprint exposes 17 tools via the [Model Context Protocol](https://modelcontextprotocol.io/), allowing AI assistants to manage your analysis workflow:

| Category | Tools |
|----------|-------|
| **Analysis Design** | `create_analysis_design`, `update_analysis_design`, `get_analysis_design`, `list_analysis_designs` |
| **Data Catalog** | `add_catalog_entry`, `update_catalog_entry`, `get_table_schema`, `search_catalog` |
| **Domain Knowledge** | `get_domain_knowledge`, `extract_domain_knowledge`, `save_extracted_knowledge`, `suggest_knowledge_for_design`, `suggest_cautions` |
| **Review Workflow** | `transition_design_status`, `save_review_comment`, `save_review_batch` |
| **Project** | `get_project_context` |

### WebUI Dashboard

A browser-based dashboard (http://127.0.0.1:3000) with two tabs:

- **Designs** -- Browse analysis designs, view details (overview + history), and track status transitions
- **Catalog** -- Search domain knowledge, browse data sources, and check cautions

### Bundled Skills

When you run `insight-blueprint --project <path>`, skill templates are copied to `.claude/skills/` in your project:

- `/analysis-design` -- Guided workflow for creating hypothesis documents
- `/analysis-journal` -- Record reasoning steps during analysis (observations, evidence, decisions, questions)
- `/analysis-reflection` -- Structured reflection to draw conclusions or branch hypotheses
- `/catalog-register` -- Step-by-step data source registration
- `/data-lineage` -- Track data transformations and export lineage diagrams (Mermaid)

Skills support both English and Japanese trigger phrases.

### Analysis Workflow

Skills chain together to support the full hypothesis-driven analysis lifecycle:

```
/analysis-design (create hypothesis)
    ↓
/analysis-journal (record reasoning: observe → hypothesize → evidence → decide)
    ↓
/analysis-reflection (reflect → conclude or branch)
    ↓
/catalog-register (register findings as domain knowledge)
```

Each design has an `analysis_intent` field (`exploratory`, `confirmatory`, or `mixed`) to distinguish whether you're testing a specific hypothesis or exploring data for patterns. The Insight Journal (`.insight/designs/{id}_journal.yaml`) tracks your reasoning process with 8 event types mapped to the Narrative Scaffolding framework (Huang+ IUI 2026).

## CLI Options

```bash
insight-blueprint --project /path/to/project   # Specify project directory
insight-blueprint --headless                    # Suppress browser auto-open
insight-blueprint --version                     # Show version
insight-blueprint                               # Use current directory
```

## Development

Requires **Python 3.11+**, **uv**, and **Node.js** (for frontend build).

```bash
git clone https://github.com/etoyama/insight-blueprint.git
cd insight-blueprint
uv sync --all-extras

# Build frontend assets (required for WebUI)
poe build-frontend

# Run lint + typecheck + test
poe all
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

## Support

If you find this project useful, consider buying me a coffee.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/etoyama)

## License

MIT

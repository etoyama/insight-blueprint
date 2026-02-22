# insight-blueprint — Technology Decisions

> **Version**: 1.0.0 (2026-02-18)
> **Status**: Active
> **Source**: DESIGN.md v1.1.0 — Sections 2, 8, 11

## Distribution

- **Package**: PyPI, `uvx insight-blueprint` (Python >=3.11, uv>=0.5)
- **Build backend**: hatchling (with `artifacts` config for static frontend files)
- **Entry point**: `insight-blueprint = insight_blueprint.cli:main`

## MCP Server

- **Library**: fastmcp>=2.0 (jlowin/fastmcp) — Pydantic-native, Inspector UI
- **Transport**: stdio (Claude Code standard for local stdio integration)
- **Process model**: Single process — MCP (stdio) + WebUI (HTTP) in one command
  - `mcp.run()` blocks main thread (stdin/stdout for MCP protocol)
  - uvicorn runs on daemon background thread (must start BEFORE `mcp.run()`)

## WebUI

- **Backend**: FastAPI>=0.115 + uvicorn (daemon thread, port auto-detect)
- **Frontend**: React 19 + Vite 6 + Tailwind CSS + shadcn/ui (pre-built, bundled in wheel)
- **Static files**: `src/insight_blueprint/static/` — hatch `artifacts` config for git-ignored files
- **Port strategy**: `socket.bind(('', 0))` → OS selects free port, default 3000
- **Browser**: opens by default, `--headless` flag to suppress

## Storage

- **Primary**: YAML files in `.insight/` directory (ruamel.yaml — preserves analyst comments)
- **Search index**: SQLite FTS5, stdlib sqlite3, rebuilt from YAML on every startup
- **Write safety**: `tempfile.mkstemp()` + `os.replace()` (atomic, crash-safe)

## Claude Code Integration

- **Registration**: `.mcp.json` at project root (`claude mcp add --scope project`)
- **Timeout**: `MCP_TIMEOUT=10000` (first run downloads uvx package)
- **Skills**: bundled at `src/insight_blueprint/_skills/`, copied to `.claude/skills/` on init
  - All bundled SKILL.md files must include YAML frontmatter per `.claude/rules/skill-format.md`
- **Path resolution**: `importlib.resources.files()` for installed package paths

## Development Methodology

### TDD (t-wada style)
- Follow the Red-Green-Refactor cycle strictly
  1. **Red**: Write a failing test that describes the desired behavior
  2. **Green**: Write the minimum code to make the test pass (no more)
  3. **Refactor**: Clean up code while keeping all tests green
- Tests are specifications — write tests to define behavior, not to verify implementation
- One failing test at a time; never write production code without a failing test
- Reference: [t-wada/power-assert](https://github.com/power-assert-js/power-assert), TDD talks by @t-wada

### YAGNI (You Aren't Gonna Need It)
- Do not add functionality until it is actually required
- Implement the simplest solution that satisfies the current requirement
- Defer abstractions until there are 3+ concrete use cases (rule of three)
- Delete speculative code; dead code is worse than no code

## Quality Tools

| Tool | Purpose |
|------|---------|
| **uv** | Package management (pip forbidden) |
| **ruff** | Lint + format (line-length 88) |
| **ty** | Type checking (Astral/Rust, replaces mypy) |
| **pytest** | Testing (80%+ coverage target) |
| **pytest-cov** | Coverage reporting |
| **poethepoet** | Task runner (`poe lint` / `poe test` / `poe all`) |

## Key MCP Tools (14 total)

### Design Tools (SPEC-1)
- `create_analysis_design(title, hypothesis_statement, hypothesis_background, parent_id?)` → design YAML
- `get_analysis_design(design_id)` → AnalysisDesign model
- `list_analysis_designs(status?)` → list with filters

### Catalog Tools (SPEC-2)
- `search_catalog(query, source_id?)` → FTS5 results
- `get_table_schema(source_id, table_name)` → ColumnSchema list
- `get_domain_knowledge(source_id)` → DomainKnowledge with cautions
- `add_catalog_entry(source_id, table_name, columns, description)` → stored

### Review Tools (SPEC-3)
- `submit_for_review(design_id)` → status → pending_review
- `save_review_comment(design_id, comment, status)` → persisted
- `extract_domain_knowledge(design_id)` → auto-extract from review comments
- `get_project_context()` → summary of all domain knowledge
- `suggest_cautions(table_names)` → relevant cautions for query

## Startup Sequence

```
uvx insight-blueprint --project /path
  1. Parse CLI args (click)
  2. Init .insight/ directory structure
  3. Copy .claude/skills/ templates (first run only)
  4. Load config from .insight/config.yaml
  5. Rebuild SQLite FTS5 index from YAML files
  6. Start FastAPI on daemon thread (uvicorn)
  7. Open browser (1.5s delay, webbrowser.open)
  8. mcp.run()  ← BLOCKS main thread
```

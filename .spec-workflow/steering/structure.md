# insight-blueprint — Codebase Structure

> **Version**: 1.0.0 (2026-02-18)
> **Status**: Active
> **Source**: DESIGN.md v1.1.0 — Section 2.3

## Repository Layout

```
insight-blueprint/
├── src/insight_blueprint/
│   ├── __init__.py
│   ├── __main__.py         # python -m insight_blueprint
│   ├── cli.py              # CLI entry point (click)
│   ├── server.py           # MCP server (fastmcp)
│   ├── web.py              # FastAPI app (WebUI backend)
│   ├── core/               # Business logic (shared by MCP tools + API)
│   │   ├── __init__.py
│   │   ├── designs.py      # AnalysisDesign CRUD
│   │   ├── catalog.py      # DataCatalog operations
│   │   ├── rules.py        # Rules and domain knowledge
│   │   └── reviews.py      # Review workflow
│   ├── models/             # Pydantic models (single source of truth)
│   │   ├── __init__.py
│   │   ├── design.py       # AnalysisDesign, DesignStatus
│   │   ├── catalog.py      # DataSource, ColumnSchema
│   │   ├── rules.py        # Rule, DomainKnowledge
│   │   └── common.py       # Shared types
│   ├── storage/            # Persistence layer
│   │   ├── __init__.py
│   │   ├── yaml_store.py   # ruamel.yaml read/write + atomic write
│   │   ├── sqlite_store.py # SQLite FTS5 index
│   │   └── project.py      # .insight/ directory management
│   ├── static/             # Pre-built React frontend (wheel artifact, git-ignored)
│   └── _skills/            # Bundled Claude Code skill templates
│       ├── analysis-design/SKILL.md
│       └── data-explorer/SKILL.md
├── frontend/               # React+Vite source (dev only)
│   ├── src/
│   ├── package.json
│   └── vite.config.ts      # outDir: ../src/insight_blueprint/static
├── tests/
│   ├── conftest.py
│   ├── test_designs.py
│   ├── test_catalog.py
│   ├── test_rules.py
│   └── test_storage.py
└── pyproject.toml
```

## Project Storage (.insight/)

```
.insight/
├── config.yaml
├── catalog/
│   ├── sources.yaml
│   └── knowledge/{source_id}.yaml
├── designs/{id}_hypothesis.yaml
└── rules/
    ├── review_rules.yaml
    └── analysis_rules.yaml
```

## Layer Architecture

```
CLI (cli.py)
  ├── MCP Server (server.py)  ─── registers 14 MCP tools
  ├── Web Server (web.py)     ─── FastAPI, 15 REST endpoints
  └── Both ↓
      Core Services (core/)  ─── business logic, shared
          ↓
      Storage (storage/)     ─── YAML primary + SQLite FTS5
          ↓
      .insight/ directory
```

## Coding Conventions

- **All code and comments**: English
- **User-facing responses** (Claude → analyst): Japanese
- **Type hints**: required on all functions
- **Control flow**: early return over deep nesting
- **State**: create new objects instead of mutating existing ones
- **Constants**: UPPER_SNAKE_CASE (no magic numbers)
- **Pydantic models**: shared by MCP, API, AND storage layer — single source of truth
- **File length**: 200–400 lines (max 800)

## Key Invariants

- YAML files are source of truth; SQLite is a read-only derived index
- All YAML writes are atomic (`tempfile.mkstemp()` + `os.replace()`)
- `mcp.run()` is always the LAST call in `cli.py` (blocks stdin/stdout)
- uvicorn starts in daemon thread BEFORE `mcp.run()`
- No locking needed for v1 (single-user, atomic writes prevent corruption)
- `importlib.resources.files()` for skill path resolution in installed packages

## Spec-to-Module Mapping

| Spec | Modules Created |
|------|----------------|
| SPEC-1 | `cli.py`, `server.py`, `models/design.py`, `models/common.py`, `storage/yaml_store.py`, `storage/project.py`, `core/designs.py` |
| SPEC-2 | `models/catalog.py`, `storage/sqlite_store.py`, `core/catalog.py` (+ server.py additions) |
| SPEC-3 | `models/rules.py`, `core/rules.py`, `core/reviews.py` (+ server.py additions) |
| SPEC-4 | `web.py`, `frontend/`, `static/` (build artifact) |
| SPEC-5 | `_skills/`, README, pyproject.toml build config, PyPI release |

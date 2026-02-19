# SPEC-1: core-foundation — Design

> **Spec ID**: SPEC-1
> **Status**: pending_approval
> **Created**: 2026-02-18
> **Source**: DESIGN.md v1.1.0

---

## Overview

SPEC-1 establishes the core foundation of insight-blueprint: a zero-install MCP server
that data scientists can launch with a single `uvx insight-blueprint --project /path` command.
It covers CLI entry point, `.insight/` directory initialization, Pydantic data models,
atomic YAML persistence, and three MCP tools (`create_analysis_design`, `get_analysis_design`,
`list_analysis_designs`) that allow Claude Code to manage hypothesis-driven analysis design
documents without manual file system access.

## Steering Document Alignment

### Technical Standards (tech.md)

This design follows the documented technical standards:

- **MCP server**: fastmcp>=2.0 with stdio transport (Claude Code standard for local integration)
- **Storage**: ruamel.yaml for comment-preserving YAML; `tempfile.mkstemp()` + `os.replace()` for atomic writes
- **Quality tools**: ruff (lint/format, line-length 88), ty (type checking, replaces mypy), pytest (80%+ coverage target)
- **Methodology**: TDD (Red-Green-Refactor) and YAGNI — implement only what SPEC-1 requires; no WebUI, no daemon thread
- **Process model**: `mcp.run()` blocks main thread (stdin/stdout for MCP protocol); uvicorn daemon thread is SPEC-4 scope

### Project Structure (structure.md)

The implementation follows the `src/` layout convention with three-layer separation:

- **src/insight_blueprint/** — top-level package with `__init__.py` and `__main__.py`
- **Three-layer architecture**: `cli.py` → `server.py` → `core/designs.py` → `storage/`
- **One-directional dependency**: CLI → MCP → Core → Storage; no reverse dependencies
- **Modules created in SPEC-1**: `cli.py`, `server.py`, `models/design.py`, `models/common.py`, `storage/yaml_store.py`, `storage/project.py`, `core/designs.py`
- **Key Invariants**: `mcp.run()` is always the last call in `cli.py`; all YAML writes are atomic; `_service` is wired by `init_project()` before any MCP tool is called

## Code Reuse Analysis

### Existing Components to Leverage

SPEC-1 is the first spec, so no existing application code is available to leverage.
The following external libraries provide the foundational building blocks:

- **fastmcp**: MCP tool registration via `@mcp.tool()` decorator and stdio transport
- **Pydantic v2 BaseModel**: type-safe data modeling, serialization, and validation for `AnalysisDesign`
- **ruamel.yaml**: YAML read/write with analyst comment preservation (vs pyyaml which strips comments)
- **click**: CLI argument parsing with `@click.command()` and `@click.option()`

### Integration Points

- **Claude Code `.mcp.json`**: `init_project()` registers the MCP server entry in `.mcp.json` at project root so Claude Code auto-discovers it on next launch
- **SPEC-2 onward**: `storage/yaml_store.py` and `storage/project.py` will be extended; `server.py` will receive additional `@mcp.tool()` registrations without changing existing tools; `core/designs.py` patterns will be replicated for catalog and rules modules

## Architecture

### Modular Design Principles

- **Single File Responsibility**: Each file handles one specific concern (`cli.py` = entry point, `server.py` = MCP tools, `core/designs.py` = business logic, `storage/yaml_store.py` = YAML I/O)
- **Component Isolation**: Layers are independently testable; `core/designs.py` can be unit-tested without importing `server.py` or `cli.py`
- **Service Layer Separation**: MCP tools (`server.py`) delegate to `DesignService` (`core/designs.py`) which delegates to `yaml_store.py` — no cross-layer skipping allowed
- **Utility Modularity**: `models/common.py` holds only shared utilities (`now_jst()`); not mixed into larger modules

### Component Diagram (SPEC-1 scope)

```
Claude Code (AI Client)
       |
  stdio (MCP Protocol)
       |
  +---------------------------+
  |  insight-blueprint        |
  |  (Python Process)         |
  |                           |
  |  cli.py (entry point)     |
  |    ├── init_project()     |
  |    └── mcp.run() ← BLOCKS |
  |                           |
  |  server.py (FastMCP)      |
  |    ├── create_analysis_design  |
  |    ├── get_analysis_design     |
  |    └── list_analysis_designs   |
  |           ↓               |
  |  core/designs.py          |
  |           ↓               |
  |  storage/yaml_store.py    |
  |  storage/project.py       |
  +---------------------------+
           ↓
  .insight/designs/*.yaml
```

### Key Design Decision: stdio Transport

fastmcp's `mcp.run()` uses stdio transport. This is the correct choice because:
- Claude Code's `claude mcp add` expects stdio by default for local integrations
- No network configuration required, no port conflicts
- `mcp.run()` blocks the main thread — this is intentional design

SPEC-4 adds uvicorn on a daemon thread. SPEC-1 has no HTTP server.

## Components and Interfaces

### `cli.py`

- **Purpose:** CLI entry point — parses `--project` and `--headless` options, validates project path existence, calls `init_project()`, and launches MCP server via `mcp.run()`
- **Interfaces:** `main(project: str, headless: bool) -> None` (click command, registered as `insight-blueprint` console script)
- **Dependencies:** `click`, `storage/project.py:init_project`, `server.py:mcp`
- **Reuses:** None (first module in the dependency chain)

### `server.py`

- **Purpose:** FastMCP server — registers 3 async MCP tools and holds a module-level `_service` reference that is initialized by `init_project()` before `mcp.run()` is called
- **Interfaces:** `create_analysis_design(title, hypothesis_statement, hypothesis_background, parent_id?) -> dict`, `get_analysis_design(design_id) -> dict`, `list_analysis_designs(status?) -> dict` (all async, decorated with `@mcp.tool()`)
- **Dependencies:** `fastmcp.FastMCP`, `core/designs.py:DesignService`
- **Reuses:** None

### `models/common.py`

- **Purpose:** Shared timezone utility — provides `now_jst()` for JST-aware datetime defaults used across all Pydantic models
- **Interfaces:** `now_jst() -> datetime`
- **Dependencies:** `zoneinfo.ZoneInfo`
- **Reuses:** None

### `models/design.py`

- **Purpose:** Pydantic data model — defines `DesignStatus` enum and `AnalysisDesign` BaseModel with all required fields and JST timezone defaults
- **Interfaces:** `DesignStatus` (str Enum with 5 values), `AnalysisDesign` (BaseModel with 9 fields)
- **Dependencies:** `pydantic.BaseModel`, `pydantic.Field`, `models/common.py:now_jst`
- **Reuses:** None

### `storage/project.py`

- **Purpose:** Project initialization — creates `.insight/` directory structure idempotently, initializes config and rules YAML stubs, wires `DesignService` into `server._service`
- **Interfaces:** `init_project(project_path: Path) -> None`
- **Dependencies:** `pathlib.Path`, `core/designs.py:DesignService`, `server._service`
- **Reuses:** None

### `storage/yaml_store.py`

- **Purpose:** Atomic YAML I/O — provides crash-safe read and write operations using `tempfile.mkstemp()` + `os.replace()` to guarantee no partial writes
- **Interfaces:** `read_yaml(path: Path) -> dict`, `write_yaml(path: Path, data: dict) -> None`
- **Dependencies:** `ruamel.yaml.YAML`, `tempfile`, `os`
- **Reuses:** None

### `core/designs.py`

- **Purpose:** Business logic for analysis design CRUD — manages sequential ID generation (H01, H02, ...), creation, retrieval, and status-filtered listing of `AnalysisDesign` entities
- **Interfaces:** `DesignService(project_path: Path)` with methods `create_design(title, hypothesis_statement, hypothesis_background, parent_id?) -> AnalysisDesign`, `get_design(design_id) -> AnalysisDesign | None`, `list_designs(status?) -> list[AnalysisDesign]`
- **Dependencies:** `models/design.py:AnalysisDesign`, `storage/yaml_store.py:read_yaml, write_yaml`
- **Reuses:** None

## Data Models

### File: `.insight/designs/{id}_hypothesis.yaml`

```yaml
id: H01
title: Foreign population vs crime rate correlation
hypothesis_statement: No positive correlation exists between...
hypothesis_background: |
  ...
status: draft
parent_id: null
metrics: {}
created_at: "2026-02-18T10:00:00+09:00"
updated_at: "2026-02-18T10:00:00+09:00"
```

ID generation: `H{N:02d}` (N = existing design file count + 1)
Range: H01–H99 (sufficient for typical EDA sessions)

## Error Handling

### Error Scenarios

1. **Design not found** — `get_analysis_design("H99")` where H99 does not exist
   - **Handling:** `DesignService.get_design()` returns `None`; `server.py` converts to `{"error": "Design 'H99' not found"}`
   - **User Impact:** Claude receives an error dict and can inform the analyst that the design ID does not exist

2. **Invalid project path** — `--project /nonexistent` passed to CLI
   - **Handling:** `click.ClickException` raised with human-readable message before any initialization
   - **User Impact:** Error message printed to stderr with exit code 1; no partial state is created

3. **YAML write failure** — I/O error occurs during `write_yaml()`
   - **Handling:** `os.replace()` is never called; tempfile is cleaned up in the `except` block; original YAML is unchanged
   - **User Impact:** `create_analysis_design()` raises an exception; Claude reports a storage error; analyst can retry

4. **Service not initialized** — MCP tool called before `init_project()`
   - **Handling:** `get_service()` raises `RuntimeError("Service not initialized. Call init_project() first.")`
   - **User Impact:** MCP protocol returns an error response; only possible in test/development scenarios since `cli.py` always calls `init_project()` before `mcp.run()`

## Testing Strategy

### Unit Testing

Tests are organized by module boundary:

| File | Coverage Target |
|------|----------------|
| `tests/test_designs.py` | `core/designs.py` + `models/design.py` |
| `tests/test_storage.py` | `storage/yaml_store.py` + `storage/project.py` |

**test_designs.py** test cases:
- `test_create_design_returns_design_with_generated_id` — happy path
- `test_create_design_saves_yaml_file` — filesystem side effect
- `test_create_design_sequential_ids` — H01, H02, H03 order
- `test_get_design_returns_correct_design` — round-trip
- `test_get_design_returns_none_for_missing_id` — not found
- `test_list_designs_returns_all` — multiple designs
- `test_list_designs_filtered_by_status` — status filter

**test_storage.py** test cases:
- `test_write_yaml_creates_file` — basic write
- `test_write_yaml_is_atomic` — failure cleanup
- `test_read_yaml_returns_empty_for_missing_file` — graceful missing
- `test_init_project_creates_directory_structure` — idempotent

**Test infrastructure** (`tests/conftest.py`):

```python
@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Returns a temporary project directory with .insight/ initialized."""
    from insight_blueprint.storage.project import init_project
    init_project(tmp_path)
    return tmp_path
```

### Integration Testing

- CLI-to-CRUD round-trip: `init_project()` → `create_analysis_design()` → verify YAML file created → `get_analysis_design()` → verify data matches → `list_analysis_designs()` → verify count and status filter
- Covered in `tests/test_integration.py` (implemented in task 1.6)
- Tests run against a real `tmp_path` fixture; storage layer is not mocked

### End-to-End Testing

MCP protocol E2E testing (connecting a real MCP client to the stdio server) is **out of scope for SPEC-1**. The integration tests in `test_integration.py` cover the full business logic stack end-to-end. Full MCP protocol E2E will be addressed when a fastmcp stdio test harness is available in a later spec.

---

## Dependencies (SPEC-1 only)

```toml
[project]
dependencies = [
    "fastmcp>=2.0",
    "pydantic>=2.10",
    "ruamel.yaml>=0.18",
    "click>=8.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=6.0",
    "ruff>=0.8",
    "ty>=0.1",
    "poethepoet>=0.31",
]
```

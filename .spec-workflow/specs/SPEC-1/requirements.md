# SPEC-1: core-foundation — Requirements

> **Spec ID**: SPEC-1
> **Feature Name**: core-foundation
> **Status**: pending_approval
> **Created**: 2026-02-18
> **Depends On**: none (first spec)

---

## User Stories

### US-1: First-Run Setup
As a data scientist using Claude Code,
I want to run `uvx insight-blueprint --project /path/to/analysis` once,
So that the `.insight/` directory is initialized and Claude Code can immediately call MCP tools.

### US-2: Create Analysis Design via Claude
As a data scientist,
I want Claude to call `create_analysis_design()` with my hypothesis,
So that a structured YAML file is saved to `.insight/designs/` and I can reference it later.

### US-3: Retrieve and List Designs
As a data scientist,
I want Claude to call `get_analysis_design(design_id)` or `list_analysis_designs()`,
So that I can review existing hypotheses without opening the filesystem manually.

---

## Functional Requirements

### FR-1: CLI Entry Point
- `uvx insight-blueprint --project <path>` starts the MCP server
- `--project` defaults to current working directory if omitted
- `--headless` flag suppresses browser opening (for automated/CI use)
- Exits with a meaningful error message if the project path does not exist

### FR-2: Project Initialization
- Creates `.insight/` directory structure on first run (idempotent — safe to call multiple times)
- Directory structure:
  ```
  .insight/
  ├── config.yaml
  ├── catalog/
  │   ├── sources.yaml
  │   └── knowledge/
  ├── designs/
  └── rules/
      ├── review_rules.yaml
      └── analysis_rules.yaml
  ```
- Copies `.claude/skills/` templates on first run (only if `.claude/skills/analysis-design/` does not exist)
- Registers `.mcp.json` at project root if not already present

### FR-3: Pydantic Data Models
- `AnalysisDesign` model with fields:
  - `id: str` — auto-generated (e.g., `H01`, `H02`)
  - `title: str`
  - `hypothesis_statement: str`
  - `hypothesis_background: str`
  - `status: DesignStatus` — `draft | active | supported | rejected | inconclusive`
  - `parent_id: str | None`
  - `metrics: dict`
  - `created_at: datetime`
  - `updated_at: datetime`
- `DesignStatus` enum
- All models must be importable from `insight_blueprint.models`

### FR-4: YAML Storage Layer
- `yaml_store.py` reads/writes YAML using ruamel.yaml (preserves comments)
- All writes are atomic: `tempfile.mkstemp()` + `os.replace()`
- `project.py` manages `.insight/` directory paths (no hardcoded paths)

### FR-5: Core Design Service
- `core/designs.py` implements:
  - `create_design(title, hypothesis_statement, hypothesis_background, parent_id?) → AnalysisDesign`
    - Auto-generates `id` as `H{N:02d}` (next sequential ID)
    - Sets `status = "draft"`
    - Saves to `.insight/designs/{id}_hypothesis.yaml`
  - `get_design(design_id) → AnalysisDesign | None`
  - `list_designs(status?: DesignStatus) → list[AnalysisDesign]`
    - Returns all designs if `status` is None, filtered otherwise

### FR-6: MCP Tools (3 tools)
- Registered via fastmcp `@mcp.tool()` decorator in `server.py`
- `create_analysis_design(title, hypothesis_statement, hypothesis_background, parent_id?) → dict`
  - Returns `{id, title, status, message}`
- `get_analysis_design(design_id) → dict`
  - Returns full AnalysisDesign as dict
  - Returns error dict if not found
- `list_analysis_designs(status?) → dict`
  - Returns `{designs: [...], count: int}`
- All tools are async-compatible (fastmcp handles event loop)

---

## Non-Functional Requirements

### NFR-1: Performance
- CLI startup (from cold `uvx`) completes in < 5 seconds (excluding first-run uvx download)
- `create_analysis_design()` completes in < 100ms (local YAML write)
- `list_analysis_designs()` completes in < 200ms for up to 100 designs

### NFR-2: Reliability
- All YAML writes are atomic — no partial writes on crash
- Idempotent initialization — running `uvx insight-blueprint` twice does not corrupt data

### NFR-3: Package Distribution
- `uvx insight-blueprint` works without any prior installation
- Python >=3.11 required
- Single `uv add insight-blueprint` installs all runtime dependencies

### NFR-4: Code Quality
- ruff check passes (line-length 88)
- ty check passes (all functions have type annotations)
- pytest coverage >= 80% for `core/` and `storage/` modules

---

## Acceptance Criteria

### AC-1: CLI Starts MCP Server
```
$ uvx insight-blueprint --project /tmp/test-project
# → creates /tmp/test-project/.insight/ directory
# → prints "insight-blueprint MCP server started"
# → mcp.run() blocks and waits for MCP protocol messages
```

### AC-2: MCP Tool Round-Trip
```python
# Claude calls:
result = await create_analysis_design(
    title="Foreign population vs crime rate",
    hypothesis_statement="No positive correlation between...",
    hypothesis_background="...",
)
# → result["id"] == "H01"
# → .insight/designs/H01_hypothesis.yaml exists
# → get_analysis_design("H01") returns the same data
```

### AC-3: List with Status Filter
```python
designs = await list_analysis_designs(status="draft")
# → returns only designs with status == "draft"
# → count matches the number of draft designs
```

### AC-4: Atomic Write Safety
- Simulating a crash during YAML write (e.g., kill -9) does not produce corrupted YAML
- YAML file is either the previous version or the new version — never partial

### AC-5: Tests Pass
```bash
poe test  # pytest -v
# → all tests pass
# → coverage >= 80% for core/ and storage/
```

---

## Out of Scope (SPEC-1)

- Data catalog (SPEC-2)
- Review workflow (SPEC-3)
- WebUI dashboard (SPEC-4)
- PyPI publishing (SPEC-5)
- SQLite FTS5 index (SPEC-2)
- FastAPI web server (SPEC-4)
- `update_analysis_design()` MCP tool (SPEC-3, as part of review workflow)

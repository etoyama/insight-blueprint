# Code Quality Review: SPEC-1, SPEC-2, SPEC-3

**Date**: 2026-02-26
**Reviewer**: quality-reviewer (automated)
**Scope**: All Python source files across SPEC-1 (core-foundation), SPEC-2 (data-catalog), SPEC-3 (review-workflow)

## Linting & Formatting

- `uv run ruff check .` — All checks passed
- `uv run ruff format --check .` — 33 files already formatted

## Summary

| Severity | Count |
|----------|-------|
| High     | 2     |
| Medium   | 7     |
| Low      | 5     |

---

## High Severity Findings

### H1: Mutation of shared data structures in `ReviewService.save_extracted_knowledge`

- **File**: `src/insight_blueprint/core/reviews.py:224-236`
- **Principle Violated**: Immutability (coding-principles.md)
- **Current Code**:
  ```python
  entries_list: list[dict[str, Any]] = data.get("entries", [])
  # ...
  entries_list.append(entry.model_dump(mode="json"))
  data["entries"] = entries_list
  ```
- **Issue**: `entries_list` is obtained via `data.get("entries", [])`. When the key exists, this returns a reference to the mutable list inside `data`, and then `.append()` mutates it in-place. The subsequent `data["entries"] = entries_list` is a no-op in that case. When the key does not exist, the default `[]` is a fresh list but it is never assigned back until append — a minor inconsistency. More critically, `existing_keys.add(entry.key)` mutates the set in-place (acceptable for local variables, but the pattern overall is heavy on mutation).
- **Suggested Improvement**: Build a new entries list immutably:
  ```python
  existing_entries: list[dict[str, Any]] = data.get("entries", [])
  existing_keys = {e["key"] for e in existing_entries}
  new_entries = []
  for entry in entries:
      if entry.key not in existing_keys:
          new_entries.append(entry.model_dump(mode="json"))
          existing_keys.add(entry.key)
          saved.append(entry)
  write_yaml(ek_path, {**data, "entries": [*existing_entries, *new_entries]})
  ```

### H2: `cli.py` main function does too many things (Service Wiring)

- **File**: `src/insight_blueprint/cli.py:23-63`
- **Principle Violated**: Single Responsibility
- **Current Code**: The `main()` function validates the path, calls `init_project`, wires 4 separate services into the server module via inline imports, rebuilds the FTS index, and starts the MCP server — all in one 40-line function.
- **Issue**: This is the only "High" purely structural issue. As services grow, this function becomes a fragile wiring point. Each new service requires adding 3-4 lines of import + assignment + optional initialization.
- **Suggested Improvement**: Extract service wiring into a dedicated function:
  ```python
  def _wire_services(project_path: Path) -> None:
      """Wire all service instances into the server module."""
      import insight_blueprint.server as server_module
      from insight_blueprint.core.catalog import CatalogService
      from insight_blueprint.core.designs import DesignService
      from insight_blueprint.core.reviews import ReviewService
      from insight_blueprint.core.rules import RulesService

      server_module._service = DesignService(project_path)
      catalog_service = CatalogService(project_path)
      server_module._catalog_service = catalog_service
      catalog_service.rebuild_index()
      server_module._review_service = ReviewService(project_path, server_module._service)
      server_module._rules_service = RulesService(project_path, catalog_service)
  ```

---

## Medium Severity Findings

### M1: Magic number `80` in title truncation

- **File**: `src/insight_blueprint/core/reviews.py:197`
- **Principle Violated**: No Magic Numbers
- **Current Code**:
  ```python
  title=content[:80],
  ```
- **Suggested Improvement**:
  ```python
  _MAX_TITLE_LENGTH = 80
  # ...
  title=content[:_MAX_TITLE_LENGTH],
  ```

### M2: Magic number `32` in FTS5 snippet length

- **File**: `src/insight_blueprint/storage/sqlite_store.py:28`
- **Principle Violated**: No Magic Numbers
- **Current Code**:
  ```python
  "snippet(catalog_fts, 3, '<b>', '</b>', '...', 32) as snippet, "
  ```
- **Suggested Improvement**: Define `_SNIPPET_MAX_TOKENS = 32` as a module constant and interpolate.

### M3: Magic number `20` in search limit default

- **File**: `src/insight_blueprint/storage/sqlite_store.py:108`
- **Principle Violated**: No Magic Numbers
- **Current Code**:
  ```python
  def search_index(db_path: Path, query: str, limit: int = 20) -> list[dict]:
  ```
- **Suggested Improvement**: `_DEFAULT_SEARCH_LIMIT = 20`

### M4: `get_project_context` return type is `dict` (untyped)

- **File**: `src/insight_blueprint/core/rules.py:21`
- **Principle Violated**: Type Hints Required
- **Current Code**:
  ```python
  def get_project_context(self) -> dict:
  ```
- **Issue**: The return type is a bare `dict` without key/value type annotations. Similarly, internal variables like `knowledge_entries: list[dict]` and `rules: list[dict]` lack type specificity.
- **Suggested Improvement**: At minimum use `dict[str, Any]`:
  ```python
  def get_project_context(self) -> dict[str, Any]:
  ```
  Ideally, define a `ProjectContext` TypedDict or dataclass.

### M5: `suggest_cautions` return type is bare `list[dict]`

- **File**: `src/insight_blueprint/core/rules.py:75`
- **Principle Violated**: Type Hints Required
- **Current Code**:
  ```python
  def suggest_cautions(self, table_names: list[str]) -> list[dict]:
  ```
- **Suggested Improvement**: `list[dict[str, Any]]` at minimum, or return `list[DomainKnowledgeEntry]` directly to preserve type safety across the boundary.

### M6: Duplicate validation logic in `save_review_comment`

- **File**: `src/insight_blueprint/core/reviews.py:86-100`
- **Principle Violated**: Single Responsibility / DRY
- **Current Code**:
  ```python
  try:
      target_status = DesignStatus(status)
  except ValueError:
      valid = ", ".join(...)
      raise ValueError(...) from None
  if target_status not in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]:
      valid = ", ".join(...)
      raise ValueError(...)
  ```
- **Issue**: The error message construction (`valid = ", ".join(...)`) is duplicated. The two validation steps could be combined: first check if it's a valid DesignStatus, then check if it's a valid transition — but both produce the same error message.
- **Suggested Improvement**: Combine into a single validation:
  ```python
  valid_statuses = VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]
  try:
      target_status = DesignStatus(status)
  except ValueError:
      target_status = None
  if target_status is None or target_status not in valid_statuses:
      valid = ", ".join(s.value for s in valid_statuses)
      raise ValueError(f"Invalid post-review status '{status}'. Valid: {valid}")
  ```

### M7: Inconsistent `dict` vs `dict[str, Any]` type annotations across codebase

- **Files**: Multiple files
  - `src/insight_blueprint/models/design.py:32` — `metrics: dict`
  - `src/insight_blueprint/models/catalog.py:57` — `connection: dict`
  - `src/insight_blueprint/models/catalog.py:58` — `schema_info: dict`
  - `src/insight_blueprint/core/rules.py:44` — `knowledge_entries: list[dict]`
  - `src/insight_blueprint/server.py:143` — `updates: dict`
- **Principle Violated**: Type Hints Required
- **Issue**: Bare `dict` is used extensively. While acceptable for Pydantic model fields that accept arbitrary JSON, local variables and return types should be annotated with `dict[str, Any]` for clarity.
- **Suggested Improvement**: Use `dict[str, Any]` consistently for variables and return types. For Pydantic model fields where the schema is truly open, bare `dict` is acceptable but should be documented.

---

## Low Severity Findings

### L1: Inline import of `DesignStatus` inside `update_analysis_design`

- **File**: `src/insight_blueprint/server.py:140`
- **Current Code**:
  ```python
  @mcp.tool()
  async def update_analysis_design(...):
      ...
      from insight_blueprint.models.design import DesignStatus
  ```
- **Issue**: `DesignStatus` is already available at module level via `TYPE_CHECKING` block, but only for type checking. The inline import is technically correct for runtime but inconsistent — it also appears at line 197 in `list_analysis_designs`. Meanwhile other tool functions like `submit_for_review` access `DesignStatus` indirectly through the service layer.
- **Suggested Improvement**: Move `DesignStatus` to a regular import at the top of the file (it's a lightweight enum, not a heavy import).

### L2: `_open_connection` could use context manager pattern

- **File**: `src/insight_blueprint/storage/sqlite_store.py:36-45`
- **Current Code**: Every caller does `conn = _open_connection(...)` / `try: ... finally: conn.close()`.
- **Issue**: The try/finally pattern is repeated 6 times across `build_index`, `search_index`, `insert_document`, `delete_source_documents`, `replace_source_documents`. This is not a bug but creates boilerplate.
- **Suggested Improvement**: Consider making `_open_connection` a context manager:
  ```python
  from contextlib import contextmanager

  @contextmanager
  def _open_connection(db_path: Path):
      conn = sqlite3.connect(str(db_path))
      try:
          conn.execute("PRAGMA journal_mode=WAL")
          conn.execute("PRAGMA busy_timeout=5000")
          yield conn
      finally:
          conn.close()
  ```

### L3: `read_yaml` return type annotation is bare `dict`

- **File**: `src/insight_blueprint/storage/yaml_store.py:16`
- **Current Code**:
  ```python
  def read_yaml(path: Path) -> dict:
  ```
- **Suggested Improvement**: `dict[str, Any]` for precision.

### L4: No docstring on `_make_yaml` explaining configuration choice

- **File**: `src/insight_blueprint/storage/yaml_store.py:10-12`
- **Current Code**:
  ```python
  def _make_yaml() -> YAML:
      yaml = YAML()
      yaml.preserve_quotes = True
      return yaml
  ```
- **Issue**: Minor — the `preserve_quotes = True` choice is not documented. Future maintainers may wonder why.
- **Suggested Improvement**: Add a brief inline comment: `# preserve_quotes: keep original YAML quote style on round-trip`

### L5: `AnalysisDesign.metrics` and `explanatory` use bare `dict`/`list[dict]`

- **File**: `src/insight_blueprint/models/design.py:32-34`
- **Current Code**:
  ```python
  metrics: dict = Field(default_factory=dict)
  explanatory: list[dict] = Field(default_factory=list)
  chart: list[dict] = Field(default_factory=list)
  ```
- **Issue**: These are intentionally flexible schema fields, so bare `dict` is acceptable. However, they lack any docstring or comment explaining what shape the data takes.
- **Suggested Improvement**: Add field descriptions via `Field(description="...")` to clarify expected shape.

---

## Architecture Assessment

### Three-Layer Separation (CLI -> Core -> Storage)

The three-layer architecture is well-maintained:

| Layer | Files | Assessment |
|-------|-------|------------|
| CLI | `cli.py` | Handles argument parsing and service wiring only |
| Core | `core/designs.py`, `core/catalog.py`, `core/reviews.py`, `core/rules.py` | Business logic with no direct CLI or server dependencies |
| Storage | `storage/yaml_store.py`, `storage/sqlite_store.py`, `storage/project.py` | Pure I/O, no business logic |
| Server | `server.py` | MCP tool definitions delegate to Core layer |
| Models | `models/*.py` | Pure Pydantic data classes, no logic |

**No cross-layer skipping detected.** Server tools call Core services, Core services call Storage functions. Models are shared across layers (acceptable).

### File Length Assessment

| File | Lines | Status |
|------|-------|--------|
| `server.py` | 526 | Within range (target 200-400, max 800) |
| `core/reviews.py` | 263 | Good |
| `core/catalog.py` | 218 | Good |
| `core/rules.py` | 116 | Good |
| `core/designs.py` | 124 | Good |
| `storage/sqlite_store.py` | 232 | Good |
| `storage/yaml_store.py` | 42 | Good |
| `storage/project.py` | 108 | Good |
| `cli.py` | 64 | Good |
| `models/design.py` | 39 | Good |
| `models/review.py` | 21 | Good |
| `models/catalog.py` | 82 | Good |

`server.py` at 526 lines is the largest file but remains under 800. As more MCP tools are added, consider splitting into separate tool modules.

### Overall Code Quality

The codebase demonstrates strong adherence to coding principles:
- Early return pattern is used consistently
- Functions are reasonably sized (most under 20 lines)
- Naming conventions are consistent (snake_case, PascalCase)
- Atomic file writes are used throughout (YAML and JSON)
- Error handling is appropriate at boundaries
- Type hints are present on all public functions (though some use bare `dict`)

---

## Recommendations (Priority Order)

1. **[High]** Extract service wiring from `cli.py:main()` into a dedicated function
2. **[High]** Fix mutation pattern in `save_extracted_knowledge` to use immutable approach
3. **[Medium]** Replace magic numbers with named constants (`_MAX_TITLE_LENGTH`, `_DEFAULT_SEARCH_LIMIT`, `_SNIPPET_MAX_TOKENS`)
4. **[Medium]** Consolidate duplicate validation in `save_review_comment`
5. **[Medium]** Improve type annotations: `dict` -> `dict[str, Any]` for variables and return types
6. **[Low]** Make `_open_connection` a context manager to reduce boilerplate
7. **[Low]** Move `DesignStatus` to a regular import in `server.py`

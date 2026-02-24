# SPEC-2: data-catalog — Design

> **Spec ID**: SPEC-2
> **Status**: pending_approval
> **Created**: 2026-02-24
> **Depends On**: SPEC-1 (core-foundation), SPEC-1a (hypothesis-enrichment)

---

## Overview

SPEC-2 adds a data catalog layer to insight-blueprint. Data scientists register data
sources (CSV, API, SQL) with column-level schema information, and Claude Code searches
across sources and domain knowledge via FTS5 full-text search. The catalog follows the
same 3-layer architecture as SPEC-1: MCP tools (server.py) → CatalogService (core/catalog.py)
→ Storage (yaml_store.py + sqlite_store.py). YAML files remain the source of truth;
SQLite FTS5 is a derived index rebuilt on startup and updated incrementally when
sources are added or updated during a session.

## Steering Document Alignment

### Technical Standards (tech.md)

- **Storage**: Per-source YAML files in `.insight/catalog/sources/{id}.yaml` and
  `.insight/catalog/knowledge/{id}.yaml` — YAML remains source of truth per tech.md mandate
- **Search index**: SQLite FTS5 via stdlib `sqlite3` with `trigram` tokenizer — full
  rebuild from YAML on startup per tech.md startup sequence (step 5), plus incremental
  updates on `add_source()` and `update_source()` during a session
- **MCP tools**: 5 new async tools registered with `@mcp.tool()` on the existing
  `FastMCP("insight-blueprint")` instance
- **Quality**: TDD (Red-Green-Refactor), ruff + ty + pytest, 80%+ coverage target
- **No new dependencies**: Uses stdlib `sqlite3` for FTS5 — no additional packages

### Project Structure (structure.md)

- **New modules** per Spec-to-Module Mapping: `models/catalog.py`, `storage/sqlite_store.py`,
  `core/catalog.py`
- **Modified modules**: `server.py` (+5 tools), `cli.py` (+CatalogService wiring),
  `storage/project.py` (+sources dir, +.sqlite dir, +catalog-register skill copy)
- **3-layer separation**: MCP tools → CatalogService → yaml_store + sqlite_store
- **One-directional dependencies**: server.py → core/catalog.py → storage/*

## Code Reuse Analysis

### Existing Components to Leverage

- **`now_jst()`** (`models/common.py`): Timestamps for `DataSource.created_at/updated_at`
- **`read_yaml/write_yaml`** (`storage/yaml_store.py`): All YAML persistence for sources
  and knowledge files — atomic writes via `tempfile.mkstemp()` + `os.replace()`
- **`DesignService` pattern** (`core/designs.py`): CatalogService follows the same structure:
  constructor with `project_path`, glob-based listing, `model_copy(update=...)` for partial
  updates, `_dir` path convention
- **`get_service()` guard pattern** (`server.py`): `get_catalog_service()` follows same
  `RuntimeError` guard for uninitialized service
- **`_copy_skills_template`** (`storage/project.py`): Extended to also copy `catalog-register`
  skill from bundled `_skills/`
- **MCP error dict pattern** (`server.py`): `ValueError` → `{"error": str(e)}` conversion
- **`tmp_project` fixture** (`tests/conftest.py`): Reused for all catalog tests

### Integration Points

- **`server.py`**: New `_catalog_service` module-level reference + 5 `@mcp.tool()` functions
  added alongside existing 4 design tools
- **`cli.py`**: `CatalogService` instantiated and wired before `mcp.run()`;
  `rebuild_index()` called after wiring
- **`storage/project.py`**: `_create_insight_dirs()` extended to create `catalog/sources/`
  directory and `.sqlite/` directory; `_copy_skills_template()` extended for catalog-register

## Architecture

### Modular Design Principles

- **Single File Responsibility**: `models/catalog.py` = data models only,
  `storage/sqlite_store.py` = FTS5 index only, `core/catalog.py` = CRUD + search logic only
- **Component Isolation**: `sqlite_store.py` has no dependency on Pydantic models —
  receives plain dicts for indexing. `CatalogService` orchestrates YAML and FTS5 layers
- **Service Layer Separation**: MCP tools → CatalogService → yaml_store + sqlite_store.
  No cross-layer skipping
- **Utility Modularity**: FTS5 operations isolated in `sqlite_store.py` — easy to replace
  with alternative search backend if needed

### Component Diagram (SPEC-2 additions)

```
Claude Code (AI Client)
       |
  stdio (MCP Protocol)
       |
  +------------------------------------------+
  |  insight-blueprint (Python Process)      |
  |                                          |
  |  cli.py (entry point)                    |
  |    ├── init_project()                    |
  |    ├── wire DesignService                |
  |    ├── wire CatalogService  ← NEW        |
  |    ├── rebuild_index()      ← NEW        |
  |    └── mcp.run() ← BLOCKS               |
  |                                          |
  |  server.py (FastMCP)                     |
  |    ├── [4 existing design tools]         |
  |    ├── add_catalog_entry        ← NEW    |
  |    ├── update_catalog_entry     ← NEW    |
  |    ├── get_table_schema         ← NEW    |
  |    ├── search_catalog           ← NEW    |
  |    └── get_domain_knowledge     ← NEW    |
  |           ↓                              |
  |  core/catalog.py (CatalogService) ← NEW |
  |           ↓                              |
  |  storage/yaml_store.py (existing)        |
  |  storage/sqlite_store.py (FTS5)   ← NEW |
  +------------------------------------------+
           ↓
  .insight/
    ├── catalog/
    │   ├── sources/          ← NEW (per-file)
    │   │   ├── estat-population.yaml
    │   │   └── bq-sales-data.yaml
    │   └── knowledge/        (existing dir)
    │       ├── estat-population.yaml
    │       └── bq-sales-data.yaml
    ├── .sqlite/              ← NEW
    │   └── catalog_fts.db
    ├── designs/
    └── rules/
```

### Design Decision: FTS5 Trigram Tokenizer

Based on R1 research (`.claude/docs/research/spec2-fts5-tokenizer.md`):

- **unicode61** (default) is unsuitable for Japanese — relies on whitespace for word
  boundaries, which CJK languages lack
- **trigram** tokenizer indexes every 3-character sequence — works for both Japanese
  and English queries of 3+ characters with zero external dependencies
- **Limitation**: Queries shorter than 3 characters return no FTS5 matches. Acceptable
  for our use case since catalog search terms are typically descriptive words/phrases
- **ICU tokenizer** provides better linguistic quality but requires C extension compilation,
  violating the zero-install distribution goal

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(
    doc_type, source_id, title, content,
    tokenize='trigram'
);
```

### Design Decision: Per-Source File Storage

Following the same pattern as `DesignService` (one YAML file per entity):

- `catalog/sources/{id}.yaml` — one file per data source
- `catalog/knowledge/{id}.yaml` — one file per source's knowledge entries
- **Rationale**: Git diff clarity, glob-based listing, no concurrent write conflicts
- **Migration from SPEC-1**: `catalog/sources.yaml` (single file) → `catalog/sources/`
  (directory). Existing test `test_init_project_creates_catalog_sources_yaml` will be
  updated to check for directory instead

### Design Decision: User-Defined Source ID (Slug)

Unlike `DesignService` which auto-generates IDs (`FP-H01`), catalog sources use
user-defined slugs (e.g., `estat-population`, `bq-sales-data`):

- **Rationale**: Data source names are inherently human-readable identifiers. Auto-generated
  IDs would make MCP tool calls harder for Claude Code to construct
- **Validation**: Must be non-empty string. Duplicate ID raises `ValueError`

### Design Decision: FTS5 Index Strategy (Full Rebuild + Incremental)

The FTS5 index uses a two-pronged strategy:

**1. Full rebuild on startup** (per tech.md startup sequence):
- `rebuild_index()` drops and recreates the FTS5 table on every startup
- **Rationale**: YAML is source of truth. Full rebuild ensures consistency after
  manual YAML edits or external changes between sessions
- **Performance**: Acceptable for ≤100 sources (estimated &lt;2s based on benchmarks)

**2. Incremental updates during a session**:
- `add_source()` inserts the new source's metadata into FTS5 immediately after YAML write
  (via `insert_document()`)
- `update_source()` atomically replaces FTS5 rows for the source within a single
  transaction (via `replace_source_documents()` — DELETE + INSERT in `BEGIN IMMEDIATE`)
- **Rationale**: Users registering sources via `add_catalog_entry` MCP tool or
  `/catalog-register` skill expect immediate searchability — waiting until next restart
  would be a poor UX
- **Crash safety**: YAML write happens first (source of truth), then FTS5 update.
  If FTS5 update fails, YAML data is preserved and next `rebuild_index()` recovers
  full consistency. FTS5 failure does not cause `add_source()` or `update_source()` to fail
- **Manual YAML edits**: Changes made directly to YAML files (outside CatalogService)
  are NOT reflected in FTS5 until the next restart when `rebuild_index()` runs

## Components and Interfaces

### `models/catalog.py`

- **Purpose**: Pydantic data models for catalog entities — source types, column schema,
  data sources, domain knowledge
- **Interfaces**:
  - `SourceType(StrEnum)`: `csv`, `api`, `sql`
  - `KnowledgeCategory(StrEnum)`: `methodology`, `caution`, `definition`, `context`
  - `KnowledgeImportance(StrEnum)`: `high`, `medium`, `low`
  - `ColumnSchema(BaseModel)`: name, type, description + optional fields
  - `DataSource(BaseModel)`: id, name, type, description, connection, schema_info, tags,
    created_at, updated_at
  - `DomainKnowledgeEntry(BaseModel)`: key, title, content, category, importance + metadata
  - `DomainKnowledge(BaseModel)`: source_id, entries
- **Dependencies**: `pydantic`, `models/common.py:now_jst`
- **Reuses**: `now_jst()` for timestamp defaults (same as `AnalysisDesign`)

### `storage/sqlite_store.py`

- **Purpose**: SQLite FTS5 index management — build, search, and incrementally update
  the full-text index
- **Interfaces**:
  - `build_index(db_path: Path, sources: list[dict], knowledge: list[dict]) -> None`
    — DROP + CREATE FTS5 table, batch INSERT all documents (full rebuild)
  - `search_index(db_path: Path, query: str, limit: int = 20) -> list[dict]`
    — MATCH query with snippet() and rank ordering
  - `insert_document(db_path: Path, doc_type: str, source_id: str, title: str, content: str) -> None`
    — INSERT single row into existing FTS5 table (incremental add)
  - `delete_source_documents(db_path: Path, source_id: str) -> None`
    — DELETE all rows for a given source_id (used before re-insert on update)
  - `replace_source_documents(db_path: Path, source_id: str, rows: list[dict]) -> None`
    — Atomic DELETE + INSERT within a single transaction (used by `update_source()`)
- **Connection management**: Per-call open/close (simple, no leak risk). All connections
  set `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` on open
- **Dependencies**: `sqlite3` (stdlib), `pathlib.Path`, `logging`
- **Reuses**: None (new standalone module)
- **Error handling**:
  - FTS5 unavailable: catches `sqlite3.OperationalError` on CREATE, logs warning, returns
  - Missing DB file: `search_index()` and incremental ops return silently (no crash)
  - Incremental ops: catch `OperationalError` (e.g., `no such table`) and log warning —
    YAML operations always succeed regardless of FTS5 state
  - Query syntax error: wraps user query in double quotes (with `"` → `""` escaping),
    catches OperationalError

### `core/catalog.py`

- **Purpose**: Business logic for catalog CRUD and search operations
- **Interfaces**:
  - `CatalogService(project_path: Path)` constructor — sets `_sources_dir`, `_knowledge_dir`,
    `_db_path`
  - `add_source(source: DataSource) -> DataSource` — persist + create empty knowledge + insert into FTS5
  - `get_source(source_id: str) -> DataSource | None`
  - `list_sources() -> list[DataSource]`
  - `update_source(source_id: str, **fields) -> DataSource | None` — partial update + FTS5 atomic re-index via `replace_source_documents()`
  - `get_schema(source_id: str) -> list[ColumnSchema] | None`
  - `get_knowledge(source_id: str, category: KnowledgeCategory | None = None) -> DomainKnowledge | None`
  - `search(query: str, source_type: SourceType | None = None, tags: list[str] | None = None) -> list[dict]`
  - `rebuild_index() -> None`
- **Dependencies**: `models/catalog.py`, `storage/yaml_store.py`, `storage/sqlite_store.py`
- **Reuses**: `DesignService` patterns — glob listing, `model_copy(update=...)`, `read_yaml/write_yaml`

### `server.py` (additions)

- **Purpose**: 5 new MCP tools for catalog operations
- **Interfaces**:
  - `_catalog_service: CatalogService | None` — module-level reference
  - `get_catalog_service() -> CatalogService` — RuntimeError guard
  - `add_catalog_entry(source_id, name, type, description, connection, columns, tags?, primary_key?, row_count_estimate?) -> dict`
  - `update_catalog_entry(source_id, name?, description?, connection?, columns?, tags?) -> dict`
  - `get_table_schema(source_id) -> dict`
  - `search_catalog(query, source_type?, tags?) -> dict`
  - `get_domain_knowledge(source_id, category?) -> dict`
- **Dependencies**: `core/catalog.py:CatalogService`, `models/catalog.py`
- **Reuses**: Same error dict pattern as existing design tools

### `storage/project.py` (modifications)

- **Purpose**: Extended `init_project()` for catalog infrastructure
- **Changes**:
  - `_create_insight_dirs()`: Create `catalog/sources/` dir (replaces `sources.yaml` stub),
    create `.sqlite/` dir
  - `_copy_skills_template()`: Also copy `_skills/catalog-register/` to
    `.claude/skills/catalog-register/`
- **Reuses**: Existing `_copy_skills_template` pattern with `importlib.resources`

### `cli.py` (modifications)

- **Purpose**: Wire `CatalogService` and call `rebuild_index()` at startup
- **Changes**:
  - Import and instantiate `CatalogService(project_path)`
  - Wire `server_module._catalog_service = catalog_service`
  - Call `catalog_service.rebuild_index()` before `mcp.run()`

## Data Models

### DataSource YAML (`catalog/sources/{id}.yaml`)

```yaml
id: "estat-population"
name: "e-Stat Population Census"
type: "api"
description: "Japanese population statistics from e-Stat"
connection:
  base_url: "https://api.e-stat.go.jp/rest/3.0"
  provider: "e-stat"
  table_id: "0003348423"
  auth: "api_key"
schema_info:
  columns:
    - name: "prefecture_code"
      type: "string"
      description: "JIS X 0401 prefecture code (01-47)"
      nullable: false
      examples: ["01", "13", "47"]
    - name: "year"
      type: "integer"
      description: "Census year"
      nullable: false
      range: {min: 2000, max: 2024}
    - name: "population"
      type: "integer"
      description: "Total population"
      nullable: false
      unit: "人"
  primary_key: ["prefecture_code", "year"]
  row_count_estimate: 2350
tags: ["government", "population", "demographics"]
created_at: "2026-02-24T10:00:00+09:00"
updated_at: "2026-02-24T10:00:00+09:00"
```

### DomainKnowledge YAML (`catalog/knowledge/{id}.yaml`)

```yaml
source_id: "estat-population"
entries:
  - key: "methodology-change-2015"
    title: "2015 Census Methodology Change"
    content: |
      Population counting methodology changed in 2015.
      Direct comparison with pre-2015 data requires adjustment.
    category: "caution"
    importance: "high"
    created_at: "2026-02-24T10:00:00+09:00"
    source: "Reviewer domain expertise"
    affects_columns: ["population", "household_count"]
```

### FTS5 Index Schema

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(
    doc_type,       -- 'source' or 'knowledge'
    source_id,      -- references source YAML id
    title,          -- source name or knowledge title
    content,        -- description + column info, or knowledge content
    tokenize='trigram'
);
```

Each source is indexed as one row with `content` = concatenation of description +
column names + column descriptions. Each knowledge entry is indexed as one row with
`content` = entry content.

### Connection Field Formats (by source type)

```yaml
# CSV
connection:
  file_path: "data/sales_2024.csv"
  encoding: "utf-8"
  delimiter: ","

# API
connection:
  base_url: "https://api.e-stat.go.jp/rest/3.0"
  provider: "e-stat"
  table_id: "0003348423"
  auth: "api_key"

# SQL (BigQuery)
connection:
  provider: "bigquery"
  project_id: "my-gcp-project"
  dataset: "analytics"
  table: "user_events"
```

## Error Handling

### Error Scenarios

1. **Duplicate source ID** — `add_source()` called with an `id` that already exists
   - **Handling**: `CatalogService.add_source()` raises `ValueError`. `server.py` converts
     to `{"error": "Source 'estat-pop' already exists"}`
   - **User Impact**: Claude receives error dict and can inform the analyst to use
     `update_catalog_entry` instead

2. **Source not found** — `get_source()`, `get_schema()`, `get_knowledge()`, `update_source()`
   called with nonexistent `source_id`
   - **Handling**: Service returns `None`. Server converts to `{"error": "Source 'xyz' not found"}`
   - **User Impact**: Claude receives error dict and can suggest correct source ID

3. **Invalid source type** — `add_catalog_entry()` called with `type="parquet"`
   - **Handling**: Pydantic validation fails on `SourceType`. Server catches `ValueError`
     and returns `{"error": ...}`
   - **User Impact**: Claude informed of valid types (csv, api, sql)

4. **Invalid knowledge category** — `get_domain_knowledge()` called with invalid `category`
   - **Handling**: `KnowledgeCategory(value)` raises `ValueError`. Server returns
     `{"error": "Invalid category 'xyz'"}`
   - **User Impact**: Claude informed of valid categories

5. **FTS5 extension unavailable** — Python's sqlite3 compiled without FTS5 support
   - **Handling**: `build_index()` catches `sqlite3.OperationalError` on CREATE VIRTUAL TABLE,
     logs warning via `logging.warning()`. `search_index()` returns empty list
   - **User Impact**: Search returns no results. All other catalog operations work normally.
     Warning appears in logs for debugging

6. **FTS5 query syntax error** — Malformed search query
   - **Handling**: User queries are sanitized: `"` escaped to `""`, then wrapped in
     double quotes (`"sanitized query"`) before MATCH. Empty queries return empty results
     immediately. All queries use parameterized binding (`MATCH ?`). `search_index()`
     catches any remaining `OperationalError` and returns empty list
   - **User Impact**: Search returns no results rather than crashing

7. **CatalogService not initialized** — MCP tool called before `cli.py` wiring
   - **Handling**: `get_catalog_service()` raises `RuntimeError` (same pattern as `get_service()`)
   - **User Impact**: MCP protocol returns error. Only occurs in test/dev scenarios

## Testing Strategy

### Unit Testing

| File | Coverage Target |
|------|----------------|
| `tests/test_catalog_models.py` | `models/catalog.py` — 10 tests |
| `tests/test_sqlite_store.py` | `storage/sqlite_store.py` — 15 tests |
| `tests/test_catalog.py` | `core/catalog.py` — 26 tests |
| `tests/test_server.py` (extended) | server.py catalog tools — 15 tests |
| `tests/test_storage.py` (extended) | project.py changes — 3 tests |

**test_catalog_models.py** (models validation):
- SourceType enum values and rejection of invalid values
- ColumnSchema required/optional field defaults
- DataSource instantiation, timestamp defaults, JSON round-trip
- KnowledgeCategory/Importance enum values
- DomainKnowledgeEntry and DomainKnowledge container

**test_sqlite_store.py** (FTS5 operations):
- `build_index()`: DB file creation, empty data, source indexing, knowledge indexing, rebuild
- `search_index()`: matching results, no match, ranking, snippets, missing DB, FTS5 unavailable
- `insert_document()`: incremental add is immediately searchable
- `delete_source_documents()`: removes all rows for a source_id
- `replace_source_documents()`: atomic DELETE + INSERT in transaction, rollback on failure
- Incremental ops with missing FTS5 table: graceful no-op with warning log

**test_catalog.py** (CatalogService CRUD + search):
- `add_source()`: file creation, knowledge file creation, schema persistence, duplicate error, FTS5 incremental insert
- `get_source()`, `list_sources()`, `get_schema()`, `get_knowledge()`: retrieval and filtering
- `update_source()`: partial update, updated_at refresh, persistence, missing source, FTS5 re-index
- `search()`: FTS5 results, source_type/tags filtering, graceful degradation
- `rebuild_index()`: FTS5 DB creation

### Integration Testing

- Full round-trip test in `tests/test_integration.py`:
  `init_project()` → `add_source()` → `get_source()` → `get_schema()` → `search()`
  (immediately searchable via incremental FTS5 update) → `get_knowledge()`
  — all with real YAML files and SQLite DB
- `init_project()` creates `catalog/sources/` dir, `.sqlite/` dir, copies catalog-register skill
- Existing SPEC-1/1a tests continue to pass (regression check)

### End-to-End Testing

Full MCP protocol E2E testing remains out of scope (same as SPEC-1).
Integration tests cover the full business logic stack.

### Acceptance Criteria × Test Case Mapping

| AC | Content (Summary) | Test Cases | File |
|----|-------------------|------------|------|
| R1-AC1 | SourceType.csv stored correctly | `test_source_type_enum_has_csv_api_sql` | `test_catalog_models.py` |
| R1-AC2 | now_jst() default timestamps | `test_data_source_timestamps_default_to_jst` | `test_catalog_models.py` |
| R1-AC3 | ColumnSchema optional defaults | `test_column_schema_optional_fields_default_to_none` | `test_catalog_models.py` |
| R1-AC4 | JSON round-trip | `test_data_source_model_dump_json_round_trip` | `test_catalog_models.py` |
| R1-AC5 | DomainKnowledge empty entries | `test_domain_knowledge_container_with_empty_entries` | `test_catalog_models.py` |
| R1-AC6 | Invalid SourceType rejected | `test_source_type_rejects_invalid_value` | `test_catalog_models.py` |
| R2-AC1 | add_source creates files | `test_add_source_creates_source_yaml_file`, `test_add_source_creates_empty_knowledge_file` | `test_catalog.py` |
| R2-AC2 | Duplicate ID raises ValueError | `test_add_source_duplicate_id_raises_value_error` | `test_catalog.py` |
| R2-AC3 | get_source returns correct data | `test_get_source_returns_correct_source` | `test_catalog.py` |
| R2-AC4 | get_source returns None for missing | `test_get_source_returns_none_for_missing_id` | `test_catalog.py` |
| R2-AC5 | list_sources returns all | `test_list_sources_returns_all` | `test_catalog.py` |
| R2-AC6 | update_source patches correctly | `test_update_source_patches_name_field`, `test_update_source_refreshes_updated_at` | `test_catalog.py` |
| R2-AC7 | update_source None for missing | `test_update_source_returns_none_for_missing_id` | `test_catalog.py` |
| R2-AC8 | get_knowledge returns entries | `test_get_knowledge_returns_domain_knowledge` | `test_catalog.py` |
| R2-AC9 | get_knowledge category filter | `test_get_knowledge_filters_by_category` | `test_catalog.py` |
| R3-AC1 | rebuild creates FTS DB | `test_rebuild_index_creates_fts_db` | `test_catalog.py` |
| R3-AC2 | search returns matches | `test_search_returns_matching_results` | `test_catalog.py` |
| R3-AC3 | search with type filter | `test_search_filters_by_source_type` | `test_catalog.py` |
| R3-AC4 | search empty for no match | `test_search_index_returns_empty_for_no_match` | `test_sqlite_store.py` |
| R3-AC5 | rebuild replaces old index | `test_build_index_replaces_old_index_on_rebuild` | `test_sqlite_store.py` |
| R3-AC6 | FTS5 unavailable graceful | `test_build_index_handles_fts5_unavailable` | `test_sqlite_store.py` |
| R4-AC1 | add_catalog_entry success | `test_add_catalog_entry_returns_success_dict` | `test_server.py` |
| R4-AC2 | add_catalog_entry duplicate | `test_add_catalog_entry_duplicate_returns_error_dict` | `test_server.py` |
| R4-AC3 | add_catalog_entry invalid type | `test_add_catalog_entry_invalid_type_returns_error_dict` | `test_server.py` |
| R4-AC4 | update_catalog_entry success | `test_update_catalog_entry_patches_fields` | `test_server.py` |
| R4-AC5 | update_catalog_entry missing | `test_update_catalog_entry_missing_returns_error_dict` | `test_server.py` |
| R4-AC6 | get_table_schema success | `test_get_table_schema_returns_columns` | `test_server.py` |
| R4-AC7 | get_table_schema missing | `test_get_table_schema_missing_returns_error_dict` | `test_server.py` |
| R4-AC8 | search_catalog returns results | `test_search_catalog_returns_results_dict` | `test_server.py` |
| R4-AC9 | get_domain_knowledge success | `test_get_domain_knowledge_returns_entries` | `test_server.py` |
| R4-AC10 | get_domain_knowledge invalid | `test_get_domain_knowledge_invalid_category_returns_error` | `test_server.py` |
| R5-AC1 | CLI wires CatalogService | `test_catalog_full_round_trip` | `test_integration.py` |
| R5-AC2 | init creates sources dir | `test_init_project_creates_sources_directory` | `test_storage.py` |
| R5-AC3 | init creates .sqlite dir | `test_init_project_creates_sqlite_dir` | `test_storage.py` |
| R5-AC4 | init copies catalog-register | `test_init_project_copies_catalog_register_skill` | `test_storage.py` |
| R6-AC1 | Skill guides registration | Manual verification | — |
| R6-AC2 | Skill has valid frontmatter | `test_init_project_copies_catalog_register_skill` | `test_storage.py` |

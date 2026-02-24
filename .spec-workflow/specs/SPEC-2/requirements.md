# SPEC-2: data-catalog — Requirements

> **Spec ID**: SPEC-2
> **Feature Name**: data-catalog
> **Status**: pending_approval
> **Created**: 2026-02-24
> **Depends On**: SPEC-1 (core-foundation), SPEC-1a (hypothesis-enrichment)

---

## Introduction

SPEC-2 adds a data catalog to insight-blueprint so that data scientists can register,
search, and reference data source definitions (name, type, connection info, column schema)
and domain knowledge through MCP tools. Sources and knowledge are persisted as per-file
YAML (one file per source), while SQLite FTS5 provides fast full-text search across both
source metadata and knowledge entries. The catalog gives Claude Code the context it needs
to generate accurate queries and avoid common data pitfalls during EDA sessions.

## Alignment with Product Vision

This spec directly enables three core product goals defined in `product.md`:

- **Communicating data access rules and domain knowledge to AI**: The catalog MCP tools
  (`search_catalog`, `get_table_schema`, `get_domain_knowledge`) give Claude Code structured
  access to column schemas, connection details, and domain cautions — eliminating the burden
  of manually explaining data structure to the AI.
- **Accumulating domain knowledge for continuous reuse**: Per-source knowledge files
  (`catalog/knowledge/{source_id}.yaml`) store methodology notes, cautions, and definitions
  that persist across sessions and are searchable via FTS5.
- **Spec Roadmap progression**: SPEC-2 provides the data catalog layer that SPEC-3
  (review-workflow) extends with knowledge write tools and that SPEC-4 (webui-dashboard)
  surfaces in the Catalog tab.

## Requirements

### Requirement 1: Catalog Data Models

**User Story:** As a data scientist, I want the data sources I use in my analysis
(CSV files, API endpoints, SQL tables) to have structured definitions with column-level
schema information, so that Claude Code can understand my data and generate correct queries.

**FR-1: Source and Schema Models**
- `SourceType` enum with three values: `csv`, `api`, `sql`
- `ColumnSchema` model with required fields: `name: str`, `type: str`, `description: str`
  and optional fields: `nullable: bool` (default `True`), `examples: list[str] | None`,
  `range: dict | None`, `unit: str | None`
- `DataSource` model with fields:
  - `id: str` — user-defined slug (e.g., `estat-population`)
  - `name: str` — human-readable display name
  - `type: SourceType` — csv/api/sql
  - `description: str`
  - `connection: dict` — untyped dict (structure varies by source type)
  - `schema_info: dict` — contains `columns: list[ColumnSchema]`,
    optional `primary_key: list[str]`, optional `row_count_estimate: int`
  - `tags: list[str]` (default empty list)
  - `created_at: datetime` (default `now_jst()`)
  - `updated_at: datetime` (default `now_jst()`)

**FR-2: Domain Knowledge Models**
- `KnowledgeCategory` enum: `methodology`, `caution`, `definition`, `context`
- `KnowledgeImportance` enum: `high`, `medium`, `low`
- `DomainKnowledgeEntry` model with fields:
  - `key: str` — unique key within source (e.g., `methodology-change-2015`)
  - `title: str`
  - `content: str`
  - `category: KnowledgeCategory`
  - `importance: KnowledgeImportance` (default `medium`)
  - `created_at: datetime` (default `now_jst()`)
  - `source: str | None` — origin of knowledge (e.g., "Reviewer domain expertise")
  - `affects_columns: list[str]` (default empty list)
- `DomainKnowledge` container model with fields:
  - `source_id: str`
  - `entries: list[DomainKnowledgeEntry]` (default empty list)

#### Acceptance Criteria

1. WHEN a `DataSource` is created with `type="csv"` THEN `SourceType.csv` is stored and serialized as `"csv"` in YAML
2. WHEN a `DataSource` is created without `created_at` THEN `now_jst()` is used as default
3. WHEN a `ColumnSchema` is created with only required fields THEN optional fields default to `None` (except `nullable` which defaults to `True`)
4. WHEN a `DataSource` is serialized via `model_dump(mode="json")` and deserialized back THEN the round-trip produces an equivalent model
5. WHEN a `DomainKnowledge` is created without entries THEN `entries` defaults to an empty list
6. WHEN an invalid `SourceType` value (e.g., `"parquet"`) is used THEN a validation error is raised

### Requirement 2: Catalog CRUD Operations

**User Story:** As a data scientist using Claude Code, I want to register data sources
to the catalog and retrieve them by ID, so that Claude can reference my data definitions
when designing analyses.

**FR-3: Add Source**
- `add_source()` accepts a `DataSource` model (or equivalent parameters) and persists it
  to `catalog/sources/{id}.yaml`
- On successful add, creates an empty knowledge file at `catalog/knowledge/{id}.yaml`
  with `source_id` and empty `entries` list
- On successful add, inserts the source into the FTS5 index so it is immediately searchable
- If a source with the same `id` already exists, raises `ValueError`

**FR-4: Get Source and List Sources**
- `get_source(source_id)` reads `catalog/sources/{source_id}.yaml` and returns a
  `DataSource` model, or `None` if not found
- `list_sources()` globs `catalog/sources/*.yaml` and returns all sources as a list
- `get_schema(source_id)` returns the `columns` list from the source's `schema_info`,
  or `None` if source not found

**FR-5: Update Source**
- `update_source(source_id, **fields)` partially updates a source using `model_copy(update=...)`
- Automatically refreshes `updated_at` to `now_jst()`
- Returns updated `DataSource`, or `None` if source not found
- Persists changes to the same `sources/{id}.yaml` file
- Updates the FTS5 index (delete old rows + re-insert) so changes are immediately searchable

**FR-6: Get Domain Knowledge**
- `get_knowledge(source_id, category?)` reads `catalog/knowledge/{source_id}.yaml`
  and returns `DomainKnowledge`
- Optional `category` parameter filters entries by `KnowledgeCategory`
- Returns `None` if source knowledge file not found

#### Acceptance Criteria

1. WHEN `add_source()` is called with a new source THEN `catalog/sources/{id}.yaml` is created AND `catalog/knowledge/{id}.yaml` is created with empty entries
2. WHEN `add_source()` is called with a duplicate `id` THEN `ValueError` is raised
3. WHEN `get_source("estat-pop")` is called after adding a source with that id THEN the correct `DataSource` is returned
4. WHEN `get_source("nonexistent")` is called THEN `None` is returned
5. WHEN `list_sources()` is called after adding 3 sources THEN a list of 3 `DataSource` models is returned
6. WHEN `update_source("estat-pop", name="New Name")` is called THEN only `name` and `updated_at` are changed
7. WHEN `update_source("nonexistent", ...)` is called THEN `None` is returned
8. WHEN `get_knowledge("estat-pop")` is called THEN `DomainKnowledge` is returned (empty entries if no knowledge added)
9. WHEN `get_knowledge("estat-pop", category="caution")` is called THEN only entries with `category == "caution"` are returned

### Requirement 3: Full-Text Search

**User Story:** As a data scientist, I want to search across all data sources and domain
knowledge by keyword, so that I can quickly find relevant data and cautions for my analysis.

**FR-7: FTS5 Index Build and Incremental Update**
- `build_index(db_path, sources, knowledge_entries)` creates a SQLite FTS5 virtual table
- Indexes source metadata (name, description, column descriptions) and knowledge entries
  (title, content)
- Each indexed row includes: `doc_type` (source/knowledge), `source_id`, `title`, `content`
- On rebuild, drops existing table and recreates (full rebuild strategy per tech.md)
- Incremental operations: `insert_document()` adds a single row, `delete_source_documents()`
  removes all rows for a source_id — used by `add_source()` and `update_source()` to keep
  the FTS5 index up-to-date during a session without requiring a full rebuild

**FR-8: FTS5 Search**
- `search_index(db_path, query)` executes a MATCH query against the FTS5 table
- Returns results ranked by relevance (FTS5 built-in ranking)
- Each result includes: `source_id`, `doc_type`, `title`, `snippet` (via FTS5 `snippet()`)
- Returns empty list if database file does not exist or query matches nothing

**FR-9: Catalog Search**
- `search(query, source_type?, tags?)` combines FTS5 results with optional Python-side
  post-filtering by `source_type` and `tags`
- `rebuild_index()` collects all sources and knowledge entries and calls `build_index()`

#### Acceptance Criteria

1. WHEN `rebuild_index()` is called after adding sources THEN a `.sqlite/catalog_fts.db` file is created
2. WHEN `search("population")` is called immediately after `add_source()` (without `rebuild_index()`) THEN at least one result is returned with a snippet (incremental FTS5 update)
3. WHEN `search("population", source_type="csv")` is called but only API sources contain "population" THEN empty results are returned
4. WHEN `search("nonexistent-keyword")` is called THEN empty results are returned
5. WHEN `rebuild_index()` is called twice THEN the second call replaces the old index (no duplicate entries)
6. WHEN FTS5 extension is unavailable THEN `build_index()` logs a warning and subsequent searches return empty results

### Requirement 4: MCP Tools

**User Story:** As a data scientist using Claude Code, I want Claude to register, search,
and query my data catalog through MCP tools, so that data context is always available
during my analysis sessions.

**FR-10: add_catalog_entry Tool**
- Accepts: `source_id`, `name`, `type` (csv/api/sql), `description`, `connection` (dict),
  `columns` (list of column dicts), optional `tags`, optional `primary_key`,
  optional `row_count_estimate`
- Returns: `{source_id, name, type, message}` on success, `{error}` on failure
- Maps to `CatalogService.add_source()`

**FR-11: update_catalog_entry Tool**
- Accepts: `source_id`, optional fields to update (`name`, `description`, `connection`,
  `columns`, `tags`)
- Returns: full source dict on success, `{error}` on failure
- Maps to `CatalogService.update_source()`

**FR-12: get_table_schema Tool**
- Accepts: `source_id`
- Returns: `{source_id, columns: [...], primary_key, row_count_estimate}` on success,
  `{error}` if source not found
- Maps to `CatalogService.get_source()` with schema extraction

**FR-13: search_catalog Tool**
- Accepts: `query`, optional `source_type`, optional `tags` (comma-separated string)
- Returns: `{results: [...], count}` with each result containing `source_id`, `doc_type`,
  `title`, `snippet`
- Maps to `CatalogService.search()`

**FR-14: get_domain_knowledge Tool**
- Accepts: `source_id`, optional `category`
- Returns: `{source_id, entries: [...], count}` on success, `{error}` if not found
- Invalid `category` value returns `{error}` (not exception)
- Maps to `CatalogService.get_knowledge()`

#### Acceptance Criteria

1. WHEN `add_catalog_entry()` is called with valid parameters THEN `{source_id, name, type, message}` is returned
2. WHEN `add_catalog_entry()` is called with duplicate `source_id` THEN `{error}` dict is returned
3. WHEN `add_catalog_entry()` is called with invalid type `"parquet"` THEN `{error}` dict is returned
4. WHEN `update_catalog_entry()` is called with valid `source_id` THEN updated source dict is returned
5. WHEN `update_catalog_entry()` is called with nonexistent `source_id` THEN `{error}` dict is returned
6. WHEN `get_table_schema()` is called with existing source THEN column list is returned
7. WHEN `get_table_schema()` is called with nonexistent source THEN `{error}` dict is returned
8. WHEN `search_catalog(query="population")` is called THEN matching results with snippets are returned
9. WHEN `get_domain_knowledge(source_id="estat-pop")` is called THEN entries are returned
10. WHEN `get_domain_knowledge(source_id="estat-pop", category="invalid")` is called THEN `{error}` dict is returned

### Requirement 5: CLI Wiring and Project Initialization

**User Story:** As a data scientist, I want the catalog to be ready immediately when
I start insight-blueprint, with FTS5 index built and catalog-register skill available,
so that I can start searching data sources right away.

**FR-15: CLI Startup Integration**
- `cli.py` instantiates `CatalogService` and wires it to `server._catalog_service`
- Calls `catalog_service.rebuild_index()` before `mcp.run()` so FTS5 is ready at startup

**FR-16: Project Initialization Updates**
- `init_project()` creates `catalog/sources/` directory (replacing the old `catalog/sources.yaml` stub)
- `init_project()` creates `.insight/.sqlite/` directory for FTS5 database files
- `init_project()` copies bundled `catalog-register` skill to `.claude/skills/catalog-register/`
  (if not already present)

#### Acceptance Criteria

1. WHEN `uvx insight-blueprint --project /path` is run THEN `CatalogService` is initialized and all 5 catalog MCP tools are available
2. WHEN `init_project()` is called THEN `.insight/catalog/sources/` directory is created (not `sources.yaml` file)
3. WHEN `init_project()` is called THEN `.insight/.sqlite/` directory is created
4. WHEN `init_project()` is called THEN `.claude/skills/catalog-register/SKILL.md` is copied
5. WHEN startup completes THEN `rebuild_index()` has been called and FTS5 is searchable

### Requirement 6: Catalog Register Skill

**User Story:** As a data scientist, I want a `/catalog-register` Claude Code skill that
automatically explores my CSV/API/SQL data sources and registers them to the catalog,
so that I don't have to manually construct the catalog entry.

**FR-17: Bundled Catalog Register Skill**
- A SKILL.md file at `_skills/catalog-register/SKILL.md` with valid YAML frontmatter
- The skill guides Claude Code through:
  1. Identifying the source type (CSV/API/SQL)
  2. Exploring the data structure (read CSV headers, query API metadata, query INFORMATION_SCHEMA)
  3. Building the `DataSource` model with column schema
  4. Calling `add_catalog_entry()` MCP tool to register
- Supports all three source types: CSV, API (e-Stat pattern), SQL (BigQuery pattern)

#### Acceptance Criteria

1. WHEN `/catalog-register` skill is invoked THEN Claude Code is guided through source exploration and registration
2. WHEN the skill file is copied to `.claude/skills/` THEN it contains valid YAML frontmatter with `name`, `description`, and `disable-model-invocation: true`

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility Principle**: `models/catalog.py` = data models only,
  `storage/sqlite_store.py` = FTS5 index only, `core/catalog.py` = business logic only
- **Three-Layer Separation**: MCP tools (server.py) delegate to `CatalogService` (core/catalog.py),
  which delegates to `yaml_store.py` and `sqlite_store.py`; no cross-layer skipping
- **Pattern Reuse**: `CatalogService` follows the same structure as `DesignService`
  (constructor with project_path, glob-based listing, model_copy for updates)
- **Type Annotations Required**: All functions have complete type annotations; `ty check` passes
- **Code Quality**: `ruff check` passes; `pytest` coverage for `core/catalog.py` and
  `storage/sqlite_store.py` is 80% or higher

### Performance

- `add_source()` completes within 100ms (two YAML writes + FTS5 incremental insert)
- `search()` completes within 200ms for up to 500 indexed documents
- `rebuild_index()` completes within 2 seconds for up to 100 sources
- `get_source()` completes within 50ms (single YAML read)

### Security

- No hardcoded secrets, API keys, or credentials in source code
- FTS5 queries are parameterized (no string interpolation in SQL)
- User-provided search queries are wrapped in double quotes to prevent FTS5 syntax injection
- Error messages do not expose internal file paths or stack traces to MCP clients

### Reliability

- FTS5 extension unavailable: `build_index()` catches `OperationalError`, logs a warning,
  and subsequent searches return empty results (graceful degradation)
- FTS5 query syntax error: `search_index()` catches `OperationalError` and returns empty results
- Missing database file: `search_index()` returns empty results (no crash)
- All YAML writes remain atomic (`tempfile.mkstemp()` + `os.replace()`)
- Existing SPEC-1/SPEC-1a tests continue to pass (no regressions)

### Usability

- MCP tool docstrings clearly describe parameters and return formats
- Search results include snippets so Claude Code can show relevant context to the user
- `add_catalog_entry` accepts flat parameters (not nested model) for ease of MCP tool calling
- Error dicts include actionable messages (e.g., "Source 'xyz' already exists")

## Out of Scope

- Parquet and Excel source types (future extension)
- Delete catalog entry tool (not needed for v1 workflow)
- Knowledge write tools (SPEC-3: review-workflow will add these)
- Data preview / data exploration through MCP (the `/catalog-register` skill does exploration,
  but via Claude Code's own tools, not MCP)
- WebUI catalog tab (SPEC-4)

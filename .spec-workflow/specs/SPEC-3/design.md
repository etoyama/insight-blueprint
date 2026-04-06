# SPEC-3: review-workflow — Design

> **Spec ID**: SPEC-3
> **Status**: draft
> **Created**: 2026-02-26
> **Depends On**: SPEC-1 (core-foundation), SPEC-2 (data-catalog)

---

## Overview

SPEC-3 adds a review workflow layer to insight-blueprint. Data scientists submit
analysis designs for review, receive structured feedback as persistent comments, and
the system automatically extracts reusable domain knowledge from those comments.
The review workflow follows the same 3-layer architecture as SPEC-1 and SPEC-2:
MCP tools (server.py) → ReviewService/RulesService (core/) → Storage (yaml_store.py).
Two new service modules (`core/reviews.py` and `core/rules.py`) are introduced, along
with a new model module (`models/review.py`) for review-specific data types.
Knowledge extraction follows an Extract-Preview-Confirm pattern: entries are extracted
as preview, confirmed by the user (with scope adjustment), then persisted.

## Steering Document Alignment

### Technical Standards (tech.md)

- **Storage**: Review comments persisted as per-design YAML files in
  `.insight/designs/{design_id}_reviews.yaml`; extracted knowledge in
  `.insight/rules/extracted_knowledge.yaml` — YAML remains source of truth per tech.md
- **MCP tools**: 6 new async tools registered with `@mcp.tool()` on the existing
  `FastMCP("insight-blueprint")` instance
- **Quality**: TDD (Red-Green-Refactor), ruff + ty + pytest, 80%+ coverage target
- **No new dependencies**: Uses only existing packages (pydantic, ruamel.yaml, etc.)
- **Status lifecycle**: `DesignStatus` extended with `pending_review` — single StrEnum definition
- **Model extension**: `AnalysisDesign` extended with `source_ids: list[str]` for data source scoping

### Project Structure (structure.md)

- **New modules** per Spec-to-Module Mapping: `models/review.py`, `core/rules.py`,
  `core/reviews.py`
- **Modified modules**: `server.py` (+6 tools, +1 transition guard), `cli.py` (+service wiring),
  `storage/project.py` (+extracted_knowledge init), `models/design.py` (+pending_review),
  `models/__init__.py` (+re-exports)
- **3-layer separation**: MCP tools → ReviewService/RulesService → yaml_store + DesignService
- **One-directional dependencies**: server.py → core/{reviews,rules}.py → storage/* + core/designs.py

## Code Reuse Analysis

### Existing Components to Leverage

- **`now_jst()`** (`models/common.py`): Timestamps for `ReviewComment.created_at`
- **`read_yaml/write_yaml`** (`storage/yaml_store.py`): All YAML persistence for review comments,
  extracted knowledge — atomic writes via `tempfile.mkstemp()` + `os.replace()`
- **`DesignService`** (`core/designs.py`): `ReviewService` delegates to `DesignService.get_design()`
  and `DesignService.update_design()` for status transitions — no direct YAML access for designs
- **`CatalogService.get_knowledge()`** (`core/catalog.py`): `RulesService.get_project_context()`
  aggregates catalog knowledge alongside extracted review knowledge
- **`DomainKnowledgeEntry`** (`models/catalog.py`): Reused for extracted knowledge entries —
  same structure, stored in `rules/extracted_knowledge.yaml`
- **`get_service()` guard pattern** (`server.py`): `get_review_service()` and
  `get_rules_service()` follow same `RuntimeError` guard for uninitialized service
- **MCP error dict pattern** (`server.py`): `ValueError` → `{"error": str(e)}` conversion

### Integration Points

- **`server.py`**: New `_review_service` and `_rules_service` module-level references +
  6 `@mcp.tool()` functions + guard on `update_analysis_design` to reject `pending_review`
- **`cli.py`**: `ReviewService` and `RulesService` instantiated and wired before `mcp.run()`
- **`storage/project.py`**: `_create_insight_dirs()` extended to create
  `rules/extracted_knowledge.yaml` (empty entries)
- **`models/design.py`**: `DesignStatus` extended with `pending_review` value
- **`models/__init__.py`**: Re-export `ReviewComment` from `models/review.py`

## Architecture

### Modular Design Principles

- **Single File Responsibility**: `models/review.py` = review data models only,
  `core/reviews.py` = review workflow operations only, `core/rules.py` = knowledge
  aggregation only
- **Component Isolation**: `ReviewService` depends on `DesignService` interface only
  (get/update) — no direct YAML manipulation of design files. `RulesService` reads
  catalog knowledge via `CatalogService` — no direct file access to catalog YAML
- **Service Layer Separation**: MCP tools → ReviewService/RulesService → DesignService/
  CatalogService/yaml_store. No cross-layer skipping
- **Utility Modularity**: Status transition validation is a standalone dict/set definition
  in `core/reviews.py`, importable for testing

### Component Diagram (SPEC-3 additions)

```
Claude Code (AI Client)
       |
  stdio (MCP Protocol)
       |
  +-------------------------------------------------------+
  |  insight-blueprint (Python Process)                   |
  |                                                       |
  |  cli.py (entry point)                                 |
  |    ├── init_project()                                 |
  |    ├── wire DesignService                             |
  |    ├── wire CatalogService                            |
  |    ├── wire ReviewService(design_svc)       ← NEW     |
  |    ├── wire RulesService(catalog_svc)       ← NEW     |
  |    ├── rebuild_index()                                |
  |    └── mcp.run() ← BLOCKS                            |
  |                                                       |
  |  server.py (FastMCP)                                  |
  |    ├── [4 existing design tools]                      |
  |    │   └── update_analysis_design ← GUARD added       |
  |    ├── [5 existing catalog tools]                     |
  |    ├── submit_for_review              ← NEW           |
  |    ├── save_review_comment            ← NEW           |
  |    ├── extract_domain_knowledge       ← NEW (preview) |
  |    ├── save_extracted_knowledge       ← NEW (persist) |
  |    ├── get_project_context            ← NEW           |
  |    └── suggest_cautions               ← NEW           |
  |           ↓                                           |
  |  core/reviews.py (ReviewService)      ← NEW          |
  |    ├── submit_for_review()                            |
  |    ├── save_review_comment()                          |
  |    ├── list_comments()                                |
  |    ├── extract_domain_knowledge()                     |
  |    └── save_extracted_knowledge()                     |
  |           ↓ delegates to                              |
  |  core/designs.py (DesignService)      (existing)     |
  |                                                       |
  |  core/rules.py (RulesService)         ← NEW          |
  |    ├── get_project_context()                          |
  |    └── suggest_cautions()                             |
  |           ↓ reads from                                |
  |  core/catalog.py (CatalogService)     (existing)     |
  |  storage/yaml_store.py                (existing)     |
  +-------------------------------------------------------+
           ↓
  .insight/
    ├── designs/
    │   ├── FP-H01_hypothesis.yaml
    │   └── FP-H01_reviews.yaml       ← NEW (per-design)
    ├── catalog/knowledge/             (existing)
    ├── rules/
    │   ├── review_rules.yaml          (existing)
    │   ├── analysis_rules.yaml        (existing)
    │   └── extracted_knowledge.yaml   ← NEW
    └── .sqlite/
```

### Design Decision: Status Transition Matrix

Based on Codex risk analysis (Risk #7): The existing `update_analysis_design` MCP tool
can set `status` directly, potentially bypassing the review workflow. To prevent this:

- A `VALID_TRANSITIONS` dict is defined in `core/reviews.py` as single source of truth
- `submit_for_review()` validates `active → pending_review` only
- `save_review_comment()` validates `pending_review → {active, supported, rejected, inconclusive}`
- `update_analysis_design` in `server.py` is guarded to reject `pending_review` as a target status
- The `draft → active` transition remains possible via `update_analysis_design` (existing behavior)

```python
VALID_REVIEW_TRANSITIONS: dict[DesignStatus, set[DesignStatus]] = {
    DesignStatus.active: {DesignStatus.pending_review},
    DesignStatus.pending_review: {
        DesignStatus.active,      # request changes
        DesignStatus.supported,
        DesignStatus.rejected,
        DesignStatus.inconclusive,
    },
}
```

### Design Decision: Separate Review Comment Files

Based on Codex risk analysis (Risk #3): Review comments are stored in a separate
`{design_id}_reviews.yaml` file rather than inline in the design YAML.

- **Rationale**: Design files stay focused on hypothesis/analysis structure; review
  history can grow unbounded; separate files are easier to list/search
- **Trade-off**: Two files per reviewed design (vs. one). Acceptable since the files
  are in the same directory and linked by naming convention
- **Concurrency**: For v1 single-user, atomic `os.replace()` is sufficient.
  The read-modify-write pattern for appending comments is acceptable

### Design Decision: Extract-Preview-Confirm Pattern

Based on Codex risk analysis (Risk #4) + reviewer feedback on scoping accuracy:
Knowledge extraction follows a two-step Extract-Preview-Confirm pattern to prevent
false positive cautions from being persisted.

- **Rationale**: Extracted knowledge becomes permanent project context that Claude uses
  across sessions. Persisting incorrectly scoped knowledge (e.g., a population-specific
  caution applied to all data sources) causes false positive cautions that mislead
  analysis. Human confirmation before persistence eliminates this risk.
- **Implementation**:
  - `extract_domain_knowledge(design_id)` → returns preview (no persistence)
  - `save_extracted_knowledge(design_id, entries)` → persists after user confirmation
  - Keyword-based extraction: regex prefix detection (case-insensitive), NFKC Unicode
    normalization, process by line (each line can have its own category)
  - Scope assignment: `table:` / `テーブル:` annotation per entry, falling back to
    `AnalysisDesign.source_ids` as default scope
  - User can adjust `affects_columns` on each entry before save
- **Scope priority**: user confirmation > `table:` annotation > `design.source_ids` > `[]`
- **Accepted limitation**: Lower recall for implicit knowledge. Future enhancement:
  optional LLM extraction mode

### Design Decision: Unified affects_columns Matching

Based on Codex risk analysis (Risk #6) + reviewer feedback: `suggest_cautions()` uses a
single unified matching strategy for both catalog and extracted knowledge.

- **Strategy**: Match `DomainKnowledgeEntry.affects_columns` against provided
  `table_names` for all knowledge entries (catalog and extracted alike)
- **Rationale**: The Extract-Preview-Confirm pattern ensures that extracted knowledge
  entries have properly populated `affects_columns` at save time. This eliminates the
  need for a separate content-keyword fallback strategy and avoids the vocabulary
  mismatch between `affects_columns`, `affects_tables`, and content matching.
- **Trade-off**: Entries with `affects_columns=[]` (unscoped) will not match any
  specific table query. This is intentional — unscoped entries appear only in
  `get_project_context()` (overview), not in targeted `suggest_cautions()` queries.
  This prevents false positive cautions at the cost of potential false negatives for
  unscoped entries.

## Components and Interfaces

### `models/review.py`

- **Purpose**: Pydantic data models for review comments
- **Interfaces**:
  - `ReviewComment(BaseModel)`: id, design_id, comment, reviewer, status_after,
    created_at, extracted_knowledge
- **Dependencies**: `pydantic`, `models/common.py:now_jst`, `models/design.py:DesignStatus`
- **Reuses**: `now_jst()` for timestamp defaults (same as AnalysisDesign and DataSource)

### `core/reviews.py`

- **Purpose**: Review workflow operations — submit, comment, extract knowledge
- **Interfaces**:
  - `VALID_REVIEW_TRANSITIONS: dict[DesignStatus, set[DesignStatus]]` — transition matrix
  - `ReviewService(project_path: Path, design_service: DesignService)` constructor
  - `submit_for_review(design_id: str) -> AnalysisDesign | None`
    — validate active status, transition to pending_review
  - `save_review_comment(design_id: str, comment: str, status: str, reviewer: str = "analyst") -> ReviewComment | None`
    — validate pending_review status, persist comment, transition design
  - `list_comments(design_id: str) -> list[ReviewComment]`
    — read `{design_id}_reviews.yaml`, return all comments
  - `extract_domain_knowledge(design_id: str) -> list[DomainKnowledgeEntry]`
    — parse comments, extract knowledge as preview (NOT persisted),
      populate `affects_columns` from `table:` annotations or `design.source_ids`
  - `save_extracted_knowledge(design_id: str, entries: list[DomainKnowledgeEntry]) -> list[DomainKnowledgeEntry]`
    — persist user-confirmed entries to `rules/extracted_knowledge.yaml`,
      update `ReviewComment.extracted_knowledge` with saved keys
- **Dependencies**: `models/review.py`, `models/catalog.py:DomainKnowledgeEntry`,
  `core/designs.py:DesignService`, `storage/yaml_store.py`
- **Reuses**: `DesignService.get_design()` and `DesignService.update_design()` for
  status transitions; `read_yaml/write_yaml` for comment and knowledge persistence

### `core/rules.py`

- **Purpose**: Knowledge aggregation and caution suggestion
- **Interfaces**:
  - `RulesService(project_path: Path, catalog_service: CatalogService)` constructor
  - `get_project_context() -> dict`
    — aggregate all domain knowledge: catalog sources, catalog knowledge, extracted knowledge,
      rules; return structured summary
  - `suggest_cautions(table_names: list[str]) -> list[dict]`
    — search all domain knowledge entries (catalog and extracted) by matching
      `affects_columns` against provided table/source names — unified strategy
- **Dependencies**: `core/catalog.py:CatalogService`, `models/catalog.py`,
  `storage/yaml_store.py`
- **Reuses**: `CatalogService.list_sources()`, `CatalogService.get_knowledge()` for
  catalog data; `read_yaml` for extracted knowledge

### `server.py` (additions)

- **Purpose**: 6 new MCP tools for review workflow + 1 transition guard on existing tool
- **Interfaces**:
  - `_review_service: ReviewService | None` — module-level reference
  - `_rules_service: RulesService | None` — module-level reference
  - `get_review_service() -> ReviewService` — RuntimeError guard
  - `get_rules_service() -> RulesService` — RuntimeError guard
  - `submit_for_review(design_id) -> dict`
  - `save_review_comment(design_id, comment, status, reviewer?) -> dict`
  - `extract_domain_knowledge(design_id) -> dict` — preview, not persisted
  - `save_extracted_knowledge(design_id, entries) -> dict` — persist confirmed entries
  - `get_project_context() -> dict`
  - `suggest_cautions(table_names) -> dict`
  - **MODIFIED**: `update_analysis_design()` — reject `status="pending_review"`
    with error dict
- **Dependencies**: `core/reviews.py:ReviewService`, `core/rules.py:RulesService`
- **Reuses**: Same error dict pattern as existing design and catalog tools

### `models/design.py` (modification)

- **Purpose**: Extend `DesignStatus` with `pending_review` and add `source_ids` to `AnalysisDesign`
- **Changes**:
  - Add `pending_review = "pending_review"` to `DesignStatus(StrEnum)`
  - Add `source_ids: list[str] = Field(default_factory=list)` to `AnalysisDesign`
- **Impact**: All existing status values and fields preserved; changes are additive
  and backward-compatible (existing designs default to `source_ids=[]`)

### `storage/project.py` (modifications)

- **Purpose**: Extended `init_project()` for review workflow infrastructure
- **Changes**: Create `.insight/rules/extracted_knowledge.yaml` with
  `{source_id: "review", entries: []}` if absent
- **Reuses**: Existing `write_yaml` for YAML creation, existing directory creation pattern

### `cli.py` (modifications)

- **Purpose**: Wire `ReviewService` and `RulesService` at startup
- **Changes**:
  - Import and instantiate `ReviewService(project_path, design_service)`
  - Import and instantiate `RulesService(project_path, catalog_service)`
  - Wire `server._review_service` and `server._rules_service`
  - Both services wired after DesignService and CatalogService, before `mcp.run()`

## Data Models

### ReviewComment YAML (`designs/{design_id}_reviews.yaml`)

```yaml
comments:
  - id: "RC-a1b2c3d4"
    design_id: "FP-H01"
    comment: |
      table: population_stats
      caution: 2015年以降の人口統計は調査方法が変更されているため、
      直接比較する場合は補正が必要。
      methodology: 人口動態比較には年齢調整標準化を用いること。
      definition: MAU = 月間アクティブユーザー数
      背景: この分析はQ3の事業計画策定を目的としている。
    reviewer: "analyst"
    status_after: "supported"
    created_at: "2026-02-26T10:00:00+09:00"
    extracted_knowledge:
      - "FP-H01-0"
      - "FP-H01-1"
      - "FP-H01-2"
      - "FP-H01-3"
```

### Extracted Knowledge YAML (`rules/extracted_knowledge.yaml`)

```yaml
source_id: "review"
entries:
  - key: "FP-H01-0"
    title: "2015年以降の人口統計は調査方法が変更されている"
    content: "2015年以降の人口統計は調査方法が変更されているため、直接比較する場合は補正が必要。"
    category: "caution"
    importance: "medium"
    created_at: "2026-02-26T10:30:00+09:00"
    source: "Review comment on FP-H01"
    affects_columns: ["population_stats"]
  - key: "FP-H01-1"
    title: "人口動態比較には年齢調整標準化を用いること"
    content: "人口動態比較には年齢調整標準化を用いること。"
    category: "methodology"
    importance: "medium"
    created_at: "2026-02-26T10:30:00+09:00"
    source: "Review comment on FP-H01"
    affects_columns: ["population_stats"]
  - key: "FP-H01-2"
    title: "MAU = 月間アクティブユーザー数"
    content: "MAU = 月間アクティブユーザー数"
    category: "definition"
    importance: "medium"
    created_at: "2026-02-26T10:30:00+09:00"
    source: "Review comment on FP-H01"
    affects_columns: []
  - key: "FP-H01-3"
    title: "この分析はQ3の事業計画策定を目的としている"
    content: "この分析はQ3の事業計画策定を目的としている。"
    category: "context"
    importance: "medium"
    created_at: "2026-02-26T10:30:00+09:00"
    source: "Review comment on FP-H01"
    affects_columns: []
```

Note: All four entries were initially proposed with `affects_columns: ["population_stats"]`
from the sticky `table: population_stats` annotation. During the confirm step, the user
kept the scope for FP-H01-0 (caution) and FP-H01-1 (methodology) — both are specific to
the population_stats data source — but adjusted FP-H01-2 (definition) and FP-H01-3
(context) to unscoped (`[]`) because "MAU" and project background are not data-source-specific.
This demonstrates the Extract-Preview-Confirm pattern's value: automatic extraction proposes
scope from annotations, but the user corrects over-scoped entries before persistence.

### ReviewComment Model (models/review.py)

```python
class ReviewComment(BaseModel):
    id: str  # "RC-{8hex}"
    design_id: str
    comment: str
    reviewer: str = "analyst"
    status_after: DesignStatus
    created_at: datetime = Field(default_factory=now_jst)
    extracted_knowledge: list[str] = Field(default_factory=list)
```

## Error Handling

### Error Scenarios

1. **Invalid status transition (submit)** — `submit_for_review()` called on non-active design
   - **Handling**: `ReviewService` checks `design.status == DesignStatus.active`.
     Raises `ValueError("Design must be in 'active' status to submit for review, "
     "current status: '{status}'")`
   - **User Impact**: Claude receives error dict and can inform the analyst of the
     required status

2. **Invalid status transition (review)** — `save_review_comment()` called on non-pending design
   - **Handling**: `ReviewService` checks `design.status == DesignStatus.pending_review`.
     Raises `ValueError`. Server converts to error dict
   - **User Impact**: Claude receives error dict and can explain the design must be
     submitted for review first

3. **Invalid post-review status** — `save_review_comment()` called with `status="pending_review"`
   or `status="draft"`
   - **Handling**: `ReviewService` validates against `VALID_REVIEW_TRANSITIONS[pending_review]`.
     Raises `ValueError("Invalid post-review status 'pending_review'. "
     "Valid: active, supported, rejected, inconclusive")`
   - **User Impact**: Claude receives error dict with valid status list

4. **Design not found** — Any review operation called with nonexistent design_id
   - **Handling**: `DesignService.get_design()` returns `None`.
     ReviewService propagates `None`. Server converts to `{"error": "Design 'xyz' not found"}`
   - **User Impact**: Claude receives error dict and can suggest correct design ID

5. **Bypass attempt via update_analysis_design** — `update_analysis_design(status="pending_review")`
   - **Handling**: `update_analysis_design` in `server.py` checks if target status is
     `pending_review` and returns `{"error": "Cannot set status to 'pending_review' directly. "
     "Use submit_for_review() instead."}`
   - **User Impact**: Claude is redirected to the correct workflow tool

6. **No comments for extraction** — `extract_domain_knowledge()` called on design with no comments
   - **Handling**: `list_comments()` returns empty list. `extract_domain_knowledge` returns empty list
   - **User Impact**: Tool returns `{entries: [], count: 0}` — no error

7. **Save without preview** — `save_extracted_knowledge()` called with entries that
   have no `key` or invalid structure
   - **Handling**: `save_extracted_knowledge` validates each entry has required fields
     (`key`, `content`, `category`). Raises `ValueError` for invalid entries
   - **User Impact**: Claude receives error dict and can re-run extraction preview

8. **ReviewService/RulesService not initialized** — MCP tool called before CLI wiring
   - **Handling**: `get_review_service()`/`get_rules_service()` raises `RuntimeError`
     (same pattern as `get_service()`)
   - **User Impact**: MCP protocol returns error. Only occurs in test/dev scenarios

## Testing Strategy

### Unit Testing

| File | Coverage Target |
|------|----------------|
| `tests/test_review_models.py` | `models/review.py` + `models/design.py` extension — 7 tests |
| `tests/test_reviews.py` | `core/reviews.py` — 22 tests |
| `tests/test_rules.py` | `core/rules.py` — 10 tests |
| `tests/test_server.py` (extended) | server.py review tools — 14 tests |
| `tests/test_storage.py` (extended) | project.py changes — 2 tests |

**test_review_models.py** (model validation):
- ReviewComment creation with now_jst default
- ReviewComment creation with empty extracted_knowledge default
- ReviewComment JSON round-trip (serialize + deserialize equivalence)
- AnalysisDesign.source_ids default to empty list
- AnalysisDesign.source_ids with explicit values preserved
- DesignStatus.pending_review value
- ReviewComment with DesignStatus.supported as status_after

**test_reviews.py** (ReviewService operations):
- `submit_for_review`: active design → pending_review, non-active raises ValueError, missing returns None
- `save_review_comment`: pending → supported/rejected/inconclusive/active, non-pending raises ValueError, invalid status raises ValueError, missing returns None
- `list_comments`: returns comments in order, empty for no file, empty for nonexistent
- `extract_domain_knowledge` (preview): caution/definition/methodology/context extraction, no-prefix defaults to context, empty comments returns empty, table: annotation scoping, design.source_ids default scoping, entries returned as preview (not persisted)
- `save_extracted_knowledge` (persist): entries persisted to YAML, duplicate keys skipped, ReviewComment.extracted_knowledge updated

**test_rules.py** (RulesService operations):
- `get_project_context`: aggregates catalog sources + catalog knowledge + extracted knowledge, handles empty gracefully
- `suggest_cautions`: matches all knowledge entries via affects_columns (unified strategy), returns empty for no matches, handles mixed sources

### Integration Testing

- Full round-trip test in `tests/test_integration.py`:
  `create_design()` → `update_design(status="active")` → `submit_for_review()` →
  `save_review_comment(comment, "supported")` → `extract_domain_knowledge()` →
  `save_extracted_knowledge(entries)` → `get_project_context()` (includes extracted knowledge) →
  `suggest_cautions()` — all with real YAML files
- Existing SPEC-1/SPEC-2 tests continue to pass (regression check)
- `update_analysis_design(status="pending_review")` returns error dict (guard test)

### End-to-End Testing

Full MCP protocol E2E testing remains out of scope (same as SPEC-1/SPEC-2).
Integration tests cover the full business logic stack.

### Acceptance Criteria × Test Case Mapping

| AC | Content (Summary) | Test Cases | File |
|----|-------------------|------------|------|
| R1-AC1 | pending_review enum value | `test_design_status_pending_review_value` | `test_review_models.py` |
| R1-AC2 | ReviewComment now_jst default | `test_review_comment_timestamps_default_to_jst` | `test_review_models.py` |
| R1-AC3 | ReviewComment JSON round-trip | `test_review_comment_json_round_trip` | `test_review_models.py` |
| R1-AC4 | AnalysisDesign.source_ids default | `test_analysis_design_source_ids_default_empty` | `test_review_models.py` |
| R1-AC5 | ReviewComment extracted_knowledge default | `test_review_comment_extracted_knowledge_default_empty` | `test_review_models.py` |
| R2-AC1 | submit active → pending_review | `test_submit_for_review_active_design` | `test_reviews.py` |
| R2-AC2 | submit draft raises ValueError | `test_submit_for_review_draft_raises_value_error` | `test_reviews.py` |
| R2-AC3 | submit missing returns None | `test_submit_for_review_missing_returns_none` | `test_reviews.py` |
| R2-AC4 | save comment + status supported | `test_save_review_comment_sets_status_supported` | `test_reviews.py` |
| R2-AC5 | save comment + status active (changes) | `test_save_review_comment_sets_status_active` | `test_reviews.py` |
| R2-AC6 | save on draft raises ValueError | `test_save_review_comment_on_draft_raises_value_error` | `test_reviews.py` |
| R2-AC7 | save with pending_review raises | `test_save_review_comment_pending_review_invalid` | `test_reviews.py` |
| R2-AC8 | two comments listed in order | `test_list_comments_returns_both_in_order` | `test_reviews.py` |
| R2-AC9 | list_comments nonexistent empty | `test_list_comments_nonexistent_returns_empty` | `test_reviews.py` |
| R3-AC1 | extract caution category | `test_extract_caution_from_comment` | `test_reviews.py` |
| R3-AC2 | extract definition category | `test_extract_definition_from_comment` | `test_reviews.py` |
| R3-AC3 | extract returns preview (not persisted) | `test_extract_returns_preview_not_persisted` | `test_reviews.py` |
| R3-AC4 | save persists to YAML | `test_save_extracted_persists_to_yaml` | `test_reviews.py` |
| R3-AC5 | save duplicate keys skipped | `test_save_extracted_duplicate_keys_skipped` | `test_reviews.py` |
| R3-AC6 | no comments returns empty | `test_extract_no_comments_returns_empty` | `test_reviews.py` |
| R3-AC7 | no prefix defaults to context | `test_extract_no_prefix_defaults_to_context` | `test_reviews.py` |
| R3-AC8 | table: annotation sets affects_columns | `test_extract_table_annotation_sets_scope` | `test_reviews.py` |
| R3-AC9 | design.source_ids used as default scope | `test_extract_design_source_ids_default_scope` | `test_reviews.py` |
| R3-AC10 | no annotation + no source_ids = unscoped | `test_extract_no_scope_defaults_to_empty` | `test_reviews.py` |
| R4-AC1 | submit_for_review tool success | `test_submit_for_review_tool_success` | `test_server.py` |
| R4-AC2 | submit_for_review tool error | `test_submit_for_review_tool_non_active_error` | `test_server.py` |
| R4-AC3 | save_review_comment tool success | `test_save_review_comment_tool_success` | `test_server.py` |
| R4-AC4 | save_review_comment tool invalid status | `test_save_review_comment_tool_invalid_status` | `test_server.py` |
| R4-AC5 | extract_domain_knowledge tool (preview) | `test_extract_domain_knowledge_tool_preview` | `test_server.py` |
| R4-AC6 | save_extracted_knowledge tool (persist) | `test_save_extracted_knowledge_tool` | `test_server.py` |
| R4-AC7 | get_project_context tool | `test_get_project_context_tool` | `test_server.py` |
| R4-AC8 | suggest_cautions tool with matches | `test_suggest_cautions_tool_with_matches` | `test_server.py` |
| R4-AC9 | suggest_cautions tool no matches | `test_suggest_cautions_tool_no_matches` | `test_server.py` |
| R5-AC1 | CLI wires services (6 tools) | `test_review_full_round_trip` | `test_integration.py` |
| R5-AC2 | init creates extracted_knowledge | `test_init_project_creates_extracted_knowledge_yaml` | `test_storage.py` |
| R5-AC3 | full flow with preview-confirm | `test_review_full_round_trip` | `test_integration.py` |
| — | update_analysis_design guard | `test_update_design_rejects_pending_review` | `test_server.py` |

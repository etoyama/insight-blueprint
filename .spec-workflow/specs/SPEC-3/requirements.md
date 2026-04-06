# SPEC-3: review-workflow — Requirements

> **Spec ID**: SPEC-3
> **Feature Name**: review-workflow
> **Status**: draft
> **Created**: 2026-02-25
> **Depends On**: SPEC-1 (core-foundation), SPEC-2 (data-catalog)

---

## Introduction

SPEC-3 adds a review workflow to insight-blueprint so that data scientists can submit
analysis designs for structured review, capture reviewer feedback as persistent comments,
and automatically extract reusable domain knowledge from those comments. Extracted
knowledge is persisted to YAML and made available through MCP tools that provide
project-wide analytical context and data-specific cautions. This creates a continuously
growing knowledge base that Claude Code leverages across EDA sessions.

## Alignment with Product Vision

This spec directly enables three core product goals defined in `product.md`:

- **Accumulating domain knowledge from analyst review comments for continuous reuse**:
  The review workflow captures reviewer insights (methodology notes, data cautions,
  definition clarifications) as structured `ReviewComment` records. `extract_domain_knowledge()`
  parses these into `DomainKnowledgeEntry` items persisted to YAML — building a growing
  knowledge base session over session.
- **Communicating data access rules and domain knowledge to AI**:
  `get_project_context()` and `suggest_cautions(table_names)` give Claude Code structured
  access to all accumulated domain knowledge (from both SPEC-2 catalog sources and SPEC-3
  review comments), enabling it to proactively warn analysts about data pitfalls and provide
  relevant analytical context.
- **Spec Roadmap progression**: SPEC-3 is the third spec in the dependency chain. It
  extends SPEC-1's `AnalysisDesign` with a review status lifecycle and SPEC-2's
  `DomainKnowledge` with review-sourced entries. SPEC-4 (webui-dashboard) will surface
  the review workflow in the Rules and History tabs.

## Requirements

### Requirement 1: Review Workflow Models

**User Story:** As a data scientist, I want analysis designs to have a review status
lifecycle with structured review comments, so that feedback is captured formally and
the design's review state is always clear.

**FR-1: DesignStatus Extension**
- Extend `DesignStatus(StrEnum)` in `models/design.py` with a new value: `pending_review`
- Valid status transitions for review workflow:
  - `active` → `pending_review` (analyst submits for review)
  - `pending_review` → `active` (reviewer requests changes)
  - `pending_review` → `supported` (reviewer concludes: hypothesis supported)
  - `pending_review` → `rejected` (reviewer concludes: hypothesis rejected)
  - `pending_review` → `inconclusive` (reviewer concludes: inconclusive)
- Only `submit_for_review()` may transition to `pending_review`; only `save_review_comment()`
  may transition away from `pending_review`

**FR-2: ReviewComment Model**
- New `ReviewComment(BaseModel)` in `models/review.py` with fields:
  - `id: str` — auto-generated short ID (format: `RC-{8-char-hex}`)
  - `design_id: str` — references `AnalysisDesign.id`
  - `comment: str` — free-text review feedback
  - `reviewer: str` (default `"analyst"`)
  - `status_after: DesignStatus` — design status after this review action
  - `created_at: datetime` (default `now_jst()`)
  - `extracted_knowledge: list[str]` — keys of extracted `DomainKnowledgeEntry` items
    (default empty list)

**FR-3: AnalysisDesign Extension — source_ids**
- Extend `AnalysisDesign` in `models/design.py` with a new optional field:
  - `source_ids: list[str]` — IDs of data sources this design analyzes (default empty list)
- Backward-compatible: existing designs without `source_ids` default to `[]`
- Used as default scope when extracting domain knowledge from review comments

#### Acceptance Criteria

1. WHEN `DesignStatus("pending_review")` is created THEN the value `"pending_review"` is stored correctly
2. WHEN a `ReviewComment` is created without `created_at` THEN `now_jst()` is used as default
3. WHEN a `ReviewComment` is serialized via `model_dump(mode="json")` and deserialized back THEN the round-trip produces an equivalent model
4. WHEN an `AnalysisDesign` is created without `source_ids` THEN it defaults to an empty list
5. WHEN a `ReviewComment` is created without `extracted_knowledge` THEN it defaults to an empty list

### Requirement 2: Review Operations

**User Story:** As a data scientist using Claude Code, I want to submit my analysis
design for review and receive structured feedback, so that the review process is tracked
and all comments are preserved.

**FR-4: Submit for Review**
- `ReviewService.submit_for_review(design_id)` transitions design status from `active` to
  `pending_review` via `DesignService.update_design()`
- If design is not found, returns `None`
- If design status is not `active`, raises `ValueError` with message indicating valid
  source status (e.g., "Design must be in 'active' status to submit for review")
- Returns the updated `AnalysisDesign`

**FR-5: Save Review Comment**
- `ReviewService.save_review_comment(design_id, comment, status, reviewer?)` performs:
  1. Validates that `status` is a valid post-review `DesignStatus`
     (one of: `active`, `supported`, `rejected`, `inconclusive`)
  2. Validates that the design is in `pending_review` status
  3. Creates a `ReviewComment` with auto-generated ID
  4. Appends the comment to `.insight/designs/{design_id}_reviews.yaml`
  5. Updates the design status to the provided `status` via `DesignService.update_design()`
  6. Returns the created `ReviewComment`
- If design is not found, returns `None`
- If design is not in `pending_review` status, raises `ValueError`
- If `status` is `pending_review` or `draft`, raises `ValueError` (invalid post-review status)
- Multiple comments can be saved for the same design (review → request changes → re-review)

**FR-6: List Review Comments**
- `ReviewService.list_comments(design_id)` reads
  `.insight/designs/{design_id}_reviews.yaml` and returns all `ReviewComment` items
- Returns empty list if no comments file exists

#### Acceptance Criteria

1. WHEN `submit_for_review(design_id)` is called on an `active` design THEN status changes to `pending_review` and `updated_at` is refreshed
2. WHEN `submit_for_review(design_id)` is called on a `draft` design THEN `ValueError` is raised
3. WHEN `submit_for_review("nonexistent")` is called THEN `None` is returned
4. WHEN `save_review_comment(design_id, "Good analysis", "supported")` is called on a `pending_review` design THEN comment is persisted AND design status changes to `supported`
5. WHEN `save_review_comment(design_id, "Needs more data", "active")` is called THEN design status changes to `active` (request changes flow)
6. WHEN `save_review_comment` is called on a `draft` design THEN `ValueError` is raised
7. WHEN `save_review_comment` is called with `status="pending_review"` THEN `ValueError` is raised (invalid post-review status)
8. WHEN two comments are saved for the same design (after re-submitting) THEN `list_comments` returns both comments in chronological order
9. WHEN `list_comments("nonexistent")` is called THEN empty list is returned

### Requirement 3: Domain Knowledge Extraction

**User Story:** As a data scientist, I want domain knowledge to be automatically
extracted from review comments and saved to the knowledge base, so that insights
captured during reviews are reusable in future analysis sessions.

**FR-7a: Extract Domain Knowledge (Preview)**
- `ReviewService.extract_domain_knowledge(design_id)` performs:
  1. Reads all review comments for the design via `list_comments()`
  2. Reads `AnalysisDesign.source_ids` as default scope
  3. For each comment, extracts structured knowledge entries using keyword-based heuristics:
     - Lines containing `"caution:"` or `"注意:"` → `KnowledgeCategory.caution`
     - Lines containing `"definition:"` or `"定義:"` → `KnowledgeCategory.definition`
     - Lines containing `"methodology:"` or `"手法:"` → `KnowledgeCategory.methodology`
     - Lines containing `"context:"` or `"背景:"` → `KnowledgeCategory.context`
     - Lines containing `"table:"` or `"テーブル:"` → sets entry-level scope
       (overrides design default for subsequent entries until next `table:` line)
     - Remaining non-empty lines without category prefix → `KnowledgeCategory.context` (default)
  4. Creates `DomainKnowledgeEntry` for each extracted item with:
     - `key`: `"{design_id}-{index}"` (e.g., `"FP-H01-0"`)
     - `title`: first 80 characters of extracted text
     - `content`: full extracted text
     - `category`: detected category
     - `source`: `"Review comment on {design_id}"`
     - `importance`: `medium` (default)
     - `affects_columns`: entry-level scope if `table:` annotation present,
       otherwise `design.source_ids` (default scope)
  5. Returns list of extracted entries as preview (does NOT persist to YAML)
- If design has no comments, returns empty list
- Scope priority: `table:` annotation (entry-level) > `design.source_ids` (default) > `[]` (unscoped)

**FR-7b: Save Extracted Knowledge (Persist)**
- `ReviewService.save_extracted_knowledge(design_id, entries)` performs:
  1. Accepts a list of user-confirmed `DomainKnowledgeEntry` items
     (with `affects_columns` adjusted by user if needed)
  2. Persists entries to `.insight/rules/extracted_knowledge.yaml`
  3. Updates the `ReviewComment.extracted_knowledge` list with the saved keys
  4. Returns list of saved `DomainKnowledgeEntry` items
- Duplicate keys (from re-extraction) are skipped — no overwriting
- Entries should be reviewed and confirmed by user before calling this method

**FR-8: Knowledge Persistence Format**
- Extracted knowledge is stored in `.insight/rules/extracted_knowledge.yaml`
- Format: `DomainKnowledge` wrapper with `source_id: "review"` and
  `entries: list[DomainKnowledgeEntry-dicts]` — same container structure as
  SPEC-2 catalog knowledge files
- Each `DomainKnowledgeEntry` includes `affects_columns` populated during extraction
  (from `table:` annotation or `AnalysisDesign.source_ids`)
- New entries are appended to existing entries (accumulative, not overwritten)

#### Acceptance Criteria

1. WHEN `extract_domain_knowledge(design_id)` is called and comments contain "caution: watch for nulls in column X" THEN a `DomainKnowledgeEntry` with `category=caution` is returned in preview
2. WHEN comments contain "definition: MAU = Monthly Active Users" THEN a `DomainKnowledgeEntry` with `category=definition` is returned in preview
3. WHEN `extract_domain_knowledge(design_id)` is called THEN entries are returned as preview (NOT persisted to YAML)
4. WHEN `save_extracted_knowledge(design_id, entries)` is called THEN entries are persisted to `.insight/rules/extracted_knowledge.yaml`
5. WHEN `save_extracted_knowledge` is called twice with same keys THEN duplicate keys are skipped (no duplicates in YAML)
6. WHEN `extract_domain_knowledge` is called for a design with no comments THEN empty list is returned
7. WHEN a comment line has no recognized category prefix THEN the extracted entry defaults to `category=context`
8. WHEN a comment contains "table: population_stats" followed by "caution: ..." THEN the extracted entry has `affects_columns=["population_stats"]`
9. WHEN a comment has no "table:" annotation and design has `source_ids=["X", "Y"]` THEN extracted entries have `affects_columns=["X", "Y"]`
10. WHEN a comment has no "table:" annotation and design has `source_ids=[]` THEN extracted entries have `affects_columns=[]`

### Requirement 4: MCP Tools

**User Story:** As a data scientist using Claude Code, I want Claude to manage the
review workflow, extract knowledge, and provide project context through MCP tools,
so that the full review lifecycle is accessible during analysis sessions.

**FR-9: submit_for_review Tool**
- Accepts: `design_id: str`
- Returns: `{design_id, status, message}` on success, `{error}` on failure
- Maps to `ReviewService.submit_for_review()`

**FR-10: save_review_comment Tool**
- Accepts: `design_id: str`, `comment: str`, `status: str`, `reviewer: str` (default `"analyst"`)
- Returns: `{comment_id, design_id, status_after, message}` on success, `{error}` on failure
- Maps to `ReviewService.save_review_comment()`

**FR-11a: extract_domain_knowledge Tool (Preview)**
- Accepts: `design_id: str`
- Returns: `{design_id, entries: [{key, content, category, suggested_scope}, ...], count, message}`
  on success, `{error}` on failure
- Entries are returned as preview — not persisted until `save_extracted_knowledge` is called
- Maps to `ReviewService.extract_domain_knowledge()`

**FR-11b: save_extracted_knowledge Tool (Persist)**
- Accepts: `design_id: str`, `entries: list[{key, content, category, scope}]`
- Returns: `{design_id, saved_entries: [...], count, message}` on success, `{error}` on failure
- Should be called after user has reviewed and optionally adjusted scopes from preview
- Maps to `ReviewService.save_extracted_knowledge()`

**FR-12: get_project_context Tool**
- Accepts: no required parameters
- Returns: `{sources: [...], knowledge_entries: [...], rules: [...], total_sources, total_knowledge, total_rules}`
- Aggregates domain knowledge from:
  - `catalog/knowledge/*.yaml` (per-source knowledge from SPEC-2)
  - `.insight/rules/extracted_knowledge.yaml` (review-extracted knowledge)
- Maps to `RulesService.get_project_context()`

**FR-13: suggest_cautions Tool**
- Accepts: `table_names: str` (comma-separated string of source/table names)
- Returns: `{table_names: [...], cautions: [...], count}`
- Searches all domain knowledge entries (catalog and extracted) by matching
  `affects_columns` against provided `table_names` — single unified matching strategy
- Maps to `RulesService.suggest_cautions()`

#### Acceptance Criteria

1. WHEN `submit_for_review(design_id)` is called with a valid active design THEN `{design_id, status: "pending_review", message}` is returned
2. WHEN `submit_for_review(design_id)` is called with a non-active design THEN `{error}` dict is returned
3. WHEN `save_review_comment(design_id, "Good", "supported")` is called THEN `{comment_id, design_id, status_after: "supported", message}` is returned
4. WHEN `save_review_comment` is called with invalid status THEN `{error}` dict is returned
5. WHEN `extract_domain_knowledge(design_id)` is called THEN `{design_id, entries: [{key, content, category, suggested_scope}, ...], count, message}` is returned (preview, not persisted)
6. WHEN `save_extracted_knowledge(design_id, entries)` is called with confirmed entries THEN `{design_id, saved_entries, count, message}` is returned and entries are persisted
7. WHEN `get_project_context()` is called THEN aggregated knowledge from all sources is returned
8. WHEN `suggest_cautions(table_names="population,sales")` is called THEN relevant cautions matching those tables via `affects_columns` are returned
9. WHEN `suggest_cautions` is called with tables that have no cautions THEN `{table_names, cautions: [], count: 0}` is returned

### Requirement 5: CLI Wiring and Integration

**User Story:** As a data scientist, I want the review workflow to be ready immediately
when I start insight-blueprint, so that I can submit designs for review and access
project context right away.

**FR-14: CLI Startup Integration**
- `cli.py` instantiates `ReviewService(project_path, design_service)` and wires it to
  `server._review_service`
- `cli.py` instantiates `RulesService(project_path, catalog_service)` and wires it to
  `server._rules_service`
- Both services are wired before `mcp.run()`

**FR-15: Project Initialization Updates**
- `init_project()` creates `.insight/rules/extracted_knowledge.yaml` with
  `{source_id: "review", entries: []}` if not present
- Existing `.insight/designs/` and `.insight/rules/` directories already created by SPEC-1

#### Acceptance Criteria

1. WHEN `uvx insight-blueprint --project /path` is run THEN `ReviewService` and `RulesService` are initialized and all 6 review MCP tools are available
2. WHEN `init_project()` is called THEN `.insight/rules/extracted_knowledge.yaml` is created (if absent) with `{source_id: "review", entries: []}`
3. WHEN the full flow `submit_for_review()` → `save_review_comment()` → `extract_domain_knowledge()` → user confirms → `save_extracted_knowledge()` is executed THEN knowledge is persisted to YAML and `get_project_context()` returns it

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility Principle**: `models/review.py` = data models only,
  `core/reviews.py` = review operations only, `core/rules.py` = knowledge aggregation only
- **Three-Layer Separation**: MCP tools (server.py) delegate to `ReviewService` and
  `RulesService` (core/), which delegate to `yaml_store.py` and `DesignService`;
  no cross-layer skipping
- **Pattern Reuse**: `ReviewService` and `RulesService` follow the same structure as
  `DesignService` and `CatalogService` (constructor with `project_path`, YAML persistence)
- **Type Annotations Required**: All functions have complete type annotations; `ty check` passes
- **Code Quality**: `ruff check` passes; `pytest` coverage for `core/reviews.py` and
  `core/rules.py` is 80% or higher

### Performance

- `submit_for_review()` completes within 100ms (one YAML read + one YAML write)
- `save_review_comment()` completes within 200ms (two YAML reads + two YAML writes)
- `extract_domain_knowledge()` completes within 500ms for up to 50 review comments
- `get_project_context()` completes within 500ms for up to 100 sources and 500 knowledge entries
- `suggest_cautions()` completes within 200ms for up to 500 knowledge entries

### Security

- No hardcoded secrets, API keys, or credentials in source code
- Error messages do not expose internal file paths or stack traces to MCP clients
- User-provided review comment content is stored as-is (no code execution on comments)
- Knowledge extraction uses simple string matching — no eval/exec on user content

### Reliability

- All YAML writes remain atomic (`tempfile.mkstemp()` + `os.replace()`)
- Missing design: `submit_for_review()` and `save_review_comment()` return `None` (no crash)
- Missing reviews file: `list_comments()` returns empty list
- Missing `extracted_knowledge.yaml`: `get_project_context()` treats it as empty
- Existing SPEC-1/SPEC-2 tests continue to pass (no regressions)
- `extract_domain_knowledge()` with no comments returns empty list (no crash)
- Status transition validation prevents invalid state changes

### Usability

- MCP tool docstrings clearly describe parameters, valid status values, and return formats
- `submit_for_review` error messages indicate the current status and valid source status
- `save_review_comment` error messages include list of valid post-review statuses
- `get_project_context` returns a well-structured summary for Claude Code to present
- `suggest_cautions` returns human-readable caution entries for easy display

## Out of Scope

- Real-time collaborative review (only single-reviewer workflow in v1)
- AI-powered knowledge extraction using LLM (keyword-based heuristics only in v1)
- Review notification system (no email/webhook notifications)
- Review assignment workflow (reviewer is implicitly the analyst or a designated reviewer)
- WebUI review interface (SPEC-4 will add this)
- Version history for extracted knowledge (no rollback capability)
- Custom knowledge category definitions (uses SPEC-2's fixed `KnowledgeCategory` enum)
- Automatic FTS5 indexing of extracted knowledge (future enhancement)
- `Rule` model and rule-based knowledge management (replaced by unified
  `DomainKnowledgeEntry` with `affects_columns` scoping via Extract-Preview-Confirm workflow)

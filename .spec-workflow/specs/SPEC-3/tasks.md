# SPEC-3: review-workflow — Tasks

> **Spec ID**: SPEC-3
> **Status**: draft
> **Created**: 2026-02-26
> **Depends On**: SPEC-1 (core-foundation), SPEC-2 (data-catalog)

---

## Dependency Graph

```
1.1 ──→ 1.2 ──→ 2.1 ──→ 2.2 ──→ 4.1 ──→ 4.2 ──→ 5.1
                                   ↑
                  3.1 ─────────────┘
```

---

## Completion Criteria

| # | Criterion | Metric |
|---|-----------|--------|
| C1 | All tasks completed | 8/8 tasks marked `[x]` |
| C2 | New unit tests pass | 56 tests green (3 + 4 + 13 + 9 + 10 + 14 + 2 + 1) |
| C3 | No regressions | All existing SPEC-1/SPEC-2 tests still pass |
| C4 | Quality gate passes | `poe all` (ruff + ty + pytest) exits 0 |
| C5 | MCP tools registered | 6 new tools callable via FastMCP instance |
| C6 | Integration round-trip | `test_review_full_round_trip` covers submit → comment → extract → save → context → cautions |

## Verification Procedures

1. **Run full quality gate**
   ```bash
   poe all
   ```
   - Confirm: exit code 0, zero ruff violations, zero ty errors, all pytest tests pass

2. **Verify test counts**
   ```bash
   pytest --co -q | tail -1
   ```
   - Confirm: total test count = previous count + 56 new tests

3. **Verify MCP tool registration**
   ```bash
   pytest tests/test_server.py -v -k "review or rules or knowledge or caution or context"
   ```
   - Confirm: 14 server tests pass, covering all 6 new tools + pending_review guard

4. **Verify integration round-trip**
   ```bash
   pytest tests/test_integration.py::test_review_full_round_trip -v
   ```
   - Confirm: full Extract-Preview-Confirm flow passes with real YAML files

5. **Verify no regressions**
   ```bash
   pytest tests/test_integration.py -v
   ```
   - Confirm: `test_full_round_trip`, `test_catalog_full_round_trip`, and `test_review_full_round_trip` all pass

---

- [x] 1.1 Extend DesignStatus and add source_ids to AnalysisDesign
  - File: `src/insight_blueprint/models/design.py`, `tests/test_review_models.py`
  - Add `pending_review = "pending_review"` to `DesignStatus(StrEnum)`
  - Add `source_ids: list[str] = Field(default_factory=list)` to `AnalysisDesign`
  - TDD: Write 3 tests first (Red), then implement (Green)
    - `test_design_status_pending_review_value` — AC1
    - `test_analysis_design_source_ids_default_empty` — AC4
    - `test_analysis_design_source_ids_with_values` — extra
  - Purpose: Foundation for review status lifecycle and knowledge scoping
  - _Leverage: existing `DesignStatus(StrEnum)` definition, existing `AnalysisDesign` model_
  - _Requirements: FR-1, FR-3_
  - _Prompt: Role: Python Developer with Pydantic expertise | Task: Extend DesignStatus enum with pending_review and add source_ids field to AnalysisDesign, writing tests first per TDD | Restrictions: Additive changes only — do not modify existing enum values or fields. Backward-compatible (existing YAML without source_ids must load) | Success: 3 tests pass, existing SPEC-1 design tests still pass, ty check passes_

- [x] 1.2 Create ReviewComment model and update re-exports
  - File: `src/insight_blueprint/models/review.py` (NEW), `src/insight_blueprint/models/__init__.py`, `tests/test_review_models.py`
  - Create `ReviewComment(BaseModel)` with fields: id, design_id, comment, reviewer, status_after, created_at, extracted_knowledge
  - Update `models/__init__.py` to re-export `ReviewComment`
  - TDD: Write 4 tests first (Red), then implement (Green)
    - `test_review_comment_timestamps_default_to_jst` — AC2
    - `test_review_comment_extracted_knowledge_default_empty` — AC5
    - `test_review_comment_json_round_trip` — AC3
    - `test_review_comment_status_after_supported` — extra
  - Purpose: Data model for structured review feedback
  - _Leverage: `now_jst()` from `models/common.py`, `DesignStatus` from `models/design.py`_
  - _Requirements: FR-2_
  - _Prompt: Role: Python Developer with Pydantic expertise | Task: Create ReviewComment model in new models/review.py file with all specified fields and defaults, update __init__.py re-exports, writing tests first per TDD | Restrictions: Only ReviewComment in this file (no Rule model). Follow existing model patterns (now_jst default, Field defaults) | Success: 4 tests pass, total 7 model tests pass, ruff + ty pass_

- [x] 2.1 Implement ReviewService core operations (submit, comment, list)
  - File: `src/insight_blueprint/core/reviews.py` (NEW), `tests/test_reviews.py` (NEW), `tests/conftest.py`
  - Create `ReviewService(project_path, design_service)` with:
    - `VALID_REVIEW_TRANSITIONS` dict as single source of truth
    - `submit_for_review(design_id)` — validate active, transition to pending_review
    - `save_review_comment(design_id, comment, status, reviewer)` — validate pending_review, persist comment YAML, transition design
    - `list_comments(design_id)` — read reviews YAML, return all
  - Add shared fixtures to `conftest.py`: `design_service`, `review_service`, `active_design`, `pending_design`
  - TDD: Write 13 tests first (Red), then implement (Green)
    - TestSubmitForReview: 3 tests (AC1-AC3 of R2)
    - TestSaveReviewComment: 7 tests (AC4-AC7 of R2 + status variations)
    - TestListComments: 3 tests (AC8-AC9 of R2 + empty)
  - Purpose: Core review workflow — submit designs for review and capture structured feedback
  - _Leverage: `DesignService.get_design()` / `update_design()`, `read_yaml` / `write_yaml` from `yaml_store.py`_
  - _Requirements: FR-4, FR-5, FR-6_
  - _Prompt: Role: Python Developer with DDD and TDD expertise | Task: Implement ReviewService with submit_for_review, save_review_comment, list_comments. Define VALID_REVIEW_TRANSITIONS as source of truth. Write 13 tests first per TDD | Restrictions: Delegate to DesignService for design operations — no direct YAML manipulation of design files. Atomic writes via write_yaml. Do not implement extract/save knowledge in this task | Success: 13 tests pass, status transitions enforced, comments persisted to {design_id}_reviews.yaml_

- [x] 2.2 Implement extract_domain_knowledge and save_extracted_knowledge
  - File: `src/insight_blueprint/core/reviews.py`, `tests/test_reviews.py`
  - Add to `ReviewService`:
    - `extract_domain_knowledge(design_id)` — keyword-based extraction with regex prefix detection, NFKC normalization, `table:` annotation scoping, `design.source_ids` default scope. Returns preview (NOT persisted)
    - `save_extracted_knowledge(design_id, entries)` — persist confirmed entries to `rules/extracted_knowledge.yaml`, update ReviewComment.extracted_knowledge
  - TDD: Write 9 tests first (Red), then implement (Green)
    - TestExtractDomainKnowledge: 6 tests (AC1-AC3, AC6-AC10 of R3)
    - TestSaveExtractedKnowledge: 3 tests (AC4-AC5 of R3 + comment update)
  - Purpose: Extract-Preview-Confirm pattern — extract reusable domain knowledge from review comments with user-confirmable scoping
  - _Leverage: `list_comments()` from task 2.1, `DesignService.get_design()` for source_ids, `read_yaml` / `write_yaml`, `DomainKnowledgeEntry` from `models/catalog.py`_
  - _Requirements: FR-7a, FR-7b, FR-8_
  - _Prompt: Role: Python Developer with regex and text processing expertise | Task: Implement extract_domain_knowledge (preview) and save_extracted_knowledge (persist) in ReviewService. Use regex prefix detection (case-insensitive), NFKC normalization, table: annotation scoping with design.source_ids fallback. Write 9 tests first per TDD | Restrictions: extract returns preview only — no persistence. save persists to rules/extracted_knowledge.yaml using DomainKnowledge wrapper (source_id: "review"). Duplicate keys skipped. Scope priority: table: annotation > design.source_ids > [] | Success: 9 tests pass, total 22 ReviewService tests pass, all 4 categories extracted, scoping works correctly_

- [x] 3.1 Implement RulesService (get_project_context, suggest_cautions)
  - File: `src/insight_blueprint/core/rules.py` (NEW), `tests/test_rules.py` (NEW)
  - Create `RulesService(project_path, catalog_service)` with:
    - `get_project_context()` — aggregate catalog sources + catalog knowledge + extracted knowledge + rules YAML content
    - `suggest_cautions(table_names)` — unified `affects_columns` matching against all knowledge entries
  - TDD: Write 10 tests first (Red), then implement (Green)
    - TestGetProjectContext: 5 tests (catalog sources, catalog knowledge, extracted knowledge, empty, rule files)
    - TestSuggestCautions: 5 tests (catalog match, extracted match, mixed, no match, unscoped not returned)
  - Purpose: Knowledge aggregation and targeted caution suggestion for Claude Code
  - _Leverage: `CatalogService.list_sources()` / `get_knowledge()`, `read_yaml` for extracted knowledge and rule files_
  - _Requirements: FR-12, FR-13_
  - _Prompt: Role: Python Developer with data aggregation expertise | Task: Implement RulesService with get_project_context and suggest_cautions. get_project_context aggregates all knowledge sources. suggest_cautions uses unified affects_columns matching. Write 10 tests first per TDD | Restrictions: Read-only access to catalog via CatalogService interface. Unified matching strategy — no content keyword fallback. Unscoped entries (affects_columns=[]) excluded from suggest_cautions | Success: 10 tests pass, project context aggregates all sources correctly, caution matching is accurate with no false positives_

- [x] 4.1 Add 6 MCP tools to server.py and pending_review guard
  - File: `src/insight_blueprint/server.py`, `tests/test_server.py`
  - Add module-level references: `_review_service`, `_rules_service`
  - Add guard functions: `get_review_service()`, `get_rules_service()`
  - Add 6 `@mcp.tool()` functions: `submit_for_review`, `save_review_comment`, `extract_domain_knowledge`, `save_extracted_knowledge`, `get_project_context`, `suggest_cautions`
  - Add guard on existing `update_analysis_design` to reject `status="pending_review"`
  - TDD: Write 14 tests first (Red) with mocked services, then implement (Green)
    - submit_for_review: 3 tests (success, error, not found)
    - save_review_comment: 3 tests (success, invalid status, not found)
    - extract_domain_knowledge: 1 test (preview)
    - save_extracted_knowledge: 2 tests (success, invalid)
    - get_project_context: 1 test
    - suggest_cautions: 2 tests (matches, no matches)
    - pending_review guard: 1 test
    - service not initialized: 1 test
  - Purpose: Expose review workflow to Claude Code via MCP protocol
  - _Leverage: existing `get_service()` guard pattern, existing error dict pattern (`ValueError → {error: str(e)}`)_
  - _Requirements: FR-9, FR-10, FR-11a, FR-11b, FR-12, FR-13_
  - _Prompt: Role: Python Developer with MCP/FastMCP expertise | Task: Add 6 MCP tools and pending_review guard to server.py. Follow existing tool patterns (error dict, guard functions). Write 14 tests with mocked services first per TDD | Restrictions: Tools must delegate to ReviewService/RulesService — no business logic in server.py. Follow existing error dict pattern. Mock services in tests (not YAML) | Success: 14 tests pass, 6 tools registered on FastMCP instance, pending_review guard blocks direct status set, existing server tests still pass_

- [x] 4.2 Wire services in cli.py and update init_project
  - File: `src/insight_blueprint/cli.py`, `src/insight_blueprint/storage/project.py`, `tests/test_storage.py`
  - In `cli.py`: import and instantiate `ReviewService(project_path, design_service)` and `RulesService(project_path, catalog_service)`, wire to `server._review_service` and `server._rules_service` before `mcp.run()`
  - In `storage/project.py`: extend `init_project()` / `_create_insight_dirs()` to create `.insight/rules/extracted_knowledge.yaml` with `{source_id: "review", entries: []}` if absent
  - TDD: Write 2 tests first (Red), then implement (Green)
    - `test_init_project_creates_extracted_knowledge_yaml` — AC2 of R5
    - `test_init_project_does_not_overwrite_existing_extracted_knowledge` — extra
  - Purpose: Ensure review workflow is ready at startup and storage is initialized
  - _Leverage: existing service wiring pattern in `cli.py`, existing `_create_insight_dirs()` pattern, `write_yaml`_
  - _Requirements: FR-14, FR-15_
  - _Prompt: Role: Python Developer with CLI integration expertise | Task: Wire ReviewService and RulesService in cli.py (after DesignService/CatalogService, before mcp.run). Update init_project to create extracted_knowledge.yaml. Write 2 tests first per TDD | Restrictions: Follow existing wiring order. Idempotent init — do not overwrite existing extracted_knowledge.yaml. Services wired after their dependencies | Success: 2 tests pass, existing init tests still pass, services available at startup_

- [x] 5.1 Full round-trip integration test and regression verification
  - File: `tests/test_integration.py`
  - Add `test_review_full_round_trip`: create_design → update(active) → submit_for_review → save_review_comment → extract_domain_knowledge → save_extracted_knowledge → get_project_context → suggest_cautions
  - Verify existing `test_full_round_trip` and `test_catalog_full_round_trip` still pass
  - Run `poe all` (ruff + ty + pytest) for final quality gate
  - Purpose: End-to-end validation of the complete Extract-Preview-Confirm flow with real YAML files
  - _Leverage: existing integration test patterns, `tmp_project` fixture, all new services_
  - _Requirements: FR-14 (R5-AC1), R5-AC3_
  - _Prompt: Role: QA Engineer with integration testing expertise | Task: Write full round-trip integration test covering the complete review workflow including Extract-Preview-Confirm. Verify all existing tests still pass (no regressions). Run full quality gate | Restrictions: Use real YAML files (no mocks). Test must cover submit → comment → extract (preview) → save (persist) → context → cautions. Do not modify existing test functions | Success: Integration test passes, all existing SPEC-1/SPEC-2 tests pass, poe all succeeds (ruff + ty + pytest)_

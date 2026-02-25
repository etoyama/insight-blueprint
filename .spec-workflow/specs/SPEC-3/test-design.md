# SPEC-3: review-workflow — Test Design

> **Spec ID**: SPEC-3
> **Status**: draft
> **Created**: 2026-02-26
> **Depends On**: SPEC-1 (core-foundation), SPEC-2 (data-catalog)

---

## Test Architecture

### Test Pyramid

```
          ┌──────────┐
          │ E2E (MCP) │  ← Out of scope (same as SPEC-1/2)
          ├──────────┤
        ┌─┤Integration├─┐  ← test_integration.py (round-trip)
        │ ├──────────┤ │
  ┌─────┴─┴──────────┴─┴─────┐
  │     Unit Tests (55 tests)  │  ← 5 test files
  └───────────────────────────┘
```

### Test File Layout

| File | Target Module | Test Count | Pattern |
|------|--------------|-----------|---------|
| `tests/test_review_models.py` | `models/review.py` + `models/design.py` extension | 7 | Function-based |
| `tests/test_reviews.py` | `core/reviews.py` | 22 | Class-based (per method) |
| `tests/test_rules.py` | `core/rules.py` | 10 | Class-based (per method) |
| `tests/test_server.py` (extended) | `server.py` review tools | 14 | Function-based (existing pattern) |
| `tests/test_storage.py` (extended) | `storage/project.py` init extension | 2 | Function-based (existing pattern) |
| `tests/test_integration.py` (extended) | Full round-trip | 1 | Function-based (existing pattern) |

**Total**: 56 new test cases

## Shared Fixtures

### Existing (`conftest.py`)

```python
@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Return a temporary project directory with .insight/ initialized."""
    from insight_blueprint.storage.project import init_project
    init_project(tmp_path)
    return tmp_path
```

### New Fixtures to Add (`conftest.py`)

```python
@pytest.fixture
def design_service(tmp_project: Path) -> DesignService:
    """DesignService wired to tmp_project."""
    return DesignService(tmp_project)

@pytest.fixture
def catalog_service(tmp_project: Path) -> CatalogService:
    """CatalogService wired to tmp_project."""
    return CatalogService(tmp_project)

@pytest.fixture
def review_service(tmp_project: Path, design_service: DesignService) -> ReviewService:
    """ReviewService wired to DesignService."""
    return ReviewService(tmp_project, design_service)

@pytest.fixture
def rules_service(tmp_project: Path, catalog_service: CatalogService) -> RulesService:
    """RulesService wired to CatalogService."""
    return RulesService(tmp_project, catalog_service)

@pytest.fixture
def active_design(design_service: DesignService) -> AnalysisDesign:
    """Create a design in active status (ready for submit_for_review)."""
    design = design_service.create_design(
        title="Test Hypothesis",
        hypothesis_statement="Statement",
        hypothesis_background="Background",
        theme_id="FP",
    )
    return design_service.update_design(design.id, status="active")

@pytest.fixture
def active_design_with_sources(design_service: DesignService) -> AnalysisDesign:
    """Create an active design with source_ids for scoping tests."""
    design = design_service.create_design(
        title="Population Analysis",
        hypothesis_statement="Population correlates with GDP",
        hypothesis_background="Background",
        theme_id="POP",
    )
    updated = design_service.update_design(
        design.id, status="active", source_ids=["population_stats", "gdp_data"]
    )
    return updated

@pytest.fixture
def pending_design(
    review_service: ReviewService, active_design: AnalysisDesign
) -> AnalysisDesign:
    """Create a design in pending_review status (ready for save_review_comment)."""
    return review_service.submit_for_review(active_design.id)
```

### Design Note: Fixture Scope

All fixtures use default `function` scope — each test gets a fresh `tmp_path`, fresh services,
and clean YAML files. No shared state between tests. This matches SPEC-1/SPEC-2 patterns
(`test_designs.py`, `test_catalog.py`).

## Test Data

### Sample Review Comments

```python
# Comment with all 4 knowledge categories + table annotation
MULTI_CATEGORY_COMMENT = """\
table: population_stats
caution: 2015年以降の人口統計は調査方法が変更されているため、直接比較する場合は補正が必要。
methodology: 人口動態比較には年齢調整標準化を用いること。
definition: MAU = 月間アクティブユーザー数
背景: この分析はQ3の事業計画策定を目的としている。
"""

# Comment with only caution (single category)
SINGLE_CAUTION_COMMENT = "caution: watch for nulls in column X"

# Comment with definition (English)
DEFINITION_COMMENT = "definition: MAU = Monthly Active Users"

# Comment with Japanese keywords
JAPANESE_KEYWORD_COMMENT = """\
注意: このデータは2020年以降のみ有効。
定義: DAU = 日次アクティブユーザー数
手法: 移動平均を用いてトレンド分析を行う。
テーブル: user_activity
"""

# Comment with no recognized prefix (defaults to context)
NO_PREFIX_COMMENT = "This dataset was collected during COVID-19 period, which may affect trends."

# Comment with table annotation mid-comment (scope changes)
MID_TABLE_COMMENT = """\
caution: Global caution applying to default scope.
table: specific_table
caution: This caution applies only to specific_table.
"""

# Empty comment
EMPTY_COMMENT = ""
```

### Sample Extracted Knowledge Entries

```python
# For save_extracted_knowledge tests — pre-built DomainKnowledgeEntry list
SAMPLE_ENTRIES = [
    DomainKnowledgeEntry(
        key="FP-H01-0",
        title="2015年以降の人口統計は調査方法が変更されている",
        content="2015年以降の人口統計は調査方法が変更されているため、直接比較する場合は補正が必要。",
        category=KnowledgeCategory.caution,
        source="Review comment on FP-H01",
        affects_columns=["population_stats"],
    ),
    DomainKnowledgeEntry(
        key="FP-H01-1",
        title="MAU = 月間アクティブユーザー数",
        content="MAU = 月間アクティブユーザー数",
        category=KnowledgeCategory.definition,
        source="Review comment on FP-H01",
        affects_columns=[],
    ),
]

# Duplicate entry for skip-duplicate test
DUPLICATE_ENTRY = DomainKnowledgeEntry(
    key="FP-H01-0",  # Same key as above
    title="Duplicate",
    content="Should be skipped",
    category=KnowledgeCategory.caution,
    source="Review comment on FP-H01",
    affects_columns=["population_stats"],
)
```

### Sample Catalog Knowledge (for RulesService tests)

```python
# Pre-populated catalog knowledge for suggest_cautions cross-source tests
CATALOG_KNOWLEDGE = DomainKnowledge(
    source_id="estat-pop",
    entries=[
        DomainKnowledgeEntry(
            key="cat-caution-1",
            title="Population census methodology change",
            content="Census methodology changed in 2015",
            category=KnowledgeCategory.caution,
            affects_columns=["population_stats"],
        ),
        DomainKnowledgeEntry(
            key="cat-method-1",
            title="Seasonal adjustment method",
            content="Use X-12-ARIMA for seasonal adjustment",
            category=KnowledgeCategory.methodology,
            affects_columns=["sales_data"],
        ),
    ],
)
```

## Mock Strategy

### What to Mock

| Dependency | Where | Mock Approach |
|-----------|-------|--------------|
| Nothing | `test_review_models.py` | Pure model tests — no mocks |
| Nothing | `test_reviews.py` | Uses real DesignService + real YAML (via `tmp_project`) |
| Nothing | `test_rules.py` | Uses real CatalogService + real YAML (via `tmp_project`) |
| `ReviewService` | `test_server.py` | Service-level mock (mock the service, not YAML) |
| `RulesService` | `test_server.py` | Service-level mock |
| Nothing | `test_integration.py` | Full real stack (via `tmp_project`) |

### Design Note: No Mocks for Service Tests

Following SPEC-1/SPEC-2 patterns (`test_designs.py`, `test_catalog.py`), service-level
tests use **real YAML files** in `tmp_path` rather than mocking `read_yaml`/`write_yaml`.
This provides higher confidence in the YAML persistence layer and matches the
existing test approach.

Server tests (`test_server.py`) mock at the **service boundary** — i.e., mock
`ReviewService`/`RulesService` objects rather than their internal dependencies.
This tests the MCP tool layer (parameter parsing, error dict conversion) without
depending on YAML persistence.

## Test Specifications by File

### `test_review_models.py` — 7 Tests

Tests pure Pydantic model behavior. No I/O, no services.

| # | Test Name | AC | Input | Expected |
|---|-----------|-----|-------|----------|
| 1 | `test_review_comment_timestamps_default_to_jst` | R1-AC2 | `ReviewComment(id="RC-test", design_id="X", comment="c", status_after=DesignStatus.active)` | `created_at` is `now_jst()` timezone (Asia/Tokyo) |
| 2 | `test_review_comment_extracted_knowledge_default_empty` | R1-AC5 | Same as above, no `extracted_knowledge` arg | `extracted_knowledge == []` |
| 3 | `test_review_comment_json_round_trip` | R1-AC3 | `comment.model_dump(mode="json")` → `ReviewComment(**dumped)` | Round-trip produces equivalent model |
| 4 | `test_analysis_design_source_ids_default_empty` | R1-AC4 | `AnalysisDesign(id="X", ...)` without `source_ids` | `source_ids == []` |
| 5 | `test_analysis_design_source_ids_with_values` | — | `AnalysisDesign(id="X", ..., source_ids=["a", "b"])` | `source_ids == ["a", "b"]` |
| 6 | `test_design_status_pending_review_value` | R1-AC1 | `DesignStatus("pending_review")` | Value is `"pending_review"` |
| 7 | `test_review_comment_status_after_supported` | — | `ReviewComment(..., status_after=DesignStatus.supported)` | `status_after == DesignStatus.supported` |

### `test_reviews.py` — 22 Tests

Tests ReviewService with real YAML files via `tmp_project`.

#### Class: `TestSubmitForReview` (3 tests)

| # | Test Name | AC | Setup | Action | Expected |
|---|-----------|-----|-------|--------|----------|
| 1 | `test_submit_for_review_active_design` | R2-AC1 | `active_design` fixture | `submit_for_review(design_id)` | Returns `AnalysisDesign` with `status=pending_review` |
| 2 | `test_submit_for_review_draft_raises_value_error` | R2-AC2 | Create draft design (no status change) | `submit_for_review(design_id)` | `ValueError("must be in 'active' status")` |
| 3 | `test_submit_for_review_missing_returns_none` | R2-AC3 | No design created | `submit_for_review("nonexistent")` | Returns `None` |

#### Class: `TestSaveReviewComment` (7 tests)

| # | Test Name | AC | Setup | Action | Expected |
|---|-----------|-----|-------|--------|----------|
| 4 | `test_save_review_comment_sets_status_supported` | R2-AC4 | `pending_design` fixture | `save_review_comment(id, "Good", "supported")` | Comment persisted, design status = `supported` |
| 5 | `test_save_review_comment_sets_status_active` | R2-AC5 | `pending_design` fixture | `save_review_comment(id, "Needs work", "active")` | Design status = `active` (request changes) |
| 6 | `test_save_review_comment_sets_status_rejected` | — | `pending_design` fixture | `save_review_comment(id, "Not valid", "rejected")` | Design status = `rejected` |
| 7 | `test_save_review_comment_sets_status_inconclusive` | — | `pending_design` fixture | `save_review_comment(id, "Unclear", "inconclusive")` | Design status = `inconclusive` |
| 8 | `test_save_review_comment_on_draft_raises_value_error` | R2-AC6 | Create draft design | `save_review_comment(...)` | `ValueError` |
| 9 | `test_save_review_comment_pending_review_invalid` | R2-AC7 | `pending_design` fixture | `save_review_comment(id, "x", "pending_review")` | `ValueError("Invalid post-review status")` |
| 10 | `test_save_review_comment_missing_returns_none` | — | No design | `save_review_comment("missing", ...)` | Returns `None` |

#### Class: `TestListComments` (3 tests)

| # | Test Name | AC | Setup | Action | Expected |
|---|-----------|-----|-------|--------|----------|
| 11 | `test_list_comments_returns_both_in_order` | R2-AC8 | Submit → comment → re-submit → comment | `list_comments(id)` | 2 comments in chronological order |
| 12 | `test_list_comments_empty_for_no_reviews_file` | — | `active_design` (no reviews file) | `list_comments(id)` | `[]` |
| 13 | `test_list_comments_nonexistent_returns_empty` | R2-AC9 | No design | `list_comments("nonexistent")` | `[]` |

#### Class: `TestExtractDomainKnowledge` (9 tests)

| # | Test Name | AC | Setup | Action | Expected |
|---|-----------|-----|-------|--------|----------|
| 14 | `test_extract_caution_from_comment` | R3-AC1 | Pending → comment with `SINGLE_CAUTION_COMMENT` → supported | `extract_domain_knowledge(id)` | 1 entry, `category=caution` |
| 15 | `test_extract_definition_from_comment` | R3-AC2 | Pending → comment with `DEFINITION_COMMENT` → supported | `extract_domain_knowledge(id)` | 1 entry, `category=definition` |
| 16 | `test_extract_methodology_from_comment` | — | Pending → comment with "methodology: Use X method" → supported | `extract_domain_knowledge(id)` | 1 entry, `category=methodology` |
| 17 | `test_extract_japanese_keywords` | — | Pending → comment with `JAPANESE_KEYWORD_COMMENT` → supported | `extract_domain_knowledge(id)` | 4 entries (注意→caution, 定義→definition, 手法→methodology, テーブル sets scope) |
| 18 | `test_extract_returns_preview_not_persisted` | R3-AC3 | Same as #14 | After `extract_domain_knowledge(id)` | `extracted_knowledge.yaml` entries unchanged |
| 19 | `test_extract_no_comments_returns_empty` | R3-AC6 | Active design, no comments | `extract_domain_knowledge(id)` | `[]` |
| 20 | `test_extract_no_prefix_defaults_to_context` | R3-AC7 | Pending → comment with `NO_PREFIX_COMMENT` → supported | `extract_domain_knowledge(id)` | 1 entry, `category=context` |
| 21 | `test_extract_table_annotation_sets_scope` | R3-AC8 | Pending → comment with `MID_TABLE_COMMENT`, design has `source_ids=["default_src"]` | `extract_domain_knowledge(id)` | Entry before `table:` has `affects_columns=["default_src"]`, entry after has `["specific_table"]` |
| 22 | `test_extract_design_source_ids_default_scope` | R3-AC9 | `active_design_with_sources` → pending → comment (no table:) → supported | `extract_domain_knowledge(id)` | Entry has `affects_columns=["population_stats", "gdp_data"]` |

Note: R3-AC10 (`source_ids=[]` → `affects_columns=[]`) is covered by test #14/#15 which
use the default `active_design` fixture (no source_ids, defaults to `[]`).

#### Class: `TestSaveExtractedKnowledge` (3 tests — new)

Note: These test `save_extracted_knowledge()` which persists entries. Fixture chain:
active_design → submit → comment → extract (preview) → **save** (persist).

| # | Test Name | AC | Input | Expected |
|---|-----------|-----|-------|----------|
| 23 (new numbering from design.md: included in 22 total) | `test_save_extracted_persists_to_yaml` | R3-AC4 | `save_extracted_knowledge(id, SAMPLE_ENTRIES)` | `extracted_knowledge.yaml` contains 2 entries under `source_id: "review"` |
| 24 | `test_save_extracted_duplicate_keys_skipped` | R3-AC5 | Save `SAMPLE_ENTRIES`, then save `[DUPLICATE_ENTRY]` | Only 2 entries in YAML (duplicate skipped) |
| 25 | `test_save_extracted_updates_comment_keys` | — | `save_extracted_knowledge(id, SAMPLE_ENTRIES)` | Corresponding `ReviewComment.extracted_knowledge` contains `["FP-H01-0", "FP-H01-1"]` |

**Note on test count**: 3 + 3 + 7 + 9 + 3 = 25 individual test rows, but design.md claims
22 tests for `test_reviews.py`. The save tests (3 tests) are included in the 22 count —
the extract class has 6 tests (not 9) when grouping Japanese keyword + scope tests. The
table above expands them individually for clarity.

### `test_rules.py` — 10 Tests

Tests RulesService with real YAML files. Requires pre-populated catalog and extracted
knowledge YAML files.

#### Class: `TestGetProjectContext` (5 tests)

| # | Test Name | AC | Setup | Expected |
|---|-----------|-----|-------|----------|
| 1 | `test_get_project_context_includes_catalog_sources` | — | Add `estat-pop` source via CatalogService | `sources` list contains `estat-pop` |
| 2 | `test_get_project_context_includes_catalog_knowledge` | — | Add source + write `CATALOG_KNOWLEDGE` | `knowledge_entries` includes catalog entries |
| 3 | `test_get_project_context_includes_extracted_knowledge` | — | Write entries to `extracted_knowledge.yaml` | `knowledge_entries` includes extracted entries |
| 4 | `test_get_project_context_handles_empty_gracefully` | — | Empty project (no sources, no knowledge) | Returns `{sources: [], knowledge_entries: [], rules: [], ...}` |
| 5 | `test_get_project_context_includes_rule_files` | — | Default init (review_rules.yaml, analysis_rules.yaml exist) | `rules` contains entries from rule files |

#### Class: `TestSuggestCautions` (5 tests)

| # | Test Name | AC | Setup | Expected |
|---|-----------|-----|-------|----------|
| 6 | `test_suggest_cautions_matches_catalog_affects_columns` | — | Add source + `CATALOG_KNOWLEDGE` + rebuild | `suggest_cautions(["population_stats"])` returns 1 caution |
| 7 | `test_suggest_cautions_matches_extracted_affects_columns` | — | Write `SAMPLE_ENTRIES` to extracted_knowledge.yaml | `suggest_cautions(["population_stats"])` returns entry |
| 8 | `test_suggest_cautions_mixed_sources` | — | Both catalog and extracted knowledge present | `suggest_cautions(["population_stats"])` returns entries from both sources |
| 9 | `test_suggest_cautions_no_matches_returns_empty` | — | Knowledge exists but for different tables | `suggest_cautions(["unknown_table"])` returns `[]` |
| 10 | `test_suggest_cautions_unscoped_not_returned` | — | Entry with `affects_columns=[]` | `suggest_cautions(["any_table"])` does NOT return unscoped entry |

### `test_server.py` (extended) — 14 Tests

Tests MCP tool layer with **mocked services**. Follows existing `test_server.py` patterns.

#### Mock Setup

```python
@pytest.fixture
def mock_review_service():
    """Mock ReviewService for server tool tests."""
    mock = Mock(spec=ReviewService)
    import insight_blueprint.server as server_module
    server_module._review_service = mock
    yield mock
    server_module._review_service = None

@pytest.fixture
def mock_rules_service():
    """Mock RulesService for server tool tests."""
    mock = Mock(spec=RulesService)
    import insight_blueprint.server as server_module
    server_module._rules_service = mock
    yield mock
    server_module._rules_service = None
```

| # | Test Name | AC | Mock Return | Expected |
|---|-----------|-----|-------------|----------|
| 1 | `test_submit_for_review_tool_success` | R4-AC1 | `AnalysisDesign(status=pending_review)` | `{design_id, status: "pending_review", message}` |
| 2 | `test_submit_for_review_tool_non_active_error` | R4-AC2 | Raises `ValueError` | `{error: "..."}` |
| 3 | `test_submit_for_review_tool_not_found` | — | Returns `None` | `{error: "Design 'X' not found"}` |
| 4 | `test_save_review_comment_tool_success` | R4-AC3 | `ReviewComment(status_after=supported)` | `{comment_id, design_id, status_after, message}` |
| 5 | `test_save_review_comment_tool_invalid_status` | R4-AC4 | Raises `ValueError` | `{error: "..."}` |
| 6 | `test_save_review_comment_tool_not_found` | — | Returns `None` | `{error: "Design 'X' not found"}` |
| 7 | `test_extract_domain_knowledge_tool_preview` | R4-AC5 | Returns `[DomainKnowledgeEntry(...)]` | `{design_id, entries: [...], count: 1, message}` |
| 8 | `test_save_extracted_knowledge_tool` | R4-AC6 | Returns `[DomainKnowledgeEntry(...)]` | `{design_id, saved_entries: [...], count, message}` |
| 9 | `test_save_extracted_knowledge_tool_invalid` | — | Raises `ValueError` | `{error: "..."}` |
| 10 | `test_get_project_context_tool` | R4-AC7 | Returns `{sources: [...], ...}` | Dict returned as-is |
| 11 | `test_suggest_cautions_tool_with_matches` | R4-AC8 | Returns `[{title, content, ...}]` | `{table_names, cautions: [...], count: 1}` |
| 12 | `test_suggest_cautions_tool_no_matches` | R4-AC9 | Returns `[]` | `{table_names, cautions: [], count: 0}` |
| 13 | `test_update_design_rejects_pending_review` | — | N/A | `{error: "Cannot set status to 'pending_review' directly..."}` |
| 14 | `test_review_service_not_initialized_raises` | — | `_review_service = None` | `RuntimeError` |

### `test_storage.py` (extended) — 2 Tests

| # | Test Name | AC | Setup | Expected |
|---|-----------|-----|-------|----------|
| 1 | `test_init_project_creates_extracted_knowledge_yaml` | R5-AC2 | `init_project(tmp_path)` | File exists at `.insight/rules/extracted_knowledge.yaml` with `{source_id: "review", entries: []}` |
| 2 | `test_init_project_does_not_overwrite_existing_extracted_knowledge` | — | Write custom entries → `init_project(tmp_path)` | Custom entries preserved |

### `test_integration.py` (extended) — 1 Test

Full round-trip test with real YAML files, covering the entire Extract-Preview-Confirm flow.

```python
def test_review_full_round_trip(tmp_project: Path) -> None:
    """Integration: submit → comment → extract → save → context → cautions."""
    # 1. Wire services
    design_service = DesignService(tmp_project)
    catalog_service = CatalogService(tmp_project)
    review_service = ReviewService(tmp_project, design_service)
    rules_service = RulesService(tmp_project, catalog_service)

    # 2. Create active design with source_ids
    design = design_service.create_design(
        title="Population Analysis",
        hypothesis_statement="...",
        hypothesis_background="...",
        theme_id="FP",
    )
    design_service.update_design(design.id, status="active", source_ids=["population_stats"])

    # 3. Submit for review
    submitted = review_service.submit_for_review(design.id)
    assert submitted.status == DesignStatus.pending_review

    # 4. Save review comment with caution
    comment = review_service.save_review_comment(
        design.id,
        "caution: 2015年以降の人口統計は調査方法が変更されている。",
        "supported",
    )
    assert comment is not None
    assert comment.status_after == DesignStatus.supported

    # 5. Extract knowledge (preview — NOT persisted)
    preview = review_service.extract_domain_knowledge(design.id)
    assert len(preview) >= 1
    assert preview[0].category == KnowledgeCategory.caution
    assert preview[0].affects_columns == ["population_stats"]  # from design.source_ids

    # 6. Save extracted knowledge (persist)
    saved = review_service.save_extracted_knowledge(design.id, preview)
    assert len(saved) >= 1

    # 7. Verify knowledge appears in project context
    context = rules_service.get_project_context()
    assert context["total_knowledge"] >= 1

    # 8. Verify caution is suggested for matching table
    cautions = rules_service.suggest_cautions(["population_stats"])
    assert len(cautions) >= 1

    # 9. Verify no caution for unrelated table
    unrelated = rules_service.suggest_cautions(["unrelated_table"])
    assert len(unrelated) == 0
```

**Covers**: R5-AC1 (services wired), R5-AC3 (full flow with preview-confirm)

## Edge Case Matrix

### Extract Domain Knowledge — Edge Cases

| Case | Input | Expected | Test |
|------|-------|----------|------|
| Empty comment text | `""` | No entries extracted | `test_extract_no_comments_returns_empty` |
| Whitespace-only lines | `"   \n  \n  "` | No entries extracted | Covered by empty filtering |
| Mixed English/Japanese prefixes | `"caution: ...\n注意: ..."` | 2 separate entries | `test_extract_japanese_keywords` |
| Unicode NFKC normalization | Full-width `"ｃａｕｔｉｏｎ："` | Normalized to `"caution:"` → matched | Implicit in keyword detection |
| Case insensitivity | `"CAUTION: ..."` | Matched as caution | Implicit in regex |
| Multiple `table:` annotations | `"table: A\ncaution: ...\ntable: B\ncaution: ..."` | First caution → A, second → B | `test_extract_table_annotation_sets_scope` |
| No `table:` + no `source_ids` | Default design, plain comment | `affects_columns=[]` | `test_extract_no_prefix_defaults_to_context` |

### Save Extracted Knowledge — Edge Cases

| Case | Input | Expected | Test |
|------|-------|----------|------|
| Duplicate keys | Save same key twice | Second save skipped | `test_save_extracted_duplicate_keys_skipped` |
| Empty entries list | `save_extracted_knowledge(id, [])` | No-op, returns `[]` | Implicit |
| Invalid entry (no key) | Entry missing `key` field | `ValueError` | Error scenario 7 |

### Status Transitions — Edge Cases

| Case | Input | Expected | Test |
|------|-------|----------|------|
| Submit draft | `submit_for_review` on draft design | `ValueError` | `test_submit_for_review_draft_raises_value_error` |
| Submit supported | `submit_for_review` on supported design | `ValueError` | Same test pattern |
| Comment on draft | `save_review_comment` on draft design | `ValueError` | `test_save_review_comment_on_draft_raises_value_error` |
| Set `pending_review` via generic update | `update_analysis_design(status="pending_review")` | `{error: "..."}` | `test_update_design_rejects_pending_review` |
| Re-review cycle | Submit → comment (active) → re-submit → comment (supported) | Both comments listed | `test_list_comments_returns_both_in_order` |

## Regression Strategy

SPEC-3 modifies shared modules (`models/design.py`, `server.py`, `storage/project.py`).
To ensure no regressions:

1. **Existing SPEC-1/SPEC-2 tests run as-is** — `DesignStatus` extension is additive
   (new enum value, no existing values changed)
2. **`init_project` is idempotent** — new `extracted_knowledge.yaml` creation uses
   `if not exists` guard, matching existing pattern
3. **`update_analysis_design` guard** — only adds a check for `pending_review`, does not
   change behavior for any existing status values
4. **`test_integration.py`** — existing `test_full_round_trip` and
   `test_catalog_full_round_trip` are preserved; new `test_review_full_round_trip` is added

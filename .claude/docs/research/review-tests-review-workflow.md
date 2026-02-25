# Test Coverage Review — SPEC-3 review-workflow

**Date**: 2026-02-26
**Reviewer**: Test Reviewer (Agent)

---

## Coverage Summary

| Module | Stmts | Miss | Cover | Missing Lines |
|--------|-------|------|-------|---------------|
| `core/reviews.py` | 116 | 5 | **96%** | 88-92, 170, 190 |
| `core/rules.py` | 55 | 1 | **98%** | 113 |
| `models/review.py` | 12 | 0 | **100%** | — |
| **TOTAL** | **183** | **6** | **97%** | — |

All 180 project tests pass (0 failures).

---

## Test Count Verification

### Expected (from tasks.md)

| Task | Expected | Actual | Status |
|------|----------|--------|--------|
| 1.1 DesignStatus + source_ids | 3 | 3 | Match |
| 1.2 ReviewComment model | 4 | 4 | Match |
| 2.1 ReviewService core | 13 | 13 (3+7+3) | Match |
| 2.2 Extract/Save knowledge | 9 | 11 (8+3) | **+2 extra** |
| 3.1 RulesService | 10 | 10 (5+5) | Match |
| 4.1 Server MCP tools | 14 | 15 | **+1 extra** |
| 4.2 Storage init | 2 | 2 | Match |
| 5.1 Integration | 1 | 1 | Match |
| **Total** | **56** | **59** | **+3 extra** |

**Discrepancy explanation**: The implementation includes 3 extra tests beyond spec:
- `test_extract_design_source_ids_default_scope` (Task 2.2 extra)
- `test_extract_no_scope_defaults_to_empty` (Task 2.2 extra)
- `test_save_review_comment_tool_success` area has extra tests in server (Task 4.1 extra, covering more edge cases of the review MCP tools area)

This is acceptable — all spec-required tests are present, plus additional coverage.

---

## Detailed Analysis Per Test File

### `tests/test_review_models.py` (7 tests)

**Quality**: Good
- Follows AAA pattern consistently
- Test naming convention followed
- All fields tested with proper assertions

**Coverage Gaps**: None — `models/review.py` at 100%

---

### `tests/test_reviews.py` (24 tests)

**Quality**: Good
- Well-structured test classes (Submit, Comment, List, Extract, Save)
- Fixtures in conftest.py are clean and composable
- Tests are independent (each uses fresh fixtures)
- Error cases well covered (ValueError for invalid state transitions)

**Covered scenarios**:
- Happy paths: submit active -> pending_review, all 4 post-review statuses
- Error cases: submit draft, comment on draft, pending_review as post-review status, missing design
- Extraction: all 4 categories (caution, definition, context, methodology implied), table annotation, source_ids scoping, no-scope default
- Save: persistence, duplicate detection, comment back-link

**Coverage Gaps** (lines not covered in reviews.py):

| Lines | Code | Priority | What's Missing |
|-------|------|----------|----------------|
| 88-92 | `except ValueError` in `save_review_comment` — handling completely invalid status string that's not a valid `DesignStatus` value | **Low** | Test with `status="totally_invalid"` (not a DesignStatus at all). Currently only tested with `pending_review` which IS a valid DesignStatus but not a valid post-review status. The MCP layer (server.py) test `test_save_review_comment_tool_invalid_status` passes `pending_review` which hits line 96-100 instead. |
| 170 | `continue` for empty lines in extract | **Low** | No test sends a comment with blank lines (e.g., `"line1\n\nline2"`). This is a minor edge case — the logic is trivial (skip empty lines). |
| 190 | `continue` for empty content after prefix strip | **Low** | No test sends `"caution: "` (prefix only, no content). Trivial guard. |

---

### `tests/test_rules.py` (10 tests)

**Quality**: Good
- Helper functions (`_write_catalog_knowledge`, `_write_extracted_knowledge`) keep tests clean
- Both data sources (catalog + extracted) tested independently and mixed
- Negative cases covered (no match, unscoped excluded)

**Coverage Gap** (1 uncovered line in rules.py):

| Line | Code | Priority | What's Missing |
|------|------|----------|----------------|
| 113 | `return []` in `_read_extracted_knowledge` when data has no `entries` key | **Low** | The test for empty project (`test_get_project_context_empty_project`) uses `init_project` which creates `extracted_knowledge.yaml` with `entries: []` — so this branch (file exists but no `entries` key) is never triggered. Very defensive code, low risk. |

---

### `tests/test_server.py` — SPEC-3 portion (15 tests)

**Quality**: Good
- Follows existing server test patterns (asyncio.run, initialized_server fixtures)
- Guard function tests present (get_review_service, get_rules_service)
- Error dict pattern consistently tested
- Helper `_create_active_design()` keeps tests DRY

**Coverage Gaps**:

| Priority | What's Missing | Why It Matters |
|----------|---------------|----------------|
| **Medium** | `test_get_rules_service_raises_when_not_initialized` — no test for the `get_rules_service()` guard | Pattern inconsistency: `get_service`, `get_catalog_service`, and `get_review_service` all have guard tests, but `get_rules_service` does not. Lines 63-65 in server.py are uncovered by tests. |
| **Low** | `test_list_review_comments_tool` — no MCP tool test for `list_comments` | There is no `list_review_comments` MCP tool exposed in server.py, so this is actually not a gap in test coverage but rather a missing feature. The `list_comments` functionality exists in `ReviewService` and is tested there. |
| **Low** | `test_extract_domain_knowledge_tool_not_found` — no test for extracting from nonexistent design | Returns empty list (not an error), so risk is minimal. |

---

### `tests/test_storage.py` — SPEC-3 portion (2 tests)

**Quality**: Good
- `test_init_project_creates_extracted_knowledge_yaml` — verifies structure
- `test_init_project_does_not_overwrite_existing_extracted_knowledge` — idempotency check
- Both match tasks.md expectations exactly

**Coverage Gaps**: None for SPEC-3 scope.

---

### `tests/test_integration.py` — SPEC-3 portion (1 test)

**Quality**: Excellent
- `test_review_full_round_trip` covers the complete flow:
  init -> create -> active -> submit -> comment -> extract (preview verify) -> save (persist verify) -> context -> cautions (match + no-match)
- Uses real YAML files (no mocks)
- Verifies intermediate states (e.g., entries NOT persisted after extract, ARE persisted after save)
- Existing integration tests (`test_full_round_trip`, `test_catalog_full_round_trip`) still pass

**Coverage Gaps**: None.

---

### `tests/conftest.py` — SPEC-3 additions

**Quality**: Good
- `design_service`, `review_service`, `active_design`, `pending_design` fixtures are composable
- Fixtures are properly scoped (function-level)
- `tmp_project` uses `init_project` for realistic setup

---

## Findings Summary

### High Priority
None.

### Medium Priority

1. **Missing `get_rules_service` guard test** (`test_server.py`)
   - File: `tests/test_server.py`
   - What's needed: `test_get_rules_service_raises_when_not_initialized`
   - Why: Pattern consistency — all other service guards have tests. Lines 63-65 of server.py are uncovered.

### Low Priority

2. **Invalid DesignStatus string in `save_review_comment`** (`test_reviews.py`)
   - Lines 88-92 of `reviews.py` uncovered
   - What's needed: `test_save_review_comment_invalid_status_string_raises_value_error` with `status="totally_invalid"`
   - Why: Different code path from existing `pending_review` test (ValueError from DesignStatus constructor vs. VALID_REVIEW_TRANSITIONS check)

3. **Empty lines in extraction** (`test_reviews.py`)
   - Line 170 of `reviews.py` uncovered
   - What's needed: Test with multi-line comment containing blank lines
   - Why: Trivial guard, but verifying empty line skipping is good practice

4. **Prefix-only extraction line** (`test_reviews.py`)
   - Line 190 of `reviews.py` uncovered
   - What's needed: Test with `"caution: "` (prefix with no content)
   - Why: Trivial guard

5. **Missing `entries` key in extracted_knowledge.yaml** (`test_rules.py`)
   - Line 113 of `rules.py` uncovered
   - What's needed: Test with malformed `extracted_knowledge.yaml` (no `entries` key)
   - Why: Defensive code, unlikely in production

---

## Overall Assessment

**Coverage**: 97% on core SPEC-3 modules — exceeds the 80% target.

**Test Count**: 59 new SPEC-3 tests (56 expected + 3 extra) — all spec requirements met.

**Test Quality**: Tests follow AAA pattern, use proper fixtures, are independent, and cover happy paths, error cases, and boundary values. Naming conventions are followed.

**Verdict**: Test coverage is strong. The 1 medium-priority finding (missing `get_rules_service` guard test) should be addressed for consistency. The 4 low-priority findings are optional improvements.

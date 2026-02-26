# Test Coverage and Quality Review Report

**Date**: 2026-02-26
**Scope**: SPEC-1 (core-foundation), SPEC-2 (data-catalog), SPEC-3 (review-workflow)
**Branch**: feat/spec-start-pipeline

## Overall Summary

| Metric | Value |
|--------|-------|
| Total tests | 183 |
| Passing | 183 (100%) |
| Failing | 0 |
| Overall coverage | **93%** (862 stmts, 57 missed) |
| Execution time | 1.80s |
| Coverage target (per .claude/rules/testing.md) | 80% |

**Verdict**: Coverage target exceeded. All tests pass. Quality is high overall.

---

## Per-File Coverage Analysis

| File | Stmts | Miss | Cover | Missing Lines |
|------|-------|------|-------|---------------|
| `__init__.py` | 1 | 0 | 100% | - |
| `__main__.py` | 3 | 3 | **0%** | 3-6 |
| `cli.py` | 26 | 0 | 100% | - |
| `core/catalog.py` | 104 | 9 | 91% | 64-65, 80, 86, 145-146, 177, 206, 209 |
| `core/designs.py` | 60 | 5 | 92% | 90, 98, 108, 120-121 |
| `core/reviews.py` | 123 | 5 | 96% | 88-92, 170, 190 |
| `core/rules.py` | 55 | 1 | 98% | 113 |
| `models/__init__.py` | 4 | 0 | 100% | - |
| `models/catalog.py` | 48 | 0 | 100% | - |
| `models/common.py` | 5 | 0 | 100% | - |
| `models/design.py` | 26 | 0 | 100% | - |
| `models/review.py` | 12 | 0 | 100% | - |
| `server.py` | 214 | 25 | 88% | 139, 185, 203-206, 284, 286, 289-293, 295, 333-334, 338, 388, 418, 444, 448-449, 475, 485-486 |
| `storage/project.py` | 61 | 6 | 90% | 102-107 |
| `storage/sqlite_store.py` | 91 | 1 | 99% | 123 |
| `storage/yaml_store.py` | 29 | 2 | 93% | 39-40 |

---

## Coverage Gap Analysis

### Priority: High

#### 1. `server.py` (88% - 25 lines uncovered)

The server MCP tool layer is the primary entry point for all operations. Missing coverage includes:

**Missing lines 203-206**: `list_analysis_designs` with invalid status filter
- **Test needed**: `test_list_analysis_designs_invalid_status_returns_error`
- Calls `list_analysis_designs(status="invalid_xyz")` and asserts `"error"` in result
- **Coverage impact**: +2 lines

**Missing lines 284, 286, 289-293, 295**: `update_catalog_entry` when `columns` is provided and when `tags` is provided
- **Test needed**: `test_update_catalog_entry_with_columns_updates_schema_info`
- **Test needed**: `test_update_catalog_entry_with_tags_updates_tags`
- Currently only `name` field update is tested. Need to test `description`, `connection`, `columns`, and `tags` field updates
- **Coverage impact**: +8 lines

**Missing lines 333-334, 338**: `search_catalog` with invalid source_type and tags filter
- **Test needed**: `test_search_catalog_invalid_source_type_returns_error`
- **Test needed**: `test_search_catalog_with_tags_filter`
- **Coverage impact**: +3 lines

**Missing line 139**: `update_analysis_design` design_id validation path
- **Test needed**: `test_update_analysis_design_rejects_invalid_design_id` (path traversal)
- **Coverage impact**: +1 line

**Missing line 185**: `get_analysis_design` design_id validation path
- Already tested via `test_invalid_design_id_rejected` for `get_analysis_design`, but the validation on `update_analysis_design` line 139 may not be triggered
- Need to verify this

**Missing lines 388, 418, 444, 448-449, 475, 485-486**: Design ID validation in review tool functions
- `submit_for_review`, `save_review_comment`, `extract_domain_knowledge`, `save_extracted_knowledge` all call `_validate_design_id`
- **Test needed**: Tests with invalid design IDs (path traversal) for each review tool
- **Coverage impact**: +7 lines

**Total estimated improvement**: +21 lines (~10% of server.py's missed lines)

#### 2. `core/reviews.py` (96% - 5 lines uncovered)

**Missing lines 88-92**: `save_review_comment` ValueError branch when `DesignStatus(status)` raises
- This is the branch where an entirely unknown status string (not a valid DesignStatus value) is passed
- Currently tested indirectly (`pending_review` is a valid DesignStatus but invalid post-review), but the `except ValueError` on line 88 is only hit when a completely invalid status string is used (e.g., `"garbage"`)
- **Test needed**: `test_save_review_comment_invalid_status_string_raises_value_error`
  - Call `review_service.save_review_comment(design_id, "comment", "totally_invalid_status")`
- **Coverage impact**: +5 lines

**Missing line 170**: Empty content after stripping category prefix
- This is the guard `if not content: continue` on line 189-190 of `extract_domain_knowledge`
- **Test needed**: `test_extract_empty_content_after_prefix_skipped`
  - Comment like `"caution: "` (prefix with no actual content after it)
- **Coverage impact**: +1 line

**Missing line 190**: Same as above (the continue branch)

#### 3. `__main__.py` (0% - 3 lines uncovered)

This is the `python -m insight_blueprint` entry point. Only 3 lines.
- **Priority**: Low (standard Python entry point pattern, rarely tested directly)
- **Test needed**: Could test via subprocess or by importing and mocking
- **Coverage impact**: +3 lines (but minimal value)

### Priority: Medium

#### 4. `core/catalog.py` (91% - 9 lines uncovered)

**Missing lines 64-65**: `add_source` FTS5 insert exception handling (logger.warning)
- The `except Exception` block when FTS5 insert fails during add_source
- **Test needed**: `test_add_source_fts5_failure_does_not_crash`
  - Mock `insert_document` to raise, verify source is still added successfully
- **Coverage impact**: +2 lines

**Missing line 80**: `list_sources` when `_sources_dir` doesn't exist
- **Test needed**: `test_list_sources_when_sources_dir_missing_returns_empty`
- **Coverage impact**: +1 line

**Missing line 86**: `list_sources` when a YAML file is empty/corrupt
- **Test needed**: `test_list_sources_skips_empty_yaml_files`
- **Coverage impact**: +1 line

**Missing lines 145-146**: `update_source` FTS5 re-index exception handling
- **Test needed**: `test_update_source_fts5_failure_does_not_crash`
  - Mock `replace_source_documents` to raise, verify source is still updated
- **Coverage impact**: +2 lines

**Missing line 177**: `search` filter path when source is None (knowledge-only entry)
- **Test needed**: `test_search_with_filter_skips_knowledge_only_entries`
- **Coverage impact**: +1 line

**Missing lines 206, 209**: `rebuild_index` when knowledge files exist with entries
- Already partially covered by integration tests, but the specific lines for iterating knowledge entries in `rebuild_index` may need direct test
- **Coverage impact**: +2 lines

#### 5. `core/designs.py` (92% - 5 lines uncovered)

**Missing line 90**: `list_designs` when `_designs_dir` doesn't exist
- **Test needed**: `test_list_designs_when_designs_dir_missing_returns_empty`
- **Coverage impact**: +1 line

**Missing line 98**: `list_designs` when YAML file is empty/corrupt (skip branch)
- **Test needed**: `test_list_designs_skips_corrupt_yaml`
- **Coverage impact**: +1 line

**Missing line 108**: `_next_id_number` when `_designs_dir` doesn't exist
- **Test needed**: `test_next_id_number_when_designs_dir_missing_returns_1`
- **Coverage impact**: +1 line

**Missing lines 120-121**: `_next_id_number` ValueError/IndexError exception handling
- **Test needed**: `test_next_id_number_ignores_malformed_filenames`
  - Create a file with malformed name like `FP-Habc_hypothesis.yaml`
- **Coverage impact**: +2 lines

#### 6. `storage/project.py` (90% - 6 lines uncovered)

**Missing lines 102-107**: `_register_mcp_server` exception handling in atomic write
- The `except Exception` block and the nested `try/except OSError` for cleanup
- **Test needed**: `test_register_mcp_server_atomic_write_failure_cleans_up`
  - Mock `os.replace` to raise, verify temp file is cleaned up
- **Coverage impact**: +6 lines

#### 7. `storage/yaml_store.py` (93% - 2 lines uncovered)

**Missing lines 39-40**: `write_yaml` exception handling (temp file cleanup)
- The `os.unlink(tmp_path)` in the `except OSError: pass` block
- Already tested indirectly by `test_write_yaml_is_atomic`, but the inner `except OSError: pass` on line 39-40 is only hit if `os.unlink` itself fails
- **Test needed**: `test_write_yaml_cleanup_failure_still_raises_original`
  - Mock both `os.replace` and `os.unlink` to raise
- **Coverage impact**: +2 lines

#### 8. `core/rules.py` (98% - 1 line uncovered)

**Missing line 113**: `_read_extracted_knowledge` when data is empty
- The `return []` branch when `not data or "entries" not in data`
- **Test needed**: `test_read_extracted_knowledge_with_malformed_yaml_returns_empty`
- **Coverage impact**: +1 line

### Priority: Low

#### 9. `storage/sqlite_store.py` (99% - 1 line uncovered)

**Missing line 123**: `search_index` empty/whitespace query guard
- The `if not query or not query.strip(): return []` branch
- **Test needed**: `test_search_index_empty_query_returns_empty`
  - Call `search_index(db_path, "")` and `search_index(db_path, "   ")`
- **Coverage impact**: +1 line

---

## Test Quality Assessment

### 1. Happy Paths -- GOOD

All primary use cases are well-tested:
- Design CRUD (create, get, list, update) with theme_id support
- Catalog CRUD (add, get, list, update, search, knowledge)
- Review workflow (submit, comment, extract, save)
- Rules (project context, suggest cautions)
- Server MCP tools (all tools have at least basic coverage)
- Integration round-trips (3 comprehensive end-to-end tests)

### 2. Error Cases -- GOOD

Well-covered error handling:
- Missing designs/sources return None
- Invalid theme_id raises ValueError
- Invalid status transitions raise ValueError
- Duplicate source IDs raise ValueError
- Design ID validation (path traversal prevention)
- Service not initialized raises RuntimeError

**Gap**: Some server.py error paths are not tested (invalid status in list_analysis_designs, invalid source_type in search_catalog).

### 3. Boundary Values -- ADEQUATE

Covered:
- Empty lists (no designs, no sources, no comments, no knowledge)
- None values (missing entries return None)
- Empty project context
- FTS5 missing database

**Gap**: No tests for very long strings, special characters in IDs, or Unicode edge cases in design titles/comments beyond the NFKC normalization in extract_domain_knowledge.

### 4. Edge Cases -- MODERATE

Covered:
- Knowledge-only FTS5 entries
- Duplicate key deduplication in save_extracted_knowledge
- Re-submit for review after changes requested
- Correct key assignment to originating comment (regression test)
- FTS5 unavailable (mock test)
- Connection cleanup on errors (6 tests)
- Rollback on transaction failure

**Gap**:
- No concurrent access tests (e.g., parallel writes to same YAML file)
- No test for search with SQL injection-like queries (FTS5 sanitization)
- No test for extremely large datasets

### 5. AAA Pattern -- EXCELLENT

All tests follow the Arrange/Act/Assert pattern clearly. Even complex tests like `test_save_extracted_assigns_keys_to_correct_comment` have clear setup, action, and verification phases.

### 6. Independence -- EXCELLENT

- Each test uses `tmp_path` or `tmp_project` fixtures for isolation
- Server module state is properly reset via `autouse` fixtures (`_reset_service`, `_reset_catalog_service`, `_reset_review_service`, `_reset_rules_service`)
- No shared state between tests

### 7. Mocking -- GOOD

- External sqlite3 module mocked for FTS5 unavailable scenario
- `os.replace` mocked for atomic write testing
- `_open_connection` mocked for connection cleanup tests
- `mcp.run` mocked in CLI tests

**Note**: One minor concern -- `_reset_service` fixture pattern accesses private module attributes directly. This is pragmatic but fragile. Acceptable for test code.

### 8. Naming Convention -- MOSTLY COMPLIANT

Most tests follow `test_{target}_{condition}_{expected_result}` pattern.
Good examples:
- `test_add_source_duplicate_id_raises_value_error`
- `test_get_source_returns_none_for_missing_id`
- `test_search_index_handles_missing_db_gracefully`

Minor deviations (acceptable):
- Some class-organized tests like `TestSubmitForReview::test_submit_for_review_active_design` -- descriptive enough
- `test_full_round_trip` -- integration test, naming is clear

### 9. Execution Speed -- EXCELLENT

Total: 1.80s for 183 tests = ~9.8ms per test (well under the 100ms target).

---

## Specific Recommendations

### Must-Fix (High Priority)

1. **Add invalid status tests for server.py `list_analysis_designs`**
   - Missing a basic error case for the most common MCP tool

2. **Add `update_catalog_entry` field-specific tests**
   - Currently only `name` update is tested; `description`, `connection`, `columns`, `tags` paths uncovered

3. **Add design_id validation tests for review MCP tools**
   - `submit_for_review`, `save_review_comment`, `extract_domain_knowledge`, `save_extracted_knowledge` all have uncovered validation paths

4. **Add `save_review_comment` with completely invalid status string**
   - The `except ValueError` on line 88 of `reviews.py` is never triggered by current tests

### Should-Fix (Medium Priority)

5. **Add FTS5 failure resilience tests for catalog**
   - Mock `insert_document` / `replace_source_documents` to raise and verify graceful degradation

6. **Add corrupt/empty YAML file handling tests**
   - For both `list_designs` and `list_sources`

7. **Add `_register_mcp_server` atomic write failure test**
   - Verify temp file cleanup on failure

8. **Add malformed filename test for `_next_id_number`**
   - Verify ValueError/IndexError exception handling

### Nice-to-Have (Low Priority)

9. **Remove `test_placeholder.py`**
   - No longer needed with 183 real tests

10. **Add search query sanitization test**
    - Verify FTS5 query injection is properly handled

11. **Add `__main__.py` coverage** (optional)
    - Standard entry point, low risk

---

## Coverage Improvement Estimate

If all "Must-Fix" and "Should-Fix" recommendations are implemented:

| Category | New Tests | Lines Covered | Estimated New Coverage |
|----------|-----------|---------------|----------------------|
| Must-Fix | ~8 tests | ~35 lines | 93% -> 96% |
| Should-Fix | ~6 tests | ~15 lines | 96% -> 97% |
| Nice-to-Have | ~3 tests | ~7 lines | 97% -> 98% |

Current: **93%** (57 lines missed out of 862)
After Must-Fix: **~96%** (22 lines missed)
After All: **~98%** (7 lines missed)

---

## Test Architecture Notes

### Strengths
- Clean fixture hierarchy in `conftest.py` (tmp_project -> design_service -> review_service -> active_design -> pending_design)
- Integration tests provide end-to-end confidence
- Connection cleanup tests are thorough (6 tests covering all sqlite operations)
- Regression test for key-to-comment assignment bug is excellent

### Observations
- The `asyncio.run()` pattern in `test_server.py` is functional but could be simplified with `pytest-asyncio` if async testing grows
- The `autouse` fixture pattern for resetting server module state works well but creates hidden coupling -- documented clearly enough via docstrings

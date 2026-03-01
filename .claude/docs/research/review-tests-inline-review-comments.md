# Test Coverage Review: Inline Review Comments

## Summary

**Overall coverage: 82% across all tested modules (257 tests, all passing)**

The inline review comments feature has comprehensive test coverage that closely follows the test-design.md spec. All priority levels (P1-P9) are implemented, and the tests cover happy paths, error cases, boundary values, and edge cases effectively.

### Coverage by File

| File | Coverage | Missing Lines |
|------|----------|---------------|
| `models/review.py` | **100%** | None |
| `core/reviews.py` | **93%** | Lines 104-108, 168-172, 254, 259-260, 264-266, 310, 330 |
| `server.py` | **88%** | Lines 96, 142, 160-163, 245-256, 296-297, 301, 353, 383, 416, 423, 440, 444-445, 471, 481-482 |
| `web.py` | **91%** | Lines 383, 601-647 |

---

## Detailed Analysis

### 1. Model Tests (`tests/test_review_models.py`)

**Coverage: 100% for `models/review.py`**

**Strengths:**
- All `BatchComment` validators thoroughly tested (12 test cases)
- `ReviewBatch` model fully covered (8 test cases)
- Boundary values: 2000-char (pass) and 2001-char (fail) comment length
- Edge cases: whitespace-only comments, empty string target_section, extra fields
- JSON round-trip verified including `target_content` with dict values
- `JsonValue` type alias properly tested with parametrized non-JSON rejection
- AAA pattern consistently followed

**Gaps: None identified.** Model layer is fully covered.

### 2. Service Tests (`tests/test_reviews.py`)

**Coverage: 93% for `core/reviews.py`**

**Strengths:**
- `save_review_batch`: 16 test cases covering all spec requirements (FR-8, FR-12, FR-14, NFR-8)
- Target section validation: All 6 valid sections parametrized + invalid section rejection
- `list_review_batches`: 8 test cases including corrupted YAML, missing key, empty, and ordering
- Atomicity: Both YAML-write-failure and status-update-failure scenarios tested (NFR-8)
- Contract test: Backend `ALLOWED_TARGET_SECTIONS` vs frontend `COMMENTABLE_SECTIONS` sync verified
- Path traversal / ID validation: Comprehensive parametrized tests (6 bad IDs x 5 methods = 30 tests)
- Fixture composition is clean and follows existing project patterns

**Gaps:**

| Gap | Lines | Priority | Description |
|-----|-------|----------|-------------|
| `save_review_comment` with completely invalid status string | 104-108 | **Low** | The `except ValueError` branch for `DesignStatus(status)` in `save_review_comment()` is never triggered because tests use "pending_review" (a valid enum value but invalid post-review status). Tests should add a case like `status="totally_bogus"` to hit line 104-108. |
| `save_review_batch` with completely invalid status string | 168-172 | **Low** | Same pattern as above for `save_review_batch()`. The `except ValueError` branch for `DesignStatus(status)` is not directly tested. Current tests use "pending_review" which is valid enum but invalid transition. Need a test with `status="totally_bogus"`. |
| `list_review_batches` with non-list batches key | 258-260 | **Low** | The branch where `batches` key exists but is not a list (e.g., `batches: "string_value"`) is not covered. |
| `list_review_batches` with unparseable batch entries | 264-266 | **Low** | The `except Exception` branch for `ReviewBatch(**b)` parse failure. The corrupted YAML test only covers read-failure, not cases where YAML is valid but batch data doesn't match the model schema. |
| `list_review_batches` with "no batches key" (non-comments) | 254 | **Low** | The else branch of the `if "comments" in data` check. Test `test_list_batches_no_batches_key` uses `{"comments": [...]}` which hits the if-branch. Need a YAML with neither `batches` nor `comments` key to hit line 254. |
| `extract_domain_knowledge` empty line handling | 310 | **Low** | Empty lines in multiline comments are skipped but this exact branch is not tested. Tests use single-line comments. |
| `extract_domain_knowledge` empty content after prefix strip | 330 | **Low** | A comment like `"caution: "` (prefix with no content) would produce empty `content` and skip. Not tested. |

### 3. MCP Server Tests (`tests/test_server.py`)

**Coverage: 88% for `server.py`**

**Strengths:**
- `save_review_batch` MCP tool: 3 test cases (success, with sections, non-pending error)
- All existing MCP tools continue to work (submit, comment, extract, save knowledge)
- Service initialization guards tested

**Gaps:**

| Gap | Priority | Description |
|-----|----------|-------------|
| `save_review_batch` tool not-found case | **Medium** | Missing test for when `save_review_batch` is called with a valid but nonexistent design_id (should return `{"error": "... not found"}`). Line 422-423 in server.py. |
| `save_review_batch` tool validation error | **Medium** | Missing test for Pydantic ValidationError propagation through the MCP tool (e.g., comment too long, extra fields). Line 420-421. |
| `list_review_batches` MCP tool | **Medium** | No MCP tool for `list_review_batches` exists in `server.py`, but it's also not in the spec (FR-18 only covers `save_review_batch`). No gap per spec. |
| Various uncovered lines in non-review tools | **Low** | Lines 96, 142, 160-163, etc. are in existing (non-review) tool functions. Pre-existing gap, not related to this feature. |

### 4. REST API Tests (`tests/test_web.py`)

**Coverage: 91% for `web.py` (review-batch related: effectively 100%)**

**Strengths:**
- `TestReviewBatchAPI`: 14 test cases covering all spec requirements
- POST validation: empty comments (422), overlength comment (422), invalid section (422), extra fields (422), missing target_content (422)
- Status transitions: All 4 statuses parametrized
- GET ordering: Descending by created_at verified
- `target_content` round-trip: POST then GET verifies data preservation
- Error format: 400 for non-pending, 404 for nonexistent design

**Gaps:**

| Gap | Priority | Description |
|-----|----------|-------------|
| `web.py` lines 601-647 uncovered | **None** | These are `start_server()` / `ThreadedUvicorn` which is server lifecycle code, not testable via TestClient. Expected and acceptable. |
| `web.py` line 383 uncovered | **Low** | The inner loop of `get_knowledge_list()` that appends knowledge entries. This is hit only when a source actually has knowledge entries. Pre-existing gap, not related to this feature. |
| Invalid `status_after` in request body | **Low** | Currently the SubmitBatchRequest model accepts any string for `status_after`. An invalid value like `"bogus"` would propagate to the service layer as ValueError (caught by `value_error_handler`). A test proving the 400 response for this case would be beneficial. |

### 5. E2E Tests (`frontend/e2e/design-detail.spec.ts`)

**Coverage: All test-design.md E2E scenarios implemented**

**Strengths:**
- **Tab Restructuring (P7)**: 3 tests verifying Overview/History/Knowledge tabs, Review tab removal, and inline comments on Overview
- **Inline Review Comments (P8)**: 12 tests covering the full comment lifecycle
  - Comment button visibility (pending vs non-pending)
  - Inline form opening
  - Draft management (add, delete, count updates)
  - Status selector (all 4 options)
  - Submit All (batch POST verification, target_content snapshot, request body validation)
  - Failure handling (drafts preserved on 500)
  - Loading state (button disabled during submission)
  - Visual distinction (border-dashed class, "draft" label)
  - Sticky submit bar (inViewport check)
- **Review History (P9)**: 4 tests covering batch display, section labels, target_content display, timestamp ordering
- Mock data factories: `makeBatchComment()`, `makeReviewBatch()` with sensible defaults
- API route helpers: `mockReviewBatches()`, `mockReviewBatchesError()` properly handle GET/POST

**Gaps:**

| Gap | Priority | Description |
|-----|----------|-------------|
| Editing a draft comment | **Low** | No test for modifying an existing draft's text before submission. The UI may or may not support this; test-design.md doesn't require it. |
| Multiple batches in History after submission | **Low** | No test where a user submits a batch and then navigates to History to see it alongside previously submitted batches. The History tests use pre-mocked data. |
| Error message display on submission failure | **Low** | `test_drafts_preserved_on_submission_failure` verifies drafts are kept but doesn't check for a user-visible error message/toast. |

### 6. Fixtures and Test Infrastructure (`tests/conftest.py`)

**Strengths:**
- Clean fixture composition: `pending_design` depends on `active_design` + `review_service` + `design_service`
- Dedicated fixtures for inline review comments: `review_batch_data`, `non_pending_design`, `corrupted_reviews_yaml`
- `status_update_failure` fixture for atomicity testing
- `fixed_now` fixture patches both `common` and `review` modules
- Factory function `make_batch_payload()` available for test data construction

**Gaps:**

| Gap | Priority | Description |
|-----|----------|-------------|
| `make_batch_payload()` unused | **Low** | Defined in `conftest.py` but not used by any test. Could be removed or leveraged in future tests. |
| `fixed_now` fixture unused | **Low** | Defined but not referenced by any test in the current suite. |

---

## Requirements Traceability Verification

Cross-referencing test-design.md requirements traceability table against actual implementation:

| Requirement | Specified Test | Implemented? | Notes |
|-------------|---------------|--------------|-------|
| FR-1 | E2E: comment buttons visible on pending_review | YES | |
| FR-2 | E2E: comment buttons hidden on non-pending_review | YES | |
| FR-3 | E2E: clicking comment button opens inline form | YES | |
| FR-4 | test_save_batch_preserves_target_section | YES | |
| FR-5 | E2E: adding draft shows Review Submit Bar | YES | |
| FR-6 | E2E: Submit Bar shows draft count | YES | |
| FR-7 | E2E: status selector + parametrized tests | YES | |
| FR-8 | test_save_batch_transitions_design_status | YES | |
| FR-9 | E2E: Submit All sends batch and refreshes design | YES | |
| FR-10 | TestReviewBatch (all) | YES | |
| FR-11 | TestBatchComment + target_content tests | YES | |
| FR-12 | TestReviewBatchAPI.test_submit_batch_success | YES | |
| FR-13 | TestListReviewBatches + TestReviewBatchAPI list tests | YES | |
| FR-14 | test_save_batch_persists_to_yaml | YES | |
| FR-15 | E2E: tabs show Overview, History, Knowledge | YES | |
| FR-16 | E2E: inline comments without tab switch | YES | |
| FR-17 | E2E: History tab (3 tests) | YES | |
| FR-18 | TestSaveReviewBatchTool (3 tests) | YES | |
| NFR-7 | TestSaveReviewBatchTargetSectionValidation + contract test | YES | |
| NFR-8 | YAML write failure + status update failure tests | YES | |
| NFR-10 | E2E: draft visually distinct | YES | |
| NFR-11 | E2E: Submit Bar sticky | YES | |
| NFR-12 | E2E: removing all drafts | YES | |

**All testable requirements have corresponding tests.** Non-testable NFRs (NFR-1 through NFR-6, NFR-9) are correctly excluded per the test-design.md rationale.

---

## Recommended Actions

### High Priority

None. All critical paths are covered.

### Medium Priority

1. **Add MCP tool not-found test** (`tests/test_server.py`):
   ```python
   def test_save_review_batch_tool_not_found(self, initialized_review_server):
       result = asyncio.run(server_module.save_review_batch(
           design_id="NONEXIST-H99",
           status_after="supported",
           comments=[{"comment": "Ghost"}],
       ))
       assert "error" in result
       assert "not found" in result["error"]
   ```

2. **Add MCP tool validation error test** (`tests/test_server.py`):
   ```python
   def test_save_review_batch_tool_validation_error(self, initialized_review_server):
       design_id = _create_pending_design_mcp()
       result = asyncio.run(server_module.save_review_batch(
           design_id=design_id,
           status_after="supported",
           comments=[{"comment": "a" * 2001}],
       ))
       assert "error" in result
   ```

### Low Priority

3. **Add test for completely invalid status string** in `save_review_comment()`:
   ```python
   def test_save_review_comment_totally_invalid_status(self, review_service, pending_design):
       with pytest.raises(ValueError, match="Invalid post-review"):
           review_service.save_review_comment(pending_design.id, "comment", "totally_bogus")
   ```

4. **Add test for completely invalid status string** in `save_review_batch()`:
   ```python
   def test_save_batch_rejects_totally_invalid_status(self, review_service, pending_design):
       with pytest.raises(ValueError, match="Invalid"):
           review_service.save_review_batch(pending_design.id, "totally_bogus", [{"comment": "Bad"}])
   ```

5. **Add test for non-list batches key** in `list_review_batches()`:
   ```python
   def test_list_batches_non_list_batches_key(self, review_service, pending_design, tmp_path):
       reviews_path = tmp_path / ".insight" / "designs" / f"{pending_design.id}_reviews.yaml"
       write_yaml(reviews_path, {"batches": "not_a_list"})
       batches = review_service.list_review_batches(pending_design.id)
       assert batches == []
   ```

6. **Add test for YAML with neither batches nor comments key**:
   ```python
   def test_list_batches_yaml_no_relevant_keys(self, review_service, pending_design, tmp_path):
       reviews_path = tmp_path / ".insight" / "designs" / f"{pending_design.id}_reviews.yaml"
       write_yaml(reviews_path, {"unrelated": "data"})
       batches = review_service.list_review_batches(pending_design.id)
       assert batches == []
   ```

7. **Clean up unused fixtures**: Remove or mark `make_batch_payload()` and `fixed_now` if not needed.

---

## Test Quality Assessment

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Happy path coverage | Excellent | All CRUD operations tested |
| Error case coverage | Excellent | Invalid status, missing fields, non-pending, extra fields |
| Boundary values | Excellent | 2000/2001 char comments, empty list, min_length=1 |
| Edge cases | Good | Path traversal, corrupted YAML, atomicity failure |
| AAA pattern | Excellent | Consistently followed across all test files |
| Mocking quality | Excellent | External deps properly mocked; monkeypatch for failure injection |
| Test independence | Excellent | Each test uses fresh tmp_path; registry reset in fixtures |
| E2E user flow | Excellent | Full add-draft -> submit -> verify cycle tested |
| Spec traceability | Excellent | All FR/NFR mapped to tests in test-design.md |

**Overall Grade: A**

The test suite is well-structured, comprehensive, and closely follows the test-design.md specification. The few identified gaps are all low-priority edge cases in defensive code branches.

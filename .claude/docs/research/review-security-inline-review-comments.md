# Security Review: Inline Review Comments Feature

**Date**: 2026-03-01
**Scope**: All changed files for the inline-review-comments feature
**Reviewer**: Claude Opus 4.6 (automated security review)

---

## Executive Summary

The inline review comments feature has a **generally solid security posture**.
Key strengths include consistent ID validation against path traversal, no use of
`dangerouslySetInnerHTML`, and proper error message sanitization. However, several
findings of Medium and Low severity were identified.

**Critical: 0 | High: 0 | Medium: 3 | Low: 4**

---

## Findings

### M-1: No length limit on legacy `ReviewComment.comment` field

- **Severity**: Medium
- **File**: `src/insight_blueprint/models/review.py`, line 22
- **File**: `src/insight_blueprint/web.py`, lines 98-101 (`AddCommentRequest`)
- **Description**: The `BatchComment.comment` field correctly enforces
  `Field(min_length=1, max_length=2000)`, but the older `ReviewComment.comment`
  field (line 22) has no length constraint at all. The `AddCommentRequest` Pydantic
  model in `web.py` also defines `comment: str` without any `max_length`. A malicious
  or accidental client could submit arbitrarily large comment strings through the
  `POST /api/designs/{id}/comments` endpoint, leading to storage exhaustion or
  performance degradation when loading reviews.
- **Recommended Fix**:
  ```python
  # In ReviewComment (models/review.py)
  comment: str = Field(min_length=1, max_length=10000)

  # In AddCommentRequest (web.py)
  comment: str = Field(min_length=1, max_length=10000)
  ```

### M-2: No validation on `reviewer` field length/content

- **Severity**: Medium
- **Files**:
  - `src/insight_blueprint/models/review.py`, lines 23, 64
  - `src/insight_blueprint/web.py`, lines 101, 135
- **Description**: The `reviewer` field is accepted as an arbitrary string with no
  length or format constraint in both `ReviewComment`, `ReviewBatch`, `AddCommentRequest`,
  and `SubmitBatchRequest`. While it defaults to `"analyst"`, a client can override it
  with any value including extremely long strings or strings containing control
  characters. This data is persisted to YAML and rendered in the frontend.
- **Recommended Fix**:
  ```python
  reviewer: str = Field(default="analyst", min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\- ]+$")
  ```

### M-3: Broad exception catch in `save_review_batch` MCP tool exposes internal details

- **Severity**: Medium
- **File**: `src/insight_blueprint/server.py`, lines 420-421
- **Description**: The MCP tool `save_review_batch` catches `(ValueError, Exception)`,
  which means any unhandled exception (including potential internal errors) will have
  its full `str(e)` returned to the caller. This could leak internal implementation
  details such as file paths, class names, or stack information.
  ```python
  except (ValueError, Exception) as e:
      return {"error": str(e)}
  ```
  The HTTP endpoint in `web.py` handles this better with separate `ValidationError`
  and `ValueError` catches, but the MCP tool does not.
- **Recommended Fix**:
  ```python
  except ValueError as e:
      return {"error": str(e)}
  except Exception:
      logger.exception("Unexpected error in save_review_batch")
      return {"error": "Internal error while saving review batch"}
  ```

### L-1: `target_content` accepts arbitrary JSON (no depth/size limit)

- **Severity**: Low
- **File**: `src/insight_blueprint/models/review.py`, line 34
- **Description**: The `target_content` field is typed as `JsonValue` which is a
  recursive type allowing arbitrary nesting depth and size. While Pydantic and
  FastAPI/uvicorn have default request size limits, a deeply nested JSON structure
  could theoretically cause excessive memory usage during deserialization or YAML
  serialization. The risk is low because this is a local development tool, but
  defense-in-depth would suggest limiting the serialized size.
- **Recommended Fix**: Consider adding a model validator that checks
  `len(json.dumps(self.target_content)) < MAX_CONTENT_SIZE` (e.g., 50KB).

### L-2: Frontend `maxLength` on textarea is client-side only

- **Severity**: Low
- **File**: `frontend/src/pages/design-detail/components/DraftCommentForm.tsx`, line 27
- **Description**: The `<Textarea maxLength={2000}>` provides client-side enforcement
  only. The backend `BatchComment.comment` field correctly enforces `max_length=2000`
  via Pydantic, so this is defense-in-depth rather than a primary control. No action
  needed, but noted for completeness -- the backend validation is the authoritative
  check and it is correctly in place.
- **Recommended Fix**: None required. Backend validation is already enforced.

### L-3: CORS allows `localhost:3000` and `localhost:5173` without authentication

- **Severity**: Low
- **File**: `src/insight_blueprint/web.py`, lines 28-35
- **Description**: CORS is configured to allow requests from localhost origins only,
  which is appropriate for a local development tool. However, there is no
  authentication or authorization mechanism. Any process on the local machine can
  make API calls. This is an accepted risk for a local development tool, but should
  be reconsidered if the tool is ever exposed to a network.
- **Recommended Fix**: None for current scope (local dev tool). Add authentication
  before any network exposure.

### L-4: `reviewer` field rendered without sanitization in frontend

- **Severity**: Low
- **File**: `frontend/src/pages/design-detail/components/ReviewHistoryPanel.tsx`, line 66
- **Description**: The `batch.reviewer` value is rendered directly in a `<span>` element.
  React auto-escapes text content by default, so there is no XSS risk here. However,
  combined with M-2 (no backend validation on reviewer content), a very long or
  unusual reviewer string could cause UI layout issues.
- **Recommended Fix**: Fix M-2 on the backend side; the frontend rendering is safe
  thanks to React's auto-escaping.

---

## Checks Passed (No Issues Found)

### XSS Protection
- **No `dangerouslySetInnerHTML` usage found** anywhere in the frontend codebase.
- All user-supplied text (comments, reviewer names, section labels) is rendered
  through React's JSX text interpolation, which auto-escapes HTML entities.
- The `JsonTree` component is used for structured data rendering.

### Path Traversal Protection
- **All design IDs are validated** against `SAFE_ID_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")`
  at both the HTTP layer (FastAPI `Path(pattern=...)`) and the core service layer
  (`validate_id()`). This prevents `../` or other path traversal sequences in IDs
  used to construct file paths like `{design_id}_reviews.yaml`.

### Input Validation: `target_section`
- `target_section` values are validated against `ALLOWED_TARGET_SECTIONS` in
  `ReviewService.save_review_batch()` (line 187-193 of `core/reviews.py`).
- Frontend `COMMENTABLE_SECTIONS` in `sections.ts` mirrors the backend set.
- Empty string target_section is rejected by `BatchComment.validate_target_section_not_empty`.

### Command Injection
- **No subprocess calls, `os.system`, `eval()`, or `exec()` found** in any of the
  changed files or the broader `src/insight_blueprint/` directory.

### SQL Injection
- Not applicable. The application uses YAML file storage, not SQL databases.

### Error Message Handling
- The HTTP layer (`web.py`) has a proper `general_exception_handler` that returns
  `"Internal server error"` for 500 errors without leaking stack traces (line 62-67).
- The API client (`client.ts`) sanitizes error details: 5xx errors get a generic
  message, 4xx errors are truncated to 200 characters (line 30-33).

### YAML Deserialization Safety
- `ruamel.yaml` is used (not `PyYAML` with `yaml.load()`), which does not support
  Python object deserialization by default, eliminating YAML deserialization attacks.

### Atomic File Writes
- The `write_yaml()` function uses `tempfile.mkstemp` + `os.replace` for atomic
  writes, preventing data corruption from concurrent access or crashes.

### Frontend API Client
- All dynamic URL segments use `encodeURIComponent()` for proper encoding.
- Default 30-second timeout prevents hanging requests.
- AbortController is properly used for cleanup on component unmount.

---

## Summary Table

| ID  | Severity | Component | Issue |
|-----|----------|-----------|-------|
| M-1 | Medium   | Backend   | No length limit on legacy ReviewComment.comment |
| M-2 | Medium   | Backend   | No validation on reviewer field |
| M-3 | Medium   | Backend   | Broad exception catch in MCP tool leaks details |
| L-1 | Low      | Backend   | target_content accepts unlimited JSON depth/size |
| L-2 | Low      | Frontend  | maxLength is client-side only (backend enforces) |
| L-3 | Low      | Backend   | No auth (accepted for local dev tool) |
| L-4 | Low      | Frontend  | reviewer rendered without backend length check |

---

## Recommendations Priority

1. **Fix M-1 and M-2 together** -- Add Field constraints to `ReviewComment.comment`
   and `reviewer` fields across all models and request schemas.
2. **Fix M-3** -- Split the exception handling in the MCP `save_review_batch` tool.
3. **Consider L-1** -- Add a size validator for `target_content` as defense-in-depth.
4. **L-2, L-3, L-4** -- No immediate action required.

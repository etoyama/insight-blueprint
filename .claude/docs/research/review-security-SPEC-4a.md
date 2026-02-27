# Security Review: SPEC-4a (webui-backend)

**Reviewer**: Security Reviewer (Agent)
**Date**: 2026-02-27
**Scope**: `web.py`, `_registry.py`, `cli.py`, `server.py`, `pyproject.toml`, test files

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 1 |
| Medium   | 3 |
| Low      | 4 |

Overall the security posture is **good** for a v1 local-only tool. The codebase already has solid fundamentals: ID validation at the core layer, localhost-only binding, restricted CORS, generic error messages for unhandled exceptions, and parameterized SQL queries. The findings below are areas for hardening.

---

## Findings

### HIGH

#### H1: Missing ID validation on REST API path parameters (web.py)

- **Severity**: High
- **Files**: `src/insight_blueprint/web.py:179`, `web.py:191`, `web.py:273`, `web.py:286`, `web.py:313`, `web.py:374`, `web.py:390`, `web.py:404`, `web.py:422`
- **Issue**: The REST API endpoints in `web.py` do NOT validate `design_id` or `source_id` path parameters before passing them to service methods. While the core service layer (`designs.py`, `catalog.py`, `reviews.py`) has `_validate_id()` calls that use `fullmatch(r"[a-zA-Z0-9_-]+")`, the MCP `server.py` **also** validates IDs at its boundary. However, `web.py` relies entirely on the core layer's `ValueError` being caught by the global `value_error_handler`. This is inconsistent with the defense-in-depth pattern used in `server.py`.

  The risk: if any core method is refactored to remove or relax its validation, `web.py` would be exposed to path traversal via `design_id` values like `../../etc/passwd` or `../../../sensitive-file`. The ID is used to construct file paths:
  ```python
  file_path = self._designs_dir / f"{design_id}_hypothesis.yaml"
  ```

- **Fix**: Add explicit ID validation at the `web.py` boundary, mirroring `server.py`:
  ```python
  _ID_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")

  def _validate_path_id(value: str, name: str = "id") -> None:
      if not _ID_PATTERN.fullmatch(value):
          raise HTTPException(400, detail=f"Invalid {name} '{value}'")
  ```
  Call this at the top of every endpoint that accepts `design_id` or `source_id`.

---

### MEDIUM

#### M1: `update_source` endpoint accepts raw `dict` body without Pydantic validation (web.py:286)

- **Severity**: Medium
- **File**: `src/insight_blueprint/web.py:286`
- **Issue**: The `PUT /api/catalog/sources/{source_id}` endpoint declares `body: dict` instead of a Pydantic model. This bypasses FastAPI's automatic request validation. An attacker can send arbitrary keys/values:
  ```json
  {"id": "hijacked-id", "type": "sql", "__class__": "..."}
  ```
  While `model_copy(update=...)` in the service layer limits which fields are applied, the explicit whitelist in `web.py` (lines 291-305) does not prevent unexpected keys from being silently accepted. There is also no type validation on the values (e.g., `name` could be an integer or nested object).

- **Fix**: Define a Pydantic model `UpdateSourceRequest` similar to `UpdateDesignRequest`:
  ```python
  class UpdateSourceRequest(BaseModel):
      name: str | None = None
      description: str | None = None
      connection: dict | None = None
      columns: list[dict] | None = None
      tags: list[str] | None = None
  ```

#### M2: Pydantic request models lack field constraints (web.py:82-122)

- **Severity**: Medium
- **Files**: `src/insight_blueprint/web.py:82-122`
- **Issue**: Request models like `CreateDesignRequest`, `AddCommentRequest`, `AddSourceRequest` etc. have no length constraints on string fields. An attacker could send:
  - `title` with 10MB of data
  - `comment` with millions of characters
  - `connection` dict with deeply nested structures

  This could cause memory pressure or slow YAML serialization. Since the data is persisted to YAML files, extremely large payloads would bloat the filesystem.

- **Fix**: Add `Field(max_length=...)` constraints:
  ```python
  class CreateDesignRequest(BaseModel):
      title: str = Field(max_length=500)
      hypothesis_statement: str = Field(max_length=5000)
      hypothesis_background: str = Field(max_length=5000)
      ...
  ```
  Also consider adding a request body size limit via middleware or uvicorn configuration.

#### M3: CORS `allow_methods=["*"]` and `allow_headers=["*"]` are overly permissive (web.py:31-33)

- **Severity**: Medium
- **File**: `src/insight_blueprint/web.py:31-33`
- **Issue**: While origins are correctly restricted to localhost, `allow_methods=["*"]` permits DELETE, PATCH, OPTIONS, HEAD etc. even though the API only uses GET, POST, and PUT. Similarly, `allow_headers=["*"]` permits any request header. This violates the principle of least privilege.

- **Fix**: Restrict to actually used methods and headers:
  ```python
  allow_methods=["GET", "POST", "PUT", "OPTIONS"],
  allow_headers=["Content-Type", "Accept"],
  ```

---

### LOW

#### L1: No request body size limit (web.py / uvicorn config)

- **Severity**: Low
- **File**: `src/insight_blueprint/web.py:527-533` (uvicorn.Config)
- **Issue**: There is no `--limit-request-body` or equivalent uvicorn configuration to cap request sizes. A malicious local client could POST very large bodies to cause memory exhaustion. Combined with M2, this enables DoS against the local server.

- **Fix**: Add `limit_max_request_size` to uvicorn Config or add a middleware that rejects bodies over a reasonable limit (e.g., 1MB).

#### L2: `SaveKnowledgeRequest.entries` accepts `list[dict]` without schema validation (web.py:121-122)

- **Severity**: Low
- **File**: `src/insight_blueprint/web.py:121-122`
- **Issue**: The `entries` field is typed as `list[dict]` which accepts any structure. Invalid entries are caught downstream when constructing `DomainKnowledgeEntry(**e)` (line 448), which raises a generic `Exception` caught by the `ValueError` handler. However, the error message from Pydantic validation failures may leak internal model field names and types.

- **Fix**: Define entries as `list[DomainKnowledgeEntryRequest]` with a proper Pydantic model, or ensure the error handler sanitizes Pydantic validation error details.

#### L3: `ValueError` handler exposes internal error messages (web.py:48-54)

- **Severity**: Low
- **File**: `src/insight_blueprint/web.py:48-54`
- **Issue**: The `value_error_handler` returns `str(exc)` directly to the client. While the general exception handler correctly returns a generic message, `ValueError` messages may contain internal details like file paths, regex patterns, or model validation errors. For example:
  ```
  {"error": "Invalid design_id '../../etc/passwd': must match [a-zA-Z0-9_-]+"}
  ```
  This leaks the validation regex to an attacker.

- **Fix**: For a local-only tool this is acceptable, but for production, consider sanitizing ValueError messages or mapping them to predefined user-facing messages.

#### L4: `AddCommentRequest.status` and `AddCommentRequest.reviewer` lack validation (web.py:94-97)

- **Severity**: Low
- **File**: `src/insight_blueprint/web.py:94-97`
- **Issue**: The `status` field accepts any string (validated downstream by the service). The `reviewer` field has a default of `"analyst"` but no constraints on allowed values or length. A reviewer name like `<script>alert(1)</script>` would be stored in the YAML file, potentially causing issues if the data is ever rendered in HTML without escaping.

- **Fix**: Add an enum constraint for `status` and a regex/length constraint for `reviewer`:
  ```python
  status: Literal["active", "supported", "rejected", "inconclusive"]
  reviewer: str = Field(default="analyst", max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
  ```

---

## Positive Security Observations

These aspects of the codebase demonstrate good security practices:

1. **Path traversal protection**: Core layer validates all IDs with `fullmatch(r"[a-zA-Z0-9_-]+")` before constructing file paths. This effectively prevents directory traversal.

2. **Localhost binding**: `start_server()` defaults to `host="127.0.0.1"` and `cli.py` explicitly passes `host="127.0.0.1"`. Test coverage verifies this (`test_cli_start_server_uses_localhost`).

3. **CORS origin restriction**: Only `localhost:3000`, `127.0.0.1:3000`, `localhost:5173`, `127.0.0.1:5173` are allowed.

4. **Error information hiding**: The general exception handler returns `"Internal server error"` without stack traces. Test `test_unhandled_exception_returns_500` verifies no leakage.

5. **SQL injection prevention**: All SQLite queries use parameterized statements (`?` placeholders). FTS5 search query is properly quoted with double-quote escaping (`sqlite_store.py:131`).

6. **No authentication by design**: As a local MCP tool, the lack of auth is intentional and documented. The localhost-only binding provides adequate access control for this use case.

7. **Daemon threads**: Server runs in a daemon thread, so it won't block process exit.

8. **Dependency versions**: FastAPI >= 0.115 and uvicorn >= 0.41.0 are recent enough to avoid known CVEs as of the review date.

---

## Recommendations (Not Findings)

1. **Consider rate limiting**: Even for localhost, adding a simple rate limiter prevents accidental infinite loops from scripts hammering the API.

2. **Add Content-Security-Policy header**: If the static file mount serves HTML, add CSP headers to prevent XSS if user-generated content is ever rendered.

3. **Pin dependency versions**: `pyproject.toml` uses `>=` for all dependencies. Consider using `>=X.Y,<Z` ranges or lockfiles to prevent unexpected upgrades introducing vulnerabilities.

4. **Access logging**: `access_log=False` (web.py:532) disables request logging. For security auditing, consider enabling access logs at least for non-GET requests.

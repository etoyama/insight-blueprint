# Security Review Report: SPEC-1, SPEC-2, SPEC-3

**Date**: 2026-02-26
**Reviewer**: security-reviewer (automated)
**Scope**: All Python source files in insight-blueprint

## Summary

Overall security posture is **good**. The codebase follows most security best practices:
- SQL queries use parameterized statements throughout
- YAML I/O uses `ruamel.yaml` (safe by default, no `yaml.load` with `Loader=FullLoader`)
- File writes use atomic tempfile + os.replace pattern
- Input validation uses Pydantic models
- No hardcoded secrets or credentials found

**Findings: 0 Critical, 1 High, 3 Medium, 2 Low**

---

## Findings

### Finding 1: Path Traversal via design_id in ReviewService

- **Severity**: High
- **File**: `src/insight_blueprint/core/reviews.py:123, 139, 219, 249`
- **Also affects**: `src/insight_blueprint/core/designs.py:57, 72, 78`
- **Description**: The `design_id` parameter is used directly to construct file paths (e.g., `f"{design_id}_reviews.yaml"`, `f"{design_id}_hypothesis.yaml"`). While `server.py` validates design_id with `_DESIGN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")` at the MCP tool layer, the service classes (`ReviewService`, `DesignService`) do NOT validate the design_id internally. If these services are ever called from a code path that bypasses the MCP tool layer (e.g., future CLI commands, internal API, test code), a crafted design_id like `../../etc/passwd` could result in path traversal.
- **Recommended Fix**: Add design_id validation at the service layer (defense in depth). Either:
  1. Validate `design_id` in `DesignService.__init__` or each method, OR
  2. Create a shared `validate_id(value: str)` utility and call it in each service method.

```python
# Example: shared validator
import re
_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")

def validate_id(value: str, label: str = "id") -> None:
    if not _SAFE_ID.match(value):
        raise ValueError(f"Invalid {label}: must match [a-zA-Z0-9_-]+")
```

### Finding 2: source_id Path Traversal in CatalogService

- **Severity**: Medium
- **File**: `src/insight_blueprint/core/catalog.py:40, 71, 104, 125`
- **Description**: Similar to Finding 1, `source_id` is used directly in file path construction (e.g., `f"{source_id}.yaml"`). The MCP tool layer in `server.py` does NOT validate `source_id` with a regex pattern (unlike `design_id`). A malicious `source_id` containing path separators (e.g., `../../etc/passwd`) would write/read outside the intended directory.
- **Recommended Fix**: Add the same `_validate_design_id`-style validation to all MCP tools that accept `source_id`, AND add validation at the CatalogService level for defense in depth.

### Finding 3: Unvalidated `reviewer` Field Stored Directly

- **Severity**: Medium
- **File**: `src/insight_blueprint/server.py:408` and `src/insight_blueprint/core/reviews.py:77`
- **Description**: The `reviewer` parameter in `save_review_comment()` accepts any string without length or character validation. While this is a local MCP tool (not a web API), if the reviewer string is extremely long or contains control characters, it could:
  1. Bloat the YAML file size
  2. Cause display issues if rendered in a UI
  3. Potentially contain YAML injection payloads (mitigated by ruamel.yaml's safe serialization)
- **Recommended Fix**: Add Pydantic `Field` constraints to `ReviewComment.reviewer`:
```python
reviewer: str = Field(default="analyst", min_length=1, max_length=100, pattern=r"^[\w\s-]+$")
```

### Finding 4: Error Messages Expose Internal Paths

- **Severity**: Medium
- **File**: `src/insight_blueprint/cli.py:29`
- **Description**: The error message `f"Project path does not exist: {project_path}"` exposes the resolved absolute filesystem path. While this is a CLI tool (user-facing), it's worth noting per the security rules.
- **Recommended Fix**: This is acceptable for a CLI tool where the user specified the path. No change strictly required, but consider using the user's original input rather than the resolved path:
```python
f"Project path does not exist: {project}"
```

### Finding 5: FTS5 Search Query Sanitization Could Be Bypassed

- **Severity**: Low
- **File**: `src/insight_blueprint/storage/sqlite_store.py:131`
- **Description**: The search query sanitization wraps user input in double quotes with escaped inner quotes: `'"' + query.replace('"', '""') + '"'`. This is the correct approach for FTS5 phrase queries. However, SQLite FTS5's query syntax also supports special operators within quoted strings in some configurations. With the `trigram` tokenizer, this is largely a non-issue since trigram tokenization doesn't parse FTS5 query operators. The risk is minimal.
- **Recommended Fix**: No immediate action needed. The current sanitization is adequate for the trigram tokenizer. Document the assumption that the trigram tokenizer is required for this sanitization to be sufficient.

### Finding 6: Dependency Versions Not Pinned

- **Severity**: Low
- **File**: `pyproject.toml:7-12`
- **Description**: Dependencies use minimum version specifiers (`>=`) rather than pinned versions (`==`). Per the project's security rules (`.claude/rules/security.md`), pinned versions are preferred. However, this is a library/tool package where minimum versions are the standard practice (pinning is more appropriate for applications with lock files).
- **Recommended Fix**: Ensure `uv.lock` is committed to the repository for reproducible builds. The `>=` specifiers in `pyproject.toml` are acceptable for a library package.

---

## Checklist Results

| Check | Result | Notes |
|-------|--------|-------|
| Hardcoded secrets | PASS | No API keys, passwords, or tokens found |
| SQL injection | PASS | All queries use parameterized statements (`?` placeholders) |
| Command injection | PASS | No `subprocess`, `os.system`, or `eval` calls found |
| Path traversal | **FAIL** | design_id and source_id used in file paths without service-layer validation |
| Input validation | PARTIAL | MCP tools validate design_id but not source_id; services lack internal validation |
| Sensitive data exposure | PASS | Error messages are appropriately generic (minor exception in CLI) |
| Dependency vulnerabilities | PASS | No known vulnerable packages in current dependencies |
| YAML deserialization | PASS | Uses `ruamel.yaml` which is safe by default (no unsafe Loader) |
| Atomic write safety | PASS | All writes use tempfile + os.replace pattern correctly |

---

## Positive Security Patterns Observed

1. **Atomic writes**: Both `yaml_store.py` and `project.py` use `tempfile.mkstemp` + `os.replace` for crash-safe writes
2. **Parameterized SQL**: All SQLite queries in `sqlite_store.py` use `?` placeholders
3. **Safe YAML**: `ruamel.yaml` does not execute arbitrary Python objects during deserialization
4. **Pydantic validation**: Data models enforce types and constraints at the boundary
5. **WAL mode + busy_timeout**: SQLite connections configured for concurrent access safety
6. **Design ID validation**: `server.py` validates design_id with regex before passing to services

---

## Priority Recommendations

1. **(High priority)** Add `source_id` validation at the MCP tool layer (same pattern as `_validate_design_id`)
2. **(High priority)** Add ID validation at the service layer for defense in depth (both DesignService and CatalogService)
3. **(Medium priority)** Add length/pattern constraints to `ReviewComment.reviewer` field
4. **(Low priority)** Ensure `uv.lock` is committed for reproducible builds

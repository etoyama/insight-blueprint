# Security Review: SPEC-3 Review Workflow

## Review Scope

**New files:**
- `src/insight_blueprint/core/reviews.py`
- `src/insight_blueprint/core/rules.py`
- `src/insight_blueprint/models/review.py`

**Modified files:**
- `src/insight_blueprint/server.py`
- `src/insight_blueprint/cli.py`
- `src/insight_blueprint/storage/project.py`
- `src/insight_blueprint/models/design.py`
- `src/insight_blueprint/models/__init__.py`

---

## Findings

### 1. Path Traversal via `design_id` in file operations

- **Severity**: Medium
- **Files and lines**:
  - `src/insight_blueprint/core/reviews.py:123` (`{design_id}_reviews.yaml`)
  - `src/insight_blueprint/core/reviews.py:139` (`{design_id}_reviews.yaml`)
  - `src/insight_blueprint/core/reviews.py:241` (`{design_id}_reviews.yaml`)
  - `src/insight_blueprint/core/designs.py:57` (`{design_id}_hypothesis.yaml`)
  - `src/insight_blueprint/core/designs.py:72` (`{design_id}_hypothesis.yaml`)
  - `src/insight_blueprint/core/designs.py:78` (`{design_id}_hypothesis.yaml`)
- **Description**: The `design_id` parameter is used directly in file path construction (e.g., `self._designs_dir / f"{design_id}_reviews.yaml"`). If an attacker passes a `design_id` containing path traversal sequences like `../../etc/passwd`, the resulting path could escape the intended `.insight/designs/` directory. For reads, this could leak file contents; for writes, it could overwrite arbitrary files. In practice, design IDs are generated internally by `DesignService.create_design()` (format: `THEME-HNN`), but the MCP tool endpoints accept arbitrary `design_id` strings from the client.
- **Recommended fix**: Add a validation function that rejects `design_id` values containing `/`, `\`, `..`, or null bytes. Apply this validation at the MCP tool boundary (in `server.py` handlers) or at the service layer entry points. Example:
  ```python
  import re
  SAFE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-H\d{2,}$")

  def validate_design_id(design_id: str) -> None:
      if not SAFE_ID_PATTERN.match(design_id):
          raise ValueError(f"Invalid design_id format: '{design_id}'")
  ```

### 2. Unsafe YAML deserialization (ruamel.yaml)

- **Severity**: Low
- **File and line**: `src/insight_blueprint/storage/yaml_store.py:21`
- **Description**: `ruamel.yaml`'s `YAML()` (round-trip mode) is used for loading. Unlike PyYAML's `yaml.load(Loader=FullLoader)`, ruamel.yaml's default round-trip mode does NOT execute arbitrary Python constructors, so this is safe by default. However, the codebase reads YAML files that contain user-provided content (review comments serialized to YAML). If ruamel.yaml configuration were changed to `typ='unsafe'`, this would become a code execution vulnerability.
- **Recommended fix**: No immediate action needed, but consider adding a comment or assertion that the YAML loader must remain in safe/round-trip mode. Adding `yaml = YAML(typ='safe')` would be more explicit but may break round-trip comment preservation.

### 3. Race condition in read-modify-write patterns

- **Severity**: Low
- **Files and lines**:
  - `src/insight_blueprint/core/reviews.py:123-127` (save_review_comment: read reviews, append, write)
  - `src/insight_blueprint/core/reviews.py:239-248` (save_extracted_knowledge: read reviews, modify, write)
  - `src/insight_blueprint/core/reviews.py:220-236` (save_extracted_knowledge: read extracted_knowledge, modify, write)
- **Description**: Multiple operations follow a read-modify-write pattern without file locking. If two concurrent MCP requests modify the same file simultaneously, one write could overwrite the other's changes (lost update). In practice, MCP servers typically handle one request at a time (single-threaded via stdio transport), but this could become an issue with SSE transport or future concurrency changes.
- **Recommended fix**: For the current single-threaded MCP server, this is acceptable. If concurrency is introduced, add file-level locking (e.g., `fcntl.flock` or a `threading.Lock` per file path).

### 4. No input length validation on `comment` field

- **Severity**: Low
- **Files and lines**:
  - `src/insight_blueprint/server.py:388-413` (save_review_comment MCP tool)
  - `src/insight_blueprint/core/reviews.py:72-132` (ReviewService.save_review_comment)
  - `src/insight_blueprint/models/review.py:13` (comment: str, no max_length)
- **Description**: The `comment` field in `save_review_comment` accepts an arbitrary-length string. A very large comment (e.g., multi-MB) would be written to the YAML file without size limits, potentially causing disk space issues or slow parsing. The `extract_domain_knowledge` function then splits and processes every line, which could be slow for extremely large comments.
- **Recommended fix**: Add a `max_length` constraint to the Pydantic model or validate at the MCP tool boundary:
  ```python
  MAX_COMMENT_LENGTH = 50_000  # 50KB reasonable limit
  comment: str = Field(max_length=MAX_COMMENT_LENGTH)
  ```

### 5. Error messages may leak internal paths

- **Severity**: Low
- **Files and lines**:
  - `src/insight_blueprint/cli.py:28-30` (ClickException with full resolved path)
  - `src/insight_blueprint/server.py:100-101` (error messages echo user-supplied status values)
- **Description**: The CLI error message at `cli.py:29` includes the full resolved filesystem path (`f"Project path does not exist: {project_path}"`). This could reveal the server's directory structure to the user. However, since this is a CLI tool run locally (not a web service), the risk is minimal.
- **Recommended fix**: Acceptable for a local CLI tool. If the server were exposed remotely, sanitize path information from error messages.

### 6. `reviewer` field has no validation

- **Severity**: Low
- **Files and lines**:
  - `src/insight_blueprint/server.py:392` (reviewer parameter with default "analyst")
  - `src/insight_blueprint/models/review.py:17` (reviewer: str = "analyst")
- **Description**: The `reviewer` field accepts any string. While not a direct vulnerability, it could be used to inject misleading data (e.g., impersonating a different reviewer). There is no allowlist or length constraint.
- **Recommended fix**: Consider adding a `max_length` constraint and optionally a pattern validator if reviewer names should follow a specific format.

### 7. `source_id` used in extracted knowledge file has fixed path

- **Severity**: Info (No Issue)
- **File and line**: `src/insight_blueprint/core/reviews.py:219`
- **Description**: The extracted knowledge file path is fixed (`rules/extracted_knowledge.yaml`), not derived from user input. This is safe.

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 0 |
| Medium   | 1 |
| Low      | 5 |
| Info     | 1 |

### Overall Assessment

The codebase has a generally good security posture. No critical or high-severity vulnerabilities were found. The most significant finding is the **path traversal risk via `design_id`** (Medium), which should be addressed by adding input validation for ID parameters at the MCP tool boundary. The remaining findings are low-severity improvements that would harden the system against edge cases.

### Positive Security Practices Observed

- Atomic file writes using `tempfile + os.replace` (prevents partial writes)
- Pydantic model validation for structured data
- StrEnum for status values (prevents arbitrary status injection)
- ruamel.yaml in safe round-trip mode (no arbitrary code execution)
- No hardcoded secrets or credentials
- No SQL queries (YAML-based storage avoids SQL injection)
- Error messages in MCP tools are generally sanitized (return structured dicts, not stack traces)

### Regex DoS (ReDoS) Check

The regex patterns in `reviews.py:16-32` were analyzed:
- `r"^(caution|注意)\s*:\s*"` — anchored at start, no nested quantifiers. Safe.
- `r"^(definition|定義)\s*:\s*"` — same pattern. Safe.
- `r"^(methodology|手法)\s*:\s*"` — same pattern. Safe.
- `r"^(context|背景)\s*:\s*"` — same pattern. Safe.
- `r"^(table|テーブル)\s*:\s*"` — same pattern. Safe.
- `r"^[A-Z][A-Z0-9]*$"` (in designs.py) — anchored both ends, no backtracking risk. Safe.

No ReDoS vulnerabilities found.

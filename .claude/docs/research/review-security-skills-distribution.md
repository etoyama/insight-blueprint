# Security Review: SPEC-5 Skills Distribution

**Reviewer**: Security Reviewer (Agent)
**Date**: 2026-02-28
**Scope**: All changed/new files for SPEC-5 (skills-distribution)
**Overall Risk**: Low -- no critical or high-severity issues found

---

## Summary

The skills distribution implementation is well-structured with good defensive
coding practices. Atomic writes, backup/restore patterns, and graceful error
handling are all present. No hardcoded secrets, no credential exposure, and no
SQL injection vectors were found. The findings below are medium and low
severity items that represent defense-in-depth improvements.

---

## Findings

### S-1: Path Traversal via Traversable Entry Names (Medium)

**File**: `src/insight_blueprint/storage/project.py`, lines 241-249
**Function**: `_copy_traversable_recursive`

**Description**:
The function constructs `target = dest / entry.name` without validating that
`entry.name` does not contain path traversal sequences (e.g., `..`, `/`, or
absolute paths). While `importlib.resources.files()` Traversable implementations
from standard package loaders will not produce malicious entry names, a
compromised or maliciously crafted wheel package could potentially include
entries with names like `../../etc/cron.d/evil` in a custom Traversable.

The same pattern appears in `_collect_traversable_entries` (line 412) where
`entry.name` is used without validation.

**Impact**: If a malicious package were installed, files could be written outside
the intended `.claude/skills/<name>/` directory.

**Recommended Fix**:
```python
def _copy_traversable_recursive(src: Traversable, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        # Validate entry name to prevent path traversal
        if ".." in entry.name or "/" in entry.name or "\\" in entry.name:
            logger.warning("Skipping suspicious entry name: %s", entry.name)
            continue
        target = dest / entry.name
        # Verify target is still under dest
        if not target.resolve().is_relative_to(dest.resolve()):
            logger.warning("Path traversal blocked: %s", entry.name)
            continue
        if entry.is_file():
            target.write_bytes(entry.read_bytes())
        elif entry.is_dir():
            _copy_traversable_recursive(entry, target)
```

---

### S-2: Path Traversal via Skill Names in _discover_bundled_skills (Medium)

**File**: `src/insight_blueprint/storage/project.py`, lines 65-87, 307-309
**Functions**: `_discover_bundled_skills`, `_copy_skills_template`

**Description**:
`entry.name` from the Traversable is used directly to construct the destination
path: `dest = project_path / ".claude" / "skills" / skill_name` (line 309).
If a bundled skill had a name containing `..` (e.g., `../../etc`), it could
write outside the intended directory. The same concern applies to the
`_write_bundled_update` function where `dest_dir.name` is used in a diff
message (line 274-275) but that is informational only.

**Impact**: Same as S-1 -- mitigated by the fact that Traversable from standard
loaders won't produce such names, but defense-in-depth validation is missing.

**Recommended Fix**:
Add validation in `_discover_bundled_skills`:
```python
if ".." in entry.name or "/" in entry.name:
    logger.warning("Skipping invalid skill name: %s", entry.name)
    continue
```

---

### S-3: TOCTOU Race Condition in Backup/Restore (Low)

**File**: `src/insight_blueprint/storage/project.py`, lines 214-238
**Function**: `_copy_skill_tree`

**Description**:
There is a time-of-check/time-of-use gap between checking `dest.exists()`
(line 221) and performing `dest.rename(backup)` (line 224). Another process
could create or delete `dest` between these operations. Similarly, the cleanup
at line 237-238 checks `backup.exists()` before `shutil.rmtree(backup)`.

**Impact**: Low. This is a CLI tool typically run by a single user in their
project directory. Concurrent modification of `.claude/skills/` is extremely
unlikely in practice. The existing try/except at line 228-234 provides
reasonable recovery.

**Recommended Fix**: Accept current risk. If desired, use a file lock:
```python
import fcntl
# Acquire lock before backup/restore operations
```

---

### S-4: Hash Comparison is Not Constant-Time (Low)

**File**: `src/insight_blueprint/storage/project.py`, line 345
**Function**: `_copy_skills_template`

**Description**:
The hash comparison `installed_hash == prev_bundled_hash` uses Python's standard
string equality, which short-circuits on first mismatch. In security-sensitive
contexts (e.g., HMAC verification), this could enable timing attacks.

**Impact**: Very low. This is a local integrity check, not an authentication
mechanism. An attacker who can observe timing of this comparison already has
local access to the filesystem and could read the hashes directly. No real
attack vector exists here.

**Recommended Fix**: No action needed. The current implementation is appropriate
for its use case (detecting user modifications, not authenticating data).

---

### S-5: JSON State File Injection / Tampering (Low)

**File**: `src/insight_blueprint/storage/project.py`, lines 181-211
**Functions**: `_load_skill_state`, `_save_skill_state`

**Description**:
State files (`.insight-blueprint-state.json`) are read and parsed with
`json.loads`. If an attacker could modify this file, they could:
1. Set `installed_version` to a very high value to prevent upgrades
2. Set `installed_bundled_hash` to match the current hash to force auto-updates
3. Inject unexpected keys (though these are unused)

The `_load_skill_state` function gracefully handles `json.JSONDecodeError` and
returns `{}`, which is good.

**Impact**: Low. The attacker would need write access to the project directory,
at which point they could modify the skill files directly. No privilege
escalation is possible.

**Recommended Fix**: Acceptable as-is. Optional improvement: validate schema
of loaded state (check only expected keys are present).

---

### S-6: Potential Credential Exposure in docs/RELEASE.md (Low)

**File**: `docs/RELEASE.md`, lines 13-19

**Description**:
The release procedure document shows a `~/.pypirc` example with a placeholder
token value `pypi-YOUR_API_TOKEN_HERE`. While this is clearly a placeholder
and not a real credential, the document references a file that would contain
real credentials. There is no `.gitignore` entry for `~/.pypirc` (though
it's outside the repo anyway).

**Impact**: Informational. No actual credentials are committed. The placeholder
is clearly marked. The file location (`~/.pypirc`) is a user home directory
file, not within the repository.

**Recommended Fix**: No action needed. The document follows standard Python
packaging documentation practices.

---

### S-7: Version String ReDoS Potential (Low)

**File**: `src/insight_blueprint/storage/project.py`, lines 103, 111
**Functions**: `_get_skill_version`, `_get_skill_version_from_traversable`

**Description**:
The regex patterns for parsing frontmatter and version fields are:
- `r"^---\s*\n(.*?)\n---\s*\n"` (with `re.DOTALL`)
- `r"^version:\s*(.+)$"` (with `re.MULTILINE`)

The `.*?` non-greedy match with `re.DOTALL` could be slow on very large SKILL.md
files without closing `---` delimiters, but the input size is bounded by file
content (typically < 1KB for SKILL.md frontmatter).

**Impact**: Very low. Input is local file content, not user-supplied network
input. The regex patterns are simple and not vulnerable to catastrophic
backtracking.

**Recommended Fix**: No action needed.

---

### S-8: No Symlink Following Check (Low)

**File**: `src/insight_blueprint/storage/project.py`, lines 150-155
**Function**: `_hash_skill_directory`

**Description**:
`skill_dir.rglob("*")` follows symlinks by default. A malicious symlink inside
a skill directory could point to sensitive files outside the project (e.g.,
`~/.ssh/id_rsa`), causing their content to be included in the hash computation.
While the hash value is only stored locally in the state file (not transmitted),
the file content is read into memory.

Similarly, `_copy_traversable_recursive` does not check for symlinks in the
destination directory.

**Impact**: Low. The skill directory is created by the tool itself from bundled
content. A user would need to manually create symlinks in their skill directory.

**Recommended Fix**: Optional defense-in-depth:
```python
for file_path in sorted(skill_dir.rglob("*")):
    if file_path.is_symlink():
        continue  # Skip symlinks
    if not file_path.is_file():
        continue
```

---

### S-9: shutil.rmtree Without Error Handling (Low)

**File**: `src/insight_blueprint/storage/project.py`, lines 232, 238, 285
**Functions**: `_copy_skill_tree`, `_write_bundled_update`

**Description**:
`shutil.rmtree` calls at lines 232, 238, and 285 do not catch exceptions.
If `rmtree` fails (e.g., permission denied on a file), the exception will
propagate. Line 232 is in an exception handler, so a failure there could
mask the original error.

**Impact**: Low. The risk is application crash during cleanup, not a security
vulnerability. The try/except at line 228 handles the primary failure case.

**Recommended Fix**: Consider wrapping cleanup `rmtree` calls:
```python
try:
    shutil.rmtree(backup)
except OSError:
    logger.warning("Failed to clean up backup: %s", backup)
```

---

## Files Reviewed with No Findings

| File | Notes |
|------|-------|
| `pyproject.toml` | No secrets, standard metadata. `packaging` dependency for version parsing is appropriate. |
| `LICENSE` | Standard MIT license, no issues. |
| `README.md` | No credentials or sensitive information exposed. |
| `_skills/analysis-design/SKILL.md` | No executable code, no security concerns. Template instructions only. |
| `_skills/catalog-register/SKILL.md` | API key reference (`appId={api_key}`) is in example text only, not actual credentials. |
| `tests/test_skill_integration.py` | Test code uses `tmp_path` fixtures properly. No hardcoded paths. |
| `tests/test_skill_update.py` | Test code uses `tmp_path` fixtures properly. Comprehensive coverage of edge cases. |

---

## Positive Security Observations

1. **Atomic file writes**: `_register_mcp_server` and `write_yaml` use
   `tempfile.mkstemp` + `os.replace` for atomic writes, preventing corruption.
2. **Backup/restore pattern**: `_copy_skill_tree` creates backups before
   overwriting and restores on failure.
3. **Graceful error handling**: `_load_skill_state` and `_write_bundled_update`
   catch errors gracefully without crashing.
4. **Version validation**: `packaging.version.Version` is used to validate
   semver strings, rejecting arbitrary input.
5. **No hardcoded credentials**: No API keys, passwords, or tokens in any file.
6. **No network calls**: The skill distribution system operates entirely on
   local filesystem -- no data exfiltration risk.
7. **Line ending normalization**: Hash computation normalizes CRLF to LF,
   preventing cross-platform hash mismatches.

---

## Risk Summary

| ID | Severity | Category | Status |
|----|----------|----------|--------|
| S-1 | Medium | Path Traversal | Recommend fix |
| S-2 | Medium | Path Traversal | Recommend fix |
| S-3 | Low | TOCTOU | Accept |
| S-4 | Low | Timing Attack | Accept |
| S-5 | Low | Data Integrity | Accept |
| S-6 | Low | Credential Exposure | Accept |
| S-7 | Low | ReDoS | Accept |
| S-8 | Low | Symlink Following | Optional fix |
| S-9 | Low | Error Handling | Optional fix |

**Critical**: 0 | **High**: 0 | **Medium**: 2 | **Low**: 7

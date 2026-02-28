# Test Review: SPEC-5 Skills Distribution

**Date**: 2026-02-28
**Reviewer**: Claude Opus 4.6 (Test Reviewer subagent)
**Scope**: `tests/test_skill_update.py` (U1-U33), `tests/test_skill_integration.py` (I1-I6)
**SUT**: `src/insight_blueprint/storage/project.py`

---

## 1. Test Execution Summary

| Metric | Value |
|--------|-------|
| Total tests | 40 (33 unit + 7 integration) |
| Passed | 40 |
| Failed | 0 |
| Duration | 0.11s |
| project.py coverage | **90%** (236 stmts, 23 missed) |
| Full suite coverage | 94% (1353 stmts, 77 missed) |

All 40 tests pass. No flaky tests observed. Execution time well under 100ms/test threshold.

---

## 2. Coverage Analysis

### 2.1 Covered Functions (project.py)

| Function | Coverage | Notes |
|----------|----------|-------|
| `init_project()` | 100% | Tested via I1-I6 |
| `_create_insight_dirs()` | 100% | Tested via I6 |
| `_discover_bundled_skills()` | ~95% | Lines 82-86 missed (see below) |
| `_get_skill_version()` | ~97% | Lines 98-100 missed (see below) |
| `_hash_skill_directory()` | 100% | U10-U15 |
| `_load_skill_state()` | 100% | U16-U18 |
| `_save_skill_state()` | 100% | U16, U19 |
| `_copy_skill_tree()` | 100% | U20-U23 |
| `_copy_traversable_recursive()` | 100% | Via U20-U23 |
| `_write_bundled_update()` | ~97% | Line 285 missed |
| `_copy_skills_template()` | ~97% | Lines 334-335 missed |
| `_get_skill_version_from_traversable()` | ~80% | Lines 369-370, 374, 389-390 missed |
| `_hash_skill_directory_from_traversable()` | 100% | Via integration tests |
| `_collect_traversable_entries()` | ~80% | Lines 415-416 missed |
| `_register_mcp_server()` | ~90% | Lines 450-455 missed |

### 2.2 Missed Lines Detail

| Lines | Function | What's missed | Priority |
|-------|----------|---------------|----------|
| 82-86 | `_discover_bundled_skills` | `except (AttributeError, TypeError)` on `skill_md.is_file()` + `except (FileNotFoundError, TypeError)` on `iterdir()` | Medium |
| 98-100 | `_get_skill_version` | `except OSError` when `read_text()` fails (unreadable file) | Medium |
| 285 | `_write_bundled_update` | `shutil.rmtree(update_dir)` when pre-existing `.bundled-update/` dir exists | Low |
| 334-335 | `_copy_skills_template` | `except InvalidVersion: pass` fallthrough in version comparison | Medium |
| 369-370 | `_get_skill_version_from_traversable` | `except (OSError, AttributeError)` when `read_text()` fails | Medium |
| 374 | `_get_skill_version_from_traversable` | `return None` on invalid frontmatter | Low |
| 389-390 | `_get_skill_version_from_traversable` | `except InvalidVersion: return None` | Low |
| 415-416 | `_collect_traversable_entries` | Recursive directory branch (`elif entry.is_dir()`) | Low |
| 450-455 | `_register_mcp_server` | `except Exception` error cleanup path (atomic write failure) | Medium |

---

## 3. Quality Assessment

### 3.1 Strengths

1. **Comprehensive decision-logic coverage (U27-U33)**: All 7 version-aware cases are tested (fresh copy, same-version skip, upgrade unmodified, upgrade customized, downgrade skip, legacy with/without dest). This is the most critical code path and it's well covered.

2. **AAA pattern adherence**: Tests consistently follow Arrange-Act-Assert. Setup helpers (`_make_traversable`, `_setup_bundled_skill`, `_create_fake_package`) keep tests clean.

3. **Independence**: Every test uses `tmp_path` fixture. No shared state. No order dependency. Tests can run in any order or in isolation.

4. **Edge cases covered well**:
   - CRLF normalization (U14)
   - Quoted vs unquoted versions (U5, U9)
   - YAML float coercion for `version: 1.0.0` without quotes (U9)
   - Invalid JSON state file (U18)
   - Missing frontmatter delimiter (U7)
   - Invalid semver like "latest" (U8)
   - Subdirectory recursion in hash (U15)

5. **Atomic backup/restore tested (U23)**: The critical failure-safety path of `_copy_skill_tree` is tested by injecting `OSError` mid-copy and verifying restoration.

6. **External dependencies properly mocked**: `importlib.resources.files` is consistently patched via `_FakeTraversable` / `_make_traversable`. No test depends on the actual installed package layout.

7. **Performance test (I5)**: NFR-1 (10 skills < 500ms) is directly tested.

8. **No-regression test (I6)**: Verifies legacy `init_project` behavior (`.insight/` dirs, `.mcp.json`) is preserved.

### 3.2 Weaknesses

1. **`_get_skill_version_from_traversable()` is untested directly**: This function is a near-duplicate of `_get_skill_version()` but operating on `Traversable` instead of `Path`. The unit tests only cover the `Path` version. The `Traversable` version is exercised indirectly through integration tests but its error branches (OSError/AttributeError on read, invalid frontmatter, InvalidVersion) are never hit.

2. **`_collect_traversable_entries()` recursive branch untested**: The `elif entry.is_dir()` path (line 415-416) is not covered. While the function is invoked via `_hash_skill_directory_from_traversable`, the test data doesn't include nested subdirectories in the Traversable tree during hashing.

3. **`_register_mcp_server()` error cleanup path untested (lines 450-455)**: The atomic write failure path (tempfile cleanup on exception) is never exercised.

4. **`_discover_bundled_skills()` defensive exceptions untested (lines 82-86)**: The `AttributeError`/`TypeError` catch when `skill_md.is_file()` fails, and the `FileNotFoundError`/`TypeError` catch when `_skills/` doesn't exist, are never triggered.

5. **`_write_bundled_update()` pre-existing `.bundled-update/` dir not tested (line 285)**: The `shutil.rmtree(update_dir)` path when `.bundled-update/` already exists before a new write is not exercised. Only the fresh-create path is tested.

6. **`_copy_skills_template()` InvalidVersion fallthrough untested (lines 334-335)**: When `Version()` raises `InvalidVersion` during comparison, the `pass` fallthrough is never hit. This requires a skill with a valid-looking-but-actually-invalid installed version.

7. **`_get_skill_version()` OSError on read untested (lines 98-100)**: File-unreadable scenario (e.g., permission denied on SKILL.md) is not tested.

---

## 4. Gap Analysis: Missing Test Cases

### Priority: High

| # | Function | Missing Test | Rationale |
|---|----------|-------------|-----------|
| G1 | `_get_skill_version_from_traversable` | Test with OSError/AttributeError on `read_text()` | Parallel of U7 but for Traversable. This function is called in every `_copy_skills_template` invocation. Error path silently returns None which could mask real issues. |
| G2 | `_get_skill_version_from_traversable` | Test with invalid frontmatter (no closing `---`) | Parallel of U7 for Traversable variant. |
| G3 | `_get_skill_version_from_traversable` | Test with InvalidVersion (e.g., "latest") | Parallel of U8 for Traversable variant. |

### Priority: Medium

| # | Function | Missing Test | Rationale |
|---|----------|-------------|-----------|
| G4 | `_discover_bundled_skills` | Test with `_skills/` not existing at all | Exercises `FileNotFoundError` catch (line 85-86). Important for robustness when package is installed without bundled skills. |
| G5 | `_discover_bundled_skills` | Test with broken Traversable entry (AttributeError on `is_file()`) | Exercises lines 82-84. Edge case but defensive code should be verified. |
| G6 | `_get_skill_version` | Test with unreadable file (OSError) | Exercises lines 98-100. Mock `Path.read_text` to raise `PermissionError`. |
| G7 | `_register_mcp_server` | Test atomic write failure cleanup | Exercises lines 450-455. Mock `os.replace` to raise, verify tempfile is cleaned up and exception propagates. |
| G8 | `_copy_skills_template` | Test with InvalidVersion in installed state | Exercises lines 334-335. Save state with `installed_version="not-a-version"`, then attempt upgrade. |
| G9 | `_collect_traversable_entries` | Test with nested subdirectory in Traversable | Exercises lines 415-416. Create bundled skill with `references/sub/deep.md` and verify hash includes it. |

### Priority: Low

| # | Function | Missing Test | Rationale |
|---|----------|-------------|-----------|
| G10 | `_write_bundled_update` | Test with pre-existing `.bundled-update/` dir | Exercises line 285 `shutil.rmtree`. Call `_write_bundled_update` twice and verify second call replaces first. |
| G11 | `_copy_skill_tree` | Test copy to dest with no pre-existing backup (empty dest parent) | Already implicitly covered by U20, but could be more explicit. |
| G12 | `_hash_skill_directory` | Test with empty directory (no files) | Boundary value. Verify returns a valid SHA-256 hex digest (hash of empty input). |
| G13 | `_hash_skill_directory` | Test with binary files | Ensure binary content is hashed correctly without CRLF normalization breaking binary data. Note: current code replaces `\r\n` in ALL files including binary -- potential bug. |

---

## 5. Potential Bug: Binary File CRLF Normalization

In `_hash_skill_directory()` (line 168):
```python
content = content.replace(b"\r\n", b"\n")
```

This normalizes ALL file content, including binary files. If a skill directory contains binary files (e.g., images), this could corrupt the hash by modifying binary data that legitimately contains `\r\n` bytes. The same issue exists in `_hash_skill_directory_from_traversable()` (line 403).

**Recommendation**: Only normalize text files (`.md`, `.txt`, `.yaml`, etc.) or check if content is valid UTF-8 before normalizing.

**Severity**: Low (skills currently only contain text files, but could cause issues if binary assets are added in the future).

---

## 6. Testing Standards Compliance

| Rule | Status | Notes |
|------|--------|-------|
| Happy path tested | PASS | All 7 decision cases + all helper functions |
| Error cases tested | PARTIAL | Some error branches uncovered (see G1-G8) |
| Boundary values tested | PARTIAL | Empty dir (U2), missing files (U3, U17) tested; empty hash input missing |
| AAA pattern | PASS | Consistent throughout |
| Tests independent | PASS | All use `tmp_path`, no shared state |
| External deps mocked | PASS | `importlib.resources.files` properly patched everywhere |
| Tests run fast | PASS | 40 tests in 0.11s (~2.75ms/test) |
| Coverage >= 80% | PASS | 90% for project.py |

---

## 7. Summary

**Overall Assessment**: Good quality test suite with strong coverage of the critical decision logic. The 90% line coverage meets the project's 80% threshold. The main gaps are in error/exception branches of Traversable-variant functions that parallel the well-tested Path-variant functions.

**Top 3 Recommendations**:
1. Add direct unit tests for `_get_skill_version_from_traversable()` error paths (G1-G3) -- these are the highest-risk untested code paths since they run on every `init_project()` call.
2. Add `_discover_bundled_skills()` test for missing `_skills/` directory (G4) -- important for robustness.
3. Add `_register_mcp_server()` atomic write failure test (G7) -- the cleanup code should be verified.

Implementing G1-G9 would bring coverage to approximately **96-98%**.

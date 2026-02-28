# Quality Review: SPEC-5 Skills Distribution

**Reviewer**: Claude Opus 4.6 (Quality Reviewer)
**Date**: 2026-02-28
**Scope**: All changed/new files in SPEC-5 (skills-distribution)

## Summary

| Severity | Count |
|----------|-------|
| High     | 3     |
| Medium   | 6     |
| Low      | 4     |

---

## High Severity Findings

### H1: Missing `packaging` dependency in pyproject.toml

**File**: `pyproject.toml` (dependencies section)
**File**: `src/insight_blueprint/storage/project.py` line 14

```python
from packaging.version import InvalidVersion, Version
```

`packaging` is imported in production code but is NOT listed in `[project.dependencies]`. It happens to be installed as a transitive dependency of `pip`/`setuptools`/`hatchling`, but this is not guaranteed in all environments (e.g., minimal Docker images, `--no-deps` installs).

**Suggested fix**: Add `"packaging>=23.0"` to `[project.dependencies]` in `pyproject.toml`.

---

### H2: Logic bug in `_collect_traversable_entries` -- prefix condition is inverted

**File**: `src/insight_blueprint/storage/project.py` line 412

```python
rel = f"{prefix}{entry.name}" if not prefix else f"{prefix}/{entry.name}"
```

The ternary condition is backwards:
- When `prefix` is empty (`""`), `not prefix` is `True`, so it produces `f"{prefix}{entry.name}"` = `"filename"` -- correct by accident.
- When `prefix` is non-empty, it produces `f"{prefix}/{entry.name}"` -- also correct.

So the logic works by coincidence because `f"{prefix}{entry.name}"` with empty prefix gives the same result as just `entry.name`. However, the condition reads as the opposite of its intent, making the code confusing and fragile.

**Suggested fix**:
```python
rel = f"{prefix}/{entry.name}" if prefix else entry.name
```

---

### H3: Duplicated `_FakeTraversable` class across test files

**File**: `tests/test_skill_integration.py` lines 17-48
**File**: `tests/test_skill_update.py` lines 52-82

Both files define nearly identical `_FakeTraversable` classes (30+ lines each). This violates DRY and creates a maintenance burden -- any bugfix must be applied in two places.

**Suggested fix**: Extract `_FakeTraversable` (and potentially `_make_traversable`) into `tests/conftest.py` as a shared fixture or helper.

---

## Medium Severity Findings

### M1: Code duplication between `_get_skill_version` and `_get_skill_version_from_traversable`

**File**: `src/insight_blueprint/storage/project.py` lines 90-131 vs 365-392

These two functions share ~80% identical logic (frontmatter regex, version extraction, quote stripping, semver validation). The only difference is:
- `_get_skill_version`: reads from `Path`, logs warnings
- `_get_skill_version_from_traversable`: reads from `Traversable`, silently returns None

**Suggested fix**: Extract a shared `_parse_version_from_content(content: str, source_label: str | None = None) -> str | None` that handles the common parsing. Each function becomes a thin wrapper that reads content and calls the shared parser.

---

### M2: Code duplication between `_hash_skill_directory` and `_hash_skill_directory_from_traversable`

**File**: `src/insight_blueprint/storage/project.py` lines 139-175 vs 395-404

Both compute SHA-256 over file entries with LF normalization. The only difference is how entries are collected (Path.rglob vs Traversable recursion).

**Suggested fix**: Extract a `_hash_entries(entries: list[tuple[str, bytes]]) -> str` function for the common hashing logic.

---

### M3: `_load_skill_state` return type is untyped `dict`

**File**: `src/insight_blueprint/storage/project.py` line 181

```python
def _load_skill_state(skill_dir: Path) -> dict:
```

The return type `dict` lacks key/value type hints. Per coding-principles.md, all functions must have type annotations. Callers access `.get("installed_version")` and `.get("installed_bundled_hash")` without any type safety.

**Suggested fix**:
```python
def _load_skill_state(skill_dir: Path) -> dict[str, str | None]:
```

Or better, define a `TypedDict`:
```python
class SkillState(TypedDict, total=False):
    installed_version: str | None
    installed_bundled_hash: str
    updated_at: str
```

---

### M4: `_copy_skills_template` is 69 lines (function body) -- approaching complexity limit

**File**: `src/insight_blueprint/storage/project.py` lines 294-362

The function handles 6 decision cases in a single body with nested conditionals. While each case is documented, the function could benefit from extracting the per-skill update logic into a separate `_update_single_skill()` function.

**Suggested fix**: Extract the loop body (lines 308-362) into:
```python
def _process_skill_update(
    bundled_src: Traversable,
    dest: Path,
    skill_name: str,
) -> None:
```

---

### M5: `_save_skill_state` and `_write_bundled_update` use lazy imports of `datetime`

**File**: `src/insight_blueprint/storage/project.py` lines 200, 263

```python
def _save_skill_state(...) -> None:
    from datetime import UTC, datetime
```

Lazy imports inside function bodies are typically used to avoid circular imports. `datetime` has no such issue. This is a minor style inconsistency -- all other imports are at module level.

**Suggested fix**: Move `from datetime import UTC, datetime` to the top-level imports section.

---

### M6: `_copy_skills_template` redundant `dest.exists()` check at line 338

**File**: `src/insight_blueprint/storage/project.py` line 338

```python
if not bundled_version and dest.exists():
    continue
```

At this point in the code, `dest.exists()` is always `True` -- the `not dest.exists()` case was already handled at line 317 with a `continue`. The check is redundant and adds confusion.

**Suggested fix**:
```python
if not bundled_version:
    continue  # Legacy: no version on bundled side, dest already exists
```

---

## Low Severity Findings

### L1: Magic string `.insight-blueprint-state.json` partially extracted

**File**: `src/insight_blueprint/storage/project.py` line 178

`_STATE_FILENAME` is correctly extracted as a constant, but `_MANAGED_FILES` at line 135 duplicates the same string:

```python
_MANAGED_FILES = {".insight-blueprint-state.json", ".bundled-update.json"}
```

**Suggested fix**: Use the constant: `_MANAGED_FILES = {_STATE_FILENAME, ".bundled-update.json"}`

But this requires reordering declarations since `_STATE_FILENAME` is defined after `_MANAGED_FILES`. Consider moving `_STATE_FILENAME` before `_MANAGED_FILES`.

---

### L2: `_discover_bundled_skills` catches broad exception types

**File**: `src/insight_blueprint/storage/project.py` lines 82-84

```python
except (AttributeError, TypeError):
    # Traversable may not support / operator for all entries
    continue
```

The comment explains the reason, which is good. However, catching `TypeError` broadly could mask real bugs.

**Suggested fix**: Consider logging at DEBUG level when these exceptions occur, to aid troubleshooting.

---

### L3: Test file `test_skill_update.py` is 737 lines

**File**: `tests/test_skill_update.py`

While test files are allowed to be longer than production code, 737 lines for a single test module is substantial. The file tests 6 different components (`_discover_bundled_skills`, `_get_skill_version`, `_hash_skill_directory`, skill state, `_copy_skill_tree`, `_write_bundled_update`, `_copy_skills_template`).

**Suggested fix**: Consider splitting into focused test modules (e.g., `test_skill_version.py`, `test_skill_hash.py`, `test_skill_copy.py`) or keep as-is if the team prefers a 1:1 mapping with test-design.md test IDs.

---

### L4: SKILL.md files lack `version` field in frontmatter (pre-existing, now relevant)

**File**: `src/insight_blueprint/_skills/analysis-design/SKILL.md` line 3
**File**: `src/insight_blueprint/_skills/catalog-register/SKILL.md` line 3

Both skills now have `version: "1.0.0"` in their frontmatter, which is correct and required for the new update engine. No issue here -- just confirming this was properly added.

---

## File Length Check

| File | Lines | Limit | Status |
|------|-------|-------|--------|
| `src/insight_blueprint/storage/project.py` | 455 | 800 | OK (but 200-400 preferred) |
| `tests/test_skill_update.py` | 737 | - | Acceptable for tests |
| `tests/test_skill_integration.py` | 339 | - | OK |

`project.py` at 455 lines exceeds the preferred 200-400 range but is under the 800 max. The file handles project initialization (existing) plus skill lifecycle management (new). If it grows further, consider extracting skill management into a separate module like `src/insight_blueprint/storage/skill_manager.py`.

---

## Missing Dependency Check

| Package | Used In | Listed in pyproject.toml | Status |
|---------|---------|--------------------------|--------|
| `packaging` | project.py line 14 | NOT listed | **Missing** (H1) |
| `hashlib` | project.py line 1 | stdlib | OK |
| `importlib.resources` | project.py line 3 | stdlib | OK |

---

## Positive Observations

1. **Excellent docstrings**: Every function has a clear docstring explaining purpose and behavior.
2. **Atomic file operations**: `_copy_skill_tree` uses backup-and-restore pattern for crash safety.
3. **Comprehensive error handling**: Graceful degradation with logged warnings (no crashes on permission errors).
4. **Well-structured tests**: Test IDs map to specification, good use of AAA pattern, clear naming.
5. **Idempotent design**: Multiple calls produce consistent results.
6. **Version comparison using `packaging.version`**: Proper semver handling instead of string comparison.
7. **Line ending normalization**: Cross-platform hash determinism.
8. **Good separation of concerns**: Each helper function has a clear single responsibility.

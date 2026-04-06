# SPEC-5: skills-distribution — Test Design

> **Spec ID**: SPEC-5
> **Status**: draft
> **Created**: 2026-02-28
> **Depends On**: None (standalone spec)

---

## Test Architecture

### Test Scope Decision

SPEC-5 has three distinct areas:
1. **Skill Update Engine** (`storage/project.py`) — Python logic with version comparison, hash calculation, file copy. High test value.
2. **Bundled Skills** (`_skills/*.md`) — Static text files. Verified by linting and structure checks.
3. **Package Metadata** (`pyproject.toml`, `LICENSE`, `README.md`) — Static files. Verified by build validation.

**Automated testing focuses on area 1** — the skill update engine. Areas 2 and 3 are verified through build validation and manual checklist.

### Test Pyramid

```
          ┌──────────────────┐
          │  Manual Checklist  │  ← wheel contents, README, SKILL.md review
          ├──────────────────┤
        ┌─┤  Build Validation ├─┐  ← uv build, wheel inspection
        │ ├──────────────────┤ │
      ┌─┴─┤ Integration Tests├─┴─┐  ← init_project() E2E scenarios
      │   ├──────────────────┤   │
  ┌───┴───┤   Unit Tests     ├───┴───┐  ← Per-function tests for update engine
  └───────┴──────────────────┴───────┘
         +
  ┌──────────────────────────┐
  │  Existing Tests (341+)    │  ← Regression: no changes to existing modules
  └──────────────────────────┘
```

### Test File Location

```
tests/
├── conftest.py                  # Add: bundled_skills fixture, mock_skill_dir
├── test_skill_update.py         # NEW: Unit tests for update engine functions
├── test_skill_integration.py    # NEW: Integration tests for init_project() flow
└── test_storage.py              # EXISTING: Ensure no regression
```

---

## Unit Tests — Skill Update Engine

### Test File: `tests/test_skill_update.py`

All helper functions in `storage/project.py` are tested individually.

### 1. `_discover_bundled_skills()`

| # | Test Name | Setup | Expected | Req |
|---|-----------|-------|----------|-----|
| U1 | discover_with_multiple_skills | `_skills/` with 2 dirs each containing `SKILL.md` | Returns `["analysis-design", "catalog-register"]` (sorted) | FR-19 |
| U2 | discover_empty_skills_dir | `_skills/` exists but empty | Returns `[]` | NFR-5 |
| U3 | discover_skips_dir_without_skill_md | `_skills/foo/` with no `SKILL.md` | Excluded from result | FR-19 |
| U4 | discover_skips_files | `_skills/README.md` (file, not dir) | Excluded from result | FR-19 |

### 2. `_get_skill_version()`

| # | Test Name | Setup | Expected | Req |
|---|-----------|-------|----------|-----|
| U5 | version_valid_semver | SKILL.md with `version: "1.2.3"` | Returns `"1.2.3"` | FR-12 |
| U6 | version_missing_field | SKILL.md without `version` | Returns `None` | Error #2 |
| U7 | version_invalid_frontmatter | SKILL.md with broken `---` delimiters | Returns `None` + warning log | Error #4 |
| U8 | version_invalid_semver | SKILL.md with `version: "latest"` | Returns `None` + warning log | Error #6 |
| U9 | version_no_quotes | SKILL.md with `version: 1.0.0` (YAML parses as float) | Returns `"1.0.0"` (coerced to string) | Robustness |

### 3. `_hash_skill_directory()`

| # | Test Name | Setup | Expected | Req |
|---|-----------|-------|----------|-----|
| U10 | hash_deterministic | Same directory contents | Same hash on repeated calls | FR-14 |
| U11 | hash_changes_on_edit | Modify SKILL.md content | Hash changes | FR-14 |
| U12 | hash_excludes_managed_files | Add `.insight-blueprint-state.json` | Hash unchanged with `exclude_managed=True` | Design: Data Models |
| U13 | hash_excludes_bundled_update | Add `.bundled-update.json` and `.bundled-update/` dir | Hash unchanged with `exclude_managed=True` | Design: Data Models |
| U14 | hash_normalizes_line_endings | Same content with LF vs CRLF | Same hash | Design: Interfaces |
| U15 | hash_includes_subdirectory | `references/foo.md` added | Hash changes | Design: Architecture |

### 4. `_load_skill_state()` / `_save_skill_state()`

| # | Test Name | Setup | Expected | Req |
|---|-----------|-------|----------|-----|
| U16 | save_and_load_roundtrip | Save state → load state | All fields match | Design: Data Models |
| U17 | load_missing_state | No `.insight-blueprint-state.json` | Returns empty dict | Error #3 |
| U18 | load_invalid_json | Corrupt JSON in state file | Returns empty dict + warning log | Robustness |
| U19 | save_creates_parent_dirs | `dest/` exists, state file absent | File created successfully | Robustness |

### 5. `_copy_skill_tree()`

| # | Test Name | Setup | Expected | Req |
|---|-----------|-------|----------|-----|
| U20 | copy_single_file | Traversable with `SKILL.md` only | `dest/SKILL.md` exists with same content | FR-16 |
| U21 | copy_with_subdirectory | Traversable with `SKILL.md` + `references/foo.md` | Both files copied | FR-16 |
| U22 | copy_overwrites_existing | Pre-existing `dest/SKILL.md` | Overwritten with new content | FR-13 |
| U23 | copy_atomic_backup_restore | Simulate write failure mid-copy | Original files restored from `.backup` | Error #8 |

### 6. `_write_bundled_update()`

| # | Test Name | Setup | Expected | Req |
|---|-----------|-------|----------|-----|
| U24 | write_creates_json_and_dir | Normal call | `.bundled-update.json` + `.bundled-update/` dir with skill files | FR-15 |
| U25 | write_includes_diff_message | versions "1.0.0" → "1.1.0" | JSON contains `from_version`, `to_version`, diff command | FR-15 |
| U26 | write_permission_error | Read-only `dest_dir` | Exception caught, warning log, no crash | Error #5 |

### 7. `_copy_skills_template()` — Decision Logic

| # | Test Name | Setup | Expected | Req |
|---|-----------|-------|----------|-----|
| U27 | case1_fresh_copy | dest does not exist | Skill copied + state saved | FR-16, AC-3 |
| U28 | case2_same_version_skip | bundled v1.0.0, installed v1.0.0 | No copy, no change | AC-4 |
| U29 | case3_upgrade_unmodified | bundled v1.1.0, installed v1.0.0, hash matches | Skill updated + state updated | AC-1 |
| U30 | case4_upgrade_customized | bundled v1.1.0, installed v1.0.0, hash differs | Skip + warning + `.bundled-update` written | AC-2 |
| U31 | case5_downgrade_skip | bundled v0.9.0, installed v1.0.0 | No copy, no change | Error #7 |
| U32 | case6_no_version_legacy | bundled has no version, dest exists | Skip (legacy behavior) | Error #2 |
| U33 | case7_no_version_fresh | bundled has no version, dest absent | Fresh copy (legacy behavior) | FR-16 |

---

## Integration Tests — init_project() Flow

### Test File: `tests/test_skill_integration.py`

Full lifecycle tests through the public `init_project()` interface.

| # | Test Name | Steps | Expected | Req |
|---|-----------|-------|----------|-----|
| I1 | init_copies_all_bundled_skills | `init_project(tmp)` on empty dir | All skills from `_skills/` appear in `.claude/skills/` | FR-17, FR-19 |
| I2 | init_idempotent_no_change | `init_project(tmp)` twice, no edits between | Second call makes no changes | NFR-2 |
| I3 | init_respects_customization | `init_project()` → edit SKILL.md → bump bundled version → `init_project()` | Edit preserved, `.bundled-update` written | FR-14, FR-15 |
| I4 | init_updates_unmodified_skill | `init_project()` → bump bundled version → `init_project()` | Skill updated to new version | FR-13 |
| I5 | init_performance | `init_project()` with 10 skills | Completes within 500ms | NFR-1 |
| I6 | init_no_regression_dirs | `init_project(tmp)` | `.insight/` dirs still created, `.mcp.json` still registered | Regression |

---

## Build Validation

### Wheel Contents

| # | Check | Command | Expected | Req |
|---|-------|---------|----------|-----|
| B1 | Skills in wheel | `uv build && unzip -l dist/*.whl \| grep _skills` | All `_skills/*/SKILL.md` listed | FR-17 |
| B2 | Static in wheel | `uv build && unzip -l dist/*.whl \| grep static` | `static/index.html` + `static/assets/` listed | FR-18 |
| B3 | LICENSE in wheel | `unzip -l dist/*.whl \| grep LICENSE` | `LICENSE` present | FR-6 |
| B4 | Metadata license | `unzip -p dist/*.whl '*/METADATA' \| grep License` | MIT license listed | FR-5 |
| B5 | Metadata classifiers | `unzip -p dist/*.whl '*/METADATA' \| grep Classifier` | Development Status, License, Python 3.11+ | FR-7 |
| B6 | Metadata urls | `unzip -p dist/*.whl '*/METADATA' \| grep Project-URL` | Homepage, Repository, Bug Tracker | FR-8 |
| B7 | README as description | `unzip -p dist/*.whl '*/METADATA' \| head -50` | Long description from README.md | FR-10 |

### SKILL.md Structure Validation

| # | Check | Command | Expected | Req |
|---|-------|---------|----------|-----|
| B8 | Frontmatter fields | Parse all `_skills/*/SKILL.md` | Each has `name`, `version`, `description` | FR-4, FR-12 |
| B9 | Bilingual description | Grep `description` field | Contains both English and Japanese triggers | FR-2 |
| B10 | Language Rules section | Grep `## Language Rules` | Present in all SKILL.md | FR-3 |
| B11 | Body in English | Manual review | Workflow/rules sections in English | FR-1 |

---

## Manual Verification Checklist

### Pre-condition

- `uv build` succeeds
- Wheel file exists in `dist/`

### Package Metadata

| # | Operation | Steps | Expected | Req |
|---|-----------|-------|----------|-----|
| M1 | LICENSE file | `cat LICENSE` | MIT license with correct copyright holder and year | FR-6, NFR-4 |
| M2 | README readability | Read first 3 sections of README.md | Purpose, install, usage are clear without prior knowledge | FR-9, NFR-7 |
| M3 | No orchestra content | Grep README for `Codex CLI`, `Gemini CLI`, `spec-workflow` | Not found | FR-11 |
| M4 | No secrets | Grep `pyproject.toml`, README, SKILL.md for patterns like `sk-`, `api_key` | Not found | NFR-3 |

### Local Wheel Installation

| # | Operation | Steps | Expected | Req |
|---|-----------|-------|----------|-----|
| M5 | Wheel install | `pip install dist/*.whl` in clean venv | Install succeeds | FR-21 |
| M6 | Skill copy | `insight-blueprint --project /tmp/test` | `.claude/skills/` populated with all bundled skills | FR-17, FR-21 |
| M7 | WebUI launch | Same command as M6 | WebUI accessible on expected port | FR-21 |
| M8 | Skill bilingual trigger | Invoke skill via English phrase, then Japanese phrase | Both discovered | AC 1.1-1.4 |

### Release Procedure

| # | Operation | Steps | Expected | Req |
|---|-----------|-------|----------|-----|
| M9 | Release doc exists | `cat docs/RELEASE.md` | Step-by-step procedure present | FR-20 |
| M10 | Release doc completeness | Read RELEASE.md | Covers version bump, build, verify, local test, upload | FR-20, NFR-8 |

---

## Acceptance Criteria Traceability

### Requirements → Test Mapping

| AC | Test Type | Verification |
|----|-----------|-------------|
| AC 1.1 (EN trigger discovery) | Manual M8 | English phrase triggers skill |
| AC 1.2 (JP trigger discovery) | Manual M8 | Japanese phrase triggers skill |
| AC 1.3 (EN trigger catalog) | Manual M8 | English phrase triggers skill |
| AC 1.4 (JP trigger catalog) | Manual M8 | Japanese phrase triggers skill |
| AC 1.5 (default JP response) | Manual M8 | Responds in Japanese without CLAUDE.md setting |
| AC 1.6 (EN response override) | Manual M8 | Responds in English when configured |
| AC 2.1 (wheel metadata) | Build B4, B5 | License, classifiers present |
| AC 2.2 (PyPI display) | Manual (post-publish) | Out of SPEC-5 scope |
| AC 3.1 (README clarity) | Manual M2 | First 3 sections clear |
| AC 3.2 (wheel long_desc) | Build B7 | README.md in METADATA |
| AC 3.3 (no orchestra) | Manual M3 | No claude-code-orchestra content |
| AC 4.1 (version upgrade unmodified) | **Unit U29** + **Integration I4** | Auto-update works |
| AC 4.2 (version upgrade customized) | **Unit U30** + **Integration I3** | Skip + warning + `.bundled-update` |
| AC 4.3 (fresh copy) | **Unit U27** + **Integration I1** | New skill copied |
| AC 4.4 (same version skip) | **Unit U28** + **Integration I2** | No change |
| AC 5.1 (skills in wheel) | **Build B1** | `_skills/` in wheel |
| AC 5.2 (static in wheel) | **Build B2** | `static/` in wheel |
| AC 5.3 (auto-detect new skills) | **Unit U1** + **Integration I1** | No hardcoded list |
| AC 5.4 (local wheel E2E) | Manual M5, M6, M7 | Install → skills copy → WebUI |
| NFR-1 (performance) | **Integration I5** | 10 skills in 500ms |
| NFR-2 (no perceptible delay) | **Integration I2** | Idempotent call is fast |
| NFR-3 (no secrets) | Manual M4 | No secret patterns |
| NFR-4 (MIT license) | Manual M1 | Standard MIT text |
| NFR-5 (empty skills dir) | **Unit U2** | Returns empty list |
| NFR-6 (empty static dir) | **Build B2** | Build succeeds |
| NFR-7 (README readability) | Manual M2 | Understandable |
| NFR-8 (release doc clarity) | Manual M10 | PyPI beginner can follow |

---

## Regression Strategy

### Existing Tests Impact

SPEC-5 modifies only `storage/project.py` (one function: `_copy_skills_template()`). Other modules are untouched.

**Verification**: After SPEC-5 implementation, run `uv run pytest` and confirm all existing tests pass.

### Specific Regression Risks

| Risk | Mitigation | Verification |
|------|-----------|-------------|
| `init_project()` breaks existing behavior | Integration I6 explicitly checks dirs + `.mcp.json` | Unit + Integration tests |
| New `packaging` import causes import failure | `packaging` is always available via pip/setuptools | Unit test import check |
| `_copy_skills_template()` signature change | Signature unchanged (only internal logic changes) | Existing `tmp_project` fixture continues to work |
| Hardcoded skill list removal | `_discover_bundled_skills()` replaces hardcoded list | Unit U1-U4 |

---

## Security Considerations

| Concern | Mitigation | Verification |
|---------|-----------|-------------|
| Path traversal in skill names | `_discover_bundled_skills()` only reads `_skills/` subdirs via `importlib.resources` | Unit U1-U4 |
| Arbitrary file write via `.bundled-update` | Write only to `.claude/skills/<name>/` under project path | Unit U24-U26 |
| Secret leak in SKILL.md/README | No API keys, passwords, or secrets in distributed files | Manual M4 |
| LICENSE correctness | MIT text verified manually | Manual M1 |

---

## Fixtures and Test Utilities

### New Fixtures (in `conftest.py` or `test_skill_update.py`)

```python
@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    """Create a minimal skill directory with SKILL.md."""
    skill = tmp_path / "test-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: test-skill\nversion: \"1.0.0\"\n"
        "description: Test skill\n---\n# Test Skill\n"
    )
    return skill


@pytest.fixture
def bundled_skills_dir(tmp_path: Path) -> Path:
    """Create a mock _skills/ directory with multiple skills."""
    skills = tmp_path / "_skills"
    for name in ["alpha", "beta"]:
        d = skills / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\nversion: \"1.0.0\"\n"
            f"description: {name} skill\n---\n# {name}\n"
        )
    return skills
```

### Mocking Strategy

- `importlib.resources.files()` — Mock with `unittest.mock.patch` to return controlled `Traversable` objects
- File system — Use `tmp_path` fixture exclusively. No real `_skills/` access in unit tests
- Time — Freeze `datetime.now()` for `updated_at` assertions
- Logging — Use `caplog` fixture to assert warning messages

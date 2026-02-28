# SPEC-5 Codex Design Review — skills-distribution

Date: 2026-02-28
Model: gpt-5.3-codex (read-only sandbox)

## 1. Architectural Risks in Skill Update Mechanism (version + hash)

- Biggest risk: comparing only `SKILL.md` while ignoring sub-files (`references/`, `scripts/`, `assets/`). User edits to sub-files would be missed, causing accidental overwrites.
- Hash target must exclude `.bundled-update` and future management files, otherwise every run detects "customized" and blocks updates permanently.
- Line ending differences (LF/CRLF) and trailing whitespace cause hash mismatches — normalization is required.
- Version comparison alone is insufficient. Same version with different content (rebuild, hotfix re-distribution) would be missed.
- Without storing the "previous bundled hash" at install time, it's impossible to strictly determine whether the user has edited the skill or not.

## 2. importlib.resources for Directory Traversal

- Suitable. `files("insight_blueprint") / "_skills"` with `iterdir()` for auto-discovery is a sound design.
- However, `shutil.copytree(str(src), ...)` implicitly assumes `src` resolves to a real filesystem path, which is importer-implementation-dependent and fragile.
- Recommended: implement recursive copy using the `Traversable` API, or use `as_file` context manager for robustness.

## 3. .bundled-update File Approach Risks

- Multiple updates overwrite the notification file — should include datetime and from/to version info.
- If user manually deletes the file, they lose track of pending updates. CLI warning at startup should be used in tandem.
- Placing the file inside the skill directory conflicts with hash detection — must be explicitly excluded from hash calculation.
- Plain text notification is hard to consume in CI/automation. Recommend machine-readable JSON format (e.g., `.bundled-update.json`).

## 4. Version Comparison Edge Cases

- Legacy skills without `version` field (migration from pre-SPEC-5 installs).
- Malformed version strings (`v1`, `1`, `latest`).
- Pre-release ordering (`1.2.0-beta`).
- Downgrade guard: bundled version is older than installed — must not overwrite.
- "Same version, different content" scenario requires hash as tiebreaker.
- Partial update failure: some files updated, some not — re-run must handle intermediate state.

## 5. Overall Design Recommendations

- Use three decision axes: `version + managed-directory-hash + state`, not version alone.
- Persist state in `.claude/skills/<name>/.insight-blueprint-state.json` with fields: `installed_version`, `installed_bundled_hash`, `updated_at`.
- Update rule: if local hash == previous bundled hash → auto-update. If mismatch → skip + warning + notification file.
- Auto-discovery: target directories under `_skills/` that contain a `SKILL.md` file. Remove hardcoded list.
- Skill update failures during init must not block server startup (warn-only, availability-first).

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Claude Code Plugin distribution format (`.claude-plugin/plugin.json`, `.mcp.json`)
- Plugin validation CI job (`plugin-validate`)
- data-lineage Python package prerequisites check
- Migration guide in README

### Changed

- Skills moved from `src/insight_blueprint/_skills/` to `skills/` (repository root) for Plugin auto-discovery
- Rules (`_rules/`) integrated into SKILL.md definitions
- Extension policy and optional package note added to CLAUDE.md managed section

### Removed

- `upgrade-templates` CLI subcommand
- Skill/rule copy logic from `storage/project.py` (~400 lines)

## [0.4.0] - 2026-03-20

### Added

- `--mode server` for team deployment: serves WebUI + MCP SSE on the same HTTP port
- `--mode headless` for lightweight deployment: MCP SSE only (no WebUI)
- `--host` and `--port` options for server/headless mode (default: 0.0.0.0:4000)
- `--no-browser` flag to suppress browser auto-open in full mode
- Concurrent write safety with `threading.Lock` on `write_yaml`

### Deprecated

- `--headless` flag: use `--no-browser` instead (flag still works with deprecation warning)

## [0.3.0] - 2026-03-17

### Added

- `get_review_comments` MCP tool for reading review batches (closes read/write asymmetry in review workflow)
- `/analysis-revision` skill for structured revision of review comments with per-comment tracking

### Changed

- Added methodology and analysis_intent as reviewable sections in WebUI inline comments

## [0.2.0] - 2026-03-11

### Added

- Analysis Framing skill for structuring analysis scope and approach
- Unified 6-skill chaining: analysis-design → analysis-framing → analysis-journal → analysis-reflection → catalog-register → data-lineage
- `--version` flag for CLI version display

### Changed

- Upgraded shadcn from 4.0.0 to 4.0.2
- Restructured README to prioritize user experience

### CI

- Added Dependabot auto-merge for patch updates

## [0.1.0] - 2026-03-10

### Added

- Analysis Design management with hypothesis-driven workflow
- Data Catalog for domain knowledge and caution registration
- Review workflow with status transitions (draft → reviewing → approved/revised)
- Domain Knowledge suggestion for analysis designs (4 matching strategies)
- Data Lineage tracking for data transformations
- WebUI Dashboard with 2-tab navigation (Designs / Catalog)
- Bundled Skills: analysis-design, analysis-journal, analysis-reflection, catalog-register, data-lineage
- Typed verification models: ExplanatoryVariable, Metric, ChartSpec, Methodology
- YAML direct edit resilience (extra field preservation + corrupt file isolation)
- SQLite FTS5 full-text search index

[unreleased]: https://github.com/etoyama/insight-blueprint/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/etoyama/insight-blueprint/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/etoyama/insight-blueprint/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/etoyama/insight-blueprint/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/etoyama/insight-blueprint/releases/tag/v0.1.0

# insight-blueprint — Product Vision

> **Version**: 1.0.0 (2026-02-18)
> **Status**: Active

## Problem

Data scientists using Claude Code face two friction points in EDA workflows:

1. **Heavy spec-driven development doesn't fit exploratory analysis** — hypotheses
   get rejected and restarting from scratch is costly overhead.
2. **Communicating data access rules and domain knowledge to AI is burdensome**,
   leading to meaningless queries and aggregation errors.

## Vision

A local MCP server + WebUI that enables AI-driven exploratory data analysis by:

- Providing lightweight, hypothesis-driven analysis design docs (not heavy specs)
- Accumulating domain knowledge from analyst review comments for continuous reuse

## Target Users

- Data scientists / data analysts using Claude Code for EDA
- Teams who want to capture and share data domain knowledge

## Distribution

Zero-install: `uvx insight-blueprint --project /path/to/analysis`
Registers as MCP server via `.mcp.json` (project root, git-committable).
OSS (MIT), PyPI package.

---

## Spec Roadmap

The implementation is split into 5 independent specs, each verifiable as a unit.
Each spec builds on the previous. Use `/spec-start` in a new session to implement.

| Spec | Name | Summary | Verifiable Outcome |
|------|------|---------|-------------------|
| **SPEC-1** | core-foundation | CLI entry point, .insight/ init, Pydantic models, YAML storage, basic design MCP tools (create/get/list_designs) | `uvx insight-blueprint --project /path` starts; Claude can call `create_analysis_design()` and read back the YAML |
| **SPEC-2** | data-catalog | Catalog YAML storage, SQLite FTS5 index, 4 catalog MCP tools (search/schema/knowledge/add) | `search_catalog("keyword")` returns results; `get_domain_knowledge()` returns cautions |
| **SPEC-3** | review-workflow | Review comment system, status lifecycle, domain knowledge auto-save, 5 review+context tools (submit/save/extract/get_project_context/suggest_cautions) | Full flow: `submit_for_review()` → review comment saved → knowledge persisted to YAML |
| **SPEC-4** | webui-dashboard | React+Vite frontend, FastAPI backend (15 endpoints), 4-tab dashboard, daemon thread startup | Browser opens at localhost:3000; all 4 tabs (Designs/Catalog/Rules/History) functional |
| **SPEC-5** | skills-distribution | Bundled Skills (English), npm→wheel build pipeline, README, PyPI publishing | `uvx insight-blueprint` installs from PyPI; `/analysis-design` skill appears in `.claude/skills/` |

### Implementation Order

```
SPEC-1 (core-foundation)
  └── SPEC-2 (data-catalog)
        └── SPEC-3 (review-workflow)
              └── SPEC-4 (webui-dashboard)
                    └── SPEC-5 (skills-distribution)
```

### How to Continue in a New Session

1. Check this Spec Roadmap to identify the next SPEC to implement
2. Run `/spec-start` with the spec name (e.g., `/spec-start data-catalog`)
3. Reference `.spec-workflow/specs/SPEC-N/` for requirements and design
4. All previous specs must be complete before starting the next

---

## Key Constraints

- Each spec must pass all tests before the next spec begins
- WebUI (SPEC-4) requires SPEC-1, SPEC-2, SPEC-3 complete
- SPEC-5 requires SPEC-4 complete (frontend build pipeline)
- No external database — YAML files are source of truth, SQLite is derived index
- Single Python process hosts both MCP (stdio) and WebUI (HTTP daemon thread)

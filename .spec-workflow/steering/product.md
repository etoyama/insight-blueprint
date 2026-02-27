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

The implementation is split into 6 specs, each verifiable as a unit.
Each spec builds on the previous. Use `/spec-start` in a new session to implement.

| Spec | Name | Summary | Verifiable Outcome |
|------|------|---------|-------------------|
| **SPEC-1** | core-foundation | CLI entry point, .insight/ init, Pydantic models, YAML storage, basic design MCP tools (create/get/list_designs) | `uvx insight-blueprint --project /path` starts; Claude can call `create_analysis_design()` and read back the YAML |
| **SPEC-2** | data-catalog | Catalog YAML storage, SQLite FTS5 index, 4 catalog MCP tools (search/schema/knowledge/add) | `search_catalog("keyword")` returns results; `get_domain_knowledge()` returns cautions |
| **SPEC-3** | review-workflow | Review comment system, status lifecycle, domain knowledge auto-save, 5 review+context tools (submit/save/extract/get_project_context/suggest_cautions) | Full flow: `submit_for_review()` → review comment saved → knowledge persisted to YAML |
| **SPEC-4a** | webui-backend | Service registry refactor, FastAPI + uvicorn daemon thread, 14 REST endpoints (17 methods), poe build pipeline (hatch artifacts for static/) | `pytest` で全 REST endpoint が TestClient 経由で応答; `uv build` で static/ 込み wheel 生成 |
| **SPEC-4b** | webui-frontend | React 19 + Vite 6 + Tailwind CSS + shadcn/ui, 4-tab dashboard (Designs/Catalog/Rules/History), API integration | Browser opens at localhost; all 4 tabs functional with live data from REST API |
| **SPEC-5** | skills-distribution | Bundled Skills (English), README, PyPI publishing | `uvx insight-blueprint` installs from PyPI; `/analysis-design` skill appears in `.claude/skills/` |

### Implementation Order

```
SPEC-1 (core-foundation)
  └── SPEC-2 (data-catalog)
        └── SPEC-3 (review-workflow)
              └── SPEC-4a (webui-backend)
                    └── SPEC-4b (webui-frontend)
                          └── SPEC-5 (skills-distribution)
```

### SPEC-4a Design Decisions (from design-partner session)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Service wiring | Shared `_registry.py` module | DRY; cli.py wires once, server.py + web.py both consume |
| REST API | 14 URL patterns / 17 methods | Resource-centric; rebuild_index not exposed; extract+save unified |
| Process model | Daemon thread (tech.md) | `start_server()` → daemon → Timer browser open → `mcp.run()` blocks |
| Build pipeline | poe task + hatch artifacts | Dev-only Node.js; wheel includes pre-built static/; zero-install preserved |

### How to Continue in a New Session

1. Check this Spec Roadmap to identify the next SPEC to implement
2. Run `/spec-start` with the spec name (e.g., `/spec-start data-catalog`)
3. Reference `.spec-workflow/specs/SPEC-N/` for requirements and design
4. All previous specs must be complete before starting the next

---

## Key Constraints

- Each spec must pass all tests before the next spec begins
- WebUI backend (SPEC-4a) requires SPEC-1, SPEC-2, SPEC-3 complete
- WebUI frontend (SPEC-4b) requires SPEC-4a complete
- SPEC-5 requires SPEC-4b complete
- No external database — YAML files are source of truth, SQLite is derived index
- Single Python process hosts both MCP (stdio) and WebUI (HTTP daemon thread)

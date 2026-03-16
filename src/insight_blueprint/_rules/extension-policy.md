---
version: "1.0.0"
---

# Extension Policy

## Core Principle

MCP tools and WebUI are considered stable (Fix). Feature extensions are
delivered through bundled skills and skill chaining.

## MCP Layer — Stable CRUD Primitives

- MCP tools provide thin CRUD operations for designs, catalog, reviews, and knowledge
- New MCP tool addition requires strong justification (data integrity, schema enforcement)
- Context efficiency is a first-class constraint: fewer tools = less LLM context consumption
- Current tool count: 17 (server.py). This is the soft cap

## WebUI Layer — Fixed Scope

WebUI responsibilities are strictly limited to:

1. **Design overview** — List and view analysis designs
2. **Review confirmation** — View review comments and batch results
3. **Catalog browsing** — View data sources and domain knowledge

WebUI does NOT handle:
- Analysis workflow orchestration (→ skills)
- Reasoning process tracking (→ skills)
- Method/tool selection guidance (→ skills)

## Skill Layer — Extension Point

All new analysis capabilities are delivered as bundled skills under
`src/insight_blueprint/_skills/`. Skills may:

- Call existing MCP tools as CRUD primitives
- Read/write skill-managed YAML files under `.insight/` (see exceptions in insight-yaml.md)
- Chain to other skills via natural language suggestion
- Maintain their own conventions (event types, file formats) in SKILL.md

## Skill-Managed Data

Skills may directly manage YAML files that are outside MCP's schema scope.
These files must be registered as exceptions in `_rules/insight-yaml.md`.

Current skill-managed files:
- `.insight/designs/*_journal.yaml` — Insight Journal (analysis-journal skill)
- `.insight/designs/*_revision.yaml` — Revision Tracking (analysis-revision skill)

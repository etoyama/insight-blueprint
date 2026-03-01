---
version: "1.0.0"
paths:
  - ".insight/**/*.yaml"
  - ".insight/**/*.yml"
---

# .insight/ YAML File Operation Rules

## MCP-Only Editing

All catalog and design YAML files under `.insight/` MUST be edited through
insight-blueprint MCP tools. Direct file writes are prohibited to maintain
schema integrity and event consistency.

**Allowed MCP tools for editing:**
- `catalog_add_source` / `catalog_update_source` — catalog/sources/*.yaml
- `design_create` / `design_update` — designs/*.yaml
- `knowledge_store` / `knowledge_update` — catalog/knowledge/*.yaml
- `review_add_comment` / `review_submit_batch` — designs/*.yaml (review data)

**Direct read is always OK** — use Read tool or cat freely for analysis.

## Exceptions (Direct Edit Allowed)

These files may be edited directly because they contain user-managed
configuration, not MCP-managed data:

- `.insight/config.yaml` — project configuration
- `.insight/rules/review_rules.yaml` — review rule definitions
- `.insight/rules/analysis_rules.yaml` — analysis rule definitions
- `.insight/rules/extracted_knowledge.yaml` — knowledge seed data

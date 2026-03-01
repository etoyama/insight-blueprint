---
version: "1.0.0"
paths:
  - ".insight/catalog/**"
---

# Data Catalog Operation Rules

## Source Registration

- Use `/catalog-register` skill to register new data sources interactively.
- Each source gets a unique `source_id` and is stored as `.insight/catalog/sources/<source_id>.yaml`.
- Source metadata includes: name, type (csv/api/sql), description, connection info, tags.

## Schema Management

- Schemas are stored within each source YAML under the `schema` field.
- Schema changes should go through `catalog_update_source` MCP tool.
- Breaking schema changes should be noted in the source description.

## Domain Knowledge

- Extracted knowledge is stored in `.insight/catalog/knowledge/` as YAML files.
- Knowledge entries link back to their source via `source_id`.
- Use `knowledge_store` MCP tool to add knowledge entries.
- Knowledge is searchable via `knowledge_search` MCP tool (FTS5-backed).

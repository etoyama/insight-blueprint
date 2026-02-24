# Data Catalog Metadata Patterns Research

Research on how open-source data catalog tools structure source/schema metadata.
Tools surveyed: DataHub, OpenMetadata, Marquez/OpenLineage.

---

## 1. Column-Level Metadata Representation

### OpenMetadata Column Schema

OpenMetadata has the most comprehensive column model (JSON Schema draft-07).

**Required fields:**
- `name` (string, 1-256 chars) - local column identifier
- `dataType` (enum) - 70+ supported types

**Optional fields:**
- `displayName` - human-readable label
- `fullyQualifiedName` - complete qualified name
- `description` - Markdown-supported documentation
- `dataTypeDisplay` - user-friendly representation for complex types
- `dataLength` - character/binary length constraints
- `precision` - total significant digits (numeric)
- `scale` - decimal digits (fractional)
- `constraint` - enum: NULL, NOT_NULL, UNIQUE, PRIMARY_KEY
- `ordinalPosition` - column sequence within table
- `tags` - array of classification tags (PII, GDPR, etc.)
- `jsonSchema` - embedded schema for JSON columns
- `children` - nested columns for STRUCT/MAP/UNION types

**Profile/Statistics (separate `profile` object):**
- valuesCount, nullCount, uniqueCount
- min, max, mean, median, stddev
- Distribution histograms

**Example (JSON):**
```json
{
  "name": "customer_id",
  "dataType": "INT",
  "constraint": "PRIMARY_KEY",
  "description": "Unique identifier for the customer",
  "ordinalPosition": 1,
  "tags": [{"tagFQN": "PII.NonSensitive"}],
  "profile": {
    "valuesCount": 150000,
    "nullCount": 0,
    "uniqueCount": 150000,
    "min": 1,
    "max": 150000
  }
}
```

### DataHub SchemaField

DataHub uses Pegasus (PDL) schema language, mapped to JSON.

**Key fields:**
- `fieldPath` - flattened field identifier (e.g., `address.zipcode`)
- `dataType` - enum: Boolean, String, Number, Date, etc.
- `nullable` - boolean
- `description` - field documentation
- `created` / `lastModified` - audit timestamps

**Field path formats:**
- v1: Simple dot notation: `address.zipcode`
- v2: Typed notation: `[version=2.0].[type=struct].address.[type=string].zipcode`

**Metadata separation:**
- `schemaMetadata` aspect - source system metadata (immutable from source)
- `editableSchemaMetadata` aspect - user edits via UI (independent layer)

**Example (conceptual JSON):**
```json
{
  "schemaName": "CustomerEvent",
  "platform": "urn:li:platform:mysql",
  "version": 3,
  "hash": "a1b2c3d4e5f6...",
  "fields": [
    {
      "fieldPath": "customer_id",
      "dataType": "NUMBER",
      "nullable": false,
      "description": "Unique customer identifier"
    },
    {
      "fieldPath": "address.zipcode",
      "dataType": "STRING",
      "nullable": true,
      "description": "Customer ZIP code"
    }
  ],
  "primaryKeys": ["customer_id"]
}
```

### OpenLineage SchemaDatasetFacet

OpenLineage (used by Marquez) has a minimal, lineage-focused schema model.

**Field properties:**
- `name` - field identifier
- `type` - data type (int, string, boolean, array, struct, map, union)
- `description` - optional documentation
- `fields` - nested array for complex types

**Complex type conventions:**
- Array: `_element` naming for array items
- Struct: named nested fields
- Map: `key` and `value` sub-fields
- Union: numbered naming (`_0`, `_1`, etc.)

**Example (JSON):**
```json
{
  "_producer": "https://my-producer.example",
  "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/SchemaDatasetFacet.json",
  "fields": [
    {
      "name": "customer_id",
      "type": "int",
      "description": "Unique customer identifier"
    },
    {
      "name": "address",
      "type": "struct",
      "description": "Customer address",
      "fields": [
        {"name": "street", "type": "string"},
        {"name": "zipcode", "type": "string"}
      ]
    }
  ]
}
```

---

## 2. Common Fields Across All Tools

| Field | OpenMetadata | DataHub | OpenLineage | Notes |
|-------|-------------|---------|-------------|-------|
| name | `name` | `fieldPath` | `name` | Universal |
| type | `dataType` (enum 70+) | `dataType` (enum) | `type` (string) | Enum vs free-text |
| description | `description` | `description` | `description` | Universal |
| nullable | `constraint` (NOT_NULL) | `nullable` (bool) | - | Approach varies |
| nested fields | `children` | nested fieldPath | `fields` | Universal for structs |
| position | `ordinalPosition` | implicit in array | - | Not always present |
| statistics | `profile` object | separate aspect | - | Optional enrichment |
| tags | `tags` array | separate aspect | - | Classification layer |

**Core universal fields: name, type, description, nested children.**

---

## 3. Data Source Connection Configuration

### DataHub Recipe Pattern (YAML)

DataHub uses "recipes" - YAML files with source + sink + optional transformers.

```yaml
# recipe.yml
source:
  type: mysql               # connector type
  config:
    username: root
    password: ${MYSQL_PASSWORD}    # env var expansion
    host_port: localhost:3306
    database: mydb

sink:
  type: "datahub-rest"
  config:
    server: "https://datahub.example.com/gms"
    token: ${DATAHUB_TOKEN}

transformers:
  - type: "simple_add_dataset_tags"
    config:
      tag_urns:
        - "urn:li:tag:production"
```

**Key patterns:**
- One recipe per source system
- Environment variable expansion for secrets (`${VAR_NAME}`)
- Source type determines required config fields
- Transformers as middleware pipeline

### OpenMetadata Connection Configuration (YAML)

```yaml
source:
  type: Mysql
  serviceName: local_mysql
  serviceConnection:
    config:
      type: Mysql
      username: openmetadata_user
      authType:
        password: ${MYSQL_PASSWORD}
      hostPort: localhost:3306
      databaseSchema: mydb

sink:
  type: metadata-rest
  config:
    api_endpoint: http://localhost:8585/api

workflowConfig:
  openMetadataServerConfig:
    hostPort: http://localhost:8585/api
    authProvider: openmetadata
    securityConfig:
      jwtToken: ${OM_JWT_TOKEN}
```

**Key patterns:**
- Service-oriented: each connection is a "service"
- Nested `serviceConnection.config` block
- Auth separated from connection config
- Workflow-level server configuration

### Marquez/OpenLineage

Marquez does not use a recipe pattern. Instead, metadata arrives via OpenLineage events (push model), where producers emit run events containing dataset facets. Connection info is implicit in namespace/name URIs.

---

## 4. Schema Versioning Approaches

### OpenMetadata: Semantic Versioning (major.minor)

- Initial version: `0.1`
- **Minor version** (+0.1): backward-compatible changes
  - Description updates, tag additions, ownership changes
  - Example: 0.1 -> 0.2
- **Major version** (+1.0): backward-incompatible changes
  - Column deletion, type changes
  - Example: 0.2 -> 1.2
- Full version history maintained and browsable in UI

### DataHub: Numeric Versioned Aspects

- Each aspect has a numeric version
- New version created automatically on any field change
- `hash` field (SHA1) enables change detection without full comparison
- Version stored server-side, not in recipe

### OpenLineage: Facet Replacement

- No explicit versioning
- New facet emission replaces previous facet entirely
- Versioning is implicit through run event timeline
- Schema URL tracks facet specification version (not data version)

---

## 5. Handling Different Source Types

### Databases (SQL)
All three tools have strong support:
- Automatic schema extraction from information_schema
- Column types mapped to internal type enums
- Constraints (PK, FK, NOT NULL) captured
- DataHub/OpenMetadata: dedicated connectors per DB vendor

### Files (CSV, Parquet, etc.)
- **OpenMetadata**: `StorageService` with `containerMetadataConfig`
  - Can define schema via JSON config file alongside the data
  - Supports S3, GCS, ADLS as storage services
- **DataHub**: File-based sources with schema inference
- **OpenLineage**: Schema facet attached to dataset regardless of source type

### APIs
- **OpenMetadata**: `Pipeline` and `API Service` entity types
  - API endpoints modeled as services with their own schemas
- **DataHub**: Custom sources can be written for any API
- **OpenLineage**: API inputs/outputs modeled as datasets with schema facets

### Key insight: All tools abstract different sources into a common dataset/table model with a unified column schema representation. The source-specific details live in the connection configuration, not in the schema model itself.

---

## 6. Recommendations for Lightweight YAML-Based Catalog

Based on patterns observed across all three tools:

### Column Schema (keep it simple, extensible)

```yaml
columns:
  - name: customer_id
    type: integer
    description: "Unique customer identifier"
    nullable: false
    primary_key: true
    tags: [pii]

  - name: email
    type: string
    description: "Customer email address"
    nullable: false
    tags: [pii, sensitive]

  - name: address
    type: struct
    description: "Customer mailing address"
    children:
      - name: street
        type: string
      - name: zipcode
        type: string
        nullable: false

  - name: created_at
    type: timestamp
    description: "Account creation timestamp"
    nullable: false
```

### Source Connection Config

```yaml
sources:
  - id: sales_db
    type: postgresql
    config:
      host: ${DB_HOST}
      port: 5432
      database: sales
      schema: public

  - id: customer_csv
    type: csv
    config:
      path: "data/customers.csv"
      encoding: utf-8
      delimiter: ","

  - id: weather_api
    type: api
    config:
      base_url: "https://api.weather.example.com/v1"
      auth_type: api_key
      auth_key_env: WEATHER_API_KEY
```

### Design Principles (derived from research)

1. **Universal core fields**: name, type, description, nullable - present in all tools
2. **Type as string, not enum**: Use free-text types (like OpenLineage) for flexibility; validate via a known-types list rather than strict enum
3. **Nested children for complex types**: All tools support struct/array/map nesting
4. **Separate connection from schema**: Source config is independent of column definitions
5. **Environment variable expansion**: All tools support `${VAR}` for secrets
6. **Facet/aspect pattern for extensibility**: Add optional metadata blocks (statistics, lineage, tags) without changing core schema
7. **Semantic versioning for schema changes**: OpenMetadata's major.minor approach is most practical for YAML files

---

## Sources

- [DataHub Metadata Model](https://docs.datahub.com/docs/metadata-modeling/metadata-model)
- [DataHub Dataset Entity](https://docs.datahub.com/docs/generated/metamodel/entities/dataset)
- [DataHub CLI Ingestion](https://docs.datahub.com/docs/metadata-ingestion/cli-ingestion)
- [OpenMetadata Column Standard](https://openmetadatastandards.org/data-assets/databases/column/)
- [OpenMetadata Metadata Standard](https://docs.open-metadata.org/latest/main-concepts/metadata-standard)
- [OpenMetadata Versioning](https://docs.open-metadata.org/latest/how-to-guides/guide-for-data-users/versions)
- [OpenLineage Schema Facet](https://openlineage.io/docs/spec/facets/dataset-facets/schema/)
- [OpenLineage Specification](https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md)
- [Marquez Project](https://marquezproject.ai/)

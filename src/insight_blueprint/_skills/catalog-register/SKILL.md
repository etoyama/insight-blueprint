---
name: catalog-register
version: "1.1.0"
description: |
  Guides Claude through discovering data source schemas and registering them
  in the insight-blueprint data catalog. Supports CSV, API, and SQL sources.
  Triggers: "register data source", "add to catalog", "catalog register",
  "データカタログ登録", "ソース登録", "カタログにデータを追加".
disable-model-invocation: true
argument-hint: "[source_type: csv|api|sql]"
---

# /catalog-register — Data Source Registration

Guides Claude through exploring a data source's structure and registering it
in the insight-blueprint catalog via MCP tools.

## When to Use
- User wants to register a new data source (CSV file, API endpoint, SQL table)
- User wants to catalog an existing dataset with schema information
- User mentions "データカタログ", "ソース登録", or "register"

## When NOT to Use
- Updating an existing source (use `update_catalog_entry` directly)
- Searching the catalog (use `search_catalog` directly)
- Managing domain knowledge (future SPEC-3 scope)

## Workflow

### Step 1: Determine Source Type

Ask the user which type of data source to register:
- **CSV** — Local file with headers
- **API** — REST API endpoint (e.g., e-Stat, custom API)
- **SQL** — Database table (e.g., BigQuery, PostgreSQL)

If `$ARGUMENTS` is provided, use it as the source type.

### Step 2: Explore Data Structure

Follow the appropriate exploration workflow below.

### Step 3: Build Registration

Construct the `add_catalog_entry` call with discovered schema.

### Step 4: Register and Confirm

Call `add_catalog_entry` and show the result to the user.

---

## CSV Source Workflow

### Step 2a: Read File Headers

1. Ask the user for the CSV file path
2. Read the first 5 rows to discover columns:
   ```
   Read the file with limit=5 to see headers and sample data
   ```
3. For each column, infer:
   - **name**: Header name
   - **type**: Infer from sample values (string, integer, float, date, boolean)
   - **description**: Ask user or infer from column name
   - **nullable**: Check if any sample values are empty
   - **examples**: First 2-3 non-empty values

### Step 2b: Gather Metadata

Ask the user for:
- **source_id**: A short slug (e.g., `local-survey-2024`)
- **name**: Human-readable name
- **description**: What this dataset contains

### Step 3a: Build Call

```
add_catalog_entry(
    source_id="local-survey-2024",
    name="Local Survey 2024",
    type="csv",
    description="Annual community survey results",
    connection={
        "file_path": "data/survey_2024.csv",
        "encoding": "utf-8",
        "delimiter": ","
    },
    columns=[
        {"name": "respondent_id", "type": "integer", "description": "Unique respondent ID"},
        {"name": "age", "type": "integer", "description": "Respondent age", "range": {"min": 18, "max": 99}},
        ...
    ],
    tags=["survey", "local"],
)
```

---

## API Source Workflow

### Step 2a: Identify API Structure

1. Ask the user for the API base URL and provider
2. For **e-Stat** APIs:
   - Use `getMetaInfo` endpoint to discover table structure:
     ```
     GET {base_url}/app/json/getMetaInfo?appId=$API_KEY&statsDataId={table_id}
     ```
   - **Security**: API keys must come from environment variables. Never hardcode keys in YAML or catalog entries.
   - Parse CLASS_INF to extract column definitions
3. For **custom APIs**:
   - Ask the user for a sample endpoint
   - Fetch the response (or ask user to paste a sample)
   - Analyze JSON structure to extract field names and types

### Step 2b: Gather Metadata

Ask the user for:
- **source_id**: A short slug (e.g., `estat-population`)
- **name**: Human-readable name
- **description**: What this data provides
- **auth**: Authentication method (`none`, `api_key`, `oauth`)

### Step 3a: Build Call

```
add_catalog_entry(
    source_id="estat-population",
    name="e-Stat Population Census",
    type="api",
    description="Japanese population statistics from e-Stat",
    connection={
        "base_url": "https://api.e-stat.go.jp/rest/3.0",
        "provider": "e-stat",
        "table_id": "0003348423",
        "auth": "api_key"
    },
    columns=[
        {"name": "prefecture_code", "type": "string", "description": "JIS X 0401 code (01-47)",
         "nullable": false, "examples": ["01", "13", "47"]},
        {"name": "year", "type": "integer", "description": "Census year",
         "range": {"min": 2000, "max": 2024}},
        {"name": "population", "type": "integer", "description": "Total population",
         "unit": "people"},
    ],
    tags=["government", "population", "demographics"],
    primary_key=["prefecture_code", "year"],
    row_count_estimate=2350,
)
```

---

## SQL Source Workflow

### Step 2a: Query Schema Metadata

1. Ask the user for connection details (provider, project/database, table)
2. For **BigQuery**:
   ```sql
   SELECT column_name, data_type, is_nullable, description
   FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
   WHERE table_name = '{table}'
   ORDER BY ordinal_position
   ```
3. For **PostgreSQL/MySQL**:
   ```sql
   SELECT column_name, data_type, is_nullable,
          col_description(c.oid, a.attnum) as description
   FROM information_schema.columns
   WHERE table_name = '{table}'
   ORDER BY ordinal_position
   ```
4. Ask the user to run the query and paste results, or run it if credentials are available

### Step 2b: Gather Metadata

Ask the user for:
- **source_id**: A short slug (e.g., `bq-sales-data`)
- **name**: Human-readable name
- **description**: What this table contains

### Step 3a: Build Call

```
add_catalog_entry(
    source_id="bq-sales-data",
    name="BigQuery Sales Data",
    type="sql",
    description="Daily sales transaction data from BigQuery",
    connection={
        "provider": "bigquery",
        "project_id": "my-gcp-project",
        "dataset": "analytics",
        "table": "daily_sales"
    },
    columns=[
        {"name": "sale_date", "type": "date", "description": "Transaction date"},
        {"name": "product_id", "type": "string", "description": "Product identifier"},
        {"name": "amount", "type": "float", "description": "Sale amount", "unit": "JPY"},
        {"name": "quantity", "type": "integer", "description": "Units sold"},
    ],
    tags=["sales", "bigquery"],
    primary_key=["sale_date", "product_id"],
    row_count_estimate=500000,
)
```

---

## MCP Tool Reference

| Tool | Purpose |
|------|---------|
| `add_catalog_entry(...)` | Register a new data source |
| `get_table_schema(source_id)` | Verify registered schema |
| `search_catalog(query)` | Confirm source is searchable |

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| `"Source 'X' already exists"` | Duplicate source_id | Use `update_catalog_entry` or choose a different ID |
| `"Invalid source type 'parquet'"` | Unsupported type | Use csv, api, or sql |

## Chaining

| From | To | When |
|------|-----|------|
| /analysis-framing | → /catalog-register | Data missing: "必要なデータを登録するなら /catalog-register" |
| /analysis-reflection | → /catalog-register | Register conclusion as knowledge |
| /catalog-register | → /analysis-framing | Registration complete, return to framing: "フレーミングに戻るなら /analysis-framing" |
| /catalog-register | → /analysis-design | Registration complete, continue design: "デザイン作成を続けるなら /analysis-design" |

## Language Rules
- Follow project CLAUDE.md language settings. Default to Japanese if no setting.
- Code, IDs, tool names, and YAML fields always stay in English.
- Descriptions can be in the user's preferred language

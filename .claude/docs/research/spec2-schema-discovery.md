# Schema Discovery Research: BigQuery & e-Stat API

Source: Gemini CLI research (2026-02-24)

## 1. BigQuery INFORMATION_SCHEMA Patterns

### List Tables
To get a list of all tables in a specific dataset:

```sql
SELECT
  table_name,
  table_type,
  creation_time
FROM
  `project_id.dataset_id.INFORMATION_SCHEMA.TABLES`
ORDER BY
  table_name;
```

### Get Column Metadata
To retrieve column names, data types, and descriptions for a specific table:

```sql
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable,
  column_description
FROM
  `project_id.dataset_id.INFORMATION_SCHEMA.COLUMNS`
WHERE
  table_name = 'your_table_name'
ORDER BY
  ordinal_position;
```

**Key Fields:**
- `table_catalog`: Project ID
- `table_schema`: Dataset ID
- `column_description`: The description string (if one was set).

---

## 2. e-Stat API `getMetaInfo` Endpoint

### Endpoint Details
- **Method:** GET
- **Base URL:** `http://api.e-stat.go.jp/rest/3.0/app/json/getMetaInfo`
- **Required Parameters:**
  - `appId`: Your application ID.
  - `statsDataId`: The ID of the statistical data (e.g., `0000030001`).

### Example Request
```bash
curl "http://api.e-stat.go.jp/rest/3.0/app/json/getMetaInfo?appId=YOUR_APP_ID&statsDataId=0003448228"
```

### JSON Response Structure (Table Class Information)
The metadata about the table structure (headers, categories) is found under `METADATA_INF` -> `CLASS_INF`.

```json
{
  "GET_META_INFO": {
    "METADATA_INF": {
      "TABLE_INF": {
        "@id": "0003448228",
        "STATISTICS_NAME": "National Census",
        "TITLE": "Population by Age and Region"
      },
      "CLASS_INF": {
        "CLASS_OBJ": [
          {
            "@id": "cat01",
            "@name": "Age Group",
            "CLASS": [
              {
                "@code": "001",
                "@name": "Total",
                "@level": "1"
              },
              {
                "@code": "002",
                "@name": "0-4 years",
                "@level": "2"
              }
            ]
          },
          {
            "@id": "area",
            "@name": "Region",
            "CLASS": [
              {
                "@code": "00000",
                "@name": "Japan",
                "@level": "1"
              }
            ]
          }
        ]
      }
    },
    "RESULT": {
      "STATUS": 0,
      "ERROR_MSG": "Normal termination"
    }
  }
}
```

**Key Fields in `CLASS_OBJ`:**
- `@id`: The identifier for the classification (e.g., `cat01` for a category, `area` for regions, `time` for time periods).
- `@name`: The human-readable name of the classification.
- `CLASS`: Array of individual items within this classification.
  - `@code`: The code used in the data rows.
  - `@name`: The display label for the code.

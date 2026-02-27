# insight-blueprint Architecture Design Document

> **Version**: 1.1.0 (2026-02-18)
> **Status**: Draft (Updated with Researcher findings)
> **Authors**: Architect Agent, Researcher Agent

## 1. Overview

insight-blueprint is a local MCP server + React WebUI for data scientists using Claude Code. It provides structured analysis design management, a data catalog with domain knowledge, and a review/approval workflow for analysis designs.

### 1.1 Goals

- Provide MCP tools to Claude Code for managing analysis designs, data catalogs, and domain knowledge
- WebUI dashboard for reviewing/approving analysis designs
- Bundle Claude Code Skills into `.claude/skills/` on first run
- Store project data in `.insight/` directory (YAML/SQLite)
- Open source (MIT license)

### 1.2 User Workflow

```
uvx insight-blueprint --project /path/to/analysis
      |
      +-- Starts MCP server (stdio) for Claude Code
      +-- Starts WebUI server (http://localhost:3000)
      +-- Initializes .insight/ directory if needed
      +-- Copies .claude/skills/ templates on first run
```

---

## 2. System Architecture

### 2.1 Component Diagram

```
                    Claude Code (AI Client)
                         |
                    stdio (MCP Protocol)
                         |
               +--------------------+
               |  insight-blueprint |
               |  (Python Process)  |
               |                    |
               |  +--------------+  |         Browser
               |  | MCP Server   |  |            |
               |  | (FastMCP)    |  |      http://localhost:3000
               |  +--------------+  |            |
               |         |          |  +------------------+
               |  +--------------+  |  | FastAPI Server   |
               |  | Core Engine  |  |  | (WebUI Backend)  |
               |  | (Services)   |  |  +------------------+
               |  +--------------+  |            |
               |         |          |  +------------------+
               |  +--------------+  |  | Static Files     |
               |  | Storage      |  |  | (React+Vite)     |
               |  | (YAML+SQLite)|  |  +------------------+
               |  +--------------+  |
               +--------------------+
                         |
                    .insight/ directory
```

### 2.2 Process Architecture

A single `uvx insight-blueprint` command starts two servers in one process:

1. **MCP Server** (stdio transport) - Communicates with Claude Code via stdin/stdout. **Blocks main thread** via `mcp.run()`.
2. **FastAPI Server** (HTTP) - Serves WebUI on a **background daemon thread** (uvicorn). Uses dynamic port via `socket.bind(('', 0))` with fallback to config port.

```python
# Simplified startup flow
def main():
    project = init_project(args.project)       # Step 1-4: init .insight/, skills
    rebuild_fts_index(project)                  # Step 5: SQLite FTS
    port = start_webui_background(project)      # Step 6: threading.Thread(daemon=True)
    open_browser_delayed(port)                  # Step 7: 1.5s delay, webbrowser.open
    mcp.run()                                   # Step 8: BLOCKS — stdio MCP protocol
```

Key design decision: **stdio for MCP** (not SSE/HTTP) because:
- Claude Code's `claude mcp add` expects stdio transport
- No network configuration needed
- Simplest integration for local development
- SSE/Streamable HTTP reserved for future remote deployment

**Threading constraint**: `mcp.run()` takes over stdin/stdout, so the FastAPI server MUST run on a separate thread. Both servers share the same `core/` service layer and storage. For v1 (single-user), no locking is needed — atomic writes (temp file + `os.replace()`) prevent corruption.

### 2.3 Package Structure

```
insight-blueprint/
├── src/insight_blueprint/
│   ├── __init__.py
│   ├── __main__.py         # python -m insight_blueprint
│   ├── cli.py              # Entry point: uvx insight-blueprint
│   ├── server.py           # MCP server (mcp.server.fastmcp.FastMCP)
│   ├── web.py              # FastAPI app for WebUI backend
│   ├── core/               # Business logic (shared by MCP + API)
│   │   ├── __init__.py
│   │   ├── designs.py      # Analysis design management
│   │   ├── catalog.py      # Data catalog operations
│   │   ├── rules.py        # Rules and domain knowledge
│   │   └── reviews.py      # Review workflow
│   ├── models/             # Pydantic models (shared types)
│   │   ├── __init__.py
│   │   ├── design.py       # AnalysisDesign, DesignStatus, etc.
│   │   ├── catalog.py      # DataSource, ColumnSchema, etc.
│   │   ├── rules.py        # Rule, ReviewPerspective, etc.
│   │   └── common.py       # Shared types (ID, Timestamp, etc.)
│   ├── storage/            # Persistence layer
│   │   ├── __init__.py
│   │   ├── yaml_store.py   # YAML read/write (ruamel.yaml for analyst files)
│   │   ├── sqlite_store.py # SQLite FTS5 for catalog search (auto-generated)
│   │   └── project.py      # .insight/ directory management + first-run init
│   ├── _skills/            # Claude Code skill templates (bundled in wheel)
│   │   ├── analysis-design/
│   │   │   └── SKILL.md
│   │   └── data-explorer/
│   │       └── SKILL.md
│   └── static/             # Pre-built React frontend (bundled in wheel via artifacts)
│       └── index.html      # + JS/CSS assets from Vite build
├── frontend/               # React+Vite source (development only, not in wheel)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── DesignsPage.tsx
│   │   │   ├── CatalogPage.tsx
│   │   │   ├── RulesPage.tsx
│   │   │   └── HistoryPage.tsx
│   │   └── components/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── tests/
│   ├── test_designs.py
│   ├── test_catalog.py
│   ├── test_rules.py
│   └── test_storage.py
├── pyproject.toml
└── README.md
```

### 2.4 Entry Point Configuration

```toml
# pyproject.toml
[project]
name = "insight-blueprint"
version = "0.1.0"
description = "MCP server + WebUI for data science analysis design management"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.8",            # Official Anthropic MCP SDK (includes basic FastMCP)
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "pydantic>=2.10",
    "ruamel.yaml>=0.18",   # Preserves comments in analyst-authored YAML files
    "python-frontmatter>=1.1",  # Markdown + YAML frontmatter parsing
    "click>=8.1",
]

[project.scripts]
insight-blueprint = "insight_blueprint.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/insight_blueprint"]
# CRITICAL: Include git-ignored build artifacts (React frontend) in the wheel
artifacts = [
    "src/insight_blueprint/static/**/*",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.8",
    "ty>=0.1",
    "poethepoet>=0.31",
    "httpx>=0.27",
]

[tool.poe.tasks]
build-frontend = "bash -c 'cd frontend && npm install && npm run build'"
build = ["build-frontend"]
```

> **MCP SDK Decision**: Use the official `mcp` package's built-in `mcp.server.fastmcp.FastMCP`.
> If DX proves insufficient (no Pydantic auto-schema, no Inspector), upgrade to standalone
> `fastmcp` package (`uv add fastmcp`) which provides superior tooling. Both share the same
> decorator API, so migration is a one-line import change.

> **Path Resolution**: Use `importlib.resources.files("insight_blueprint")` for accessing
> bundled `_skills/` and `static/` directories. This works correctly for both editable installs
> and wheel installations.

### 2.5 Claude Code Integration

Two registration approaches — **project-scoped `.mcp.json` is recommended** (committable to git):

```bash
# Recommended: project-scoped (creates committable .mcp.json at project root)
claude mcp add --scope project insight-blueprint -- uvx insight-blueprint --project $(pwd)

# Alternative: user-scoped (writes to ~/.claude/settings.json, not committed)
claude mcp add insight-blueprint -- uvx insight-blueprint --project $(pwd)
```

**`.mcp.json` format** (project root — commit this file to share MCP config with team):
```json
{
  "mcpServers": {
    "insight-blueprint": {
      "command": "uvx",
      "args": ["insight-blueprint", "--project", "/path/to/analysis"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_TIMEOUT": "10000"
      }
    }
  }
}
```

> **Gotchas**:
> - `claude mcp add` option ordering: ALL flags (`--scope`, `--env`) MUST come BEFORE `<name>`, then `--` before the command
> - First run is slow (uvx downloads package) → `MCP_TIMEOUT=10000` prevents timeout
> - Project-scoped `.mcp.json` requires **user approval on first use** (by design, for security)
> - `PYTHONUNBUFFERED=1` ensures stdio MCP messages are flushed immediately

---

## 3. Data Models

### 3.1 Analysis Design Document (Extended Hypothesis YAML)

Design principle: **extend the existing open-data-analysis hypothesis YAML, not replace it.**
The base format (`hypothesis`, `metrics`, `explanatory`, `chart`, `next_action`) is preserved as-is.
insight-blueprint adds only `domain_references`, `reviews`, and `results` at the bottom.

**Status lifecycle**: `draft` → `active` → `supported` | `rejected` | `inconclusive`
(Intentionally simpler than a formal spec workflow — EDA requires rapid iteration.)

```yaml
# .insight/designs/H01_crime_rate_correlation.yaml
id: H01
parent: null    # Parent hypothesis ID for derived hypotheses (e.g., H01a -> parent: H01)
status: active  # draft | active | supported | rejected | inconclusive

# 1. Hypothesis (free-form, analyst-authored)
hypothesis:
  statement: "外国人人口比率が高い都道府県ほど犯罪発生率が高い、という関係は観察されない"
  background: |
    「外国人が増えると治安が悪化する」という言説は広く流布しているが、
    日本全体の刑法犯認知件数は2002年をピークに一貫して減少している一方、
    在留外国人数は増加を続けている。都道府県別のクロスセクション分析で
    外国人比率と犯罪率の間に正の相関が見られるかを検証する。

# 2. Metrics (data source references — e-Stat table ID or catalog source_id)
metrics:
  target: "crime_rate_per_100k"
  data_source:
    crime: "0000010111"       # e-Stat table ID, or catalog source_id
    population: "0000010101"
  grouping: "prefecture"
  filter: "2020年度（在留外国人数と犯罪統計が揃う最新年次）"
  aggregation: "ratio (認知件数 / 人口 * 100,000)"
  comparison: "都道府県クロスセクション相関（散布図 + OLS回帰 + Pearson / Spearman 相関係数）"

# 2b. Explanatory variables
explanatory:
  target: "foreign_population_ratio"
  data_source: "0000010101"  # A人口 → A3200（在留外国人数）/ A1101（総人口）
  aggregation: "ratio (在留外国人数 / 総人口 * 100)"

# 3. Chart spec
chart:
  type: scatter
  x: "foreign_population_ratio（外国人人口比率 %）"
  y: "crime_rate_per_100k（刑法犯認知件数率 人口10万人あたり）"
  color: "region（地方区分: 北海道・東北・関東...）"
  facet: ""
  notes: |
    - OLS回帰直線を重ねて描画
    - 相関係数(r)とp値をチャート上に表示
    - 各点に都道府県名のラベルを付与

# 4. Next action — EDA branching (critical: hypothesis rejection drives next analysis)
next_action:
  if_supported: |
    正の相関が見られた場合、交絡要因の検討へ進む。
    - 都市化率（DID人口比率）をコントロール変数に追加
    - H01a: 重回帰分析で偏回帰係数を確認
  if_rejected:
    reason: |
      有意な正の相関が観察されたが、都市化率（DID人口比率）が交絡変数として
      見せかけの相関を生んでいる可能性が高い。
    pivot: |
      交絡変数の統制と時系列分析で追加検証:
      - H01a: 都市化率統制後の重回帰分析
      - H01b: 年齢構成統制後の重回帰分析
      - H01c: 経年×地域トレンド分析

# --- insight-blueprint extensions (added below existing format) ---

# 5. Domain knowledge references (links to entries in .insight/catalog/knowledge/)
domain_references:
  - source_id: "estat-crime-stats"
    knowledge_keys: ["category_changes_2018", "cognition_vs_arrest_distinction"]
  - source_id: "estat-population"
    knowledge_keys: ["foreign_residents_definition"]

# 6. Review thread (lightweight — analyst comments during review via WebUI)
reviews:
  - id: REV-001
    reviewer: analyst
    timestamp: "2026-02-18T13:00:00+09:00"
    status: comment  # comment | approve | reject
    comment: |
      都市化率（DID人口比率）が交絡変数になっている可能性がある。
      H01aで統制変数を追加して再検証すること。
    domain_knowledge:  # Optional: attach new domain knowledge discovered during review
      key: "urbanization_spurious_correlation_risk"
      content: |
        都市部ほど外国人比率・犯罪率ともに高い傾向があり、
        都市化度が見せかけの相関を生む交絡変数になりうる。
      source: "Reviewer's domain expertise"
  - id: REV-002
    reviewer: claude
    timestamp: "2026-02-18T14:30:00+09:00"
    status: approve
    comment: "都市化率の交絡について domain_references に knowledge を追加しました。H01a を派生仮説として作成します。"

# 7. Results (populated after analysis completes)
results:
  outcome: null  # supported | rejected | inconclusive
  summary: null
  artifacts: []  # relative paths to notebooks, charts, reports

# Metadata
created_by: claude
created_at: "2026-02-18"
updated_at: "2026-02-18"
```

### 3.2 Data Catalog Schema

```yaml
# .insight/catalog/sources.yaml
sources:
  - id: "estat-income-by-prefecture"
    name: "Household Income Survey by Prefecture"
    type: "api"  # csv | api | sql | parquet | excel
    description: "e-Stat API providing household income data by Japanese prefecture"

    # --- Connection Info (type-specific) ---
    connection:
      api:
        base_url: "https://api.e-stat.go.jp/rest/3.0"
        table_id: "0003348423"
        format: "json"
        auth: "api_key"  # references .env or config
      # csv:
      #   path: "data/income_survey.csv"
      #   encoding: "utf-8"
      #   delimiter: ","
      # sql:
      #   connection_string_env: "DB_URL"
      #   table: "household_income"
      # parquet:
      #   path: "data/income_survey.parquet"

    # --- Schema ---
    schema:
      columns:
        - name: "prefecture_code"
          type: "string"
          description: "JIS X 0401 prefecture code (01-47)"
          examples: ["01", "13", "47"]
          nullable: false
        - name: "year"
          type: "integer"
          description: "Survey year"
          range: { min: 2000, max: 2024 }
          nullable: false
        - name: "average_income"
          type: "float"
          description: "Average annual household income (10,000 JPY)"
          unit: "万円"
          range: { min: 200, max: 1500 }
          nullable: true
        - name: "median_income"
          type: "float"
          description: "Median annual household income (10,000 JPY)"
          unit: "万円"
          nullable: true
        - name: "household_count"
          type: "integer"
          description: "Number of surveyed households"
          nullable: false
      primary_key: ["prefecture_code", "year"]
      row_count_estimate: 1128  # 47 prefectures * 24 years

    # --- Tags for search ---
    tags: ["income", "household", "prefecture", "e-stat", "economic"]

    # --- Metadata ---
    provider: "Statistics Bureau of Japan"
    license: "CC BY 4.0"
    update_frequency: "annual"
    last_updated: "2024-12-01"
    documentation_url: "https://www.e-stat.go.jp/"
```

### 3.3 Domain Knowledge Schema

```yaml
# .insight/catalog/knowledge/estat-income-by-prefecture.yaml
source_id: "estat-income-by-prefecture"
entries:
  - key: "income_survey_methodology"
    title: "Income Survey Methodology Notes"
    content: >
      The Household Income Survey excludes single-person households
      under 30 and households with income from agriculture/forestry.
      This may undercount low-income populations in rural areas.
    category: "methodology"  # methodology | caution | definition | context
    importance: "high"  # high | medium | low
    created_at: "2026-02-18T10:00:00+09:00"
    source: "Survey methodology document, Statistics Bureau"

  - key: "income_definition_change_2018"
    title: "Income Definition Change in 2018"
    content: >
      In 2018, the survey changed the definition of 'income' to include
      certain welfare benefits. Direct comparison with pre-2018 data
      requires adjustment factor of approximately 0.97.
    category: "caution"
    importance: "high"
    created_at: "2026-02-18T10:00:00+09:00"
    source: "Statistics Bureau notice, 2018-03"
    affects_years: [2018, 2019, 2020, 2021, 2022, 2023, 2024]

  - key: "okinawa_data_gap"
    title: "Okinawa Prefecture Data Gap"
    content: >
      Okinawa (prefecture_code: 47) has missing data for 2000-2002
      due to survey implementation delays after reversion.
    category: "caution"
    importance: "medium"
    created_at: "2026-02-18T10:00:00+09:00"
    affects_columns: ["average_income", "median_income"]
```

### 3.4 Rules Schema

```yaml
# .insight/rules/review_rules.yaml
rules:
  - id: "RR-001"
    title: "Check for temporal consistency in multi-year data"
    description: >
      When analysis spans multiple years, verify that variable definitions
      haven't changed mid-period. Check domain knowledge for definition changes.
    category: "data_quality"  # data_quality | methodology | interpretation | ethics
    severity: "warning"  # error | warning | info
    auto_check: true  # Can be checked programmatically
    trigger: "multi_year_data"
    created_from: "REV-001 on AD-001"  # Traceability

  - id: "RR-002"
    title: "Require population normalization for cross-prefecture comparison"
    description: >
      Raw counts must be normalized by population when comparing
      across prefectures. Use per-capita or per-1000 metrics.
    category: "methodology"
    severity: "error"
    auto_check: false
    trigger: "cross_prefecture_comparison"

# .insight/rules/analysis_rules.yaml
rules:
  - id: "AR-001"
    title: "Report effect size alongside p-values"
    description: >
      Statistical significance alone is insufficient.
      Always report effect size (Cohen's d, r-squared, etc.).
    category: "methodology"
    severity: "warning"
    auto_check: false
```

### 3.5 Project Configuration

```yaml
# .insight/config.yaml
project:
  name: "Open Data Analysis Project"
  description: "Statistical analysis of Japanese public data sources"
  created_at: "2026-02-18T10:00:00+09:00"

settings:
  default_language: "ja"
  design_id_prefix: "AD"
  auto_suggest_cautions: true
  require_review_before_analysis: true

webui:
  port: 3000
  host: "127.0.0.1"

catalog:
  default_source_type: "api"
  search_index: true  # Enable SQLite FTS for catalog search
```

---

## 4. MCP Tool Definitions

### 4.1 Design Management Tools

```python
@mcp.tool()
async def create_analysis_design(
    design_id: str,             # e.g. "H01", "H01a" — analyst-defined ID
    hypothesis_statement: str,
    hypothesis_background: str,
    parent_id: str | None = None,   # for derived hypotheses
    data_source_refs: list[str] | None = None,  # e-Stat table IDs or catalog source_ids
) -> dict:
    """Create a new analysis design document.

    Creates a YAML file in .insight/designs/ with 'draft' status,
    using the lightweight format compatible with open-data-analysis.
    If data_source_refs are provided, auto-populates domain_references
    from matching catalog knowledge entries.

    Returns: AnalysisDesign with id, parent_id, status, file_path
    """

@mcp.tool()
async def update_analysis_design(
    design_id: str,
    metrics: dict | None = None,
    explanatory: dict | None = None,
    chart: dict | None = None,
    next_action: dict | None = None,  # {if_supported: str, if_rejected: {reason, pivot}}
    domain_references: list[dict] | None = None,
) -> dict:
    """Update sections of an existing analysis design.

    Only provided sections are updated; others remain unchanged.
    Design must be in 'draft' or 'active' status to edit core sections.

    Returns: Updated AnalysisDesign
    """

@mcp.tool()
async def submit_for_review(
    design_id: str,
    comment: str | None = None,
) -> dict:
    """Submit an analysis design for analyst review via WebUI.

    Changes status from 'draft' to 'active'.
    Automatically calls suggest_cautions() on referenced data sources
    and includes results in the response.

    Returns: ReviewRequest with design_id, status, suggested_cautions
    """

@mcp.tool()
async def get_design(
    design_id: str,
) -> dict:
    """Retrieve a complete analysis design document.

    Returns: Full AnalysisDesign including domain_references, reviews, and results
    """

@mcp.tool()
async def list_designs(
    status: str | None = None,  # draft | active | supported | rejected | inconclusive
    parent_id: str | None = None,  # filter by parent hypothesis
) -> list[dict]:
    """List all analysis designs, optionally filtered by status or parent.

    Returns: List of AnalysisDesign summaries (id, parent_id, status, hypothesis_statement, updated_at)
    """
```

### 4.2 Data Catalog Tools

```python
@mcp.tool()
async def get_source_schema(
    source_id: str,
) -> dict:
    """Get the full schema definition of a data source.

    Returns: DataSource with connection info, column schemas,
    tags, and metadata. Useful for Claude to understand
    available fields before designing extraction.
    """

@mcp.tool()
async def get_domain_knowledge(
    source_id: str,
    category: str | None = None,  # methodology|caution|definition|context
    query: str | None = None,  # Free-text search within entries
) -> list[dict]:
    """Get domain knowledge entries for a data source.

    If query is provided, searches entry titles and content.
    If category is provided, filters by category.

    Returns: List of DomainKnowledge entries
    """

@mcp.tool()
async def search_catalog(
    keyword: str,
    source_type: str | None = None,  # csv|api|sql|parquet|excel
    tags: list[str] | None = None,
) -> list[dict]:
    """Search the data catalog by keyword, type, or tags.

    Searches across source names, descriptions, column names,
    and tags. Uses SQLite FTS if available.

    Returns: List of DataSource summaries (id, name, type, description, tags)
    """

@mcp.tool()
async def add_catalog_entry(
    id: str,
    name: str,
    source_type: str,  # csv|api|sql|parquet|excel
    description: str,
    connection: dict,
    schema_columns: list[dict],
    tags: list[str] | None = None,
    provider: str | None = None,
) -> dict:
    """Add a new data source to the catalog.

    Creates entry in .insight/catalog/sources.yaml and
    initializes empty knowledge file.

    Returns: Created DataSource
    """
```

### 4.3 Context & Rules Tools

```python
@mcp.tool()
async def get_project_context() -> dict:
    """Get comprehensive project context for Claude.

    Returns a summary including:
    - Project name and description
    - Catalog summary (source count, types)
    - Recent designs (last 5, with status)
    - Active rules count by category
    - Settings

    This is the recommended first tool call when starting
    a new analysis conversation.
    """

@mcp.tool()
async def get_active_rules(
    category: str | None = None,  # data_quality|methodology|interpretation|ethics
) -> list[dict]:
    """Get active rules, optionally filtered by category.

    Returns: List of Rule entries with id, title, description,
    severity, and trigger conditions.
    """

@mcp.tool()
async def suggest_cautions(
    source_ids: list[str],
) -> list[dict]:
    """Get relevant cautions for a set of data sources.

    Aggregates domain knowledge entries with category='caution'
    and importance='high' or 'medium' for the given sources.
    Also checks applicable rules.

    Returns: List of Caution objects with source_id, key,
    title, content, importance, and applicable_rules.
    """
```

### 4.4 Review Tools

```python
@mcp.tool()
async def save_review_comment(
    design_id: str,
    comment: str,
    reviewer: str = "claude",
    status: str = "comment",  # comment|approve|reject|request_changes
    domain_knowledge: dict | None = None,  # {key, content, source} to extract
) -> dict:
    """Save a review comment on an analysis design.

    If domain_knowledge is provided, it is automatically added
    to the relevant source's knowledge file.

    If status is 'approve', design status changes to 'approved'.
    If status is 'reject', design status changes to 'rejected'.

    Returns: Created Comment with id, timestamp
    """

@mcp.tool()
async def extract_rules_from_reviews(
    design_id: str,
) -> list[dict]:
    """Analyze review comments and extract reusable rules.

    Uses heuristics to identify review comments that contain
    generalizable guidance (methodology, data quality, etc.)
    and proposes them as new rules.

    Returns: List of proposed Rule entries (not yet saved).
    User/Claude must confirm before adding to rules.
    """
```

### 4.5 MCP Resources (Read-Only Context)

```python
@mcp.resource("insight://project/context")
async def project_context_resource() -> str:
    """Project overview as a readable resource.

    Provides project name, settings, catalog summary,
    and active design count in a human-readable format.
    Automatically loaded into Claude's context.
    """

@mcp.resource("insight://designs/{design_id}")
async def design_resource(design_id: str) -> str:
    """Individual design document as a readable resource."""

@mcp.resource("insight://catalog/{source_id}")
async def catalog_resource(source_id: str) -> str:
    """Data source catalog entry as a readable resource."""

@mcp.resource("insight://rules/active")
async def active_rules_resource() -> str:
    """All active rules as a readable resource."""
```

---

## 5. .insight/ Project Directory Structure

```
.insight/
├── config.yaml                     # Project settings
├── catalog/
│   ├── sources.yaml                # All data source definitions
│   └── knowledge/                  # Domain knowledge per source
│       ├── estat-income-by-prefecture.yaml
│       ├── police-crime-stats.yaml
│       └── census-population.yaml
├── designs/
│   ├── AD-001_crime_rate_correlation.yaml
│   ├── AD-002_education_employment.yaml
│   └── AD-003_housing_demographics.yaml
├── rules/
│   ├── review_rules.yaml           # Rules from review feedback
│   └── analysis_rules.yaml         # Methodology rules
├── history/
│   └── outcomes.yaml               # Completed analysis outcomes
└── .sqlite                         # Search index (auto-generated)
    └── catalog_fts.db              # Full-text search for catalog
```

### 5.1 Startup Sequence

When `uvx insight-blueprint --project /path` is run:

```
1. Parse CLI args, resolve project directory
2. Initialize .insight/ (create subdirs + default YAML if first run)
3. Copy _skills/ → .claude/skills/ (skip if already present)
4. Merge/register MCP server in project `.mcp.json` (skip if `insight-blueprint` already registered)
5. Rebuild SQLite FTS index from YAML files
6. Start FastAPI + uvicorn in background thread (port 3000, 127.0.0.1)
7. Open browser at http://localhost:3000 (webbrowser.open, 1s delay)
8. mcp.run()  ← blocks main thread, handles stdio MCP protocol with Claude Code
```

Key: `mcp.run()` must be last — it takes over stdin/stdout for the MCP protocol.

---

## 6. WebUI Dashboard

### 6.1 Technology Stack

- **Framework**: React 19 + TypeScript
- **Build**: Vite 6
- **UI Library**: Tailwind CSS + shadcn/ui (lightweight, no heavy dependencies)
- **State**: React Query (TanStack Query) for server state
- **Routing**: React Router v7

### 6.2 Static File Bundling

Frontend is built with Vite and output is placed in `src/insight_blueprint/static/`.
The Python package includes pre-built static files in the wheel.

```python
# web.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="insight-blueprint")

# API routes
app.include_router(api_router, prefix="/api")

# Serve React SPA
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

Vite config (builds directly into Python package):
```typescript
// frontend/vite.config.ts
export default defineConfig({
  build: {
    outDir: '../src/insight_blueprint/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",  // Dev: proxy to FastAPI backend
    },
  },
})
```

Build process:
```bash
# Development (two terminals)
cd frontend && npm run dev          # Vite dev server :5173 with proxy
uvicorn insight_blueprint.web:app   # FastAPI dev server :8000

# Production build
cd frontend && npm run build  # outputs to ../src/insight_blueprint/static/
```

### 6.3 Tab Structure

#### Tab 1: Analysis Designs

| Section | Content |
|---------|---------|
| Design List | Table: ID, Title, Status (badge), Author, Updated |
| Status Filter | Tabs: All / Draft / Submitted / Approved / In Analysis / Completed |
| Design Detail | Full YAML rendered as structured view |
| Review Panel | Comment thread + Approve/Reject buttons |
| Quick Actions | Submit, Approve, Reject, Start Analysis |

#### Tab 2: Data Catalog

| Section | Content |
|---------|---------|
| Source List | Searchable table: ID, Name, Type (icon), Column Count, Tags |
| Source Detail | Schema table + Connection info + Domain knowledge |
| Knowledge Panel | Editable list of domain knowledge entries per source |
| Add Source | Form for adding new catalog entries |

#### Tab 3: Rules

| Section | Content |
|---------|---------|
| Rule List | Table: ID, Title, Category (badge), Severity (icon) |
| Category Filter | Tabs: All / Data Quality / Methodology / Interpretation / Ethics |
| Rule Detail | Full description + trigger conditions + origin |
| Add Rule | Form for creating new rules |

#### Tab 4: History

| Section | Content |
|---------|---------|
| Outcome List | Table: Design ID, Title, Outcome (supported/rejected/inconclusive) |
| Outcome Detail | Summary + artifacts links + review trail |
| Statistics | Pie chart of outcomes, timeline of completions |

### 6.4 API Endpoints (FastAPI)

```
GET    /api/designs              # List designs
GET    /api/designs/{id}         # Get design detail
POST   /api/designs              # Create design
PUT    /api/designs/{id}         # Update design
POST   /api/designs/{id}/submit  # Submit for review
POST   /api/designs/{id}/review  # Save review (approve/reject/comment)

GET    /api/catalog/sources      # List sources
GET    /api/catalog/sources/{id} # Get source detail
POST   /api/catalog/sources      # Add source
PUT    /api/catalog/sources/{id} # Update source
GET    /api/catalog/knowledge/{source_id}  # Get domain knowledge
POST   /api/catalog/knowledge/{source_id}  # Add knowledge entry

GET    /api/rules                # List rules
POST   /api/rules                # Add rule
PUT    /api/rules/{id}           # Update rule
DELETE /api/rules/{id}           # Delete rule

GET    /api/history              # List outcomes
GET    /api/context              # Get project context summary
```

---

## 7. Skills (Claude Code Templates)

> **Language policy**: All Skill definitions (SKILL.md, prompts, workflow descriptions, comments)
> MUST be written in **English**. This ensures Skills are portable and readable by
> non-Japanese contributors, and consistent with Claude Code's own skill ecosystem.
> User-facing output from Skills (responses, analysis summaries) follows the project's
> language rules (Japanese for user communication).

### 7.1 analysis-design Skill

File: `skills/analysis-design/SKILL.md` (bundled into `.claude/skills/` on first run)

```markdown
# /analysis-design — Analysis Design Builder

Guides Claude through creating a lightweight analysis design document
using insight-blueprint MCP tools. Follows the hypothesis-driven EDA workflow.

## When to use
- Starting a new exploratory analysis
- Deriving a sub-hypothesis after a parent hypothesis is rejected
- Updating an existing design with new data source information

## Workflow
1. Call get_project_context() to understand current project state and active rules
2. Call search_catalog() to find relevant data sources for the user's topic
3. Call get_domain_knowledge() and suggest_cautions() for selected sources
4. Interview the user: hypothesis statement, background, target metric, explanatory variable
5. Ask user to specify chart type and next_action branching (if_supported / if_rejected)
6. Call create_analysis_design() with gathered information
7. Show the generated YAML and invite revisions
8. Call submit_for_review() to send to WebUI for analyst approval

## Notes
- Keep the design lightweight — avoid over-specifying processing steps
- Always populate next_action.if_rejected.pivot with concrete next hypotheses
- Link parent_id if this is a derived hypothesis (e.g., H01a derived from H01)
```

### 7.2 data-explorer Skill

File: `skills/data-explorer/SKILL.md` (bundled into `.claude/skills/` on first run)

```markdown
# /data-explorer — Data Source Explorer

Helps analysts discover and understand available data sources
in the project catalog, including schema and domain knowledge.

## When to use
- Finding which data sources are available for a given topic
- Understanding the meaning and caveats of specific columns
- Adding a new data source to the catalog

## Workflow
1. Call search_catalog() with user's topic keywords
2. For each relevant source, call get_source_schema() to show column details
3. Call get_domain_knowledge() to surface important cautions and methodology notes
4. Summarize findings in a table: source / columns / key cautions
5. If the user wants to add a new source, call add_catalog_entry()

## Notes
- Always highlight high-importance cautions prominently
- Cross-reference related sources (e.g., population data needed to normalize counts)
```

---

## 8. Key Design Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| stdio for MCP transport | Claude Code standard; simplest local integration | SSE (backward compat only), Streamable HTTP (overkill for local) |
| YAML + Markdown frontmatter for primary storage | Human-readable, git-friendly, analyst-editable; `ruamel.yaml` preserves comments on round-trip editing | JSON (no comments, painful multi-line), SQLite only (binary diffs break git) |
| SQLite for search index | FTS5 for fast keyword search; auto-generated from YAML | No search (scan all files), Elasticsearch (too heavy) |
| Official `mcp` SDK's FastMCP (start), upgrade to `fastmcp` if needed | Start with fewer deps; one-line import change to upgrade | `fastmcp` standalone from day 1 (better DX but extra dep) |
| Single process (MCP + WebUI) | Simple deployment; one `uvx` command | Separate processes (complex), WebUI optional flag |
| **uvx (PyPI) for distribution** | Data scientists are Python-native; no Node.js dependency required | npx (npm) — common in MCP ecosystem but foreign to DS audience |
| **Extend existing YAML format** | Preserve `hypothesis`, `metrics`, `chart`, `next_action`, `parent` from open-data-analysis; EDA iteration must stay lightweight | Full redesign — would break compatibility and increase overhead |
| **Hypothesis enrichment can proceed before data-catalog schema finalization** | `metrics`/`explanatory` `data_source` can stay as plain string IDs (e.g., e-Stat table IDs). Later catalog linkage can be additive (optional `catalog_source_id`/validation) without breaking existing design files. | Block on SPEC-2 first (delays analyst workflow), or tightly couple to catalog model now (premature) |
| **Design tool contract: create accepts rich optional fields; update supports patch** | New fields (`metrics` structured, `explanatory`, `chart`, `next_action`) should be accepted at create-time for one-shot authoring. A dedicated `update_analysis_design` patch tool is still required for iterative EDA refinement. | Create-only (forces full rewrites), update-only expansion (awkward initial authoring UX) |
| **Status: draft→active→supported/rejected/inconclusive** | Matches EDA reality (hypotheses pivot, not get "approved"); fewer states = less ceremony | draft→submitted→approved→in_analysis→completed — too formal for EDA |
| **Skills written in English** | Portability for OSS contributors; consistent with Claude Code skill ecosystem | Japanese — limits international adoption of skills |
| React + Vite bundled in wheel | Standard pattern for Python+JS apps | Separate frontend server (complex), HTMX (limited interactivity) |
| Pydantic models shared | Single source of truth for MCP tools + API + storage | Separate schemas (duplication risk) |
| Design ID as `AD-NNN` prefix | Readable, sortable, compatible with hypothesis IDs | UUID (less readable), auto-increment (collision risk) |
| Domain knowledge per-source files | Scalable; easy to find knowledge for a source | Single file (unwieldy), database only (not editable) |
| Review comments inline in design | Full context in one file; git diff shows review history | Separate review files (harder to correlate) |

---

## 9. Implementation Phases

### Phase 1: Core Foundation (Priority)
- CLI entry point (`cli.py`)
- Project initialization (`.insight/` directory)
- Pydantic models
- YAML storage layer
- Basic MCP tools: `create_analysis_design`, `get_design`, `list_designs`

### Phase 2: Data Catalog
- Catalog YAML storage
- Domain knowledge management
- MCP tools: `search_catalog`, `get_source_schema`, `get_domain_knowledge`
- SQLite FTS index

### Phase 3: Review Workflow
- Review comment system
- Status lifecycle management
- MCP tools: `submit_for_review`, `save_review_comment`
- Rule extraction from reviews
- Caution suggestion engine

### Phase 4: WebUI Dashboard
- FastAPI backend with API endpoints
- React+Vite frontend (4 tabs)
- Static file bundling in wheel
- WebUI startup in background thread

### Phase 5: Skills & Polish
- Claude Code skill templates
- First-run skill installation
- Documentation
- PyPI publishing

---

## 10. Open Questions

1. **Concurrent access**: Should we use file locking for YAML writes, or is single-user sufficient for v1?
   - **Recommendation**: Single-user for v1. MCP server is per-project, and WebUI writes go through the same process.

2. **Authentication for WebUI**: Should the dashboard require authentication?
   - **Recommendation**: No auth for v1 (local-only, bound to 127.0.0.1). Add optional token auth in v2.

3. **Design versioning**: Should we track full version history of designs?
   - **Recommendation**: Yes, via git (`.insight/` is in the working tree). Status history in YAML provides lightweight audit trail.

4. **SQLite vs pure YAML**: Should analysis history use SQLite for queries?
   - **Recommendation**: YAML primary, SQLite as read-only index. Rebuilt on startup from YAML files.

5. **Notification to Claude Code**: How to notify Claude when a design is approved via WebUI?
   - **Recommendation**: Claude polls via `list_designs(status="approved")` or uses MCP resource subscription (if supported by client). For v1, polling is sufficient.

6. **YAML concurrency (MCP + WebUI writing same files)**: Resolved for v1 — use atomic writes (`tempfile` + `os.replace()`) to prevent corruption. Both MCP tools and FastAPI endpoints share the same `core/` service layer, so writes are serialized within the single process.

7. **Project initialization strategy (`init_project`)**:
   - **Recommendation**: Use per-item idempotent initialization, not a single "directory exists" guard.
   - **Template install**: Copy bundled `templates/skills/analysis-design/` into `.claude/skills/analysis-design/` only when absent (never overwrite). Do not use symlinks.
   - **MCP registration**: Merge into existing project `.mcp.json` and upsert only `mcpServers["insight-blueprint"]`.
   - **Portability**: If `.mcp.json` stores absolute machine-specific paths, keep it out of git (or generate per-machine).
   - **Failure model**: `init_project` should be safe to rerun after partial failures and complete missing artifacts on the next run.

---

## 11. Dependency Summary

| Package | Purpose | Why This One |
|---------|---------|-------------|
| `mcp>=1.8` | MCP server SDK | Official Anthropic package; includes basic FastMCP |
| `fastapi>=0.115` | WebUI HTTP backend | Industry standard; async, auto OpenAPI docs |
| `uvicorn>=0.34` | ASGI server for FastAPI | Lightweight, handles SIGINT natively |
| `pydantic>=2.10` | Data validation & models | Shared by MCP tools, API, and storage |
| `ruamel.yaml>=0.18` | YAML round-trip editing | **Preserves comments** in analyst-edited files (PyYAML cannot) |
| `python-frontmatter>=1.1` | Markdown + YAML frontmatter | For design docs that combine structured metadata + free-form content |
| `click>=8.1` | CLI framework | Clean `--project` flag handling, help text |

> **Upgrade path**: If `mcp`'s built-in FastMCP proves insufficient, switch to standalone
> `fastmcp` package. Change: `from mcp.server.fastmcp import FastMCP` -> `from fastmcp import FastMCP`.
> Gains: automatic Pydantic model -> JSON Schema, `ctx.info()` client logging, built-in Inspector UI.

---

## 12. Changelog

- **2026-02-27**: Recorded frontend E2E test architecture decisions for expanded Playwright coverage.
  - **Spec organization**: Split detailed E2E tests by feature/page (`design-detail`, `catalog`, `rules`, `history`, `cross-tab`) and keep `smoke.spec.ts` as a fast gate.
  - **Parallelism strategy**: Prefer file-level parallel execution (Playwright default across files). Keep tests isolated so workers can scale without order dependencies.
  - **Mocking architecture**: Extract shared route setup + mock data factories into reusable E2E helpers/fixtures; keep each test responsible for its own route registrations and overrides.
  - **Loading-state test stability**: Use a promise-gated `page.route()` delay (manual release) instead of fixed sleep-based timing to verify spinner-visible then spinner-hidden transitions.
  - **SPA history behavior**: Validate back-navigation with both URL assertion and active-tab UI assertion because `history.pushState` + `popstate` is same-document navigation.
  - **Isolation principle**: Do not chain tests by state; share setup code, not runtime state. `beforeEach` can prepare common mocks/UI entrypoint, but each test must be independently executable.

- **2026-02-27**: Recorded SPEC-4b frontend test strategy refinement (Codex review).
  - Kept the baseline gate as `TypeScript strict + build verification`.
  - Added recommendation to introduce a **small Playwright smoke suite** (not full E2E) for high-risk UI flows:
    - App shell + tab navigation (`?tab=` sync, invalid fallback, browser back/forward)
    - Core data rendering per tab (Designs/Catalog/Rules/History first-view checks)
    - API failure banner + retry affordance visibility
  - Positioning decision: Use Playwright primarily as a **Claude Code-driven verification tool** in development/review sessions; optional CI integration later when test stability is proven.
  - Scope guardrail: Keep broad exploratory scenarios in manual checklist, and automate only deterministic acceptance-critical checks to avoid low-ROI maintenance.

- **2026-02-26**: Full SPEC-3 (review-workflow) technical risk analysis via Codex.

  ### Risk Analysis Summary

  | # | Risk | Severity | Mitigation | Complexity |
  |---|------|----------|-----------|-----------|
  | 1 | **ReviewService -> DesignService cross-dependency** increases coupling | Medium | Depend only on `get_design`/`update_design` interface. Consider Protocol/port injection for testability. Keep transition logic in ReviewService. | M |
  | 2 | **DesignStatus enum extension** (`pending_review`) may break existing tests | Medium | Update server.py status description strings, test expected values, and list_analysis_designs filter docs in one atomic commit. Keep enum values in single definition. | S |
  | 3 | **Review comment append pattern** — `{design_id}_reviews.yaml` uses read-modify-write via yaml_store (full-file overwrite, not true append). Race condition if MCP + WebUI write concurrently. | High | For v1 single-user: acceptable with atomic `os.replace`. For future multi-user: add per-design file lock or optimistic concurrency (revision token). Document the limitation. | M |
  | 4 | **Keyword-based extraction heuristics** — case sensitivity, Unicode normalization (NFKC), multi-line comments, lines with multiple keywords, prefix stripping | Medium | Use regex-based prefix detection (case-insensitive). Apply NFKC normalization before matching. Process by block (not raw line split). Add duplicate key check. Accept imperfect recall for v1 (out-of-scope: LLM extraction). | M |
  | 5 | **get_project_context file aggregation cost** — reads all `catalog/knowledge/*.yaml` + `extracted_knowledge.yaml` | Medium | Acceptable for v1 (<100 sources). For future scale: add mtime-based cache. Monitor in NFR perf tests (500ms target for 100 sources + 500 entries). | M |
  | 6 | **suggest_cautions vocabulary mismatch** — DomainKnowledgeEntry.affects_columns vs Rule.affects_tables vs free-text content keyword match | High | Define canonical matching strategy: (a) catalog entries match by `affects_columns` field, (b) extracted knowledge matches by keyword search in `content` field against table_names. Document the dual-strategy explicitly. Consider normalizing to `affects_entities` in future. | M |
  | 7 | **Status transition validation gaps** — existing `update_analysis_design` tool can bypass review workflow by setting status directly | High | Add transition matrix as single-source-of-truth (dict/set in models or service). Block `pending_review` in generic `update_analysis_design`. Only `submit_for_review` can set `pending_review`; only `save_review_comment` can transition away. Add CAS-style guard (check current status before write). | M |

  ### Overall Assessment
  - **Implementation Complexity**: **L** (Large) — Feature additions are medium-sized, but state transition integrity, backward compatibility with existing tests, and dual-knowledge-source aggregation make the test surface heavy.
  - **Estimated Effort**: 3-4 days for a thorough TDD implementation.

  ### Recommended Implementation Order
  1. **DesignStatus extension + transition matrix** — Foundation for all review operations. Single validator/guard module. Update existing test expectations.
  2. **models/rules.py** — ReviewComment + Rule models. Pure data models, no dependencies.
  3. **core/reviews.py** — ReviewService skeleton: `submit_for_review`, `save_review_comment`, `list_comments`. Depends on DesignService + yaml_store.
  4. **core/reviews.py** — `extract_domain_knowledge` with regex-based heuristics + NFKC normalization.
  5. **core/rules.py** — RulesService: `get_project_context`, `suggest_cautions`. Depends on CatalogService + yaml_store.
  6. **server.py** — 5 new MCP tools + restrict `update_analysis_design` from setting `pending_review`.
  7. **cli.py + project.py** — Wire ReviewService/RulesService. Create `extracted_knowledge.yaml` in init.
  8. **Regression tests** — Verify existing SPEC-1/SPEC-2 tests pass with DesignStatus extension.

  ### Alternative Approaches Considered
  1. **Inline reviews in design YAML** (instead of separate `_reviews.yaml`) — Better integrity but design file grows unbounded. Rejected: separate file is cleaner.
  2. **Append-only JSONL for review comments** — Avoids read-modify-write race entirely. Rejected for v1: YAML consistency preferred, single-user is acceptable.
  3. **SQLite for extracted knowledge** — Better query performance for `suggest_cautions`. Rejected for v1: YAML-first philosophy. Can add FTS5 indexing later.

- **2026-02-25**: Initial SPEC-3 risk assessment recorded.
  - **Status machine enforcement**: Add explicit transition matrix (`active -> pending_review -> supported/rejected/inconclusive/active`) and block direct terminal-state updates via generic patch tools.
  - **Concurrency safety for review writes**: For `save_review_comment`, avoid blind read-modify-write races by introducing per-design locking or optimistic concurrency checks (`updated_at` / revision token).
  - **Cross-service dependency boundary**: Keep `ReviewService` orchestration-level dependency on `DesignService`, but depend on a minimal protocol interface to reduce coupling and simplify tests.
  - **Knowledge schema alignment**: Normalize `suggest_cautions` target matching by defining canonical table/column mapping rules between `affects_columns` and extracted knowledge metadata.
  - **Heuristic extraction robustness**: Normalize Unicode/case and parse review text by block (not raw line-only split) to improve Japanese/English keyword extraction stability.

- **2026-02-24**: Recorded SPEC-2 revised design review (incremental FTS5 updates during session).
  - **Write ordering**: Keep YAML as source-of-truth and perform YAML commit first, then best-effort FTS mutation. Never write FTS first.
  - **Self-healing index**: Persist index state (`healthy/degraded`) and schedule opportunistic `rebuild_index()` when incremental update fails or startup skipped FTS.
  - **Update atomicity in SQLite**: For `update_source`, execute `DELETE + INSERT` in a single SQLite transaction to avoid transient no-row windows.
  - **Connection model**: Keep short-lived per-operation SQLite connections for v1 simplicity and thread safety; use WAL + busy_timeout; revisit persistent connection only if profiling shows overhead.
  - **Capability guard**: Gate all incremental ops behind the same `fts_enabled` capability decided at startup (and revalidated on first failure), with no-op fallback when disabled.
  - **External edit consistency**: Document that manual YAML edits can stale FTS until next startup rebuild; recommend restart/reindex after bulk or out-of-band edits.
  - **Incremental test strategy**: Add focused sqlite_store unit tests (insert/delete/update transaction behavior) and service integration tests for crash/failure recovery and stale-index rebuild.

- **2026-02-24**: Recorded SPEC-2 (data-catalog) design review guidance.
  - **FTS5 availability**: Detect with `SELECT sqlite_compileoption_used('ENABLE_FTS5')` at service initialization, then fail-soft on actual `CREATE VIRTUAL TABLE`/`MATCH` with `sqlite3.OperationalError` handling.
  - **Search fallback**: Add optional fallback path using a plain `catalog_search_fallback` table with normalized text and parameterized `LIKE` search when FTS5 is unavailable.
  - **MATCH safety**: Do not interpolate raw user query. Escape embedded quotes and bind the full MATCH phrase as a SQL parameter (e.g., `WHERE docs MATCH ?`).
  - **YAML concurrent writes**: Keep `tempfile + os.replace` and add per-source lock files (`.lock` via `fcntl`/`msvcrt` abstraction) to avoid last-write-wins races in rapid consecutive updates.
  - **Schema evolution**: Introduce per-file `schema_version`, alias-based rename support, and explicit migration functions for breaking changes (especially field removals/renames).
  - **Index rebuild performance**: Keep full rebuild as default for small catalogs, but add startup heuristic (`<=500` full rebuild, `>500` incremental by mtime/hash) and store index metadata.
  - **Japanese+English search**: Default to FTS5 `tokenize='trigram'` for mixed-language recall; allow configurable tokenizer override to `unicode61`/`icu` when available.

- **2026-02-22**: Recorded hypothesis enrichment sequencing decision (SPEC-1 vs SPEC-2).
  - Confirmed `chart`/`next_action`/`explanatory` do not require finalized catalog schema.
  - Adopted additive strategy: keep `data_source` as `str` now; add catalog reference/validation later without breaking changes.
  - Tooling direction: `create_analysis_design` should accept rich optional fields now, and `update_analysis_design` should be added for patch updates.
  - Spec tracking recommendation: handle as SPEC-1 amendment (or SPEC-1.1), keep data-catalog scope in SPEC-2.

- **2026-02-21**: Recorded SPEC-1 initialization design guidance.
  - Startup sequence updated to project `.mcp.json` registration (merge/upsert).
  - Confirmed template distribution strategy: copy-once (no overwrite), no symlink.
  - Confirmed idempotency scope: per-file/per-directory checks to recover from partial init.
  - Added portability note: absolute project paths in `.mcp.json` are machine-specific.

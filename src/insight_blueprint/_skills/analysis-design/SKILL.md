---
name: analysis-design
version: "1.0.0"
description: |
  Guides Claude through creating analysis design documents for hypothesis-driven EDA.
  Use when the user wants to create, manage, or review analysis designs.
  Triggers: "create analysis design", "hypothesis document", "new hypothesis",
  "分析設計を作りたい", "仮説を立てたい", "新しい仮説", "仮説ドキュメント".
disable-model-invocation: true
argument-hint: "[theme_id]"
---

# /analysis-design — Analysis Design Builder

Guides Claude through creating a lightweight analysis design document using
insight-blueprint MCP tools. Follows the hypothesis-driven EDA workflow.

## When to Use
- Starting a new exploratory analysis (user wants to formalize a hypothesis)
- Deriving a sub-hypothesis after a parent hypothesis is rejected
- Reviewing or listing existing analysis designs

## When NOT to Use
- Browsing the data catalog (future: `/data-explorer` skill)
- General EDA discussion without intent to persist a design document

## Workflow

### Step 1: Check Current State
Call `list_analysis_designs()` to understand existing designs:
- Note existing theme IDs (e.g., "FP", "TX")
- Check if a `parent_id` should be referenced

### Step 2: Gather Hypothesis Details

Interview the user for required fields:

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `title` | Yes | Short descriptive title | "Foreign population vs crime rate" |
| `hypothesis_statement` | Yes | Testable statement | "No positive correlation exists between..." |
| `hypothesis_background` | Yes | Context and motivation (free-form, multi-line) | Background reasoning |
| `theme_id` | No | Uppercase identifier — defaults to "DEFAULT" | "FP", "TX", "ECON" |
| `parent_id` | No | Parent design ID if this is derived | "FP-H01" |
| `analysis_intent` | No | "exploratory", "confirmatory" (default), or "mixed" | "exploratory" |
| `metrics` | No | List of verification metric dicts (tier: "primary" / "secondary" / "guardrail") | `[{target: "crime_rate_per_100k", tier: "primary", data_source: {crime: "0000010111"}, grouping: [...], filter: "...", aggregation: "mean", comparison: "..."}]` |
| `explanatory` | No | List of explanatory variable dicts (role: "treatment" / "confounder" / "covariate" / "instrumental" / "mediator") | `[{name: "foreign_ratio", description: "外国人比率", role: "treatment", data_source: "0000010101", time_points: "2012-2022"}]` |
| `chart` | No | List of visualization definition dicts (intent: "distribution" / "correlation" / "trend" / "comparison") | `[{intent: "correlation", type: "scatter", description: "FP ratio vs crime rate", x: "foreign_ratio", y: "crime_rate"}]` |
| `methodology` | No | Analysis method and package | `{method: "OLS", package: "statsmodels", reason: "線形回帰で相関を検証"}` |
| `next_action` | No | Branch definition after hypothesis test | `{if_supported: "...", if_rejected: {reason: "...", pivot: "..."}}` |

If the user passed `$ARGUMENTS`, use it as `theme_id` (validate format first).

### Step 3: Create the Design

```
create_analysis_design(
    title="<title>",
    hypothesis_statement="<statement>",
    hypothesis_background="<background>",
    theme_id="<theme_id or DEFAULT>",
    parent_id=<"FP-H01" or None>,
    metrics=<list[dict] or None>,        # each dict: {target, tier?, data_source?, grouping?, filter?, aggregation?, comparison?}
    explanatory=<list[dict] or None>,    # each dict: {name, description?, role?, data_source?, time_points?}
    chart=<list[dict] or None>,          # each dict: {intent, type?, description?, x?, y?}
    methodology=<dict or None>,          # {method, package?, reason?}
    next_action=<dict or None>,
)
```

Expected success response:
```json
{"id": "FP-H01", "title": "...", "status": "in_review", "message": "Analysis design 'FP-H01' created successfully."}
```

### Step 3b: Update an Existing Design (optional)

To add or modify fields on an already-created design, use `update_analysis_design()`:

```
update_analysis_design(
    design_id="FP-H01",
    next_action={"if_supported": "パネルFEへ進む", "if_rejected": {"reason": "相関なし", "pivot": "時系列分析"}},
)
```

Only provided fields are updated; all others remain unchanged.

### Step 4: Confirm and Suggest Next Steps
- Show the returned `id` (e.g., "FP-H01") to the user
- Confirm the YAML file location: `.insight/designs/FP-H01_hypothesis.yaml`
- Suggest next steps:
  - Refine the hypothesis: add `chart` / `next_action` via `update_analysis_design()`
  - **Start recording reasoning: `/analysis-journal FP-H01`**
  - **Review and conclude: `/analysis-reflection FP-H01`**

## MCP Tool Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `list_analysis_designs(status?)` | List existing designs | `status`: in_review \| revision_requested \| analyzing \| supported \| rejected \| inconclusive |
| `create_analysis_design(...)` | Create new design | `title`, `hypothesis_statement`, `hypothesis_background`, `theme_id?`, `parent_id?`, `metrics?`, `explanatory?`, `chart?`, `methodology?`, `next_action?`, `analysis_intent?` |
| `update_analysis_design(...)` | Partially update existing design | `design_id`, `title?`, `hypothesis_statement?`, `hypothesis_background?`, `metrics?`, `explanatory?`, `chart?`, `methodology?`, `next_action?`, `analysis_intent?` |
| `get_analysis_design(design_id)` | Retrieve a specific design | `design_id`: str (e.g., "FP-H01") |

## Typed Field Values Reference

| Field | Type | Valid Values | Default |
|-------|------|-------------|---------|
| `explanatory[].role` | VariableRole | `"treatment"`, `"confounder"`, `"covariate"`, `"instrumental"`, `"mediator"` | `"covariate"` |
| `metrics[].tier` | MetricTier | `"primary"`, `"secondary"`, `"guardrail"` | `"primary"` |
| `chart[].intent` | ChartIntent | `"distribution"`, `"correlation"`, `"trend"`, `"comparison"` | inferred from `type` |
| `methodology.method` | str | free text (required, non-empty) | — |
| `methodology.package` | str | free text (optional) | `""` |
| `methodology.reason` | str | free text (optional) | `""` |

**Backward compatibility**: `role`, `tier`, `intent` fields are optional in input. If omitted, defaults are applied automatically.

## theme_id Rules

- Must match `[A-Z][A-Z0-9]*` (uppercase letter first, then uppercase letters or digits)
- Valid: `"FP"`, `"TX"`, `"ECON"`, `"DEFAULT"`, `"FP2"`
- Invalid: `"fp"` (lowercase), `"FP/X"` (slash), `"1FP"` (starts with digit)
- On invalid input, the MCP tool returns an error dict — ask the user to correct it

## Error Handling

| Error Response | Cause | Action |
|----------------|-------|--------|
| `{"error": "Invalid theme_id 'fp': must match [A-Z][A-Z0-9]*"}` | Invalid theme_id format | Ask user for a valid uppercase theme_id |
| `{"error": "Design 'FP-H99' not found"}` | Non-existent design_id | Confirm ID via `list_analysis_designs()` |

## Language Rules
- Follow project CLAUDE.md language settings. Default to Japanese if no setting.
- Code, IDs, tool names, and YAML fields always stay in English.
- Hypothesis text follows the user's language (usually Japanese)

---
name: analysis-design
version: "1.1.0"
description: |
  Guides Claude through creating analysis design documents for hypothesis-driven EDA.
  Use when the user wants to create, manage, or review analysis designs.
  Triggers: "create analysis design", "hypothesis document", "new hypothesis",
  "分析設計を作りたい", "仮説を立てたい", "新しい仮説", "仮説ドキュメント".
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

### Step 0: User Confirmation Gate

Before proceeding, confirm with the user:

- Ask: "分析設計を新規作成しますか？"
- If the user declines, exit gracefully with a brief message and do not proceed
- If the user confirms, continue to Step 1

### Step 1: Check Current State
Call `list_analysis_designs()` to understand existing designs:
- Note existing theme IDs (e.g., "FP", "TX")
- Check if a `parent_id` should be referenced

### Step 1.5: Check for Framing Brief

Check the conversation context for a `## Framing Brief` from analysis-framing.

**Detection rules** (all must be satisfied):
1. `## Framing Brief` heading exists in conversation
2. `### テーマ` subsection exists under Framing Brief
3. `### 推奨方向` subsection exists under Framing Brief
4. `theme_id:` field exists within the 推奨方向 section
5. If multiple Framing Briefs exist, use the last (most recent) one

**If valid Framing Brief found:**

Map Brief sections to analysis-design fields as draft values:

| Framing Brief セクション | analysis-design フィールド | マッピング |
|---|---|---|
| テーマ | `title` | テーマの1行要約を title の候補として提示 |
| 利用可能データ | `explanatory`, `metrics` | データソース・カラムから explanatory/metrics の候補を生成 |
| 既存分析 | `parent_id` | 関連デザイン ID を parent_id の候補として提示 |
| ギャップ | `hypothesis_background` | ギャップ情報を仮説の背景・動機の下書きに活用 |
| 推奨方向.仮説の方向性 | `title`, `hypothesis_background` | 方向性から title 候補を生成し、背景の下書きに活用 |
| 推奨方向.theme_id | `theme_id` | デフォルト値として設定 |
| 推奨方向.parent_id | `parent_id` | デフォルト値として設定 |
| 推奨方向.analysis_intent | `analysis_intent` | デフォルト値として設定 |
| 推奨方向.推奨手法 | `methodology` | `{method: "推奨手法の値", reason: "Framing Brief の推奨"}` としてデフォルト設定 |

Present draft values to user: "Framing Brief の内容でよいか、修正したい点があるか"

Step 2 ではゼロからインタビューせず、draft 値を提示して確認しながら進める。

**If Framing Brief missing or incomplete:**
Framing Brief がない、または検出条件を満たさない場合は何もしない。Step 2 の通常インタビューフローに進む（後方互換）。不完全な場合はユーザーに通知: "Framing Brief が不完全なため通常フローで進めます"

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

## Chaining

| From | To | When |
|------|-----|------|
| /analysis-framing | → /analysis-design | Framing Brief 付きでフォワーディング |
| /analysis-design | → /analysis-journal | デザイン作成後: "推論過程を記録するなら /analysis-journal {id}" |
| /analysis-design | → /analysis-framing | データ不足で仮説の方向を再検討: "データを探し直すなら /analysis-framing" |
| /catalog-register | → /analysis-design | データ登録完了後にデザイン作成を続行 |
| /analysis-reflection | → /analysis-design | 派生仮説が明確な場合 |
| /analysis-revision | → /analysis-design | レビュー修正で大きな方針変更が必要な場合 |

## Language Rules
- Follow project CLAUDE.md language settings. Default to Japanese if no setting.
- Code, IDs, tool names, and YAML fields always stay in English.
- Hypothesis text follows the user's language (usually Japanese)

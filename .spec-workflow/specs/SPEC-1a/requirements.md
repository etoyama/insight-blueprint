# SPEC-1a: hypothesis-enrichment — Requirements

> **Spec ID**: SPEC-1a
> **Feature Name**: hypothesis-enrichment
> **Status**: completed (retroactive spec)
> **Created**: 2026-02-22
> **Depends On**: SPEC-1 (core-foundation)

---

## Introduction

SPEC-1a extends the `AnalysisDesign` model introduced in SPEC-1 with three enrichment fields
(`explanatory`, `chart`, `next_action`) that allow Claude Code to record the analytical plan
alongside each hypothesis. It also adds an `update_analysis_design()` MCP tool so Claude can
iteratively refine existing designs without recreating them. These additions are fully
backward-compatible — existing YAML files produced by SPEC-1 remain valid and load without
migration.

## Alignment with Product Vision

- **Lightweight analysis design docs**: `explanatory`, `chart`, and `next_action` capture
  the analytical intent (variables, visualizations, follow-up actions) in the same YAML
  document, reducing round-trips between tools and keeping the design self-contained.
- **Claude Code integration**: `update_analysis_design()` enables Claude to refine a hypothesis
  after collecting analyst feedback, supporting iterative EDA workflows without re-creating
  designs from scratch.
- **Spec Roadmap foundation**: The enrichment fields establish the schema that SPEC-2
  (catalog integration) and SPEC-3 (review workflow) will populate; SPEC-1a is a prerequisite
  for those specs.

## Requirements

### Requirement 1: 仮説エンリッチメントフィールド

**User Story:** As a data scientist, I want Claude to record the list of explanatory variables,
planned charts, and next analysis actions together with each hypothesis, so that the design
document is self-contained and I can hand it off or review it without switching to another
tool.

**FR-1: AnalysisDesign フィールド拡張**
- `AnalysisDesign` モデルに以下のフィールドを追加すること（すべて optional、デフォルト値あり）:
  - `explanatory: list[dict]` — 説明変数リスト（デフォルト: `[]`）
    - 各要素の推奨キー: `variable`, `description`, `dtype`, `source`（強制なし）
  - `chart: list[dict]` — 可視化計画リスト（デフォルト: `[]`）
    - 各要素の推奨キー: `type`, `x`, `y`, `title`（強制なし）
  - `next_action: dict | None` — 次ステップ記述（デフォルト: `None`）
    - 推奨キー: `action`, `target`, `rationale`（強制なし）
- 追加フィールドは後方互換であること:
  - SPEC-1 が生成した既存 YAML（これらのフィールドを含まない）は、デフォルト値で正常にロードされること
  - 既存 YAML の書き換えやマイグレーション処理は不要であること

**FR-2: create_analysis_design() オプションパラメータ拡張**
- 既存の `create_analysis_design()` MCP tool が新フィールドを optional パラメータとして受理すること:
  - `explanatory: list[dict] | None = None`
  - `chart: list[dict] | None = None`
  - `next_action: dict | None = None`
- パラメータ省略時はデフォルト値（空リスト、None）が使用されること
- 既存のシグネチャ（`title`, `hypothesis_statement`, `hypothesis_background`, `parent_id?`, `theme_id?`）は変更しないこと

#### Acceptance Criteria

1. WHEN `create_analysis_design()` is called without `explanatory`, `chart`, or `next_action`
   THEN a valid AnalysisDesign is created with `explanatory=[]`, `chart=[]`, `next_action=None`
2. WHEN `create_analysis_design()` is called with `explanatory=[{"variable": "age"}]`
   THEN the YAML file at `.insight/designs/` contains the `explanatory` field with that value
3. WHEN an existing YAML file produced by SPEC-1 (no enrichment fields) is loaded
   THEN it loads without error and enrichment fields are populated with their defaults
4. WHEN `AnalysisDesign` is instantiated from a YAML dict that lacks `explanatory`
   THEN `design.explanatory` equals `[]` (Pydantic default)

### Requirement 2: 分析設計の部分更新

**User Story:** As a data scientist, I want Claude to call `update_analysis_design()` with only
the fields I want to change, so that I can iteratively refine a hypothesis without losing
previously recorded data.

**FR-3: update_design() ビジネスロジック**
- `DesignService.update_design(design_id, **fields)` を実装すること:
  - 指定されたフィールドのみを上書きし、その他のフィールドは保持すること
  - `updated_at` は常に現在時刻（JST）に更新されること
  - Pydantic v2 の `model_copy(update=...)` パターンを使用すること
  - `design_id` が存在しない場合は `None` を返すこと（例外を raise しないこと）
  - 更新後の `AnalysisDesign` を YAML として保存し、返すこと

**FR-4: update_analysis_design() MCP Tool**
- Claude が呼び出せる MCP tool として `update_analysis_design()` を追加すること:
  - シグネチャ: `update_analysis_design(design_id, title?, hypothesis_statement?, hypothesis_background?, status?, metrics?, explanatory?, chart?, next_action?) → dict`
  - すべてのフィールドパラメータは optional（`None` 省略時は更新しない）
  - 成功時: 更新後の AnalysisDesign を dict として返す
  - `design_id` 不存在時: `{"error": "Design '{design_id}' not found"}` を返す（例外なし）
  - `status` に不正値が指定された場合: `{"error": "Invalid status '{status}'"}` を返す
  - `None` フィールドは更新対象から除外すること（False や空文字列は更新対象とする）

#### Acceptance Criteria

1. WHEN `update_analysis_design("FP-H01", title="New Title")` is called on an existing design
   THEN only `title` and `updated_at` are changed; all other fields retain their previous values
2. WHEN `update_analysis_design("FP-H01", explanatory=[{"variable": "age"}])` is called
   THEN the YAML file is updated and `design.explanatory == [{"variable": "age"}]`
3. WHEN `update_analysis_design("NONE-H99")` is called for a non-existent design
   THEN `{"error": "Design 'NONE-H99' not found"}` is returned (no exception raised)
4. WHEN `update_analysis_design("FP-H01", status="invalid_value")` is called
   THEN `{"error": "Invalid status 'invalid_value'"}` is returned
5. WHEN `update_analysis_design("FP-H01")` is called with no field arguments
   THEN only `updated_at` is refreshed and all other fields remain unchanged
6. WHEN `update_analysis_design("FP-H01", next_action={"action": "collect more data"})` is called
   THEN `design.next_action == {"action": "collect more data"}`

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility Principle**: フィールド追加は `models/design.py` のみ、ビジネスロジックは `core/designs.py` のみ、MCP tool は `server.py` のみを修正すること
- **Backward Compatibility**: 新フィールドはすべて Pydantic `Field(default_factory=...)` または `= None` とし、既存 YAML の読み込みを壊さないこと
- **YAGNI**: フィールドの型は `list[dict]` / `dict | None` とし、サブモデル（`ExplanatoryVariable`, `ChartSpec` 等）は SPEC-3 以降まで導入しないこと
- **Type Annotations**: すべての関数に完全な型アノテーションを付与すること（`ty check` エラーゼロ）

### Performance

- `update_analysis_design()` は 100ms 以内に完了すること（ローカル YAML 読み書き）
- モデルへのフィールド追加は startup time に影響しないこと

### Security

- フィールド値（`list[dict]`）にシェルコマンドや SQL クエリが含まれていても、ストレージ層はそのまま YAML に保存するだけであること（実行しないこと）
- MCP tool のエラーレスポンスにスタックトレースや内部ファイルパスを含めないこと

### Reliability

- `update_design()` は `write_yaml()` の atomic write（`tempfile.mkstemp()` + `os.replace()`）を経由するため、クラッシュ時に元ファイルが破損しないこと
- `model_copy(update=...)` は新しいオブジェクトを生成するため、更新中の元データは変更されないこと

### Usability

- `update_analysis_design()` の docstring は Claude が各パラメータの意味を正確に把握できる程度に記述すること
- `explanatory`, `chart`, `next_action` フィールドのキー構造はドキュメント上「推奨」であり、Claude が任意の dict 構造を渡せること

## Out of Scope

- `data_source` フィールドの追加（SPEC-2: catalog integration で実装）
- `ExplanatoryVariable`, `ChartSpec` 等の型付きサブモデル（SPEC-3 以降）
- `explanatory` / `chart` の JSON Schema バリデーション（SPEC-3 以降）
- レビューワークフロー（SPEC-3）
- WebUI での enrichment フィールド表示（SPEC-4）

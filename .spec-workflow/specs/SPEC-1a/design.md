# SPEC-1a: hypothesis-enrichment — 設計

> **Spec ID**: SPEC-1a
> **Status**: completed (retroactive spec)
> **Created**: 2026-02-22
> **Depends On**: SPEC-1 (core-foundation)

---

## 概要

SPEC-1a は SPEC-1 で確立した 3 層アーキテクチャ（CLI → MCP → Core → Storage）を壊さずに
`AnalysisDesign` モデルを拡張し、`update_analysis_design()` MCP ツールを追加する。
変更対象は `models/design.py`・`core/designs.py`・`server.py`・`_skills/analysis-design/SKILL.md`
の 4 ファイルのみであり、ストレージ層・CLI・テストインフラは変更しない。

## ステアリングドキュメントとの整合

### 技術標準（tech.md）

- **YAGNI**: フィールド型は `list[dict]` / `dict | None` とし、`ExplanatoryVariable` や
  `ChartSpec` 等の型付きサブモデルは SPEC-3 以降まで導入しない
- **Pydantic v2**: `model_copy(update=...)` パターンで部分更新を実現。`model.copy()` (v1 API)
  は使用しない
- **アトミック書き込み**: `update_design()` も `write_yaml()` を経由することで、
  SPEC-1 のクラッシュセーフ保証を引き継ぐ
- **型アノテーション**: すべての関数・メソッドに完全な型アノテーションを付与し、`ty check` エラーゼロを維持
- **TDD**: 各変更はテストファースト（Red → Green → Refactor）で実装

### プロジェクト構造（structure.md）

- **単方向依存の維持**: `server.py` → `core/designs.py` → `storage/` の依存方向は変わらない
- **ファイル単一責任**: フィールド追加は `models/design.py`、ビジネスロジックは `core/designs.py`、
  MCP ツールは `server.py` にのみ変更を加える

## コード再利用分析

### 活用できる既存コンポーネント

- **`models/design.py: AnalysisDesign`**: 既存モデルに 3 フィールドを追記するのみ。
  Pydantic の `Field(default_factory=list)` と `= None` デフォルトで後方互換を保証する
- **`core/designs.py: DesignService`**: `update_design()` を追加する。
  `get_design()` / `write_yaml()` の既存実装を内部で再利用する
- **`storage/yaml_store.py: write_yaml()`**: `update_design()` の永続化に再利用。
  ストレージ層の変更なし
- **`models/common.py: now_jst()`**: `update_design()` での `updated_at` 更新に再利用

### 統合ポイント

- **`server.py: update_analysis_design()`**: SPEC-1 の `create_analysis_design()` / `get_analysis_design()`
  と同じ `get_service()` パターンを踏襲する
- **既存テスト**: `tests/test_designs.py` / `tests/test_server.py` に SPEC-1a 向けのテストケースを追記する

## アーキテクチャ

### モジュラー設計原則

- **ファイル単一責任**: 追加フィールドは `models/design.py` のみ。`update_design()` は `core/designs.py` のみ。
  MCP ツールは `server.py` のみ。一切の層越えは行わない
- **コンポーネント分離**: `DesignService.update_design()` は `server.py` や `cli.py` を知らない。
  独立してユニットテスト可能
- **サービス層分離**: `update_analysis_design()` (MCP tool) → `update_design()` (DesignService)
  → `write_yaml()` (yaml_store) の 3 段を維持

```
Claude Code (AI Client)
       |
  stdio (MCP Protocol)
       |
  server.py
    ├── create_analysis_design(... explanatory?, chart?, next_action?)  [SPEC-1 + 拡張]
    ├── update_analysis_design(design_id, *fields)                      [SPEC-1a 新規]
    ├── get_analysis_design(design_id)
    └── list_analysis_designs(status?)
           ↓
  core/designs.py: DesignService
    ├── create_design(... explanatory?, chart?, next_action?)            [SPEC-1 + 拡張]
    └── update_design(design_id, **fields) → AnalysisDesign | None      [SPEC-1a 新規]
           ↓
  storage/yaml_store.py
    └── write_yaml()  [変更なし]
           ↓
  .insight/designs/{id}_hypothesis.yaml
```

### 設計決定: `list[dict]` / `dict | None` で YAGNI

**選択**: `explanatory: list[dict]`、`chart: list[dict]`、`next_action: dict | None`

**理由**: 現時点でバリデーションが必要な上位呼び出し元（Claude Code）は辞書構造を知っている。
型付きサブモデル（`ExplanatoryVariable`, `ChartSpec` 等）を今導入しても、
SPEC-3 でレビューワークフローが確定する前に破壊的変更が生じるリスクがある。
`list[dict]` は「いつでも型付きサブモデルに昇格できる」経路を閉じない。

### 設計決定: `model_copy(update=...)` パターン

**選択**: `updated = design.model_copy(update={**fields, "updated_at": now_jst()})`

**理由**:
- Pydantic v2 の推奨 API（`model.copy()` は v1 互換の非推奨 API）
- `update` dict のキーのみが上書きされ、他フィールドは元の値を引き継ぐ
- イミュータブルな操作のため、更新中に元オブジェクトが変更されない
- `now_jst()` をこの時点で注入することで `updated_at` の更新漏れを防ぐ

### 設計決定: `None` 引数のスキップ

`update_analysis_design()` MCP ツールでは、`None` の引数を更新対象から除外する:

```python
updates = {k: v for k, v in {...}.items() if v is not None}
```

**理由**: MCP プロトコルでは省略パラメータが `None` として渡される。
`None` を「フィールドを `None` にセット」と解釈すると、
`next_action` を `None` に戻す操作が「引数省略」と区別できなくなる。
SPEC-1a では「省略 = 変更しない」のセマンティクスを採用し、
将来の「明示的に None をセット」ユースケースは SPEC-3 以降で対応する。

## コンポーネントとインターフェース

### `models/design.py` (拡張)

- **目的**: `AnalysisDesign` に 3 つの enrichment フィールドを追加。後方互換保証
- **変更内容**:
  ```python
  explanatory: list[dict] = Field(default_factory=list)
  chart: list[dict] = Field(default_factory=list)
  next_action: dict | None = None
  ```
- **依存関係**: 変更なし
- **後方互換**: Pydantic がデフォルト値を補完するため、既存 YAML（フィールドなし）は変更なしにロードされる

### `core/designs.py: DesignService` (拡張)

- **目的**: `update_design()` の追加。`create_design()` の optional パラメータ拡張
- **インターフェース追加**:
  - `update_design(design_id: str, **fields: object) -> AnalysisDesign | None`
    - `get_design()` で現在値を取得 → `model_copy(update=...)` で新オブジェクト生成 → `write_yaml()` で永続化
    - 存在しない `design_id` → `None` を返す（例外なし）
  - `create_design()` に `explanatory`, `chart`, `next_action` optional params 追加
- **依存関係**: `models/common.py:now_jst`（追加）、他は変更なし
- **再利用**: `get_design()`, `write_yaml()` を内部で再利用

### `server.py: update_analysis_design()` (新規)

- **目的**: `update_design()` を Claude から呼び出せる MCP ツールとして公開
- **インターフェース**:
  ```python
  async def update_analysis_design(
      design_id: str,
      title: str | None = None,
      hypothesis_statement: str | None = None,
      hypothesis_background: str | None = None,
      status: str | None = None,
      metrics: dict | None = None,
      explanatory: list[dict] | None = None,
      chart: list[dict] | None = None,
      next_action: dict | None = None,
  ) -> dict
  ```
- **戻り値**:
  - 成功: `design.model_dump(mode="json")`（全フィールド含む完全な dict）
  - `design_id` 不存在: `{"error": "Design '{design_id}' not found"}`
  - 不正 `status`: `{"error": "Invalid status '{status}'"}`
- **依存関係**: `core/designs.py:DesignService`、`models/design.py:DesignStatus`

### `_skills/analysis-design/SKILL.md` (更新)

- **目的**: Claude に `update_analysis_design()` ツールの存在と使い方を伝える
- **変更内容**: Step 2 テーブルに `update_analysis_design` 行を追加、ツールリファレンスセクションを更新

## データモデル

### 拡張後の `.insight/designs/{id}_hypothesis.yaml`

```yaml
id: FP-H01
theme_id: FP
title: Foreign population vs crime rate correlation
hypothesis_statement: No positive correlation exists between...
hypothesis_background: |
  ...
status: draft
parent_id: null
metrics: {}
explanatory:
  - variable: foreign_population_ratio
    description: Prefecture-level ratio of foreign residents
    dtype: float
    source: e-stat stat_id:00200521
chart:
  - type: scatter
    x: foreign_population_ratio
    y: crime_rate_per_10k
    title: Foreign Population vs Crime Rate
next_action:
  action: collect_data
  target: e-stat API
  rationale: Need official prefecture-level statistics
created_at: "2026-02-22T10:00:00+09:00"
updated_at: "2026-02-22T10:15:00+09:00"
```

**後方互換**: SPEC-1 が生成した既存 YAML（`explanatory`/`chart`/`next_action` なし）は
Pydantic がデフォルト値（`[]`, `[]`, `None`）で補完するため変更不要。

## エラーハンドリング

1. **`design_id` 不存在** — `update_analysis_design("NONE-H99")` で設計が存在しない場合
   - **ハンドリング**: `DesignService.update_design()` が `None` を返す。`server.py` が `{"error": "Design 'NONE-H99' not found"}` に変換する
   - **ユーザーへの影響**: Claude がエラー dict を受け取り、IDが不正であることをアナリストに伝える

2. **不正な `status` 値** — `update_analysis_design("FP-H01", status="invalid")` の場合
   - **ハンドリング**: `DesignStatus("invalid")` が `ValueError` を raise。`server.py` が `{"error": "Invalid status 'invalid'"}` に変換する
   - **ユーザーへの影響**: Claude が有効なステータス値（draft/active/supported/rejected/inconclusive）をアナリストに案内する

3. **引数なし呼び出し** — `update_analysis_design("FP-H01")` でフィールド引数がすべて `None` の場合
   - **ハンドリング**: `updates` dict が空 → `model_copy(update={"updated_at": now_jst()})` のみが実行される。設計は `updated_at` だけ更新されて返却される
   - **ユーザーへの影響**: 冪等に近い動作（`updated_at` のみ変化）。エラーにはならない

4. **YAML 書き込み失敗** — `write_yaml()` 実行中に I/O エラーが発生した場合
   - **ハンドリング**: SPEC-1 と同じ — `os.replace()` が呼ばれる前に失敗するため、元ファイルは保全される
   - **ユーザーへの影響**: `update_analysis_design()` が MCP エラーレスポンスを返す。リトライ可能

## テスト戦略

### ユニットテスト

**`tests/test_designs.py` への追加テストケース:**
- `test_create_design_with_enrichment_fields` — `explanatory`, `chart`, `next_action` 付き作成
- `test_create_design_without_enrichment_defaults_to_empty` — 省略時のデフォルト確認
- `test_update_design_changes_only_specified_fields` — 部分更新の正確性
- `test_update_design_refreshes_updated_at` — `updated_at` の自動更新
- `test_update_design_returns_none_for_missing_id` — 不存在 ID で `None`
- `test_update_design_with_no_fields_only_updates_timestamp` — フィールドなし呼び出し

**`tests/test_server.py` への追加テストケース:**
- `test_update_analysis_design_partial_update` — 1 フィールドのみ更新
- `test_update_analysis_design_returns_error_for_missing_design` — 不存在 ID
- `test_update_analysis_design_returns_error_for_invalid_status` — 不正 status
- `test_update_analysis_design_updates_enrichment_fields` — `explanatory`/`chart`/`next_action` 更新

### インテグレーションテスト

- `tests/test_integration.py` への追加:
  - `create_design()` → `update_design()` → `get_design()` のラウンドトリップで部分更新が保存されることを確認
  - 既存 YAML（enrichment フィールドなし）をロードし、デフォルト値が補完されることを確認

### E2E テスト

MCP プロトコル E2E テストは SPEC-1a のスコープ外（SPEC-1 と同様の方針）。
ユニット + インテグレーションテストが全 AC をカバーする。

### AC × テストケース 対応表

| AC | 内容（要約） | テストケース | ファイル |
|----|-------------|-------------|---------|
| 1-1 | enrichment フィールドなし作成 → デフォルト値 | `test_create_design_without_enrichment_defaults_to_empty` | `test_designs.py` |
| 1-2 | `explanatory` 付き作成 → YAML に保存 | `test_create_design_with_enrichment_fields` | `test_designs.py` |
| 1-3 | 既存 YAML（フィールドなし）ロード → エラーなし | `test_integration.py` でラウンドトリップ確認 | `test_integration.py` |
| 1-4 | `AnalysisDesign(...)` フィールドなし → `explanatory==[]` | `test_create_design_without_enrichment_defaults_to_empty` | `test_designs.py` |
| 2-1 | 1 フィールドのみ更新 → 他は保持 | `test_update_design_changes_only_specified_fields` | `test_designs.py` |
| 2-2 | `explanatory` 更新 → YAML に保存 | `test_update_analysis_design_updates_enrichment_fields` | `test_server.py` |
| 2-3 | 不存在 ID → error dict | `test_update_analysis_design_returns_error_for_missing_design` | `test_server.py` |
| 2-4 | 不正 status → error dict | `test_update_analysis_design_returns_error_for_invalid_status` | `test_server.py` |
| 2-5 | フィールドなし呼び出し → `updated_at` のみ変化 | `test_update_design_with_no_fields_only_updates_timestamp` | `test_designs.py` |
| 2-6 | `next_action` 更新 → 保存確認 | `test_update_analysis_design_updates_enrichment_fields` | `test_server.py` |

# Requirements: YAML Direct Edit Resilience

## Introduction

AnalysisDesign の YAML ファイルは分析者の思考記録であり、MCP tool 経由が推奨パスだが、vim 等での直接編集は避けられない。現状2つの致命的問題がある:

1. **サイレントデータロス (F1)**: 分析者が YAML に追加したカスタムフィールドが、MCP tool 経由の更新時に無言で消失する
2. **全体クラッシュ (F2)**: 1つの YAML ファイルに不正値があると、一覧取得を含むシステム全体が停止する

本 spec はこの2問題を解消し、「MCP tool 経由を推奨パスに維持しつつ、直接編集を壊さない」状態を実現する。

## Alignment with Product Vision

- **Product Principle #2 "YAML as Source of Truth"**: YAML が人間の読み書き可能なフォーマットである以上、人間が直接編集することは設計上の正当な行為。その行為でデータが消えるのは原則に反する
- **Product Principle #5 "後方互換の優先"**: 既存データを壊さない原則の拡張として、ユーザーが追加したデータも壊さない
- **Business Objective "分析の再現性向上"**: 分析者のメモ・注記が消えると、分析の文脈が失われ再現性が低下する

## Requirements

### REQ-1: Extra Field Preservation

**User Story:** As a data analyst, I want my custom fields added to YAML files to survive MCP tool updates, so that my notes and annotations are not silently lost.

#### Functional Requirements

- **FR-1.1**: AnalysisDesign モデルのスキーマに定義されていないトップレベルフィールドが、`model_dump()` の出力に含まれること
- **FR-1.2**: Metric, ExplanatoryVariable, ChartSpec, Methodology の各サブモデルについても、スキーマ外フィールドが `model_dump()` の出力に含まれること
- **FR-1.3**: `update_design()` による部分更新後、更新対象外の extra フィールドが YAML ファイルに保持されること
- **FR-1.4**: `create_design()` → `get_design()` の round-trip で extra フィールドが保持されること（YAML に手動追加した場合）

#### Acceptance Criteria

- **AC-1.1**: WHEN an AnalysisDesign YAML file contains a field not in the schema (e.g., `analyst_note: "..."`) THEN `get_design()` SHALL return an AnalysisDesign whose `model_dump()` includes that field
- **AC-1.2**: WHEN a Metric entry in YAML contains a field not in the Metric schema (e.g., `note: "seasonal adjustment needed"`) THEN `model_dump()` of the parent AnalysisDesign SHALL include that field nested under the corresponding metric
- **AC-1.3**: WHEN `update_design(id, title="new title")` is called on a design whose YAML contains extra fields THEN the resulting YAML file SHALL contain both the updated `title` and the preserved extra fields
- **AC-1.4**: WHEN a ChartSpec entry contains an extra field AND `update_design()` modifies a different field THEN the ChartSpec extra field SHALL be preserved in the written YAML
- **AC-1.5**: WHEN an ExplanatoryVariable entry contains an extra field THEN `model_dump()` SHALL include that field
- **AC-1.6**: WHEN a Methodology object contains an extra field THEN `model_dump()` SHALL include that field

### REQ-2: Corrupt File Isolation

**User Story:** As a data analyst, I want one corrupted YAML file not to crash the entire system, so that I can continue working with my other analysis designs.

#### Functional Requirements

- **FR-2.1**: `list_designs()` が、バリデーションエラーのあるファイルをスキップし、正常なファイルのみを返すこと
- **FR-2.2**: `list_designs()` が、スキップしたファイルについて warning レベルのログを出力すること
- **FR-2.3**: `get_design()` が、バリデーションエラーのあるファイルに対して、エラー内容を含む例外を発生させること（`None` を返さない）
- **FR-2.4**: REST API が、corrupt design の取得時に 422 ステータスコードとエラー詳細を返すこと

#### Acceptance Criteria

- **AC-2.1**: WHEN `.insight/designs/` contains 3 valid YAML files and 1 file with an invalid enum value THEN `list_designs()` SHALL return exactly 3 AnalysisDesign objects
- **AC-2.2**: WHEN `list_designs()` skips a corrupt file THEN a warning log message SHALL be emitted containing the filename
- **AC-2.3**: WHEN `list_designs()` encounters a file with a missing required field (e.g., no `id`) THEN it SHALL skip that file and continue processing remaining files
- **AC-2.4**: WHEN `get_design("CORRUPT-H01")` is called for a design whose YAML has invalid data THEN the system SHALL raise an exception with the validation error details (not return `None`)
- **AC-2.5**: WHEN REST API `GET /api/designs/{id}` is called for a corrupt design THEN the response SHALL have status 422 and include a JSON body with an `error` field describing the validation failure
- **AC-2.6**: WHEN `list_designs(status="in_review")` is called and a corrupt file exists THEN only valid designs matching the filter SHALL be returned, and the corrupt file SHALL be skipped

## Non-Functional Requirements

### Code Architecture and Modularity

- **NFR-A.1**: extra フィールドの保全は model 層 (`models/design.py`) で解決する。service 層に deep merge ロジックを追加しない
- **NFR-A.2**: corrupt file の isolation は service 層 (`core/designs.py`) で解決する。model 層はバリデーションエラーを正常に発生させる責務を維持する
- **NFR-A.3**: REST API 層の変更は `web.py` に閉じる。MCP 層 (`server.py`) の既存エラーハンドリングは変更しない

### Performance

- **NFR-P.1**: extra フィールドの保全が既存の YAML read/write のパフォーマンスを劣化させないこと（測定不可能な差に収まること）
- **NFR-P.2**: `list_designs()` の corrupt file skip が、正常ファイルの処理速度に影響しないこと

### Backward Compatibility

- **NFR-B.1**: 既存の 681 テストが全て通ること
- **NFR-B.2**: 既存の Pydantic coercion（dict → Metric, str → StrEnum 等）が維持されること
- **NFR-B.3**: 既存の `model_validator`（`_migrate_metrics`, `_infer_intent_from_type`）が維持されること
- **NFR-B.4**: `extra="allow"` による typo 黙認リスクは、MCP tool / REST API の入口にある別バリデーションモデル (`DesignCreateBody`, `DesignUpdateBody`) で吸収されること（既存の防御が機能すること）

### Reliability

- **NFR-R.1**: corrupt ファイルの存在がシステムの起動・通常運用を阻害しないこと

## Out of Scope

- **スキーマ検証コマンド** (`validate` サブコマンド等): F3 として別 spec で対応
- **分析テンプレート機構**: F4 として別 spec で対応
- **MCP tool の追加・変更**: extension-policy の tool cap (17個) を維持
- **MCP 層 (`server.py`) のエラーハンドリング変更**: 既存の `except Exception` ブロックで対応済み
- **WebUI での corrupt ファイル警告表示**: REST API が 422 を返すところまでが本 spec のスコープ

## Glossary

| Term | Definition |
|------|-----------|
| Extra field | Pydantic モデルのスキーマに定義されていない、ユーザーが YAML に直接追加したフィールド |
| Corrupt file | Pydantic の ValidationError を引き起こす YAML ファイル（不正な enum 値、必須フィールド欠損等） |
| Round-trip | YAML → Pydantic model → model_dump() → YAML の変換サイクル。データが変化しないことが期待される |
| MCP tool path | `server.py` の tool 関数 → `core/` の service メソッド → `storage/` の read/write を経由するデータフロー |
| Direct edit path | 分析者が vim 等で `.insight/designs/*.yaml` を直接編集するデータフロー |

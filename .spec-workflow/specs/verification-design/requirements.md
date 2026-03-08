# Requirements Document

## Introduction

AnalysisDesign の `explanatory`、`metrics`、`chart` フィールドは現在 `dict` / `list[dict]` で定義されており、スキーマ検証がない。分析設計の「検証手段」を構造化するため、これらのフィールドに Pydantic BaseModel + StrEnum による型付けを導入する。加えて、analysis-journal の `decide` イベントで記録される手法・パッケージ情報を AnalysisDesign モデルに `methodology` フィールドとして昇格させる。

## Alignment with Product Vision

- **分析の再現性向上**: 検証手段（変数の役割、指標の優先度、可視化の意図、手法）を構造化することで、分析設計の再現性を高める
- **知見の蓄積と再利用**: 型付けにより、変数の因果的役割や指標の重要度が検索・フィルタリング可能になる
- **Claude Code First**: MCP ツールの入力スキーマが型で導かれ、SKILL が生成するデータの品質が向上する
- **YAML as Source of Truth**: Pydantic モデルから YAML へのシリアライズは既存パターン（StrEnum + BaseModel）と一致する
- **後方互換の優先**: 既存 YAML データは Pydantic の coercion と model_validator で自動変換。デフォルト値によりフィールド未指定でも読み込み可能

## Requirements

### REQ-1: Explanatory Variable の型付け

**User Story:** As a データアナリスト, I want 説明変数に因果的役割（treatment/confounder/covariate/instrumental/mediator）を指定できること, so that 分析設計の変数構成が明示的になり、レビュー時に検証戦略の妥当性を判断できる

#### Functional Requirements

- FR-1.1: `VariableRole` StrEnum を定義する（値: treatment, confounder, covariate, instrumental, mediator）
- FR-1.2: `ExplanatoryVariable` Pydantic BaseModel を定義する（フィールド: name, description, role, data_source, time_points）
- FR-1.3: `AnalysisDesign.explanatory` の型を `list[dict]` から `list[ExplanatoryVariable]` に変更する
- FR-1.4: `role` フィールドのデフォルト値は `VariableRole.covariate` とし、既存データとの後方互換を保つ

#### Acceptance Criteria

- AC-1.1: WHEN `role` フィールドなしの dict を含む YAML を読み込む THEN システムは `role: covariate` をデフォルトで適用し、正常に `ExplanatoryVariable` オブジェクトを生成する SHALL
- AC-1.2: WHEN `role` に `VariableRole` に存在しない値を指定する THEN システムは Pydantic ValidationError を送出する SHALL
- AC-1.3: WHEN 有効な `ExplanatoryVariable` オブジェクトを YAML にシリアライズする THEN `role` フィールドが文字列として正しく保存される SHALL
- AC-1.4: WHEN MCP ツール `create_design` / `update_design` で `explanatory` を指定する THEN dict のリストと `ExplanatoryVariable` のリストの両方を受け付ける SHALL

### REQ-2: Metrics の型付けとリスト化

**User Story:** As a データアナリスト, I want 検証指標に優先度（primary/secondary/guardrail）を付与し、複数指標を管理できること, so that 主要な検証指標とガードレール指標を区別し、分析結果の判定基準を明確にできる

#### Functional Requirements

- FR-2.1: `MetricTier` StrEnum を定義する（値: primary, secondary, guardrail）
- FR-2.2: `Metric` Pydantic BaseModel を定義する（フィールド: target, tier, data_source, grouping, filter, aggregation, comparison）
- FR-2.3: `AnalysisDesign.metrics` の型を `dict` から `list[Metric]` に変更する
- FR-2.4: 既存の単一 dict 形式の `metrics` を `list[Metric]` に自動変換する model_validator を実装する
- FR-2.5: `tier` フィールドのデフォルト値は `MetricTier.primary` とする

#### Acceptance Criteria

- AC-2.1: WHEN `metrics` が単一 dict（`{"target": "...", ...}` 形式）の YAML を読み込む THEN システムは自動的に `[Metric(**dict)]` に変換する SHALL
- AC-2.2: WHEN `metrics` が list 形式の YAML を読み込む THEN 各要素を `Metric` オブジェクトに変換する SHALL
- AC-2.3: WHEN `metrics` が空 dict `{}` の YAML を読み込む THEN 空リスト `[]` として扱う SHALL
- AC-2.4: WHEN `tier` フィールドなしの dict を含む YAML を読み込む THEN `tier: primary` をデフォルトで適用する SHALL
- AC-2.5: WHEN MCP ツールで `metrics` を dict 形式で指定する THEN 自動的に `list[Metric]` に変換して保存する SHALL

### REQ-3: Chart の Intent 駆動化

**User Story:** As a データアナリスト, I want 可視化に分析意図（distribution/correlation/trend/comparison）を指定できること, so that チャートの目的が明示的になり、出力形式（scatter/bar/line 等）の選択根拠が記録される

#### Functional Requirements

- FR-3.1: `ChartIntent` StrEnum を定義する（値: distribution, correlation, trend, comparison）
- FR-3.2: `ChartSpec` Pydantic BaseModel を定義する（フィールド: intent, type, description, x, y）
- FR-3.3: `AnalysisDesign.chart` の型を `list[dict]` から `list[ChartSpec]` に変更する
- FR-3.4: 既存の `intent` フィールドなし dict に対して、`type` フィールドの値から intent を推定する後方互換ロジックを実装する

#### Acceptance Criteria

- AC-3.1: WHEN `intent` フィールドなしで `type: scatter` の dict を読み込む THEN システムは `intent: correlation` を推定して適用する SHALL
- AC-3.2: WHEN `intent` フィールドなしで `type: table` の dict を読み込む THEN システムは `intent: comparison` を推定して適用する SHALL
- AC-3.3: WHEN `intent` フィールドなしで推定不可能な `type` の dict を読み込む THEN システムは `intent: distribution` をデフォルトとして適用する SHALL
- AC-3.4: WHEN 有効な `ChartSpec` オブジェクトを YAML にシリアライズする THEN `intent` と `type` の両方が保存される SHALL

### REQ-4: Methodology フィールドの追加

**User Story:** As a データアナリスト, I want 分析設計に使用する手法・パッケージを記録できること, so that 分析の再現性が向上し、レビュー時に手法の妥当性を判断できる

#### Functional Requirements

- FR-4.1: `Methodology` Pydantic BaseModel を定義する（フィールド: method, package, reason）
- FR-4.2: `AnalysisDesign` に `methodology: Methodology | None = None` フィールドを追加する
- FR-4.3: `methodology` は任意フィールドとし、既存データに影響を与えない

#### Acceptance Criteria

- AC-4.1: WHEN `methodology` フィールドなしの YAML を読み込む THEN `methodology` は `None` として扱う SHALL
- AC-4.2: WHEN `methodology` を dict 形式で指定する THEN `Methodology` オブジェクトに自動変換する SHALL
- AC-4.3: WHEN `methodology` の `method` フィールドが空文字列 THEN Pydantic ValidationError を送出する SHALL
- AC-4.4: WHEN MCP ツール `update_design` で `methodology` を指定する THEN 設計書に手法情報が保存される SHALL

### REQ-5: Frontend 型定義の同期

**User Story:** As a 開発者, I want フロントエンドの TypeScript 型定義が Python モデルと同期していること, so that 型の不整合による実行時エラーを防止できる

#### Functional Requirements

- FR-5.1: `frontend/src/types/api.ts` に `ExplanatoryVariable`, `Metric`, `ChartSpec`, `Methodology` の TypeScript 型を追加する
- FR-5.2: `AnalysisDesign` 型の `explanatory`, `metrics`, `chart` フィールドを型付き定義に更新する
- FR-5.3: `VariableRole`, `MetricTier`, `ChartIntent` の TypeScript enum / union 型を追加する

#### Acceptance Criteria

- AC-5.1: WHEN フロントエンドをビルドする THEN TypeScript コンパイルエラーが発生しない SHALL
- AC-5.2: WHEN REST API から `AnalysisDesign` を取得する THEN レスポンスが TypeScript 型定義と一致する SHALL

### REQ-6: SKILL ドキュメントの更新

**User Story:** As a Claude Code, I want analysis-design スキルのフィールド例が型付きモデルに更新されていること, so that SKILL 実行時に正しい構造のデータを生成できる

#### Functional Requirements

- FR-6.1: `analysis-design/SKILL.md` の `explanatory`, `metrics`, `chart` フィールド例を型付きモデルの構造に更新する
- FR-6.2: `analysis-design/SKILL.md` に `methodology` フィールドの使用例を追加する
- FR-6.3: `analysis-journal/SKILL.md` の `decide` イベントに、`methodology` フィールドへの昇格導線を記載する

#### Acceptance Criteria

- AC-6.1: WHEN analysis-design スキルのフィールド例を参照する THEN `role`, `tier`, `intent` フィールドが含まれている SHALL
- AC-6.2: WHEN analysis-journal の decide イベントを記録した後 THEN methodology フィールドへの昇格手順が SKILL.md に記載されている SHALL

## Non-Functional Requirements

### Code Architecture and Modularity

- 新規モデル（`ExplanatoryVariable`, `Metric`, `ChartSpec`, `Methodology`）は既存の `models/design.py` に追加する（1ファイル = 1ドメイン領域の原則に従う）
- StrEnum は既存パターン（`DesignStatus`, `AnalysisIntent`, `KnowledgeCategory`）と一貫した定義方法を使う
- model_validator は `AnalysisDesign` クラス内に定義し、外部関数に切り出さない

### Performance

- モデルのバリデーション処理が既存の MCP ツールレスポンス時間（500ms 以内）に影響を与えないこと
- Pydantic の coercion / validator は初回 YAML 読み込み時のみ実行される

### Security

- 新規フィールドに外部入力が直接渡される箇所がないこと（MCP ツール経由のみ）

### Reliability

- 既存の 624 テストが全て通ること（後方互換の検証）
- 新規モデルに対するテストカバレッジ 80% 以上

### Maintainability

- 全モデルに型ヒントを付与すること
- StrEnum の値追加は後方互換を保つ（デフォルト値の設定）

## Out of Scope

- **analysis-journal の decide イベントから methodology への自動昇格機能**: 本スペックでは methodology フィールドの追加と SKILL ドキュメントの導線記載のみ。自動昇格のロジック実装は対象外
- **WebUI での新規フィールドの表示変更**: extension-policy により WebUI は Fixed Scope。型定義の同期のみ実施し、UI コンポーネントの変更は行わない
- **MCP ツールの追加**: extension-policy により MCP 17個の soft cap を維持。既存ツールのスキーマ変更のみ
- **VariableRole / MetricTier / ChartIntent に基づくバリデーションロジック**: 例えば「treatment は1つだけ」等の制約は本スペック対象外
- **Metric の統計的検定パラメータ**: 検定手法（t検定、カイ二乗等）の詳細パラメータは methodology に委ね、Metric には含めない

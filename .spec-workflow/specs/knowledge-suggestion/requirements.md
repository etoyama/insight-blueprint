# Requirements Document: Knowledge Suggestion

## Introduction

分析設計（AnalysisDesign）の各セクション作成時に、過去の分析から蓄積された Knowledge を自動サジェストし、参照した Knowledge のトレーサビリティを確保する機能。

### 背景

現状の Knowledge 管理には以下の課題がある:

1. **活用の仕組みがない**: `get_project_context()` で全 knowledge を一括取得するか、`suggest_cautions()` で `affects_columns` マッチするだけ。分析設計の各セクションに適した knowledge を自動提示する仕組みがない
2. **分析結果が knowledge 化されない**: 仮説が Supported/Rejected/Inconclusive になっても、その結果が自動的に knowledge として蓄積されない。次回の分析で先行知見を参照する手段がない
3. **トレーサビリティがない**: 分析設計がどの knowledge を参照して書かれたかが記録されず、レビュー時に参照の適切性を検証できない

### 設計方針

- **カテゴリ最小化 + マッチング戦略分離**: KnowledgeCategory に `finding` を1つ追加するのみ。サジェスト精度はカテゴリの細分化ではなくマッチング戦略（theme_id / lineage / source_ids / FTS5）で担保する
- **後方互換**: 既存の methodology, caution, definition, context カテゴリおよび既存データに変更なし

## Alignment with Product Vision

本機能は `steering/product.md` の以下の目標に直接貢献する:

### Business Objectives との対応

| Product Objective | 本機能での実現 |
|---|---|
| **知見の蓄積と再利用** | FR-2 (finding 自動抽出) で分析結果を自動蓄積、FR-3 (suggest_knowledge_for_design) で次回分析に自動反映 |
| **分析の再現性向上** | FR-4 (referenced_knowledge) で参照した知見を記録し、第三者が再現時に同じ知見を参照可能に |
| **レビュー品質の標準化** | FR-5 (レビューでの参照適切性指摘) で知見の引用が適切かをレビュー対象に含める |

### Success Metrics への貢献

- **Knowledge 蓄積率 (目標: 80%以上)**: FR-2 により terminal ステータス到達時に自動で finding を抽出。手動作業不要で蓄積率を引き上げる
- **知見の再利用率 (目標: 50%以上)**: FR-3 により新規分析設計の各セクション作成時に過去の knowledge を自動サジェスト。FR-4 で実際に参照されたかを計測可能にする

### Product Principles との整合

- **Claude Code First**: FR-3 は MCP ツールとして提供し、Claude Code の analysis-design スキルから直接呼び出し可能
- **知識の自動蓄積**: FR-2 の fire-and-forget 方式で、分析ライフサイクルの中で自然に knowledge が蓄積される
- **後方互換の優先**: FR-1 で enum に `finding` を追加するのみ。既存データ・既存ツールへの影響なし

### Future Vision の実現

`product.md` の Future Vision で「Knowledge Suggestion: 次期開発予定」として明記されている機能の実装。

## Requirements

### FR-1: KnowledgeCategory への finding 追加

**User Story:** As an analyst, I want analysis results (supported/rejected/inconclusive) to be categorized as "finding" knowledge, so that prior analysis outcomes are available as structured knowledge for future analyses.

#### Acceptance Criteria

1. WHEN KnowledgeCategory enum is defined THEN it SHALL contain: `methodology`, `caution`, `definition`, `context`, `finding`
2. WHEN an existing knowledge entry with category `methodology`, `caution`, `definition`, or `context` is accessed THEN it SHALL work without any migration or conversion
3. WHEN a new knowledge entry is created with category `finding` THEN it SHALL be stored and retrieved identically to other categories

### FR-2: Terminal 遷移時の finding 自動抽出

**User Story:** As an analyst, I want the system to automatically extract a finding entry when a design reaches a terminal status, so that analysis results accumulate as reusable knowledge without manual effort.

#### Acceptance Criteria

1. WHEN a design transitions to `supported`, `rejected`, or `inconclusive` via `transition_design_status` THEN the system SHALL automatically create a `DomainKnowledgeEntry` with category `finding`
2. WHEN a finding is auto-extracted THEN its `key` SHALL be `"{design_id}-finding"`, its `title` SHALL be `"[{STATUS}] {design.title}"` (truncated to 80 chars), its `content` SHALL be `design.hypothesis_statement`, its `source` SHALL be `"design:{design_id}"`, and its `affects_columns` SHALL be `design.source_ids`
3. WHEN a finding is auto-extracted THEN it SHALL be persisted to `.insight/rules/extracted_knowledge.yaml` using the existing storage mechanism
4. WHEN a design transitions to a terminal status AND a finding with key `"{design_id}-finding"` already exists THEN the system SHALL NOT create a duplicate entry
5. WHEN finding auto-extraction fails (e.g., I/O error) THEN the status transition itself SHALL NOT be rolled back, and the failure SHALL be logged as a warning

### FR-3: suggest_knowledge_for_design MCP ツール

**User Story:** As Claude Code (analysis-design skill), I want to retrieve knowledge entries relevant to a specific section of the analysis design, so that I can inform the design with prior knowledge.

#### Acceptance Criteria

1. WHEN `suggest_knowledge_for_design` is called with `section` parameter THEN the system SHALL filter knowledge by the categories mapped in SECTION_KNOWLEDGE_MAP:
   - `hypothesis_statement` -> `[finding]`
   - `hypothesis_background` -> `[finding, context]`
   - `source_ids` -> `[caution, definition]`
   - `metrics` -> `[methodology]`
   - `explanatory` -> `[methodology, caution]`
   - `chart` -> `[methodology]`
   - `next_action` -> `[finding]`
2. WHEN `section` is not provided (None) THEN the system SHALL return suggestions from all categories
3. WHEN `section` is provided with an unknown value THEN the system SHALL return an error dict with a descriptive message
4. WHEN `theme_id` is provided THEN the system SHALL match knowledge entries whose source references a design with the same `theme_id` (for categories: finding, context)
5. WHEN `parent_id` is provided THEN the system SHALL walk the ancestor chain (parent_id -> parent's parent_id -> ...) and return finding entries from ancestor designs (for category: finding)
6. WHEN ancestor walking encounters a cycle or reaches a depth of 10 THEN it SHALL stop and return results collected so far
7. WHEN `source_ids` is provided (comma-separated) THEN the system SHALL match knowledge entries whose `affects_columns` intersects with the provided source IDs (for categories: caution, definition)
8. WHEN `hypothesis_text` is provided THEN the system SHALL search the FTS5 index for matching knowledge entries and filter by category `methodology`
9. WHEN suggestions are returned THEN each entry SHALL include a `relevance` field describing the match reason (e.g., "theme_id match: CHURN", "ancestor design: H-001", "source_id match: orders", "FTS5 match")
10. WHEN no matching knowledge is found THEN the system SHALL return `{"section": ..., "suggestions": {}, "total": 0}`

### FR-4: referenced_knowledge フィールド

**User Story:** As a reviewer, I want to see which knowledge entries were referenced when creating each section of the analysis design, so that I can verify the appropriateness of the references during review.

#### Acceptance Criteria

1. WHEN `AnalysisDesign` model is defined THEN it SHALL include a `referenced_knowledge` field of type `dict[str, list[str]]` with a default of empty dict
2. WHEN `create_analysis_design` MCP tool is called with `referenced_knowledge` parameter THEN the design SHALL be created with the provided references
3. WHEN `update_analysis_design` MCP tool is called with `referenced_knowledge` parameter THEN the design's referenced_knowledge SHALL be updated (merged, not replaced: existing keys not in the update are preserved)
4. WHEN an existing design without `referenced_knowledge` field is loaded THEN it SHALL default to empty dict without error (backward compatibility)
5. WHEN `get_analysis_design` is called THEN the response SHALL include the `referenced_knowledge` field

### FR-5: レビューでの参照適切性指摘

**User Story:** As a reviewer, I want to comment on the appropriateness of knowledge references used in the design, so that inappropriate references can be identified and corrected.

#### Acceptance Criteria

1. WHEN `save_review_batch` is called with `target_section: "referenced_knowledge"` THEN it SHALL be accepted as a valid target section
2. WHEN a review comment targets `referenced_knowledge` and the design transitions to a terminal status THEN the review comment SHALL be extractable as knowledge via `extract_domain_knowledge` (using existing extraction logic)

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: suggest ロジックは `RulesService` に集約する。マッチング戦略ごとにプライベートメソッドに分離する
- **SECTION_KNOWLEDGE_MAP**: `core/rules.py` に定数として定義する。server.py には配置しない
- **Matching strategies**: カテゴリごとのマッチング戦略は `core/rules.py` 内で管理する

### Performance

- `suggest_knowledge_for_design` のレスポンスは 500ms 以内（knowledge entries 100件以下の想定）
- ancestor walking の深度上限は 10（無限ループ防止 + パフォーマンス制限）

### Backward Compatibility

- 既存の `KnowledgeCategory` 4値（methodology, caution, definition, context）を使用した全てのデータ・コードは変更なしで動作する
- 既存の `suggest_cautions()` MCP ツールおよび `get_project_context()` MCP ツールは変更なし
- `AnalysisDesign` に `referenced_knowledge` を追加するが、既存 YAML でこのフィールドがない場合は空 dict にフォールバックする

### Reliability

- finding 自動抽出の失敗がステータス遷移をブロックしない（fire-and-forget with warning log）
- ancestor walking の循環参照を検出して停止する

## Out of Scope

- 既存 knowledge データのマイグレーション（不要: 後方互換維持のため）
- フロントエンドでの referenced_knowledge 表示（別 spec で対応）
- analysis-design スキルの SKILL.md プロンプト変更（スキル側で別途対応）
- knowledge entry の手動編集・削除機能
- knowledge entry の重要度 (importance) によるサジェストランキング

## Glossary

| Term | Definition |
|------|-----------|
| Knowledge entry | `DomainKnowledgeEntry` モデルで表現される知見の単位 |
| Finding | 分析が terminal ステータスに到達した際に自動抽出される知見（category: finding） |
| SECTION_KNOWLEDGE_MAP | 分析設計の各セクション名から、参照すべき knowledge カテゴリへの対応表 |
| Matching strategy | knowledge の検索方式。theme_id 一致、lineage 走査、source_ids 一致、FTS5 の4種 |
| Ancestor walking | parent_id チェーンを辿って祖先の design から finding を収集する操作 |
| Relevance | サジェスト結果に付与される「なぜこの knowledge がマッチしたか」の説明 |
| referenced_knowledge | 分析設計の各セクションが参照した knowledge entry key のリスト |

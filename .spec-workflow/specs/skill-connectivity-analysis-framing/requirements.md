# Requirements: skill-connectivity-analysis-framing

## Introduction

insight-blueprint のバンドルスキル群（analysis-design, analysis-journal, analysis-reflection, catalog-register, data-lineage）に、ドメインに接地した分析フレーミングスキル（analysis-framing）を追加し、全6スキルのフォワーディング（スキル間接続）を体系的に整備する。

### 現状の問題

1. **上流スキルの不在**: ユーザーが漠然とした分析テーマを持っているとき、カタログや既存分析を探索してフレーミングを支援するスキルがない。ユーザーは手動で `.insight/` を調べるか、直接 analysis-design に飛び込む
2. **フォワーディングの不整合**: analysis-journal と analysis-reflection には Chaining セクションがあるが、analysis-design / catalog-register / data-lineage にはない。スキル間接続が一方向的で、帰り道（サイクル）が定義されていない
3. **コンテキストの消失**: あるスキルから別のスキルへ移行するとき、構造化された情報の引き継ぎプロトコルがない

## Alignment with Product Vision

- **知見の蓄積と再利用**（product.md: Business Objectives）: analysis-framing がカタログと既存デザインを探索し、過去の知見をフレーミングに活用する
- **Claude Code との協働の効率化**（product.md: Business Objectives）: スキル間の自然な接続により、ユーザーのコンテキスト再説明を削減する
- **Claude Code First**（product.md: Product Principles）: スキルは Claude Code 上で動作するワークフローガイド。MCP ツールの追加は不要

## Requirements

### REQ-1: analysis-framing スキルの作成

**User Story:** As a data analyst using Claude Code, I want a skill that explores my existing data and analyses when I have a vague analytical theme, so that I can form a well-grounded hypothesis based on what data is available and what has already been analyzed.

#### Functional Requirements

- FR-1.1: analysis-framing は以下の3ディレクトリを Agentic Search（Glob / Read / Grep）で直接探索し、テーマに関連する情報を収集する: `.insight/designs/`（既存デザイン）、`.insight/catalog/`（データソース）、`.insight/rules/`（ドメイン知識）。MCP ツールは使用しない — キーワード検索の取りこぼしを避けるため、Claude が YAML の中身を意味的に理解して関連性を判断する
- FR-1.2: 探索結果を「データ地図」として構造化して提示する: (a) 利用可能データソース（ソース名・主要カラム・期間・粒度）、(b) 既存分析（デザイン ID・ステータス・結論・手法）、(c) 関連ドメイン知識（過去の知見・注意事項）、(d) 知識ギャップ（未探索領域・不足データ）
- FR-1.3: ユーザーとの対話を通じて仮説の方向性を絞り込む。仮説文（hypothesis_statement）の作成は行わない（analysis-design の責務）
- FR-1.4: 方向性が定まったら Framing Brief（FR-3.1 で定義）を出力し、analysis-design へのフォワーディングを提案する

#### Acceptance Criteria

- AC-1.1: WHEN user invokes `/analysis-framing` with a theme (e.g., "外国人比率と犯罪率") THEN the skill SHALL explore `.insight/designs/`, `.insight/catalog/`, and `.insight/rules/` using Glob and Read tools
- AC-1.2: WHEN exploration completes THEN the skill SHALL present a structured "data map" containing: (a) relevant data sources with schema summary (source name, key columns, period, granularity), (b) related existing designs with status and conclusion, (c) related domain knowledge entries (past findings, cautions), (d) identified knowledge gaps
- AC-1.3: WHEN a hypothesis direction is agreed upon THEN the skill SHALL output a Framing Brief (see AC-3.1) and suggest `/analysis-design`
- AC-1.4: WHEN the user's theme is too vague to explore effectively THEN the skill SHALL ask the user to narrow down the scope, presenting 2-3 candidate directions based on available data
- AC-1.5: WHEN no relevant data is found in `.insight/catalog/` THEN the skill SHALL suggest `/catalog-register` to register new data sources

### REQ-2: 6スキル全体のフォワーディング表の整備

**User Story:** As a data analyst, I want each skill to naturally suggest the next appropriate skill based on the current analysis context, so that I can flow through the analysis lifecycle without memorizing skill names.

#### Functional Requirements

- FR-2.1: 全6スキル（analysis-framing, analysis-design, analysis-journal, analysis-reflection, catalog-register, data-lineage）の SKILL.md に統一フォーマットの Chaining セクションを持つ
- FR-2.2: フォワーディングは双方向を含む。analysis-reflection → analysis-framing（再フレーミング）、analysis-design → analysis-framing（データ不足時の帰り道）のようなサイクルを定義する
- FR-2.3: 各フォワーディングエントリに条件（When）を明記する。「いつこのスキルに遷移すべきか」が一読で分かること

#### Acceptance Criteria

- AC-2.1: WHEN any of the 6 skills is invoked THEN its SKILL.md SHALL contain a `## Chaining` section with a table of `| From | To | When |` entries
- AC-2.2: WHEN analysis-reflection reaches a "new hypothesis needed" conclusion THEN its Chaining table SHALL include an entry forwarding to `/analysis-framing`
- AC-2.3: WHEN analysis-design determines that required data is missing THEN its Chaining table SHALL include an entry forwarding back to `/analysis-framing`
- AC-2.4: WHEN catalog-register completes a registration THEN its Chaining table SHALL include an entry suggesting return to the originating skill (analysis-framing or analysis-design)
- AC-2.5: WHEN data-lineage generates a Mermaid diagram THEN its Chaining table SHALL include an entry suggesting `/analysis-journal` to record the lineage as evidence

### REQ-3: フレーミングブリーフプロトコル

**User Story:** As a data analyst, I want the context gathered by analysis-framing to be automatically picked up by analysis-design, so that I don't have to re-explain my analysis setup.

#### Functional Requirements

- FR-3.1: analysis-framing は完了時に以下の5セクションを持つ構造化テキスト（Framing Brief）を会話コンテキストに出力する:
  - **テーマ**: 分析テーマの1行要約
  - **利用可能データ**: カタログ上のデータソース名、主要カラム、期間、粒度
  - **既存分析**: 関連するデザイン ID、ステータス、結論の要約
  - **ギャップ**: 未探索領域、不足データ、未検証の仮説方向
  - **推奨方向**: 推奨する仮説の方向性、suggested theme_id、parent_id（既存デザインからの派生の場合）、analysis_intent（exploratory / confirmatory / mixed）
- FR-3.2: analysis-design は起動時に会話コンテキストから Framing Brief の存在を確認し、存在すれば draft 値として使用する（フィールドの自動提案、theme_id / parent_id / analysis_intent の推奨）
- FR-3.3: Framing Brief が存在しない場合、analysis-design は現行のインタビューフロー（Step 2）をそのまま実行する（後方互換）

#### Acceptance Criteria

- AC-3.1: WHEN analysis-framing completes THEN it SHALL output a Framing Brief with at minimum: Theme, Available Data (source names + key schema info), Existing Analyses (design IDs + status), Gaps, Recommended Direction (including suggested theme_id, parent_id, analysis_intent)
- AC-3.2: WHEN analysis-design starts after analysis-framing AND a Framing Brief exists in conversation THEN analysis-design SHALL pre-populate suggested values and confirm with user instead of interviewing from scratch
- AC-3.3: IF no Framing Brief exists in conversation context THEN analysis-design SHALL proceed with its current Step 2 interview flow unchanged

### REQ-4: 外部スキルとの条件付き接続

**User Story:** As a data analyst who may or may not have development-deck installed, I want analysis-framing to work independently while optionally leveraging development-partner if available.

#### Functional Requirements

- FR-4.1: analysis-framing は development-partner（development-deck の外部スキル）への依存を持たない。単独で動作する
- FR-4.2: development-partner が存在する環境では、analysis-framing の Chaining セクションにオプショナルなフォワーディングとして記載する（テーマが分析ドメインを超えて漠然としている場合）
- FR-4.3: development-partner が存在しない環境では、analysis-framing 自身がテーマの絞り込みを行う（ユーザーに選択肢を提示して方向を決定）

#### Acceptance Criteria

- AC-4.1: WHEN analysis-framing is invoked in an environment without development-partner THEN the skill SHALL function fully, handling vague themes by presenting candidate directions to the user
- AC-4.2: WHEN analysis-framing is invoked in an environment with development-partner AND the theme is beyond the analysis domain THEN the Chaining section SHALL note development-partner as an optional forwarding target with a caveat that it is an external skill
- AC-4.3: WHEN development-partner forwards to analysis-framing THEN analysis-framing SHALL accept the framing context from the conversation and build upon it

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: analysis-framing は「探索・統合」の単一責務。仮説の定式化（analysis-design）、推論記録（analysis-journal）、結論（analysis-reflection）の責務を侵食しない
- **Consistent Structure**: 全6スキルの SKILL.md が最低限以下のセクションを持つ: frontmatter, When to Use, When NOT to Use, Workflow, Chaining, Language Rules。スキル固有のセクション（MCP Tool Reference, Error Handling 等）は各スキルが必要に応じて追加する
- **Minimal Coupling**: analysis-framing は MCP ツールに依存しない。Agentic Search（Glob / Read / Grep）のみで `.insight/` 以下を探索する

### Backward Compatibility

- 既存5スキルの現行動作は変更しない。Chaining セクションの追加・更新のみ
- analysis-design の Framing Brief 検出は追加のステップ（Step 1.5）であり、既存の Step 1-4 を変更しない
- Framing Brief なしで analysis-design を直接起動した場合、現行のインタビューフローがそのまま動作する

### Deployment

- analysis-framing は `src/insight_blueprint/_skills/analysis-framing/SKILL.md` に配置し、既存のスキルデプロイメカニズム（`_copy_skills_template()`）で `.claude/skills/` にデプロイされる
- 既存スキルの SKILL.md 更新はバージョン番号のインクリメント（1.0.0 → 1.1.0）で配信される

## Out of Scope

- 新しい MCP ツールの追加（extension policy により MCP は Fix）
- WebUI の変更
- Python コード（models / storage / core）の変更
- analysis-framing のための新しい YAML データ構造の追加
- development-deck 側の SKILL.md 修正（外部リポジトリ）

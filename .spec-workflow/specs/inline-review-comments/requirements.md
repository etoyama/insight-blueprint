# Requirements: Inline Review Comments

## Introduction

現在の Review ワークフローには2つの問題がある。Overview タブと Review タブが分離しておりコンテキスト断絶が起きる。コメントに Design セクションへのアンカーがなく指摘対象が不明。本機能はセクション単位のインラインコメントとバッチ投稿を導入し、レビュワーの UX と AI revision の精度を同時に改善する。

## Alignment with Product Vision

1. **ドメイン知識の蓄積品質向上**: アンカー付きコメントにより、knowledge extraction の精度が上がる（product.md: "analyst review comments からの domain knowledge 蓄積"）
2. **AI-driven analysis workflow**: `target_section` + `target_content` により AI revision が指摘対象セクションの元内容を参照しピンポイントで修正可能（product.md: "AI-driven exploratory data analysis"）
3. **軽量レビュー**: タブ往復の排除とバッチ投稿で、hypothesis-driven な軽量ワークフローを維持（product.md: "lightweight, hypothesis-driven analysis design docs"）

## Requirements

### 1. Inline Contextual Comments

**User Story:** データアナリストとして、レビュー対象のセクション横にコメントを直接追加したい。タブ切り替えでコンテキストを失わないために。

- FR-1: Design の各コメント対象セクション（`hypothesis_statement`, `hypothesis_background`, `metrics`, `explanatory`, `chart`, `next_action`）の横にコメントボタンを表示する
- FR-2: コメントボタンは `pending_review` 時のみ表示する
- FR-3: コメントボタンクリックで、該当セクション下にインラインコメントフォームを展開する
- FR-4: 各コメントに `target_section` フィールドを持たせ、対象セクションを識別する

#### Acceptance Criteria

1. WHEN Design の status が `pending_review` THEN Overview パネルの6セクション横にコメントボタンを表示する
2. WHEN status が `pending_review` 以外 THEN コメントボタンを非表示にする
3. WHEN コメントボタンをクリック THEN 該当セクション下にテキスト入力フォームを展開する
4. WHEN インラインコメントを追加 THEN `target_section` にセクション識別子（例: `"hypothesis_statement"`）を設定してドラフト保存する

### 2. Draft Management and Batch Submission

**User Story:** データアナリストとして、複数のコメントをドラフトとして溜めてから一括で投稿したい。Design 全体を確認してからレビュー判定を下すために。

- FR-5: 複数のドラフトコメントをクライアント state に蓄積できる
- FR-6: ドラフトが1件以上あるとき、フローティングの Review Submit Bar を表示する（ドラフト件数 + ステータスセレクタ + "Submit All" ボタン）
- FR-7: ステータスセレクタの選択肢: `supported`, `rejected`, `inconclusive`, `active`（request changes）
- FR-8: "Submit All" で全ドラフトを1つの `ReviewBatch` として POST し、ステータス遷移は1回だけ
- FR-9: 投稿成功後、ドラフトをクリアし Design を再取得する

#### Acceptance Criteria

1. WHEN ドラフトを追加 THEN Review Submit Bar にドラフト件数を更新表示する
2. WHEN ドラフトを削除し残り0件 THEN Submit Bar を非表示にする
3. WHEN "Submit All" をクリック THEN `POST /api/designs/{id}/review-batches` に全ドラフトを1バッチで送信する
4. WHEN バッチ投稿成功 THEN `status_after` の値に1回だけステータス遷移する
5. WHEN バッチ投稿成功 THEN ドラフトをクリアし Design データを refresh する

### 3. ReviewBatch Data Model

**User Story:** システムメンテナーとして、レビューコメントをバッチ単位でグループ化し、1バッチ=1ステータス遷移としたい。データモデルがレビューワークフローを正確に表現するために。

- FR-10: `ReviewBatch` モデルを導入する（`id`, `design_id`, `status_after`, `reviewer`, `comments: list[BatchComment]`, `created_at`）
- FR-11: `BatchComment` は `comment`（テキスト）、`target_section`（optional string）、`target_content`（対象セクションのレビュー時点のスナップショット）を持つ
- FR-12: `POST /api/designs/{id}/review-batches` でバッチ投稿を受け付ける
- FR-13: `GET /api/designs/{id}/review-batches` で全バッチを取得する
- FR-14: `{design_id}_reviews.yaml` の `batches` キーにバッチを永続化する

#### Acceptance Criteria

1. WHEN 有効な ReviewBatch を POST THEN YAML に永続化し Design のステータスを遷移する
2. WHEN status が `pending_review` でない THEN バッチ投稿 API は 400 エラーを返す
3. WHEN GET review-batches THEN 全バッチを `created_at` 降順で返す
4. WHEN ReviewBatch を永続化 THEN 各コメントの `target_section` と `target_content` を保持する

### 4. Tab Restructuring

**User Story:** データアナリストとして、Design の内容表示とコメント投稿を1つの画面で行いたい。タブ切り替えなしでレビューを完結するために。

- FR-15: `DesignDetail` のタブ構成を `Overview | Review | Knowledge` から `Overview | History | Knowledge` に変更する
- FR-16: Overview タブにインラインコメント機能を統合する（旧 Review タブの機能を吸収）
- FR-17: History タブに過去の ReviewBatch を read-only リスト形式で表示する。各コメントに `target_content`（レビュー時点のセクション内容）を並べて表示する

#### Acceptance Criteria

1. WHEN Design 詳細を開く THEN タブは "Overview", "History", "Knowledge" の3つ
2. WHEN `pending_review` の Design で Overview タブにいる THEN タブ切り替えなしでインラインコメントが可能
3. WHEN History タブに切り替え THEN 過去の ReviewBatch がコメント・`target_section`・`target_content`・タイムスタンプ付きで表示される

### 5. MCP Tool Update

**User Story:** MCP ツールを使う AI エージェントとして、セクションアンカー付きのレビューバッチを投稿したい。構造化されたレビューフィードバックを提供するために。

- FR-18: `save_review_batch` MCP ツールを追加する（`target_section` + `target_content` 付きコメントリスト + 単一 `status_after`）

#### Acceptance Criteria

1. WHEN MCP クライアントが `save_review_batch` を呼び出す THEN ReviewBatch を作成しステータスを遷移する

## Non-Functional Requirements

### Code Architecture and Modularity

- **NFR-1**: `ReviewBatch`, `BatchComment` は `models/review.py` に定義する（Pydantic models の single-source-of-truth パターン維持、structure.md 準拠）
- **NFR-2**: バッチレビューのビジネスロジックは `core/reviews.py`（ReviewService）に追加する
- **NFR-3**: 新規フロントエンドコンポーネント（`SectionRenderer`, `DraftCommentForm`, `ReviewBatchComposer`）は `pages/design-detail/components/` に配置する（SPEC-4b の SRP ディレクトリパターン準拠）
- **NFR-4**: リファクタ後の OverviewPanel は400行以内に収める。インラインコメント機能は専用コンポーネントに切り出す

### Performance

- **NFR-5**: ドラフト state の更新で無関係なセクションの re-render を起こさない

### Security

- **NFR-6**: コメントテキストは XSS 防止のためレンダリング前にサニタイズする
- **NFR-7**: `target_section` は既知のセクション識別子に対してバリデーションする

### Reliability

- **NFR-8**: バッチ投稿は YAML-first atomicity — YAML への永続化は atomic write で保証する。ステータス遷移は YAML 書き込み成功後に実行する。YAML 書き込み失敗時はステータスも遷移しない。YAML 成功後にステータス遷移が失敗した場合、バッチは保存済みだがステータスは未遷移となる（ローカルツールのため発生確率は極めて低い。再試行で回復可能）
- **NFR-9**: （NFR-8 に統合）

### Usability

- **NFR-10**: ドラフトコメントは投稿済みコメントと視覚的に区別する（破線ボーダー、"draft" ラベル等）
- **NFR-11**: ドラフトが存在するとき、Review Submit Bar はスクロールなしで常に見える（sticky/fixed）
- **NFR-12**: ドラフト削除はワンクリック（確認ダイアログなし — ドラフトは揮発性データ）

## Out of Scope

- **フィールドレベルアンカー**（例: `metrics.kpi_name`）: セクション単位で十分。将来 `target_section` をドット記法に拡張可能
- **サーバーサイドドラフト永続化**: 単一ユーザーツールのため、クライアント React state のみ
- **AI revision API 実装**: 本 spec はアンカーデータ + スナップショットの提供まで。revision エンドポイントは別機能
- **リアルタイムコラボレーション**: 同時レビュワー同期（WebSocket）は不要。単一ユーザー前提
- **投稿済みバッチの編集・削除**: 投稿済みバッチは immutable
- **レガシーデータの後方互換・マイグレーション**: 旧 `comments` 形式のデータは移行しない。新形式 `batches` で上書き
- **重複投稿防止（idempotency key）**: Submit ボタンの disable で UI レベルで防止。サーバーサイドの冪等性は不要

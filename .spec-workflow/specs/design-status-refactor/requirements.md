# Requirements Document: Design Status Refactor

## Introduction

DesignStatus enum を現行の6値（draft, active, pending_review, supported, rejected, inconclusive）から、実際のワークフローに合致する6値（in_review, revision_requested, analyzing, supported, rejected, inconclusive）に置換する。この変更は Python バックエンド、MCP ツール、REST API、React フロントエンド、E2E テストの全レイヤーに横断的に影響する。

### 背景

現行のステータスフロー（draft → active → pending_review → terminal）は、実際の運用フローと乖離している。ユーザーの実際のワークフローは以下の通り:

1. Claude Code が design.yaml を生成 → **In Review**（ユーザーがレビュー可能）
2. ユーザーがフィードバック → **Revision Requested**（Claude が修正担当）
3. Claude が修正後、再レビュー依頼 → **In Review**
4. ユーザーが承認 → **Analyzing**（分析実行中）
5. 分析結果を反映 → **In Review**（結果レビュー）
6. ユーザーが最終判定 → **Supported / Rejected / Inconclusive**

### セマンティクス: "誰がボールを持っているか"

| Status | ボール保持者 | 意味 |
|--------|------------|------|
| in_review | ユーザー | レビュー待ち（設計レビュー or 結果レビュー） |
| revision_requested | Claude | ユーザーフィードバックに基づく修正中 |
| analyzing | Claude | 分析コード実装・実行中 |
| supported / rejected / inconclusive | - | 終端（遷移なし） |

## Requirements

### FR-1: DesignStatus enum の置換

**User Story:** As a developer, I want the DesignStatus enum to reflect the actual workflow, so that the status values have clear semantics.

#### Acceptance Criteria

1. WHEN DesignStatus enum is defined THEN it SHALL contain exactly: `in_review`, `revision_requested`, `analyzing`, `supported`, `rejected`, `inconclusive`
2. WHEN the old statuses `draft`, `active`, `pending_review` are referenced anywhere in the codebase THEN they SHALL be replaced with the corresponding new statuses
3. WHEN a design is created via `create_design` THEN its default status SHALL be `in_review` (not `draft`)

### FR-2: 遷移ルールの再定義

**User Story:** As a system, I want to enforce valid status transitions, so that designs follow the intended workflow.

#### Acceptance Criteria

1. WHEN a design is in `in_review` THEN valid transitions SHALL be `{revision_requested, analyzing, supported, rejected, inconclusive}`
2. WHEN a design is in `revision_requested` THEN the only valid transition SHALL be `{in_review}`
3. WHEN a design is in `analyzing` THEN the only valid transition SHALL be `{in_review}`
4. WHEN a design is in `supported`, `rejected`, or `inconclusive` THEN no transitions SHALL be allowed (terminal states)
5. WHEN an invalid transition is attempted THEN the system SHALL raise a ValueError with a descriptive message

### FR-3: API エンドポイントの変更

**User Story:** As a frontend client, I want a unified transition endpoint, so that status changes are handled consistently.

#### Acceptance Criteria

1. WHEN `POST /api/designs/{id}/transition` is called with `{"status": "<valid_status>"}` THEN the design status SHALL transition if the transition is valid
2. WHEN `POST /api/designs/{id}/transition` is called with an invalid transition THEN the API SHALL return HTTP 400 with an error message
3. WHEN the old endpoint `POST /api/designs/{id}/review` is called THEN it SHALL no longer exist (removed)
4. WHEN `submit_for_review` function is referenced THEN it SHALL be replaced by `transition_status` (or equivalent)

### FR-4: MCP ツールの変更

**User Story:** As Claude Code, I want a `transition_design_status` MCP tool, so that I can transition designs through the workflow.

#### Acceptance Criteria

1. WHEN `transition_design_status` is called with `design_id` and `status` THEN it SHALL transition the design if valid
2. WHEN the old `submit_for_review` MCP tool is referenced THEN it SHALL be replaced by `transition_design_status`
3. WHEN `transition_design_status` is called with an invalid transition THEN it SHALL return an error message

### FR-5: レビューバッチの前提条件変更

**User Story:** As a reviewer, I want to submit review batches only when a design is in_review, so that reviews happen at the right time.

#### Acceptance Criteria

1. WHEN a review batch is submitted THEN the design SHALL be in `in_review` status (previously `pending_review`)
2. WHEN a review batch is submitted with `status_after` THEN valid values SHALL be `{supported, rejected, inconclusive, revision_requested, analyzing}` (previously `{supported, rejected, inconclusive, active}`)
3. WHEN a review batch is submitted on a design NOT in `in_review` THEN the system SHALL return HTTP 400

### FR-6: フロントエンド DesignStatus 型と UI の更新

**User Story:** As a user, I want the UI to display the new statuses with appropriate labels and colors, so that I understand the current state of each design.

#### Acceptance Criteria

1. WHEN the `DesignStatus` TypeScript type is defined THEN it SHALL contain `"in_review" | "revision_requested" | "analyzing" | "supported" | "rejected" | "inconclusive"`
2. WHEN `DESIGN_STATUS_LABELS` is defined THEN it SHALL map: in_review → "In Review", revision_requested → "Revision Requested", analyzing → "Analyzing", supported → "Supported", rejected → "Rejected", inconclusive → "Inconclusive"
3. WHEN `StatusBadge` renders a status THEN it SHALL use the following color scheme: in_review = yellow, revision_requested = blue, analyzing = purple, supported = green, rejected = red, inconclusive = orange
4. WHEN the status filter dropdown is rendered THEN it SHALL list the 6 new statuses (not the old ones)

### FR-7: OverviewPanel ワークフロー変更

**User Story:** As a reviewer, I want the overview panel to guide me through the review workflow, so that I know what actions are available.

#### Acceptance Criteria

1. WHEN a design is in `in_review` status THEN the review comment UI (SectionRenderer + ReviewBatchComposer) SHALL be active
2. WHEN a design is NOT in `in_review` THEN comment UI SHALL be hidden
3. WHEN `STATUS_GUIDE` is displayed THEN it SHALL show guidance for all 6 new statuses
4. WHEN the old "Submit for Review" button exists THEN it SHALL be removed (designs start in in_review, no draft→active→pending_review flow)

### FR-8: API クライアント関数の変更

**User Story:** As a frontend developer, I want the API client to use the new transition endpoint, so that the frontend communicates correctly with the backend.

#### Acceptance Criteria

1. WHEN `transitionDesign(designId, status)` is called THEN it SHALL POST to `/api/designs/{id}/transition` with `{"status": status}`
2. WHEN the old `submitReview` function exists THEN it SHALL be removed

### FR-9: ReviewBatchComposer のステータス選択肢変更

**User Story:** As a reviewer, I want the batch verdict options to match the new workflow, so that I can choose the correct next status.

#### Acceptance Criteria

1. WHEN `BATCH_STATUSES` is defined THEN it SHALL contain `["supported", "rejected", "inconclusive", "revision_requested", "analyzing"]` (previously included `"active"`)

### FR-10: E2E テストフィクスチャの更新

**User Story:** As a developer, I want E2E test fixtures to use the new statuses, so that tests validate the correct workflow.

#### Acceptance Criteria

1. WHEN `makeDesign()` is called with no status override THEN default status SHALL be `"in_review"` (not `"draft"` or `"active"`)
2. WHEN `mockTransitionDesign` is used THEN it SHALL mock `POST /api/designs/{id}/transition` (not `/review`)
3. WHEN E2E tests reference old statuses (`draft`, `active`, `pending_review`) THEN they SHALL be replaced with appropriate new statuses
4. WHEN the status filter E2E test (S6) selects a status THEN it SHALL select `"in_review"` (not `"draft"`)

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single source of truth**: DesignStatus enum は Python の `DesignStatus(StrEnum)` と TypeScript の `DesignStatus` type の2箇所のみで定義する。他の箇所はこれらを参照する
- **遷移ルールの集約**: `VALID_TRANSITIONS` マップは `reviews.py` に1箇所で定義する

### Backward Compatibility

- この変更は破壊的変更である。既存の YAML ファイル内の旧ステータス値のマイグレーションはスコープ外とする（v0.1.0 リリース前の変更のため、既存データなし）

### Scope

**スコープ内:**
- Python: models/design.py, core/designs.py, core/reviews.py, web.py, server.py
- Python テスト: test_designs.py, test_reviews.py, test_web.py, test_web_integration.py, test_integration.py, test_server.py
- Frontend: types/api.ts, lib/constants.tsx, components/StatusBadge.tsx, pages/DesignsPage.tsx, pages/design-detail/OverviewPanel.tsx, api/client.ts, pages/design-detail/components/ReviewBatchComposer.tsx
- E2E: fixtures/mock-data.ts, fixtures/api-routes.ts, design-detail.spec.ts, smoke.spec.ts, history.spec.ts

**スコープ外:**
- 既存 YAML データのマイグレーション
- 新しい UI コンポーネントの追加
- ステータス遷移の自動化（MCP ツール経由で手動遷移）

## Glossary

| Term | Definition |
|------|-----------|
| Terminal state | 遷移先がないステータス（supported, rejected, inconclusive） |
| Transition | 有効な遷移ルールに基づくステータス変更 |
| Review batch | 複数のレビューコメントをまとめて提出する単位 |
| Ball holder | あるステータスで次のアクションを取る責任者（ユーザー or Claude） |

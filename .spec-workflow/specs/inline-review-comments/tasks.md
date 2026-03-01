# Tasks: Inline Review Comments

## Notes

- **TDD 順序**: 各フェーズでテストを先に書き（RED）、実装で通す（GREEN）。タスク番号の小さい方が先
- **NFR-8 原子性**: design.md の仕様に従う — YAML 書き込み成功後にステータス遷移。ステータス遷移失敗時はバッチ保存済み・ステータス未遷移（要再試行）。requirements.md の "all-or-nothing" 表現はローカルツールの現実的制約を反映して design.md で refinement 済み
- **NFR-6 XSS**: React の JSX は default でエスケープするため、全コンポーネントで `dangerouslySetInnerHTML` の使用を禁止する。これにより NFR-6 を満たす

---

## Phase 1: Models (test-design P1)

- [ ] 1. Write unit tests for `BatchComment` and `ReviewBatch` models (RED)
  - File: `tests/test_review_models.py` (modify)
  - Add `TestBatchComment` class: valid construction, optional target_section, target_content_requires_section (model_validator), text/json target_content preservation, non-JSON value rejection (parametrize: datetime, set), empty/whitespace comment rejection, max length boundary (2000/2001), empty string target_section rejection, extra field rejection
  - Add `TestReviewBatch` class: valid construction, id format (RB- prefix + 8 hex), invalid status rejection, empty comments rejection, JST default timestamp, reviewer default, JSON round-trip, extra field rejection
  - Purpose: TDD Red phase — model contracts を先に定義する
  - _Leverage: `tests/test_review_models.py` (existing class-based pattern), `tests/conftest.py` (fixtures)_
  - _Requirements: FR-10, FR-11_
  - _Prompt: Role: Python test engineer | Task: Write comprehensive unit tests for BatchComment and ReviewBatch models covering all P1 test cases from test-design.md | Restrictions: Follow existing class-based grouping pattern, use parametrize for multi-value tests, add AC reference docstrings. Tests will initially fail (RED phase) | Success: Tests correctly define the expected model behavior — will pass after Task 1.1_
  - **完了基準**: `TestBatchComment` と `TestReviewBatch` が test-design.md P1 の全ケースを網羅している
  - **確認手順**: `uv run pytest tests/test_review_models.py -v --co -k "TestBatchComment or TestReviewBatch"` でテストケースが収集される（RED 状態で OK）

- [ ] 1.1 Implement `BatchComment` and `ReviewBatch` Pydantic models (GREEN)
  - File: `src/insight_blueprint/models/review.py` (modify), `src/insight_blueprint/models/__init__.py` (modify)
  - Define `JsonValue` recursive type alias for YAML-safe serializable values
  - Add `BatchComment(BaseModel, extra="forbid")` with `comment`, `target_section`, `target_content: JsonValue`, and `model_validator` ensuring `target_section` set implies `target_content` required
  - Add `ReviewBatch(BaseModel, extra="forbid")` with `id`, `design_id`, `status_after`, `reviewer`, `comments: list[BatchComment]`, `created_at`
  - Add `comment` field validation: non-empty, strip whitespace, max 2000 chars
  - Add `target_section` validation: must be `None` or non-empty string (empty string rejected)
  - Re-export new models from `__init__.py`
  - Purpose: Task 1 のテストを GREEN にする
  - _Leverage: `models/review.py` (existing `ReviewComment`), `models/common.py` (`now_jst`), `models/design.py` (`DesignStatus`)_
  - _Requirements: FR-10, FR-11, NFR-1_
  - _Prompt: Role: Python developer with Pydantic expertise | Task: Create `BatchComment` and `ReviewBatch` models with `JsonValue` type alias, `model_validator`, `extra="forbid"`, and field-level validations per FR-10/FR-11 | Restrictions: Do not modify existing `ReviewComment`. Keep `JsonValue` as a module-level type alias. Use `model_validator(mode="after")` not `field_validator` | Success: All Task 1 tests pass green_
  - **完了基準**: Task 1 の全テストが GREEN になる
  - **確認手順**: `uv run pytest tests/test_review_models.py -v -k "TestBatchComment or TestReviewBatch"` で全テストがパスする。`uv run ruff check src/insight_blueprint/models/review.py` がパスする

## Phase 2: Service Layer (test-design P2 + P3)

- [ ] 2. Write unit tests for `ReviewService` batch methods (RED)
  - File: `tests/test_reviews.py` (modify), `tests/conftest.py` (modify)
  - Add fixtures to `conftest.py`: `review_batch_data`, `make_batch_payload` (factory), `non_pending_design`, `fixed_now` (dual-patch for `models.common` + `models.review`), `corrupted_reviews_yaml`, `status_update_failure`
  - Add `TestSaveReviewBatch` class: valid save, status transition, YAML persistence, target_section preservation, target_content text/json, non-pending rejection, invalid status, empty comments, invalid design_id (parametrize), missing design, YAML write failure (no status change), status update failure (batch preserved — atomicity order), all 4 status transitions (parametrize), append to existing, create new file
  - Add `TestSaveReviewBatchTargetSectionValidation` class: valid sections (parametrize 6), invalid section, null section accepted
  - Add `TestListReviewBatches` class: returns all, descending order, empty, nonexistent design, no file, no batches key (+ warning log), target_content preservation, corrupted YAML (+ warning log)
  - Purpose: TDD Red phase — service contracts を先に定義する。P2 + P3 全ケース
  - _Leverage: `tests/test_reviews.py` (existing patterns), `tests/conftest.py` (existing fixtures)_
  - _Requirements: FR-4, FR-7, FR-8, FR-11, FR-12, FR-13, FR-14, NFR-7, NFR-8, NFR-9_
  - _Prompt: Role: Python test engineer | Task: Write unit tests for save_review_batch and list_review_batches covering all P2+P3 test cases from test-design.md | Restrictions: Follow existing class-based pattern, use `fixed_now` for timestamp tests, mock YAML write for failure tests. Tests will initially fail (RED phase) | Success: Tests correctly define expected service behavior — will pass after Tasks 2.1 and 2.2_
  - **完了基準**: test-design.md P2 + P3 の全テストケースが定義されている
  - **確認手順**: `uv run pytest tests/test_reviews.py -v --co -k "SaveReviewBatch or ListReviewBatches or TargetSectionValidation"` でテストケースが収集される

- [ ] 2.1 Implement `save_review_batch` in `ReviewService` (GREEN)
  - File: `src/insight_blueprint/core/reviews.py` (modify)
  - Add `ALLOWED_TARGET_SECTIONS` set: `{"hypothesis_statement", "hypothesis_background", "metrics", "explanatory", "chart", "next_action"}`
  - Implement `save_review_batch(design_id, status, comments, reviewer)` method:
    - Validate design_id, check design exists and is `pending_review`
    - Validate `status` against `VALID_REVIEW_TRANSITIONS`
    - Validate each comment's `target_section` against `ALLOWED_TARGET_SECTIONS`
    - Create `ReviewBatch` with `RB-{uuid4.hex[:8]}` id
    - Write batch to `{design_id}_reviews.yaml` under `batches` key (atomic write via `write_yaml`)
    - On YAML success, transition design status
    - Return `ReviewBatch` or `None`
  - Purpose: Task 2 の `TestSaveReviewBatch` + `TestSaveReviewBatchTargetSectionValidation` を GREEN にする
  - _Leverage: `save_review_comment()` (existing pattern), `VALID_REVIEW_TRANSITIONS`, `_validate_id()`, `read_yaml`/`write_yaml`_
  - _Requirements: FR-8, FR-12, FR-14, NFR-2, NFR-7, NFR-8, NFR-9_
  - _Prompt: Role: Python backend developer | Task: Implement `save_review_batch` in ReviewService with YAML atomic write, status transition, and target_section validation | Restrictions: Follow existing method patterns. YAML write first, then status update (atomicity order). Do not modify existing `save_review_comment` | Success: Task 2 の save 関連テストが全て GREEN_
  - **完了基準**: `TestSaveReviewBatch` と `TestSaveReviewBatchTargetSectionValidation` の全テストが GREEN
  - **確認手順**: `uv run pytest tests/test_reviews.py -v -k "SaveReviewBatch or TargetSectionValidation"` で全テストがパスする

- [ ] 2.2 Implement `list_review_batches` in `ReviewService` (GREEN)
  - File: `src/insight_blueprint/core/reviews.py` (modify)
  - Implement `list_review_batches(design_id)` method:
    - Read `{design_id}_reviews.yaml`, extract `batches` key
    - If file not found or `batches` key missing → return empty list (+ `logging.warning()`)
    - If YAML parse error → `logging.warning()` + return empty list
    - If old format (`comments` key without `batches`) → `logging.warning()` + return empty list
    - Sort by `created_at` descending
    - Return `list[ReviewBatch]`
  - Purpose: Task 2 の `TestListReviewBatches` を GREEN にする
  - _Leverage: `list_comments()` (existing read pattern), `read_yaml()`_
  - _Requirements: FR-13_
  - _Prompt: Role: Python backend developer | Task: Implement `list_review_batches` with YAML corruption handling and warning logs | Restrictions: Do not raise exceptions on corrupt/missing data — return empty list. Use `logging.warning()` for degraded states | Success: Task 2 の list 関連テストが全て GREEN_
  - **完了基準**: `TestListReviewBatches` の全テストが GREEN
  - **確認手順**: `uv run pytest tests/test_reviews.py -v -k "ListReviewBatches"` で全テストがパスする。`uv run ruff check src/insight_blueprint/core/reviews.py` がパスする

## Phase 3: Transport Layer (test-design P5 + P6)

- [ ] 3. Write integration tests for REST API and MCP tool (RED)
  - File: `tests/test_web.py` (modify), `tests/test_server.py` (modify)
  - Add `TestReviewBatchAPI` class to `test_web.py`: submit success (201), status transition, all 4 statuses (parametrize), non-pending 400, invalid design 404, invalid section 422, empty comments 422, overlength comment 422, missing target_content 422, extra field 422, with target_content round-trip, list success, list empty, list descending, list includes target_content
  - Add `TestSaveReviewBatchTool` class to `test_server.py`: success, with sections, non-pending error
  - Purpose: TDD Red phase — transport contracts を先に定義する。P5 + P6 全ケース
  - _Leverage: `tests/test_web.py` (existing `client` fixture, `_create_pending_design_via_api` helper), `tests/test_server.py` (existing `initialized_review_server` fixture)_
  - _Requirements: FR-7, FR-8, FR-12, FR-13, FR-18, NFR-7_
  - _Prompt: Role: Python integration test engineer | Task: Write integration tests for review-batch REST API and MCP tool covering P5+P6 test cases from test-design.md | Restrictions: Use existing test fixtures and helpers. Follow existing test patterns. Tests will initially fail (RED phase) | Success: Tests correctly define expected transport behavior_
  - **完了基準**: test-design.md P5 + P6 の全テストケースが定義されている
  - **確認手順**: `uv run pytest tests/test_web.py::TestReviewBatchAPI tests/test_server.py::TestSaveReviewBatchTool -v --co` でテストケースが収集される

- [ ] 3.1 Implement REST API endpoints for review batches (GREEN)
  - File: `src/insight_blueprint/web.py` (modify)
  - Add `SubmitBatchRequest` Pydantic model: `status_after: str`, `reviewer: str = "analyst"`, `comments: list[dict]`
  - Add `POST /api/designs/{design_id}/review-batches` endpoint:
    - Call `review_service.save_review_batch()`
    - Return 201 with `{batch_id, status_after, comment_count}`
    - Handle ValueError → 400, ValidationError → 422, None → 404
  - Add `GET /api/designs/{design_id}/review-batches` endpoint:
    - Call `review_service.list_review_batches()`
    - Return `{design_id, batches: [...], count}`
  - Purpose: Task 3 の `TestReviewBatchAPI` を GREEN にする
  - _Leverage: `web.py` (existing endpoint patterns, `_ID_PATTERN`, `ApiError`), `submit_review`/`add_comment` handlers_
  - _Requirements: FR-12, FR-13_
  - _Prompt: Role: Python web developer (Starlette/FastAPI) | Task: Add POST/GET /review-batches endpoints following existing handler patterns | Restrictions: Follow existing error handling (ValueError→400, ValidationError→422). Do not duplicate business logic from ReviewService | Success: Task 3 の REST API テストが全て GREEN_
  - **完了基準**: `TestReviewBatchAPI` の全テストが GREEN
  - **確認手順**: `uv run pytest tests/test_web.py::TestReviewBatchAPI -v` で全テストがパスする

- [ ] 3.2 Implement `save_review_batch` MCP tool (GREEN)
  - File: `src/insight_blueprint/server.py` (modify)
  - Add `save_review_batch` MCP tool with parameters: `design_id`, `status_after`, `comments` (list of dicts with `comment`, `target_section`, `target_content`), `reviewer`
  - Call `review_service.save_review_batch()` internally
  - Return success dict with batch_id and status_after, or error dict
  - Purpose: Task 3 の `TestSaveReviewBatchTool` を GREEN にする
  - _Leverage: `server.py` (existing tool patterns: `save_review_comment` tool), `_validate_design_id()`_
  - _Requirements: FR-18_
  - _Prompt: Role: MCP tool developer | Task: Add `save_review_batch` MCP tool following existing tool patterns | Restrictions: Use same ReviewService method as REST endpoint. Follow existing error dict pattern | Success: Task 3 の MCP ツールテストが全て GREEN_
  - **完了基準**: `TestSaveReviewBatchTool` の全テストが GREEN
  - **確認手順**: `uv run pytest tests/test_server.py::TestSaveReviewBatchTool -v` で全テストがパスする。`uv run ruff check src/insight_blueprint/server.py` がパスする

## Phase 4: Frontend Types + Section Registry (test-design P4)

- [ ] 4. Add frontend types and API client functions
  - File: `frontend/src/types/api.ts` (modify), `frontend/src/api/client.ts` (modify)
  - Add to `types/api.ts`: `JsonValue` type alias, `BatchComment`, `ReviewBatch`, `DraftComment`, `SubmitBatchRequest` interfaces
  - Add to `client.ts`: `submitReviewBatch(designId, body: SubmitBatchRequest)` → POST `/review-batches`, `listReviewBatches(designId)` → GET `/review-batches`
  - Purpose: Frontend data layer for batch operations
  - _Leverage: `types/api.ts` (existing `ReviewComment`, `DesignStatus`), `api/client.ts` (existing `request()` helper, `addComment` pattern)_
  - _Requirements: FR-12, FR-13_
  - _Prompt: Role: TypeScript developer | Task: Add review batch types and API client functions following existing patterns | Restrictions: Use existing `request<T>()` helper. `JsonValue` must match backend definition. Do not remove existing types | Success: Types compile, API functions match backend endpoint signatures_
  - **完了基準**: 型定義と API クライアント関数が追加され、既存コードとの整合性がとれている
  - **確認手順**: `cd frontend && npx tsc --noEmit` がパスする

- [ ] 4.1 Create `COMMENTABLE_SECTIONS` registry and `useReviewDrafts` hook
  - File: `frontend/src/pages/design-detail/components/sections.ts` (new), `frontend/src/pages/design-detail/components/useReviewDrafts.ts` (new)
  - Note: `frontend/src/pages/design-detail/components/` ディレクトリを新規作成する（SPEC-4b SRP パターン）
  - Create `sections.ts` with `COMMENTABLE_SECTIONS` array: `{ id, label, type }` for 6 sections (`hypothesis_statement`, `hypothesis_background`, `metrics`, `explanatory`, `chart`, `next_action`)
  - Create `useReviewDrafts` hook:
    - State: `drafts: DraftComment[]` (React useState)
    - `addDraft(section, comment, content)`: add with `crypto.randomUUID()` id and `structuredClone(content)` for snapshot
    - `removeDraft(draftId)`: filter by id
    - `clearAll()`: reset to empty
    - `hasDrafts`: derived boolean
    - `draftsBySection`: derived `Map<string, DraftComment[]>` (useMemo)
    - `beforeunload` listener when `hasDrafts` is true
  - Purpose: Section 定義の single source of truth + draft state management
  - _Leverage: React hooks (useState, useEffect, useCallback, useMemo)_
  - _Requirements: FR-5, NFR-5_
  - _Prompt: Role: React developer | Task: Create sections registry and useReviewDrafts hook with structuredClone for snapshot immutability | Restrictions: React state only — no sessionStorage. Use structuredClone for content deep copy. Memoize draftsBySection. Section IDs must match backend ALLOWED_TARGET_SECTIONS | Success: Hook manages drafts correctly, beforeunload fires when drafts exist, snapshots are immutable copies_
  - **完了基準**: `sections.ts` に6セクション定義、`useReviewDrafts.ts` に hook が実装され、`structuredClone` でスナップショットを取得している
  - **確認手順**: `cd frontend && npx tsc --noEmit` がパスする

- [ ] 4.2 Add section definition sync contract test
  - File: `tests/test_reviews.py` (modify)
  - Add `TestSectionDefinitionSync` class with 1 test:
    - Read frontend `COMMENTABLE_SECTIONS` from `frontend/src/pages/design-detail/components/sections.ts` (regex parse)
    - Compare ID set with backend `ALLOWED_TARGET_SECTIONS` from `core/reviews.py`
    - Assert equality
  - Purpose: backend/frontend セクション ID のドリフトを自動検知する
  - _Leverage: `core/reviews.py` (`ALLOWED_TARGET_SECTIONS`), `sections.ts` (`COMMENTABLE_SECTIONS`)_
  - _Requirements: NFR-7_
  - _Prompt: Role: Cross-stack test engineer | Task: Write contract test parsing frontend TypeScript source to extract section IDs and comparing with backend set | Restrictions: Use regex to parse TS source — do not import TypeScript. Test must fail if either side adds/removes a section without updating the other. Use explicit file path: `frontend/src/pages/design-detail/components/sections.ts` | Success: Test passes when sections match, fails when they drift_
  - **完了基準**: `TestSectionDefinitionSync` が backend と frontend のセクション ID の一致を検証している
  - **確認手順**: `uv run pytest tests/test_reviews.py::TestSectionDefinitionSync -v` がパスする

## Phase 5: Frontend Components

- [ ] 5. Create `SectionRenderer`, `InlineCommentAnchor`, `DraftCommentForm` components
  - File: `frontend/src/pages/design-detail/components/SectionRenderer.tsx` (new), `frontend/src/pages/design-detail/components/InlineCommentAnchor.tsx` (new), `frontend/src/pages/design-detail/components/DraftCommentForm.tsx` (new)
  - `SectionRenderer`: renders a single design section (text via `<p>`, json via `JsonTree`), passes `structuredClone(value)` as target_content when adding draft
  - `InlineCommentAnchor`: comment button (visible only in review mode), toggles `DraftCommentForm`
  - `DraftCommentForm`: textarea + submit/cancel buttons, inline under section. Draft cards below with dashed border + "draft" label + delete button (one-click, no confirmation dialog)
  - Purpose: SRP に分離されたインラインコメント UI コンポーネント
  - _Leverage: `JsonTree` (json display), shadcn/ui `Button`, `Textarea`_
  - _Requirements: FR-1, FR-2, FR-3, NFR-3, NFR-4, NFR-6, NFR-10, NFR-12_
  - _Prompt: Role: React component developer | Task: Create 3 SRP components for inline commenting — renderer, anchor, and form | Restrictions: SectionRenderer under 100 lines. Use existing JsonTree for JSON sections. Draft cards must have dashed border and "draft" label (NFR-10). Delete is one-click, no confirmation (NFR-12). NEVER use `dangerouslySetInnerHTML` (NFR-6) | Success: Components render correctly, form submits draft, delete removes draft without dialog_
  - **完了基準**: 3つのコンポーネントが作成され、ドラフトカードに破線ボーダー + "draft" ラベルが表示され、`dangerouslySetInnerHTML` が使用されていない
  - **確認手順**: `cd frontend && npx tsc --noEmit` がパスする。`grep -r "dangerouslySetInnerHTML" frontend/src/pages/design-detail/components/` が 0件

- [ ] 5.1 Create `ReviewBatchComposer` component
  - File: `frontend/src/pages/design-detail/components/ReviewBatchComposer.tsx` (new)
  - Floating bar (sticky bottom): draft count badge + status selector (supported/rejected/inconclusive/active) + "Submit All" button
  - Visible only when `hasDrafts` is true
  - Status selector の選択肢定数を定義（旧 `ReviewPanel.tsx` の `COMMENT_STATUSES` 相当を移設）
  - Submit: call `submitReviewBatch()`, on success call `onSubmitted()` + `onClearDrafts()`
  - Submit button disabled during API call (double-submit prevention)
  - On error: show error message via `ErrorBanner`, preserve drafts
  - Purpose: Batch submission UI（ドラフト件数表示 + ステータス選択 + 一括投稿）
  - _Leverage: `api/client.ts` (`submitReviewBatch`), shadcn/ui `Select`, `Button`, `Badge`, `ErrorBanner`_
  - _Requirements: FR-6, FR-7, FR-8, FR-9, NFR-6, NFR-11_
  - _Prompt: Role: React developer | Task: Create ReviewBatchComposer as sticky bottom bar with status selector and submit | Restrictions: Use `position: sticky; bottom: 0` (NFR-11). Disable submit button during API call. Show ErrorBanner on failure. NEVER use `dangerouslySetInnerHTML` (NFR-6) | Success: Bar appears when drafts exist, disappears when empty, submit sends batch and clears drafts_
  - **完了基準**: sticky bottom で表示され、ステータスセレクタと Submit All ボタンが機能する。送信中は Submit ボタンが disabled
  - **確認手順**: `cd frontend && npx tsc --noEmit` がパスする

- [ ] 5.2 Create `ReviewHistoryPanel` component
  - File: `frontend/src/pages/design-detail/components/ReviewHistoryPanel.tsx` (new)
  - Read-only history view — 旧 `ReviewPanel` のコンセプトを再設計
  - Fetch batches via `listReviewBatches(designId)`
  - Display each batch as a card: `StatusBadge`, reviewer, timestamp, comment list
  - Each comment shows: comment text, `target_section` label, `target_content` quote block (via `JsonTree` for json, `<blockquote>` for text)
  - Purpose: 過去の ReviewBatch を読み取り専用で表示（セクションスナップショット付き）
  - _Leverage: `StatusBadge`, `JsonTree`, `formatDateTime` from existing code_
  - _Requirements: FR-17, NFR-6_
  - _Prompt: Role: React developer | Task: Create ReviewHistoryPanel that displays past batches with target_content quotes | Restrictions: Read-only — no edit/delete. Use JsonTree for JSON target_content, blockquote for text. Reuse StatusBadge. NEVER use `dangerouslySetInnerHTML` (NFR-6) | Success: Batches displayed in descending order with section labels and content quotes_
  - **完了基準**: 過去の ReviewBatch を read-only 表示し、各コメントに `target_content` を引用表示する
  - **確認手順**: `cd frontend && npx tsc --noEmit` がパスする

## Phase 6: Frontend Integration

- [ ] 6. Restructure tabs and integrate inline comments into OverviewPanel
  - File: `frontend/src/pages/design-detail/DesignDetail.tsx` (modify), `frontend/src/pages/design-detail/OverviewPanel.tsx` (modify)
  - Change tabs: `overview | review | knowledge` → `overview | history | knowledge`
  - Replace `review` tab content with `ReviewHistoryPanel`
  - Refactor `OverviewPanel`:
    - Replace static field rendering with `SectionRenderer` loop over `COMMENTABLE_SECTIONS`
    - Integrate `useReviewDrafts` hook
    - Add `ReviewBatchComposer` at bottom
    - Pass `refreshDesign` callback to `ReviewBatchComposer.onSubmitted`
    - Move "Submit for Review" button from `ReviewPanel` to Overview（status が `active` の時のみ表示）
  - Remove import of `ReviewPanel` from `DesignDetail.tsx`
  - Purpose: レビューワークフローを Overview タブに統合する
  - _Leverage: `DesignDetail.tsx` (tab structure), `OverviewPanel.tsx` (field rendering), `ReviewPanel.tsx` (submit-for-review button logic)_
  - _Requirements: FR-15, FR-16, NFR-4_
  - _Prompt: Role: React developer with refactoring expertise | Task: Restructure tabs and integrate inline commenting into OverviewPanel | Restrictions: OverviewPanel must stay under 400 lines (NFR-4). Move submit-for-review button from ReviewPanel to Overview. Do not break KnowledgePanel | Success: 3 tabs (Overview/History/Knowledge), inline comments work without tab switch, OverviewPanel ≤ 400 lines_
  - **完了基準**: タブが Overview | History | Knowledge の3つ。Overview で inline comment が可能。OverviewPanel ≤ 400行
  - **確認手順**: `cd frontend && npx tsc --noEmit` がパスする。`wc -l frontend/src/pages/design-detail/OverviewPanel.tsx` が 400 以下

- [ ] 6.1 Clean up `ReviewPanel.tsx`
  - File: `frontend/src/pages/design-detail/ReviewPanel.tsx` (delete or archive)
  - Remove `ReviewPanel.tsx` — 機能は `OverviewPanel`（submit-for-review ボタン）と `ReviewHistoryPanel`（履歴表示）に分散済み
  - Update `index.ts` の re-export を確認
  - Verify no remaining imports of `ReviewPanel` in codebase
  - Purpose: 旧コンポーネントの明示的クリーンアップ
  - _Leverage: Task 6 で移設完了後のクリーンアップ_
  - _Requirements: FR-15 (タブ再構成の一部)_
  - _Prompt: Role: React developer | Task: Remove ReviewPanel.tsx after its responsibilities have been distributed | Restrictions: Verify zero references to ReviewPanel before deletion. Check index.ts re-exports | Success: No import errors, ReviewPanel fully replaced_
  - **完了基準**: `ReviewPanel.tsx` が削除され、`ReviewPanel` への参照がコードベースに存在しない
  - **確認手順**: `grep -r "ReviewPanel" frontend/src/ --include="*.ts" --include="*.tsx"` が 0件（ファイル自体を除く）。`cd frontend && npx tsc --noEmit` がパスする

## Phase 7: E2E Tests (test-design P7 + P8 + P9)

- [ ] 7. Add E2E test fixtures and mock routes for review batches
  - File: `frontend/e2e/fixtures/mock-data.ts` (modify), `frontend/e2e/fixtures/api-routes.ts` (modify)
  - Add `makeBatchComment()` and `makeReviewBatch()` factory functions to `mock-data.ts`
  - Add `mockReviewBatches(page, batches)` and `mockReviewBatchesError(page)` route helpers to `api-routes.ts`
  - Purpose: E2E テストインフラ整備
  - _Leverage: `mock-data.ts` (existing factory pattern: `makeComment`), `api-routes.ts` (existing route pattern: `mockComments`)_
  - _Requirements: (infrastructure for FR-1 through FR-17 E2E tests)_
  - _Prompt: Role: Playwright test infrastructure developer | Task: Add mock data factories and API route helpers for review batches | Restrictions: Follow existing factory and route patterns exactly. Include target_content in mock data | Success: Factories produce valid mock data, routes intercept GET/POST /review-batches correctly_
  - **完了基準**: `makeBatchComment`, `makeReviewBatch`, `mockReviewBatches`, `mockReviewBatchesError` が追加されている
  - **確認手順**: `cd frontend && npx tsc --noEmit` がパスする

- [ ] 7.1 Write E2E tests for tab restructuring (P7)
  - File: `frontend/e2e/design-detail.spec.ts` (modify)
  - Add `test.describe("Tab Restructuring")` block:
    - tabs show Overview, History, Knowledge
    - Review tab is removed
    - inline comments available without tab switch on pending_review
  - Purpose: タブ再構成の E2E 検証。test-design P7
  - _Leverage: `frontend/e2e/design-detail.spec.ts` (existing test patterns), `mock-data.ts` / `api-routes.ts` (new fixtures)_
  - _Requirements: FR-15, FR-16_
  - _Prompt: Role: Playwright E2E test engineer | Task: Write E2E tests for tab restructuring verifying 3-tab layout | Restrictions: Use mock routes for API calls | Success: Tab structure verified, inline comments work without tab switch_
  - **完了基準**: 3つのタブ構成テストが追加され、全テストが GREEN
  - **確認手順**: `cd frontend && npx playwright test --grep "Tab Restructuring"` で全テストがパスする

- [ ] 7.2 Write E2E tests for inline comment flow (P8)
  - File: `frontend/e2e/design-detail.spec.ts` (modify)
  - Add `test.describe("Inline Review Comments")` block:
    - Comment buttons: visible on pending_review, hidden on non-pending, click opens form
    - Draft management: adding draft shows Submit Bar, removing all hides bar, count updates, status selector shows all 4 options
    - Batch submission: Submit All sends batch + refreshes, target_content snapshot in POST body, drafts preserved on failure, submit button disabled during submission
    - Visual/usability: draft visually distinct (dashed border), Submit Bar sticky
  - Purpose: インラインコメントフローの E2E 検証。test-design P8
  - _Leverage: `frontend/e2e/design-detail.spec.ts` (existing patterns), `mock-data.ts` / `api-routes.ts` (new fixtures)_
  - _Requirements: FR-1, FR-2, FR-3, FR-5, FR-6, FR-7, FR-8, FR-9, NFR-10, NFR-11_
  - _Prompt: Role: Playwright E2E test engineer | Task: Write comprehensive E2E tests for inline comment flow covering P8 test cases | Restrictions: Use mock routes for API calls. Check for visual indicators (dashed border class, sticky positioning). Intercept POST body to verify target_content | Success: All E2E tests pass, visual assertions confirmed, POST body contains target_content_
  - **完了基準**: test-design.md P8 の全テストケースが E2E テストとして追加され、全テストが GREEN
  - **確認手順**: `cd frontend && npx playwright test --grep "Inline Review Comments"` で全テストがパスする

- [ ] 7.3 Write E2E tests for History tab (P9)
  - File: `frontend/e2e/design-detail.spec.ts` (modify)
  - Add `test.describe("Review History")` block:
    - History tab shows past review batches
    - Batch displays comments with target_section labels
    - Batch displays target_content alongside comments (blockquote for text, JSON tree for objects)
    - Batches ordered by timestamp descending
  - Purpose: History タブの E2E 検証。test-design P9
  - _Leverage: `frontend/e2e/design-detail.spec.ts` (existing patterns), `mock-data.ts` (makeReviewBatch)_
  - _Requirements: FR-17_
  - _Prompt: Role: Playwright E2E test engineer | Task: Write E2E tests for History tab verifying batch display with target_content | Restrictions: Use mock routes with multiple batches. Verify target_content rendering | Success: All History tab tests pass, target_content displayed correctly_
  - **完了基準**: 4つの E2E テストが追加され、全テストが GREEN
  - **確認手順**: `cd frontend && npx playwright test --grep "Review History"` で全テストがパスする

## Phase 8: Final Verification

- [ ] 8. Run full quality check and verify all requirements
  - File: (all modified files)
  - Run backend quality checks: `poe all` (lint + typecheck + test)
  - Run frontend type check: `cd frontend && npx tsc --noEmit`
  - Run Playwright E2E tests: `cd frontend && npx playwright test`
  - Verify OverviewPanel line count ≤ 400 (NFR-4)
  - Verify `dangerouslySetInnerHTML` not used in new components (NFR-6)
  - Verify section definition sync contract test passes (NFR-7)
  - Verify requirements traceability: all FR/NFR from test-design.md traceability matrix have corresponding passing tests
  - Purpose: 全要件の最終検証
  - _Leverage: `pyproject.toml` (poe tasks), test-design.md (traceability matrix)_
  - _Requirements: All_
  - _Prompt: Role: QA engineer | Task: Run full quality suite and verify all FR/NFR requirements are covered | Restrictions: Do not skip any check. Fix any failures before marking complete | Success: All checks pass, traceability matrix fully covered_
  - **完了基準**: 全テスト GREEN、lint/type パス、NFR-4/NFR-6/NFR-7 の確認完了、traceability matrix の全項目にテストが存在する
  - **確認手順**: `poe all && cd frontend && npx tsc --noEmit && npx playwright test` が全パスする

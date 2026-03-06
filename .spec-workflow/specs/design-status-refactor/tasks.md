# Tasks: Design Status Refactor

TDD 順序（Red → Green → Refactor）でボトムアップに実装する。各タスクは「テスト更新 → 実装変更 → Green 確認」のサイクルで進める。

- [x] 1. DesignStatus enum 置換 + create_design デフォルト変更
  - Files: `src/insight_blueprint/models/design.py`, `tests/test_designs.py`
  - Red: `test_design_status_members`, `test_design_status_values` を新6値で書き換え → `test_create_design_default_status` を `in_review` 期待に変更
  - Green: `DesignStatus(StrEnum)` のメンバーを `in_review, revision_requested, analyzing, supported, rejected, inconclusive` に置換。`AnalysisDesign.status` の default を `DesignStatus.in_review` に変更
  - Verify: `pytest tests/test_designs.py -q` で Unit-01, Unit-02 が pass
  - Purpose: 全レイヤーの基盤となる enum 定義を確定する
  - _Leverage: 既存の `DesignStatus(StrEnum)` クラス構造を維持_
  - _Requirements: FR-1 (AC 1.1, 1.3)_
  - _Prompt: Role: Python developer | Task: DesignStatus enum のメンバーを新6値に置換し、AnalysisDesign.status のデフォルトを in_review に変更する。テストを先に更新し、Red を確認してから実装を変更する | Restrictions: enum のクラス構造（StrEnum 継承）は変更しない。旧ステータス値を残さない | Success: Unit-01, Unit-02 が pass。enum メンバーが正確に6個_

- [x] 2. 遷移ルール再定義 + transition_status メソッド実装
  - Files: `src/insight_blueprint/core/reviews.py`, `tests/test_reviews.py`
  - Red: Unit-03 のテストケース群を新遷移ルールで作成（test-design.md に定義された12ケース: 有効遷移7パターン + 無効遷移4パターン + エラーメッセージ1）。parametrize で有効/無効を分類
  - Green: `VALID_REVIEW_TRANSITIONS` → `VALID_TRANSITIONS` にリネーム + 内容差し替え。`submit_for_review` → `transition_status(design_id, target_status)` に置換。`_validate_post_review_status` → `_validate_transition(current, target)` に汎用化
  - Verify: `pytest tests/test_reviews.py -q` で Unit-03 が pass
  - Purpose: ドメインロジックの中核である遷移ルールを確定する
  - _Leverage: 既存の `VALID_REVIEW_TRANSITIONS` dict 構造、`ReviewService` クラス_
  - _Requirements: FR-2 (AC 2.1-2.5)_
  - _Prompt: Role: Python developer | Task: VALID_TRANSITIONS マップを新遷移ルールに差し替え、submit_for_review を transition_status に置換する。parametrize で全遷移パターンのテストを先に書く | Restrictions: terminal states は明示的に空 set を定義（KeyError 回避）。ValueError メッセージに current と valid targets を含める | Success: Unit-03 の12ケースが全 pass。有効遷移は成功、無効遷移は ValueError_

- [x] 3. レビューバッチ前提条件の更新
  - Files: `src/insight_blueprint/core/reviews.py`, `tests/test_reviews.py`, `tests/test_web.py`
  - Red: Unit-06 テスト作成 — `test_save_review_batch_in_review`, `test_save_review_batch_status_after_values`（新5値）, `test_save_review_batch_non_in_review_rejected`, `test_submit_batch_api_non_in_review_400`
  - Green: `_ensure_pending_review` → `_ensure_in_review` にリネーム。バッチの `status_after` 許容値を `{supported, rejected, inconclusive, revision_requested, analyzing}` に更新
  - Verify: `pytest tests/test_reviews.py tests/test_web.py -q` で Unit-06 が pass
  - Purpose: レビューバッチのガードを新ワークフローに合わせる
  - _Leverage: 既存の `_ensure_pending_review` ガード、`save_review_batch` メソッド_
  - _Requirements: FR-5 (AC 5.1-5.3)_
  - _Prompt: Role: Python developer | Task: _ensure_pending_review を _ensure_in_review にリネームし、status_after の許容値を新5値に更新する。テストを先に書く | Restrictions: バッチ保存の既存ロジック（コメント保存、ステータス遷移）は変更しない | Success: Unit-06 の4ケースが全 pass_

- [x] 4. REST API エンドポイント置換
  - Files: `src/insight_blueprint/web.py`, `tests/test_web.py`
  - Red: Unit-04 テスト作成 — `test_transition_design_success`, `test_transition_design_invalid`, `test_transition_design_invalid_status_value`, `test_transition_design_not_found`, `test_old_review_endpoint_removed`
  - Green: `POST /api/designs/{id}/review` を削除。`POST /api/designs/{id}/transition` を追加（`TransitionRequest` Pydantic モデル）。内部で `ReviewService.transition_status` を呼び出し
  - Verify: `pytest tests/test_web.py -q` で Unit-04 が pass
  - Purpose: フロントエンドが呼び出す API エンドポイントを統一遷移 API に置換する
  - _Leverage: 既存の web.py ルーティングパターン、ValueError → 400 ハンドラ_
  - _Requirements: FR-3 (AC 3.1-3.4)_
  - _Prompt: Role: Python developer | Task: POST /review を削除し POST /transition を追加する。TransitionRequest Pydantic モデルを定義。テストを先に書く | Restrictions: 既存の ValueError ハンドラ（400 変換）を活用する。新しいエラーハンドリングパターンを導入しない | Success: Unit-04 の5ケースが全 pass。旧エンドポイントが 404/405 を返す_

- [x] 5. Python 統合テスト更新
  - Files: `tests/test_integration.py`, `tests/test_web_integration.py`
  - Red: Integ-01 `test_design_lifecycle` を新フロー（create→in_review→revision_requested→in_review→batch(supported)→knowledge）で書き換え。Integ-02 `test_full_web_workflow` を新エンドポイント（POST /transition）で書き換え
  - Green: Task 1-4 の実装が正しければテストは pass するはず。失敗した場合は実装側を修正
  - Verify: `pytest tests/test_integration.py tests/test_web_integration.py -q` で Integ-01, Integ-02 が pass（注: test_server.py は Task 6 で更新するため、ここでは全 Python テスト Green を要求しない）
  - Purpose: レイヤー横断のフルフロー検証で、Task 1-4 の実装が正しく連携することを確認する
  - _Leverage: 既存の統合テストパターン（YAML ファイルシステム + TestClient）_
  - _Requirements: FR-1 (AC 1.3), FR-2 (AC 2.1, 2.2), FR-3 (AC 3.1), FR-5 (AC 5.3)_
  - _Prompt: Role: Python developer | Task: 統合テストを新ワークフローに書き換える。test_design_lifecycle は create→遷移サイクル→バッチ→知識抽出のフルフロー。test_full_web_workflow は HTTP 経由の全操作 | Restrictions: テストの検証ポイントを減らさない。フルフローの各ステップで状態を確認する | Success: Integ-01, Integ-02 が pass。python -m pytest tests/ -q で全 Python テスト 0 failures_

- [x] 6. MCP ツール置換
  - Files: `src/insight_blueprint/server.py`, `tests/test_server.py`
  - Red: Unit-05 テスト作成 — `test_transition_design_status_success`, `test_transition_design_status_invalid`, `test_submit_for_review_removed`
  - Green: `submit_for_review` ツールを削除。`transition_design_status(design_id, status)` ツールを追加。ValueError キャッチで `{"error": "..."}` 返却。`update_analysis_design` の `pending_review` ガード削除。`create_analysis_design` の docstring 更新
  - Verify: `pytest tests/test_server.py -q` で Unit-05 が pass。続けて `python -m pytest tests/ -q` で全 Python テスト 0 failures を確認（Task 1-5 の変更との統合検証）
  - Purpose: Claude Code が使う MCP ツールを新ワークフローに合わせる。Python バックエンド全体の Green をここで確定する
  - _Leverage: 既存の MCP ツールパターン（dict 返却、エラー dict）_
  - _Requirements: FR-4 (AC 4.1-4.3)_
  - _Prompt: Role: Python developer | Task: submit_for_review MCP ツールを transition_design_status に置換する。テストを先に書く | Restrictions: MCP ツールは例外を raise せず dict を返す既存パターンに従う。エラー時は `{"error": "Cannot transition from X to Y. Valid: ..."}` 形式 | Success: Unit-05 の3ケースが全 pass。python -m pytest tests/ -q で全 Python テスト 0 failures_

- [x] 7. フロントエンド型・定数・コンポーネント・API クライアント更新
  - Files: `frontend/src/types/api.ts` (C5), `frontend/src/lib/constants.tsx` (C6), `frontend/src/components/StatusBadge.tsx` (C7), `frontend/src/pages/DesignsPage.tsx` (C8), `frontend/src/pages/design-detail/OverviewPanel.tsx` (C9), `frontend/src/api/client.ts` (C10), `frontend/src/pages/design-detail/components/ReviewBatchComposer.tsx` (C11)
  - 粒度の判断: 7ファイルだが全て値の機械的差し替え（enum 値・ラベル・色・配列・URL）で設計判断が不要。型定義 (C5) を起点に tsc が依存エラーを示すため、一括変更の方が中間の壊れた状態を避けられる
  - Red: `tsc --noEmit` で旧型参照のコンパイルエラーを確認（Static-01 の逆利用）
  - Green:
    - C5: `DesignStatus` 型を新6値の union に置換
    - C6: `DESIGN_STATUS_LABELS` を新ラベルマップに置換
    - C7: `STATUS_STYLES` を新カラースキーム（in_review=yellow, revision_requested=blue, analyzing=purple）に置換
    - C8: `ALL_STATUSES` を新6値に置換
    - C9: `STATUS_GUIDE` を新6ステータス対応に更新。`isReviewMode` を `status === "in_review"` に変更。Submit for Review ボタン削除。未使用 import 削除
    - C10: `submitReview` 関数を削除。`transitionDesign(designId, status)` を追加（POST `/api/designs/{id}/transition`）
    - C11: `BATCH_STATUSES` を `["supported", "rejected", "inconclusive", "revision_requested", "analyzing"]` に置換
  - Verify: `tsc --noEmit` pass (Static-01)
  - Purpose: フロントエンド全コンポーネントを新ステータスに一括更新する
  - _Leverage: 既存のコンポーネント構造をそのまま維持。値の差し替えのみ_
  - _Requirements: FR-6 (AC 6.1-6.4), FR-7 (AC 7.1-7.4), FR-8 (AC 8.1-8.2), FR-9 (AC 9.1)_
  - _Prompt: Role: TypeScript/React developer | Task: フロントエンド全ファイルの旧ステータス参照を新ステータスに置換する。型定義から始め、依存する定数・コンポーネント・API クライアントを順に更新 | Restrictions: コンポーネント構造は変更しない。値の差し替えのみ。新コンポーネントを追加しない | Success: tsc --noEmit が pass。旧ステータスリテラル（draft, active, pending_review）がフロントエンドコードに残らない_

- [x] 8. E2E テストフィクスチャ・スペック更新
  - Files: `frontend/e2e/fixtures/mock-data.ts` (C12), `frontend/e2e/fixtures/api-routes.ts` (C13), `frontend/e2e/design-detail.spec.ts`, `frontend/e2e/smoke.spec.ts`, `frontend/e2e/history.spec.ts` (C14)
  - Red: 旧ステータス参照のまま `npx playwright test` → 失敗を確認
  - Green:
    - C12: `makeDesign` デフォルト status を `"in_review"` に変更
    - C13: `mockSubmitReview` → `mockTransitionDesign` にリネーム。エンドポイントを `/transition` に変更
    - C14: 旧ステータス参照を新ステータスに置換。`mockSubmitReview` → `mockTransitionDesign`。Submit for Review テスト → ワークフローガイド表示テストに置換。S6 フィルタテストを `"in_review"` に変更
  - Verify: `npx playwright test` で E2E-01〜05 が pass
  - Purpose: E2E テストを新ワークフローに合わせ、フロントエンドとバックエンドの連携を検証する
  - _Leverage: 既存の E2E テスト構造、Playwright API モックパターン_
  - _Requirements: FR-10 (AC 10.1-10.4)。E2E テスト経由で FR-6 (AC 6.2-6.4), FR-7 (AC 7.1-7.4), FR-8 (AC 8.1), FR-9 (AC 9.1) も間接検証_
  - _Prompt: Role: E2E test developer | Task: E2E フィクスチャとスペックの旧ステータス参照を新ステータスに置換する。mockSubmitReview を mockTransitionDesign にリネーム | Restrictions: cross-tab.spec.ts の `data-state="active"` は Radix UI 属性なので変更しない。テスト構造は維持し、値の置換のみ | Success: npx playwright test で全 E2E テスト pass_

- [x] 9. Static 検証 + 全体リグレッションチェック
  - Files: なし（検証のみ）
  - 検証項目:
    - Static-01: `cd frontend && npx tsc --noEmit` → pass
    - Static-02: `grep -rn "draft\|pending_review" src/insight_blueprint/ tests/ frontend/src/` でプロダクションコード + テスト + フロントエンドにヒット 0 件。`grep -rn '"active"' src/insight_blueprint/ frontend/src/types/ frontend/src/lib/constants.tsx frontend/src/pages/` で DesignStatus 文脈を広めに確認（`cross-tab.spec.ts` 等の `data-state="active"` は Radix UI 属性のため対象外）
    - Static-03: `grep -rn "submit_for_review\|submitReview" src/ frontend/src/` でヒット 0 件
    - Python 全テスト: `python -m pytest tests/ -q` → 0 failures
    - E2E 全テスト: `cd frontend && npx playwright test` → all pass
  - Purpose: 旧コード残存がないことを保証し、全レイヤーのリグレッションがないことを最終確認する
  - _Requirements: FR-1 (AC 1.2), FR-3 (AC 3.4), FR-8 (AC 8.2) + 全 FR の統合検証_
  - _Prompt: Role: QA engineer | Task: Static 検証コマンド群を実行し、旧ステータス・旧関数の残存がゼロであることを確認。全テストスイートを実行してリグレッションがないことを確認 | Restrictions: テストやプロダクションコードを変更しない。検証のみ。失敗があれば該当タスクに差し戻す | Success: Static-01〜03 全 pass。pytest 0 failures。Playwright all pass。成功基準チェックリスト全項目クリア_

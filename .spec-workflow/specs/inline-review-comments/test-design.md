# Test Design: Inline Review Comments

## Overview

インラインレビューコメント機能のテスト設計（簡素化版）。レガシー互換・冪等性・sessionStorage 永続化を排除し、コア機能に集中する。TDD の Red-Green-Refactor サイクルに従い、テストを実装より先に書く。既存プロジェクトのテストパターン（class-based grouping、fixture composition、AC 参照 docstring）を踏襲する。

## Test Scope

| レイヤー | テスト種別 | フレームワーク | 対象 |
|----------|-----------|---------------|------|
| Models | Unit | pytest | `ReviewBatch`, `BatchComment` |
| Service | Unit | pytest | `ReviewService` 拡張 |
| REST API | Integration | pytest + TestClient | `/review-batches` |
| MCP Tool | Integration | pytest + asyncio | `save_review_batch` tool |
| Contract | Unit | pytest | Section 定義同期 |
| Frontend | E2E | Playwright | インラインコメントフロー, History タブ |

**フロントエンド Unit テストは対象外** — プロジェクトに vitest/jest は未導入。ロジックは E2E でカバーする。

## Fixtures

### 既存 fixtures（再利用）

- `tmp_project(tmp_path)` — `.insight/` 初期化済みの一時プロジェクト
- `design_service(tmp_path)` — DesignService インスタンス
- `review_service(tmp_path, design_service)` — ReviewService インスタンス
- `active_design(design_service)` — `active` ステータスの Design
- `pending_design(design_service, review_service, active_design)` — `pending_review` の Design

### 新規 fixtures（`conftest.py` に追加）

```python
@pytest.fixture
def review_batch_data():
    """有効な ReviewBatch 投稿リクエストの基本データ。"""
    return {
        "status_after": "supported",
        "reviewer": "analyst",
        "comments": [
            {
                "comment": "仮説の指標が曖昧",
                "target_section": "hypothesis_statement",
                "target_content": "〇〇の施策はCVRを改善する",
            },
            {
                "comment": "KPI測定期間が未定義",
                "target_section": "metrics",
                "target_content": {"kpi_name": "CVR", "current_value": "2.5%"},
            },
        ],
    }

def make_batch_payload(**overrides):
    """テスト用バッチ payload ファクトリ。有効/無効データの量産に使用。"""
    base = {
        "status_after": "supported",
        "reviewer": "analyst",
        "comments": [
            {
                "comment": "テストコメント",
                "target_section": "hypothesis_statement",
                "target_content": "テスト仮説",
            },
        ],
    }
    base.update(overrides)
    return base

@pytest.fixture
def non_pending_design(design_service):
    """draft ステータスの Design。投稿拒否テスト用。"""
    return design_service.create_design(
        hypothesis="テスト仮説", source_ids=["SRC-1"]
    )

@pytest.fixture
def fixed_now(monkeypatch):
    """now_jst() を固定時刻に差し替え。ソート安定化用。
    Note: models/review.py 内の import にも対応するため両方 patch する。"""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    fixed = datetime(2026, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    monkeypatch.setattr("insight_blueprint.models.common.now_jst", lambda: fixed)
    monkeypatch.setattr("insight_blueprint.models.review.now_jst", lambda: fixed)
    return fixed

@pytest.fixture
def corrupted_reviews_yaml(tmp_path):
    """パース不能な reviews YAML ファイル。YAML 破損テスト用。"""
    path = tmp_path / ".insight" / "designs" / "DES-corrupt_reviews.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("batches:\n  - invalid: [unclosed bracket", encoding="utf-8")
    return path

@pytest.fixture
def status_update_failure(monkeypatch, design_service):
    """DesignService のステータス更新を強制失敗させる。原子性テスト用。"""
    original = design_service.update_status
    def fail_update(*args, **kwargs):
        raise RuntimeError("Simulated status update failure")
    monkeypatch.setattr(design_service, "update_status", fail_update)
    return original
```

## Unit Tests: Models

### ファイル: `tests/test_review_models.py`（既存に追加）

```
class TestBatchComment:
    test_valid_batch_comment                    # FR-11: comment + target_section + target_content で生成できる
    test_target_section_optional                # FR-11: target_section は None 許容
    test_target_content_optional_when_no_section  # FR-11: target_section=None なら target_content=None 許容
    test_target_section_requires_target_content # FR-11: target_section set + target_content=None → ValidationError
    test_target_content_preserves_text          # FR-11: text 型セクションの内容保持
    test_target_content_preserves_json          # FR-11: json 型セクションの内容保持（dict/list）
    test_target_content_rejects_non_json_values # JsonValue: datetime/set 等の非 JSON 互換値を拒否（parametrize）
    test_empty_comment_rejected                 # 空文字コメントを拒否
    test_whitespace_only_comment_rejected       # 空白のみコメント（"   "）を拒否
    test_comment_max_length_boundary            # 2000文字ちょうど → 許可
    test_comment_over_max_length_rejected       # 2001文字 → 拒否
    test_empty_string_target_section_rejected   # target_section="" を拒否（None のみ許容）
    test_extra_field_rejected                   # extra="forbid": 未知フィールドで ValidationError

class TestReviewBatch:
    test_valid_review_batch                     # FR-10: 全フィールドで生成できる
    test_id_format                              # FR-10: id は "RB-" prefix + 8文字 hex
    test_status_after_must_be_valid             # FR-10: 不正ステータスを拒否
    test_comments_must_not_be_empty             # FR-10: コメント0件を拒否
    test_created_at_defaults_to_jst             # FR-10: デフォルトで JST タイムスタンプ
    test_reviewer_defaults_to_analyst           # FR-10: reviewer のデフォルト値
    test_json_round_trip                        # シリアライズ→デシリアライズの一貫性（target_content 含む）
    test_extra_field_rejected                   # extra="forbid": 未知フィールドで ValidationError
```

## Unit Tests: ReviewService

### ファイル: `tests/test_reviews.py`（既存に追加）

```
class TestSaveReviewBatch:
    test_save_batch_with_valid_data             # FR-8, FR-12: 正常系。バッチ保存 + ステータス遷移
    test_save_batch_transitions_design_status   # FR-8: Design ステータスが status_after に遷移する
    test_save_batch_persists_to_yaml            # FR-14: YAML ファイルに永続化される
    test_save_batch_preserves_target_section    # FR-4: 各コメントの target_section が保存される
    test_save_batch_preserves_target_content_text   # FR-11: text 型 target_content が保存される
    test_save_batch_preserves_target_content_json   # FR-11: json 型 target_content が保存される
    test_save_batch_rejects_non_pending_review  # AC: pending_review でない場合 ValueError
    test_save_batch_rejects_invalid_status      # 不正な status_after を拒否
    test_save_batch_rejects_empty_comments      # コメント0件を拒否
    test_save_batch_rejects_invalid_design_id   # パストラバーサル等の不正 ID を拒否（parametrize）
    test_save_batch_missing_design              # 存在しない design_id で None 返却
    test_save_batch_yaml_write_failure_no_status_change  # NFR-8, NFR-9: YAML 書き込み失敗時ステータス未遷移
    test_save_batch_status_update_failure_keeps_batch  # NFR-8: YAML 成功 → ステータス更新失敗 → バッチは保存済み
    test_save_batch_all_status_transitions      # FR-7: supported/rejected/inconclusive/active 全遷移（parametrize）
    test_save_batch_appends_to_existing_batches # 既存バッチがあるファイルに追記される
    test_save_batch_creates_new_file            # reviews.yaml が存在しない場合に新規作成

class TestSaveReviewBatchTargetSectionValidation:
    test_valid_target_sections_accepted          # NFR-7: 6セクション全てが通る（parametrize）
    test_invalid_target_section_rejected          # NFR-7: 不正なセクション名を拒否
    test_null_target_section_accepted             # NFR-7: None は許容（アンカーなしコメント）

class TestListReviewBatches:
    test_list_batches_returns_all                # FR-13: 全バッチを返す
    test_list_batches_descending_order           # FR-13: created_at 降順
    test_list_batches_empty                      # バッチなしで空リスト
    test_list_batches_nonexistent_design         # 存在しない design_id で空リスト
    test_list_batches_no_file                    # reviews.yaml が存在しない場合に空リスト
    test_list_batches_no_batches_key             # YAML に batches キーがない場合に空リスト + warning log
    test_list_batches_preserves_target_content   # target_content がバッチ取得時に保持される
    test_list_batches_corrupted_yaml             # Error#7: YAML 破損時に空リスト + warning log
```

## Contract Tests: Section Definition Sync

### ファイル: `tests/test_reviews.py`（既存に追加）

```
class TestSectionDefinitionSync:
    test_allowed_sections_matches_commentable_sections  # NFR-7: backend ALLOWED_TARGET_SECTIONS と frontend COMMENTABLE_SECTIONS の ID 集合が一致する
```

**Note**: フロントエンドの `COMMENTABLE_SECTIONS` 定義ファイルを読み取り、バックエンドの `ALLOWED_TARGET_SECTIONS` と ID セットが一致するかを検証する。セクション追加漏れの自動検知。

## Integration Tests: REST API

### ファイル: `tests/test_web.py`（既存に追加）

```
class TestReviewBatchAPI:
    # POST /api/designs/{id}/review-batches
    test_submit_batch_success                    # FR-12: 正常系。201 + batch_id 返却
    test_submit_batch_transitions_status         # FR-8: ステータス遷移確認
    test_submit_batch_all_statuses               # FR-7: supported/rejected/inconclusive/active（parametrize）
    test_submit_batch_non_pending_returns_400    # AC: pending_review でなければ 400
    test_submit_batch_invalid_design_returns_404 # Error#5: 存在しない design_id で 404
    test_submit_batch_invalid_section_returns_422 # NFR-7: 不正 target_section で 422（レスポンスに field 名含む）
    test_submit_batch_empty_comments_returns_422  # Error#6: コメント0件で 422
    test_submit_batch_overlength_comment_returns_422  # Error#6: 2001文字コメントで 422
    test_submit_batch_missing_target_content_returns_422  # FR-11: target_section set + target_content なしで 422
    test_submit_batch_extra_field_returns_422     # extra="forbid": 未知フィールドで 422
    test_submit_batch_with_target_content        # FR-11: target_content の round-trip 確認

    # GET /api/designs/{id}/review-batches
    test_list_batches_success                    # FR-13: 正常系。バッチリスト返却
    test_list_batches_empty                      # バッチなしで空リスト
    test_list_batches_descending_order           # FR-13: 降順ソート
    test_list_batches_includes_target_content    # FR-11: レスポンスに target_content 含む
```

## Integration Tests: MCP Tool

### ファイル: `tests/test_server.py`（既存に追加）

```
class TestSaveReviewBatchTool:
    test_save_review_batch_tool_success          # FR-18: 正常系。バッチ作成 + ステータス遷移
    test_save_review_batch_tool_with_sections    # FR-18: target_section + target_content 付きコメント
    test_save_review_batch_tool_non_pending      # FR-18: pending_review でなければエラー
```

## E2E Tests: Playwright

### ファイル: `frontend/e2e/design-detail.spec.ts`（既存に追加）

```
test.describe("Inline Review Comments", () => {
    // Tab Restructuring (FR-15, FR-16)
    test("tabs show Overview, History, Knowledge")
    test("Review tab is removed")
    test("inline comments available without tab switch on pending_review")  // FR-16

    // Comment Buttons (FR-1, FR-2, FR-3)
    test("comment buttons visible on pending_review design")
    test("comment buttons hidden on non-pending_review design")
    test("clicking comment button opens inline form")

    // Draft Management (FR-5, FR-6, FR-7)
    test("adding draft shows Review Submit Bar")
    test("removing all drafts hides Submit Bar")
    test("Submit Bar shows draft count")
    test("adding drafts to multiple sections updates count")
    test("status selector shows all 4 options")  // FR-7

    // Batch Submission (FR-8, FR-9)
    test("Submit All sends batch and refreshes design")
    test("Submit All sends target_content snapshot in POST body")  // FR-11: スナップショット送信確認
    test("drafts preserved on submission failure")
    test("Submit button disabled during submission")

    // Visual / Usability (NFR-10, NFR-11)
    test("draft comments visually distinct from submitted")  // NFR-10
    test("Submit Bar sticky at bottom")  // NFR-11
})
```

### ファイル: `frontend/e2e/history.spec.ts`（既存に追加）

```
test.describe("Review History", () => {
    // History Tab (FR-17)
    test("History tab shows past review batches")
    test("batch displays comments with target_section labels")
    test("batch displays target_content alongside comments")  // FR-17: スナップショット表示
    test("batches ordered by timestamp descending")
})
```

### Mock Data 追加（`frontend/e2e/fixtures/mock-data.ts`）

```typescript
export function makeBatchComment(overrides?: Partial<BatchComment>): BatchComment {
    return {
        comment: "テストコメント",
        target_section: "hypothesis_statement",
        target_content: "テスト仮説の内容",
        ...overrides,
    };
}

export function makeReviewBatch(overrides?: Partial<ReviewBatch>): ReviewBatch {
    return {
        id: "RB-test0001",
        design_id: "DES-test",
        status_after: "supported",
        reviewer: "analyst",
        comments: [makeBatchComment()],
        created_at: "2026-03-01T10:00:00+09:00",
        ...overrides,
    };
}
```

### API Route 追加（`frontend/e2e/fixtures/api-routes.ts`）

```typescript
export function mockReviewBatches(page: Page, batches: ReviewBatch[] = []) {
    return page.route("**/api/designs/*/review-batches", (route) => {
        if (route.request().method() === "GET") {
            route.fulfill({ json: { batches, count: batches.length } });
        } else if (route.request().method() === "POST") {
            route.fulfill({
                status: 201,
                json: { batch_id: "RB-new00001", status_after: "supported", comment_count: 1 },
            });
        }
    });
}

export function mockReviewBatchesError(page: Page) {
    return page.route("**/api/designs/*/review-batches", (route) => {
        if (route.request().method() === "POST") {
            route.fulfill({ status: 500, json: { error: "Internal Server Error" } });
        }
    });
}
```

## Test Priority（実装順序）

TDD の Red-Green-Refactor で、以下の順にテスト→実装を進める。P1 内で model_validator / extra=forbid / JsonValue 制約を最初に固める。

| Priority | テスト対象 | 理由 |
|----------|-----------|------|
| **P1** | `BatchComment` / `ReviewBatch` モデル（validator, extra=forbid, JsonValue 含む） | 他の全てがこのモデルに依存。バリデーション契約を最初に固める |
| **P2** | `ReviewService.save_review_batch()` + YAML 永続化 + 原子性 | コアビジネスロジック + 永続化契約 + 操作順序を同時に固める |
| **P3** | `ReviewService.list_review_batches()` + YAML 破損ハンドリング | 読み取り系。異常系（破損ファイル）含む |
| **P4** | Contract: Section 定義同期 | backend/frontend の整合性保証 |
| **P5** | REST API エンドポイント | サービス層のトランスポート |
| **P6** | MCP ツール | REST API と同一サービス層を使用 |
| **P7** | E2E: タブ再構成 | フロントエンドの骨格 |
| **P8** | E2E: インラインコメントフロー + スナップショット送信 | フルフロー |
| **P9** | E2E: History タブ + target_content 表示 | 読み取り系 UI + スナップショット表示 |

## Requirements Traceability

全 FR/NFR を網羅。自動テスト対象外の項目は根拠と代替手段を明記。

| Requirement | テストケース | 備考 |
|-------------|-------------|------|
| FR-1 | E2E: comment buttons visible on pending_review | |
| FR-2 | E2E: comment buttons hidden on non-pending_review | |
| FR-3 | E2E: clicking comment button opens inline form | |
| FR-4 | TestSaveReviewBatch.test_save_batch_preserves_target_section | |
| FR-5 | E2E: adding draft shows Review Submit Bar | |
| FR-6 | E2E: Submit Bar shows draft count, adding drafts to multiple sections updates count | |
| FR-7 | E2E: status selector shows all 4 options, TestSaveReviewBatch.test_save_batch_all_status_transitions, TestReviewBatchAPI.test_submit_batch_all_statuses | |
| FR-8 | TestSaveReviewBatch.test_save_batch_transitions_design_status, TestReviewBatchAPI.test_submit_batch_transitions_status | |
| FR-9 | E2E: Submit All sends batch and refreshes design | |
| FR-10 | TestReviewBatch (全テスト) | |
| FR-11 | TestBatchComment (全テスト含む validator/JsonValue), TestSaveReviewBatch.test_save_batch_preserves_target_content_*, TestReviewBatchAPI.test_submit_batch_with/missing_target_content, E2E: Submit All sends target_content | model_validator + JsonValue + round-trip |
| FR-12 | TestReviewBatchAPI.test_submit_batch_success | |
| FR-13 | TestListReviewBatches.test_list_batches_returns_all, TestReviewBatchAPI.test_list_batches_success | |
| FR-14 | TestSaveReviewBatch.test_save_batch_persists_to_yaml | |
| FR-15 | E2E: tabs show Overview, History, Knowledge | |
| FR-16 | E2E: inline comments available without tab switch on pending_review | |
| FR-17 | E2E: History tab shows past review batches, batch displays target_section labels, batch displays target_content alongside comments | |
| FR-18 | TestSaveReviewBatchTool.test_save_review_batch_tool_success | |
| NFR-1 | — | 構造規約。コードレビューで確認（ファイル配置） |
| NFR-2 | — | 構造規約。コードレビューで確認（ファイル配置） |
| NFR-3 | — | 構造規約。コードレビューで確認（ファイル配置） |
| NFR-4 | — | 構造規約。実装後に `wc -l` で行数確認 |
| NFR-5 | — | 構造規約。React DevTools Profiler で再レンダリング確認 |
| NFR-6 | — | `Manual`: E2E で XSS payload を入力し、エスケープを目視確認 |
| NFR-7 | TestSaveReviewBatchTargetSectionValidation (全テスト), TestSectionDefinitionSync | バリデーション + backend/frontend 同期契約 |
| NFR-8 | TestSaveReviewBatch.test_save_batch_yaml_write_failure_no_status_change, test_save_batch_status_update_failure_keeps_batch | YAML 失敗・ステータス失敗の両方向 |
| NFR-9 | TestSaveReviewBatch.test_save_batch_yaml_write_failure_no_status_change | NFR-8 と同一テストでカバー |
| NFR-10 | E2E: draft comments visually distinct from submitted | CSS クラス存在チェック |
| NFR-11 | E2E: Submit Bar sticky at bottom | viewport 内に表示されるかチェック |
| NFR-12 | E2E: removing all drafts hides Submit Bar | |

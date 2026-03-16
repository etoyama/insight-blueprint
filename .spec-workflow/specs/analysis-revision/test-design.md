# Test Design: analysis-revision

## Overview

analysis-revision スペックのテスト設計。REQ-1（MCP tool `get_review_comments`）のテストカバレッジを定義する。

REQ-2（analysis-revision スキル）と REQ-3（tracking file）は SKILL.md（プロンプト）と skill-managed YAML であり、自動テストの対象外。MCP tool 層の Unit + Integration テストで本 spec の Python コード変更を十分にカバーする。

テストコードは正（仕様）。実装コードのみを修正対象とする（TDD 原則）。

---

## Coverage Matrix

### REQ-1: レビューコメント読み取り MCP tool

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-1.1 | `get_review_comments` がバッチ一覧を返す | Unit-01 | Integ-01 | - |
| AC-1.2 | レビュー未存在で空リスト | Unit-02 | - | - |
| AC-1.3 | 空文字列 design_id でエラー | Unit-03 | - | - |
| AC-1.4 | 破損 YAML で空リスト（エラーにならない） | Unit-04 | - | - |

### REQ-2: analysis-revision スキル

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-2.1 | スキルトリガー | - | - | - |
| AC-2.2 | status != revision_requested でエラー | - | - | - |
| AC-2.3 | コメントのグルーピング表示 | - | - | - |
| AC-2.4 | tracking file 更新 | - | - | - |
| AC-2.5 | 全対応完了で in_review 遷移提案 | - | - | - |
| AC-2.6 | セッション再開で状態復元 | - | - | - |

**テストしない理由**: REQ-2 は SKILL.md（Claude への指示プロンプト）であり、Python コード変更を伴わない。スキルの動作は Claude の実行に依存するため、自動テストではなく手動のスキル実行で検証する。

### REQ-3: コメント対応状態の追跡

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-3.1 | tracking file 初回作成 | - | - | - |
| AC-3.2 | セッション再開で再利用 | - | - | - |
| AC-3.3 | 新バッチで上書きリセット | - | - | - |
| AC-3.4 | addressed_at タイムスタンプ記録 | - | - | - |
| AC-3.5 | 全対応完了の判定 | - | - | - |

**テストしない理由**: REQ-3 の tracking file は Claude が Read/Write tool で直接操作する skill-managed data。Python コード変更なし。SKILL.md のワークフロー定義で制御される。

### 補完テスト

| 検証項目 | Unit | Integ | E2E |
|---------|------|-------|-----|
| 複数バッチが created_at 降順で返る | Unit-05 | - | - |
| save_review_batch → get_review_comments ラウンドトリップ | - | Integ-01 | - |
| target_section/target_content がレスポンスに含まれる | Unit-06 | - | - |
| valid 形式だが存在しない design_id で空リスト | Unit-07 | - | - |
| ReviewService 例外時に error dict を返す | Unit-08 | - | - |
| 既存テスト全 pass（リグレッションなし） | - | CI | - |

> Unit-07, Unit-08 は Codex test-design レビューで追加。

---

## Test Scenarios

### Unit Tests

#### Unit-01: get_review_comments returns batches

```
File: tests/test_server.py
Pattern: test_get_review_comments_returns_batches

Arrange:
  - initialized_review_server fixture
  - Create in_review design via _create_in_review_design()
  - Save review batch via save_review_batch(design_id, "revision_requested", [{"comment": "Fix hypothesis"}])
Act: result = asyncio.run(server_module.get_review_comments(design_id))
Assert:
  - result["design_id"] == design_id
  - result["count"] == 1
  - result["batches"][0]["status_after"] == "revision_requested"
  - result["batches"][0]["comments"][0]["comment"] == "Fix hypothesis"
```

#### Unit-02: get_review_comments returns empty when no reviews

```
File: tests/test_server.py
Pattern: test_get_review_comments_empty_when_no_reviews

Arrange:
  - initialized_review_server fixture
  - Create in_review design (no reviews saved)
Act: result = asyncio.run(server_module.get_review_comments(design_id))
Assert:
  - result["design_id"] == design_id
  - result["batches"] == []
  - result["count"] == 0
```

#### Unit-03: get_review_comments rejects invalid design_id

```
File: tests/test_server.py
Pattern: test_get_review_comments_invalid_design_id

Arrange: (no server setup needed for validation-only test)
  - initialized_review_server fixture
Act: result = asyncio.run(server_module.get_review_comments(""))
Assert:
  - "error" in result

Act: result = asyncio.run(server_module.get_review_comments("../etc/passwd"))
Assert:
  - "error" in result
```

#### Unit-04: get_review_comments handles corrupted YAML gracefully

```
File: tests/test_server.py
Pattern: test_get_review_comments_corrupted_yaml_returns_empty

Arrange:
  - initialized_review_server fixture
  - Create in_review design
  - Overwrite {design_id}_reviews.yaml with invalid YAML content
Act: result = asyncio.run(server_module.get_review_comments(design_id))
Assert:
  - result["batches"] == []
  - result["count"] == 0
  - "error" not in result  (graceful degradation, not error)
```

#### Unit-05: get_review_comments returns batches sorted descending

```
File: tests/test_server.py
Pattern: test_get_review_comments_sorted_descending

Arrange:
  - initialized_review_server fixture
  - Create in_review design
  - Save batch 1 via save_review_batch(..., "revision_requested", ...)
  - Transition back to in_review via transition_design_status
  - Save batch 2 via save_review_batch(..., "revision_requested", ...)
Act: result = asyncio.run(server_module.get_review_comments(design_id))
Assert:
  - result["count"] == 2
  - result["batches"][0]["created_at"] >= result["batches"][1]["created_at"]
```

#### Unit-06: get_review_comments includes target_section and target_content

```
File: tests/test_server.py
Pattern: test_get_review_comments_includes_target_fields

Arrange:
  - initialized_review_server fixture
  - Create in_review design
  - Save batch with comment containing target_section="metrics" and target_content=[{"target": "rev"}]
Act: result = asyncio.run(server_module.get_review_comments(design_id))
Assert:
  - batch = result["batches"][0]
  - batch["comments"][0]["target_section"] == "metrics"
  - batch["comments"][0]["target_content"] == [{"target": "rev"}]
```

### Integration Tests

#### Unit-07: get_review_comments returns empty for valid but nonexistent design_id (Codex review)

```
File: tests/test_server.py
Pattern: test_get_review_comments_nonexistent_design_id

Arrange:
  - initialized_review_server fixture
  - Do NOT create any design
Act: result = asyncio.run(server_module.get_review_comments("NONEXISTENT-H99"))
Assert:
  - result["design_id"] == "NONEXISTENT-H99"
  - result["batches"] == []
  - result["count"] == 0
  - "error" not in result
```

#### Unit-08: get_review_comments returns error when service raises exception (Codex review)

```
File: tests/test_server.py
Pattern: test_get_review_comments_service_exception_returns_error

Arrange:
  - initialized_review_server fixture
  - unittest.mock.patch ReviewService.list_review_batches to raise RuntimeError
Act: result = asyncio.run(server_module.get_review_comments("ANY-H01"))
Assert:
  - "error" in result
```

### Integration Tests

#### Integ-01: save_review_batch → get_review_comments round-trip

```
File: tests/test_server.py
Pattern: test_review_write_then_read_roundtrip

Arrange:
  - initialized_review_server fixture
  - Create in_review design
  - Save batch with 3 comments (mixed: with/without target_section)
Act:
  - write_result = asyncio.run(server_module.save_review_batch(...))
  - read_result = asyncio.run(server_module.get_review_comments(design_id))
Assert:
  - write_result["batch_id"] is present
  - read_result["count"] == 1
  - len(read_result["batches"][0]["comments"]) == 3
  - All comment contents match what was written
```

---

## Test File Structure

| Test File | Target | Tests Added |
|-----------|--------|-------------|
| `tests/test_server.py` | server.py (MCP tool) | Unit-01〜08, Integ-01 |

---

## Coverage Target

- **MCP tool layer**: `get_review_comments` の全分岐パスをカバー（正常、空、不正 ID、破損 YAML、存在しない ID、service 例外）
- **Service layer**: `ReviewService.list_review_batches()` は既存テスト（`tests/test_reviews.py`）でカバー済み。追加不要
- **Backward compatibility**: 既存 725 テスト全 pass が CI で確認されること

## Success Criteria

1. 上記 Unit-01〜08 + Integ-01 の全9テストが pass
2. 既存テストにリグレッションなし
3. `get_review_comments` MCP tool の全エラーパスがテストでカバーされていること

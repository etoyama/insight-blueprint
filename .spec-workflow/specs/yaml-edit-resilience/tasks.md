# Tasks: YAML Direct Edit Resilience

## Overview

F1（Extra Field Preservation）と F2（Corrupt File Isolation）は独立した変更。
2トラックの並行実装が可能。各トラックは Red → Green の TDD サイクルで進める。

**Codex レビュー反映**: try/except スコープ拡大（`read_yaml()` 含む）、Task 1.3 を Verification に変更、回帰テストタスク追加。

---

## Tasks

- [x] 1.1. Write F1 model-layer unit tests (Red)
  - File: `tests/test_design_models.py`
  - Purpose: extra フィールド保全の model 層テストを追加し、Red 状態を確立する
  - Leverage: 既存テストの fixture パターン（`_base_design_data()`）、`model_dump(mode="json")` の既存テスト
  - Requirements: REQ-1 (FR-1.1, FR-1.2)
  - Prompt: Test Design の Unit-01〜06, Unit-12, Unit-13, Unit-16 を実装。全テストで `model_dump(mode="json")` を明示使用。Unit-16 は parametrize で 4 StrEnum の不正値を検証
  - Dependencies: None

- [x] 1.2. Implement ConfigDict(extra="allow") on 5 models (Green)
  - File: `src/insight_blueprint/models/design.py`
  - Purpose: 5つの BaseModel サブクラスに `ConfigDict(extra="allow")` を追加し、Task 1.1 のテストを Green にする
  - Leverage: Pydantic v2 `ConfigDict` の標準機能。既存の全 validator・フィールド定義は変更なし
  - Requirements: REQ-1 (FR-1.1, FR-1.2)
  - Prompt: `ExplanatoryVariable`, `Metric`, `ChartSpec`, `Methodology`, `AnalysisDesign` の 5 クラスに `model_config = ConfigDict(extra="allow")` を追加。import に `ConfigDict` を追加。既存コードは一切変更しない
  - Dependencies: 1.1

- [x] 1.3. Write F1 service-layer verification tests (Verification)
  - File: `tests/test_designs.py`
  - Purpose: `update_design()` 経由の extra フィールド round-trip と `referenced_knowledge` merge との相互作用を検証する。Task 1.2 の model 変更のみで Green が期待される（service 層の変更なし）
  - Leverage: 既存の `service` fixture、`write_yaml` / `read_yaml` ヘルパー
  - Requirements: REQ-1 (FR-1.3, FR-1.4)
  - Prompt: Test Design の Unit-03, Unit-14, Integ-01 を実装。Unit-03: YAML に手動で extra field を追加後 `update_design()` で保持確認。Unit-14: `referenced_knowledge` merge 後に extra 保持確認。Integ-01: top-level + metrics-level の extra が YAML round-trip で保持される統合テスト。service 層の変更なしで全テスト Green になることを確認
  - Dependencies: 1.2

- [x] 2.1. Write F2 service-layer unit tests (Red)
  - File: `tests/test_designs.py`
  - Purpose: corrupt ファイル隔離の service 層テストを追加し、Red 状態を確立する
  - Leverage: 既存の `service` fixture、`write_yaml` による corrupt ファイル直接書き込み。`yaml_syntax_error` パターンは YAML ファイルに不正構文を直接書き込む（`write_yaml` ではなく `Path.write_text`）
  - Requirements: REQ-2 (FR-2.1, FR-2.2, FR-2.3)
  - Prompt: Test Design の Unit-07〜11, Unit-15 を実装。Unit-15 は pytest.mark.parametrize で 5 corrupt パターン（yaml_syntax_error, non_dict_root, missing_required, invalid_enum, invalid_nested_enum）を検証。`yaml_syntax_error` と `non_dict_root` は `Path.write_text()` で直接ファイル書き込み（`read_yaml()` レベルでエラーを起こすため）。Unit-08 は `caplog` で warning ログ出力を確認。Unit-10 は `pytest.raises(ValidationError)`
  - Dependencies: None

- [x] 2.2. Implement corrupt file isolation in list_designs (Green)
  - File: `src/insight_blueprint/core/designs.py`
  - Purpose: `list_designs()` に per-file try/except + warning ログを追加し、Task 2.1 のテストを Green にする
  - Leverage: 既存の `list_designs()` ループ構造に try/except を追加するだけ。`logging` 標準ライブラリ
  - Requirements: REQ-2 (FR-2.1, FR-2.2)
  - Prompt: `list_designs()` の try/except を `read_yaml(file_path)` から `AnalysisDesign(**data)` まで包含するスコープで追加。理由: `yaml_syntax_error` は `read_yaml()` 段階で `YAMLError` を raise するため、`AnalysisDesign(**data)` だけを囲むと不十分。`except Exception as exc` で catch し、`logger.warning("Skipping corrupt design file %s: %s", file_path.name, exc)` を出力して `continue`。module-level で `logger = logging.getLogger(__name__)` を定義。`get_design()` は変更なし（ValidationError はそのまま伝播）
  - Dependencies: 2.1

- [x] 2.3. Write F2 REST API test + implement ValidationError handler (Red → Green)
  - File: `tests/test_web.py`, `src/insight_blueprint/web.py`
  - Purpose: REST API で corrupt design → 422 レスポンスを返すテストと実装
  - Leverage: 既存の exception handler パターン（`ValueError → 400`）、既存の TestClient fixture
  - Requirements: REQ-2 (FR-2.4)
  - Prompt: Red: `test_get_design_corrupt_returns_422` を追加。corrupt YAML を直接書き込み、`GET /api/designs/{id}` で 422 + `error` フィールド確認。Green: `web.py` に `@app.exception_handler(ValidationError)` を追加。status_code=422, content=`{"error": f"Invalid design data: {exc.error_count()} validation error(s)"}`
  - Dependencies: 2.1

- [x] 3.1. Run regression tests + coverage confirmation
  - File: (テスト実行のみ、ファイル変更なし)
  - Purpose: 既存 681 テスト + 新規 25 テストの全 pass と `models/design.py` coverage 100% を確認する
  - Leverage: `uv run pytest -v` + `uv run pytest --cov=src/insight_blueprint/models/design --cov-report=term-missing`
  - Requirements: NFR-B.1, NFR-B.2, NFR-B.3
  - Prompt: `uv run pytest -v` で全テスト pass を確認。`uv run pytest --cov=src/insight_blueprint/models/design --cov-report=term-missing` で design.py のカバレッジ 100% 維持を確認。`uv run ruff check .` でリントエラーなしを確認
  - Dependencies: 1.3, 2.3

---

## Dependency Graph

```
Track 1 (F1):  1.1 → 1.2 → 1.3 ──┐
                                    ├→ 3.1
Track 2 (F2):  2.1 → 2.2 → 2.3 ──┘

Track 1 と Track 2 は独立。並行実装可能。
Task 3.1 は両トラック完了後に実行。
```

## Implementation Notes

- Task 1.2 の変更量は最小（5行の `model_config = ConfigDict(extra="allow")` 追加 + 1 import 追加）
- Task 2.2 の変更量も最小（try/except 追加 + logging import + logger 定義）
- Task 2.2 の try/except スコープは `read_yaml()` から `AnalysisDesign(...)` まで（Codex レビュー: `yaml_syntax_error` は `read_yaml()` で発生するため）
- Task 2.3 の依存は 2.1（2.2 とは独立: REST handler は service 層実装と無関係に実装可能）
- `web.py` の `ValidationError` import は既に `from pydantic import BaseModel, Field` がある行に追加

## Codex Review Log

| 指摘 | 重要度 | 対応 |
|------|--------|------|
| Task 2.2 の try/except スコープが狭い（`yaml_syntax_error` は `read_yaml()` で発生） | Critical | try/except を `read_yaml()` から `AnalysisDesign(...)` まで拡大 |
| Task 1.3 の TDD ラベル「Red→Green」は不正確（service 変更なしで Green 期待） | Low | 「Verification」に変更 |
| 回帰テスト + coverage 確認タスクが欠落 | Moderate | Task 3.1 追加 |
| design.md の `GET /api/designs` corrupt 混在テストが test-design.md に未反映 | Important | Unit-07 で service 層をカバー済み。REST 層は `list_designs()` をそのまま呼ぶだけなので service テストで十分。Integration テスト追加は不要と判断 |
| Task 2.1 が大きい（分割検討） | Moderate | parametrize で共通 fixture を使うため分割すると重複が増える。現状維持 |
| Task 2.3 の依存が 2.2 だが独立可能 | Important | 依存を 2.1 に変更（REST handler は service 実装と独立） |

## Team Review Results (2026-03-08)

**Commit**: `8f156f6` (実装) + `382c262` (review 修正)

| カテゴリ | Critical | High | Medium | Low |
|---------|----------|------|--------|-----|
| Security | 0 | 0 | 3 | 2 |
| Quality | 0 | 0 | 1 | 7 |
| Test | - | - | 2 | 3 |
| Requirements | 12/12 ACs Covered | 11/11 NFRs Covered | - | - |

### 修正済み (commit 382c262)

- **S-05**: `web.py` の `validation_error_handler` に handler 優先順序の NOTE コメント追加
- **T-04**: `test_list_designs_with_corrupt_returns_valid_only` テスト追加 (707 tests)

### 対応不要と判断

- **S-02**: `except Exception` スコープ — design doc で意図的に選択。YAMLError/ValidationError/TypeError 一括捕捉のため
- **S-01**: `extra="allow"` 蓄積リスク — REST API request model は extra="allow" なし。侵入経路はローカルのみ
- **Q-01**: テスト ID 重複 — docstring のみ、実害なし

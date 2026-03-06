# Design Status Refactor - テスト設計書

**Spec ID**: `design-status-refactor`

## 概要

DesignStatus enum リファクタに伴う全レイヤーのテスト設計。既存テストの更新（旧ステータス参照の置換）と、新遷移ルールの検証テスト追加を含む。

## テストレベル定義

| テストレベル | 略称 | 説明 | ツール |
|-------------|------|------|--------|
| 単体テスト | Unit | 個々のクラス・関数を独立してテスト | pytest |
| 統合テスト | Integ | 複数コンポーネントの連携をテスト（YAML ファイルシステム経由） | pytest |
| E2E テスト | E2E | Playwright でブラウザ操作、API モック経由でフロントエンド検証 | Playwright |
| 静的検証 | Static | コンパイラ/型チェッカーによる検証。テストランナー不要 | tsc, grep |

### テストレベル選択の根拠

| 対象 | レベル | 根拠 |
|------|--------|------|
| enum 値・遷移ルール | Unit | 純粋なロジック。外部依存なし。parametrize で全パターン網羅が最も効率的 |
| REST API エンドポイント | Unit + Integ | Unit: TestClient で個別ハンドラ検証。Integ: YAML 永続化を含むフルフロー |
| MCP ツール | Unit | asyncio.run で直接呼び出し。HTTP 経由不要 |
| フロントエンド型・ラベル・色 | E2E + Static | TypeScript 型は tsc で静的検証。UI 表示は Playwright でブラウザ検証 |
| API クライアント関数 | Static + E2E | 関数シグネチャは tsc。実際の HTTP 呼び出しは E2E で間接検証 |
| E2E フィクスチャ | E2E | フィクスチャ自体をテストするのではなく、使用する E2E テストの Green で検証 |
| 旧コード残存チェック | Static | grep で旧ステータス・旧関数の残存を検知。実行時テスト不要 |

### Static 検証 ID 一覧

| ID | 検証内容 | コマンド | カバーする AC |
|----|---------|---------|-------------|
| Static-01 | TypeScript 型整合性 | `tsc --noEmit` | 6.1, 8.1, 9.1 |
| Static-02 | 旧ステータスリテラル残存 | `grep -rn` (draft, pending_review) + active は DesignStatus 文脈のみ確認 | 1.2 |
| Static-03 | 旧関数残存 | `grep -rn` (submit_for_review, submitReview) | 3.4, 8.2 |

## 要件カバレッジマトリクス

### FR-1: DesignStatus enum の置換

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 1.1 | enum に新6値が含まれる | Unit-01 | - | - | - | DesignStatus の全メンバーが正しい |
| 1.2 | 旧ステータスがコードベースに残らない | - | - | - | Static-02 | 旧ステータスリテラルがプロダクションコードに0件 |
| 1.3 | create_design のデフォルトが in_review | Unit-02 | Integ-01 | - | - | 生成された design の status が in_review |

### FR-2: 遷移ルールの再定義

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 2.1 | in_review → {revision_requested, analyzing, supported, rejected, inconclusive} | Unit-03 | - | - | - | 5つの遷移が全て成功 |
| 2.2 | revision_requested → {in_review} のみ | Unit-03 | - | - | - | in_review への遷移成功、他は ValueError |
| 2.3 | analyzing → {in_review} のみ | Unit-03 | - | - | - | in_review への遷移成功、他は ValueError |
| 2.4 | terminal states → 遷移なし | Unit-03 | - | - | - | 全遷移で ValueError |
| 2.5 | 無効遷移で ValueError | Unit-03 | - | - | - | 適切なエラーメッセージ |

### FR-3: API エンドポイントの変更

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 3.1 | POST /transition で有効遷移 | Unit-04 | Integ-02 | - | - | 200 + 遷移後ステータス |
| 3.2 | POST /transition で無効遷移 → 400 | Unit-04 | - | - | - | 400 + エラーメッセージ |
| 3.3 | POST /review が存在しない | Unit-04 | - | - | - | 404 or 405 |
| 3.4 | submit_for_review 関数が削除済み | - | - | - | Static-03 | 関数参照がプロダクションコードに0件 |

### FR-4: MCP ツールの変更

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 4.1 | transition_design_status で有効遷移 | Unit-05 | - | - | - | 遷移成功 dict |
| 4.2 | submit_for_review ツール削除 | Unit-05 | - | - | - | 関数が存在しない |
| 4.3 | 無効遷移でエラー dict 返却 | Unit-05 | - | - | - | `{"error": "..."}` |

### FR-5: レビューバッチの前提条件変更

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 5.1 | in_review 時にバッチ提出可能 | Unit-06 | - | - | - | バッチ保存成功 |
| 5.2 | status_after に新値が使える | Unit-06 | - | - | - | revision_requested, analyzing を含む5値が有効 |
| 5.3 | non-in_review でバッチ → 400 | Unit-06 | Integ-02 | - | - | ValueError / 400 |

### FR-6: フロントエンド DesignStatus 型と UI

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 6.1 | DesignStatus 型が新6値 | - | - | - | Static-01 | `tsc --noEmit` pass（旧型参照でコンパイルエラー） |
| 6.2 | DESIGN_STATUS_LABELS が正しい | - | - | E2E-01 | - | ラベルが UI に表示 |
| 6.3 | StatusBadge の色が正しい | - | - | E2E-01 | - | バッジ表示確認 |
| 6.4 | フィルタに新ステータス表示 | - | - | E2E-02 | - | フィルタ選択で API リクエスト |

### FR-7: OverviewPanel ワークフロー変更

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 7.1 | in_review でレビュー UI 表示 | - | - | E2E-03 | - | コメント UI が表示される |
| 7.2 | non-in_review でレビュー UI 非表示 | - | - | E2E-03 | - | コメント UI が非表示 |
| 7.3 | STATUS_GUIDE が全ステータスに対応 | - | - | E2E-03 | - | ワークフローガイド表示 |
| 7.4 | Submit for Review ボタン削除 | - | - | E2E-03 | - | ボタンが存在しない |

### FR-8: API クライアント関数の変更

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 8.1 | transitionDesign が /transition に POST | - | - | E2E-03 | Static-01 | tsc で型チェック + E2E-03 で UI フロー経由の間接検証 |
| 8.2 | submitReview 関数が削除 | - | - | - | Static-03 | 関数参照がプロダクションコードに0件 |

### FR-9: ReviewBatchComposer

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 9.1 | BATCH_STATUSES に新5値 | - | - | E2E-04 | Static-01 | Playwright でセレクタに5つの選択肢 + tsc で型整合性 |

### FR-10: E2E テストフィクスチャ

| AC# | Acceptance Criteria | Unit | Integ | E2E | Static | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|:------:|--------|
| 10.1 | makeDesign デフォルト in_review | - | - | E2E-05 | - | テスト内で正しいデフォルト使用 |
| 10.2 | mockTransitionDesign が /transition | - | - | E2E-05 | - | モックが正しいエンドポイント |
| 10.3 | 旧ステータス参照の置換 | - | - | E2E-05 | - | 全 E2E テストが Green |
| 10.4 | S6 フィルタテスト in_review | - | - | E2E-02 | - | status=in_review でリクエスト |

---

## 単体テストシナリオ

### Unit-01: DesignStatus enum 値の検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-01 |
| **テストファイル** | `tests/test_designs.py` |
| **目的** | DesignStatus enum が正確に6値を持つことを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_design_status_members` | enum メンバーが {in_review, revision_requested, analyzing, supported, rejected, inconclusive} であること | 1.1 |
| `test_design_status_values` | 各メンバーの .value が snake_case 文字列であること | 1.1 |

### Unit-02: create_design デフォルトステータス

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-02 |
| **テストファイル** | `tests/test_designs.py` |
| **目的** | create_design で生成される design のデフォルト status が in_review であること |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_create_design_default_status` | 引数なしで status == DesignStatus.in_review | 1.3 |

### Unit-03: 遷移ルールの網羅的テスト

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-03 |
| **テストファイル** | `tests/test_reviews.py` |
| **目的** | VALID_TRANSITIONS マップに基づく全遷移パターンの検証 |

> **設計判断**: parametrize で全 (current, target) ペアを網羅し、有効/無効を一括テストする

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_transition_valid_from_in_review[revision_requested]` | in_review → revision_requested 成功 | 2.1 |
| `test_transition_valid_from_in_review[analyzing]` | in_review → analyzing 成功 | 2.1 |
| `test_transition_valid_from_in_review[supported]` | in_review → supported 成功 | 2.1 |
| `test_transition_valid_from_in_review[rejected]` | in_review → rejected 成功 | 2.1 |
| `test_transition_valid_from_in_review[inconclusive]` | in_review → inconclusive 成功 | 2.1 |
| `test_transition_valid_revision_requested_to_in_review` | revision_requested → in_review 成功 | 2.2 |
| `test_transition_valid_analyzing_to_in_review` | analyzing → in_review 成功 | 2.3 |
| `test_transition_invalid_from_revision_requested[analyzing]` | revision_requested → analyzing で ValueError | 2.2 |
| `test_transition_invalid_from_terminal[supported]` | supported → any で ValueError | 2.4 |
| `test_transition_invalid_from_terminal[rejected]` | rejected → any で ValueError | 2.4 |
| `test_transition_invalid_from_terminal[inconclusive]` | inconclusive → any で ValueError | 2.4 |
| `test_transition_error_message` | エラーメッセージに current と valid targets が含まれる | 2.5 |

### Unit-04: REST API /transition エンドポイント

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-04 |
| **テストファイル** | `tests/test_web.py` |
| **目的** | POST /transition の正常・異常系を検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_transition_design_success` | 有効遷移で 200 + 正しいレスポンス | 3.1 |
| `test_transition_design_invalid` | 無効遷移で 400 | 3.2 |
| `test_transition_design_invalid_status_value` | 無効なステータス文字列（例: "bogus"）で 400 + "Invalid status" | 3.2 |
| `test_transition_design_not_found` | 存在しない design で 404 | 3.1 |
| `test_old_review_endpoint_removed` | POST /review が 404 or 405 | 3.3 |

### Unit-05: MCP transition_design_status ツール

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-05 |
| **テストファイル** | `tests/test_server.py` |
| **目的** | MCP ツールの遷移成功・エラー返却を検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_transition_design_status_success` | 有効遷移で design dict 返却 | 4.1 |
| `test_transition_design_status_invalid` | 無効遷移で `{"error": "..."}` 返却 | 4.3 |
| `test_submit_for_review_removed` | submit_for_review が server module に存在しない | 4.2 |

### Unit-06: レビューバッチ前提条件

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-06 |
| **テストファイル** | `tests/test_reviews.py` + `tests/test_web.py` |
| **目的** | バッチ提出の前提条件（in_review）と status_after の許容値を検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_save_review_batch_in_review` | in_review 時にバッチ保存成功 | 5.1 |
| `test_save_review_batch_status_after_values` | status_after に supported/rejected/inconclusive/revision_requested/analyzing が有効 | 5.2 |
| `test_save_review_batch_non_in_review_rejected` | revision_requested 等の design でバッチ → ValueError | 5.3 |
| `test_submit_batch_api_non_in_review_400` | API 経由で non-in_review → 400 | 5.3 |

---

## 統合テストシナリオ

### Integ-01: Design 作成〜遷移のフルフロー

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-01 |
| **テストファイル** | `tests/test_integration.py` |
| **目的** | YAML ファイルシステム経由で design 作成→遷移→バッチ提出→知識抽出のフルフローを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_design_lifecycle` | create(in_review) → transition(revision_requested) → transition(in_review) → batch(supported) → knowledge extraction | 1.3, 2.1, 2.2 |

### Integ-02: Web API フルフロー

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-02 |
| **テストファイル** | `tests/test_web_integration.py` |
| **目的** | HTTP 経由で全ワークフローを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_full_web_workflow` | POST create → GET(in_review) → POST transition(revision_requested) → POST batch(→400: non-in_review) → POST transition(in_review) → POST batch(supported) → POST knowledge | 3.1, 5.3 |

---

## E2E テストシナリオ

### E2E-01: Design 一覧・ステータス表示

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-01 |
| **テストファイル** | `frontend/e2e/smoke.spec.ts` |
| **実行方法** | Playwright（API モック） |

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | Design カードに StatusBadge が正しいラベルで表示 | 6.2, 6.3 |
| 2 | makeDesign() デフォルトが in_review | 10.1 |

### E2E-02: ステータスフィルタ

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-02 |
| **テストファイル** | `frontend/e2e/smoke.spec.ts` (S6) |
| **実行方法** | Playwright（API モック） |

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | フィルタドロップダウンに新ステータスが表示 | 6.4 |
| 2 | "In Review" 選択で status=in_review パラメータ送信 | 10.4 |

### E2E-03: OverviewPanel ワークフロー

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-03 |
| **テストファイル** | `frontend/e2e/design-detail.spec.ts` |
| **実行方法** | Playwright（API モック） |

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | in_review design でレビューコメント UI が表示 | 7.1 |
| 2 | revision_requested design でレビュー UI 非表示 | 7.2 |
| 3 | ワークフローガイドが表示される | 7.3 |
| 4 | Submit for Review ボタンが存在しない | 7.4 |

### E2E-04: ReviewBatchComposer ステータス選択

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-04 |
| **テストファイル** | `frontend/e2e/design-detail.spec.ts` |
| **実行方法** | Playwright（API モック） |

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | ステータスセレクタに5つの選択肢 | 9.1 |

### E2E-05: E2E テスト全体の Green 確認

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-05 |
| **テストファイル** | `smoke.spec.ts`, `design-detail.spec.ts`, `history.spec.ts`, `cross-tab.spec.ts`, `catalog.spec.ts`, `rules.spec.ts` |
| **実行方法** | `npx playwright test` |

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 全 E2E テストが pass | 10.1, 10.2, 10.3 |

---

## テストファイル構成

```
tests/
├── test_designs.py          # Unit-01, Unit-02
├── test_reviews.py          # Unit-03, Unit-06 (一部)
├── test_web.py              # Unit-04, Unit-06 (API 側)
├── test_server.py           # Unit-05
├── test_integration.py      # Integ-01
└── test_web_integration.py  # Integ-02

frontend/e2e/
├── fixtures/
│   ├── mock-data.ts         # E2E fixture
│   └── api-routes.ts        # E2E fixture
├── smoke.spec.ts            # E2E-01, E2E-02
├── design-detail.spec.ts    # E2E-03, E2E-04
├── history.spec.ts          # E2E-05 (一部)
└── cross-tab.spec.ts        # 変更不要（data-state="active" は Radix UI 属性）
```

## カバレッジ目標

### Python バックエンド

| コンポーネント (Design Doc ID) | 目標カバレッジ | 主なテスト |
|-------------------------------|--------------|-----------|
| `models/design.py` (C1) | 100% | Unit-01, Unit-02 |
| `core/reviews.py` (C2) | 100% | Unit-03, Unit-06 |
| `core/designs.py` (C1 関連) | 90%以上 | Unit-02, Integ-01 |
| `web.py` (C3) | 90%以上 | Unit-04, Integ-02 |
| `server.py` (C4) | 90%以上 | Unit-05 |

### フロントエンド（Static + E2E）

| コンポーネント (Design Doc ID) | 検証方法 | 根拠 |
|-------------------------------|---------|------|
| `types/api.ts` (C5) | Static: tsc --noEmit | 型定義変更。旧型参照があればコンパイルエラーで検知 |
| `api/client.ts` (C10) | Static: tsc + grep | 関数シグネチャ・URL は型チェック。submitReview 残存は grep |
| `fixtures/mock-data.ts`, `api-routes.ts` (C12, C13) | E2E-05 | フィクスチャはテストの一部。全 E2E pass で検証 |
| `lib/constants.tsx` (C6) | E2E-01 | ラベル表示を Playwright で目視検証 |
| `StatusBadge.tsx` (C7) | E2E-01 | バッジ描画を Playwright で検証 |
| `DesignsPage.tsx` (C8) | E2E-02 | フィルタ動作を Playwright で検証 |
| `OverviewPanel.tsx` (C9) | E2E-03 | ワークフロー表示・非表示を Playwright で検証 |
| `ReviewBatchComposer.tsx` (C11) | E2E-04 | 選択肢表示を Playwright で検証 |
| `mock-data.ts` (C12) | E2E-05 | makeDesign デフォルト値を全 E2E pass で検証 |
| `api-routes.ts` (C13) | E2E-05 | mockTransitionDesign を全 E2E pass で検証 |
| E2E spec files (C14) | E2E-01〜05 | 旧ステータス参照の置換を全 E2E pass で検証 |

## 成功基準

- [ ] Unit-01〜06: 全テストケースが pass
- [ ] Integ-01〜02: フルフローが pass
- [ ] E2E-01〜05: 全 Playwright テストが pass
- [ ] Static 検証:
  - [ ] `tsc --noEmit`: TypeScript 型チェック pass（AC 6.1, 8.1, 9.1）
  - [ ] `grep -rn "draft\|pending_review" src/insight_blueprint/ tests/ frontend/src/` でプロダクションコード + テスト + フロントエンドにヒット0件（AC 1.2）。`active` は Radix UI 属性等で誤検知するため `grep -rn '"active"' src/insight_blueprint/ frontend/src/types/ frontend/src/lib/constants.tsx frontend/src/pages/` で DesignStatus 文脈を広めに確認（`cross-tab.spec.ts` 等の `data-state="active"` は Radix UI 属性のため対象外）
  - [ ] `grep -rn "submit_for_review\|submitReview" src/ frontend/src/` でヒット0件（AC 3.4, 8.2）
- [ ] `python -m pytest tests/ -q`: 全 Python テスト pass（0 failures）
- [ ] `npx playwright test`: 全 E2E テスト pass

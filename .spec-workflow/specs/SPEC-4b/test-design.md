# SPEC-4b: webui-frontend — Test Design

> **Spec ID**: SPEC-4b
> **Status**: draft
> **Created**: 2026-02-28
> **Depends On**: SPEC-4a (webui-backend)

---

## Test Architecture

### Test Scope Decision

SPEC-4b はフロントエンド（React SPA）であり、ビジネスロジックは全て Python バックエンド
（SPEC-4a の 341 テスト）でカバー済み。フロントエンドの責務は「API を呼んで表示する」のみ。

**自動テストの対象外とする理由:**
- フロントエンド単体テスト（Vitest + Testing Library）: ROI が低い。表示ロジックのみ

**品質担保の手段:**
1. **TypeScript strict mode** — コンパイルエラーゼロが実装の静的検証
2. **ビルド検証** — `npm run build` + `poe build-frontend` の成功を CI ゲートに
3. **Playwright smoke tests** — リグレッションリスクの高い 8 ケースを自動検証（Claude Code + Playwright MCP で実行）
4. **手動検証チェックリスト** — Playwright でカバーしない操作を手動で確認
5. **バックエンド API テスト** — SPEC-4a の 341 テストが API 契約を保証

### Test Pyramid

```
          ┌──────────────┐
          │  手動検証      │  ← Playwright でカバーしない操作
          ├──────────────┤
        ┌─┤ Playwright    ├─┐  ← 8 smoke tests (Claude Code + MCP で実行)
        │ ├──────────────┤ │
      ┌─┤  ビルド検証    ├─┐  ← npm run build, poe build-frontend
      │ ├──────────────┤ │
  ┌───┴─┴──────────────┴─┴───┐
  │  TypeScript Compiler (静的) │  ← tsc --noEmit (strict: true)
  └──────────────────────────┘
        +
  ┌──────────────────────────┐
  │  Backend API Tests (341)  │  ← SPEC-4a pytest (API 契約保証)
  └──────────────────────────┘
```

## Build Verification

### TypeScript Compilation

```bash
# ビルド時に tsc が実行される（package.json: "build": "tsc -b && vite build"）
# strict: true により以下を検出:
# - 未定義の変数・関数
# - 型の不一致（API レスポンス型の誤り）
# - null/undefined の未チェック参照
# - 未使用の変数・import
```

| Check | Command | Expected | AC |
|-------|---------|----------|-----|
| TypeScript compile | `cd frontend && npx tsc --noEmit` | Exit 0, no errors | NFR-Reliability |
| Vite build | `cd frontend && npm run build` | `src/insight_blueprint/static/` にファイル出力 | FR-23, R6-AC3 |
| Poe pipeline | `poe build-frontend` | 上記と同じ結果 | R6-AC5 |
| Build time | `time npm run build` | 30秒以内 | NFR-Performance |
| Output contents | `ls src/insight_blueprint/static/` | `index.html` + `assets/` (JS/CSS) | FR-23 |
| Static serving | FastAPI 起動 → `GET /` | `index.html` が返る | R6-AC3 |

### Dev Server Verification

| Check | Command | Expected | AC |
|-------|---------|----------|-----|
| Dev start | `cd frontend && npm run dev` | Vite dev server 起動（port 5173） | FR-22, R6-AC1 |
| HMR | ファイル編集 → ブラウザ自動更新 | 即座に反映 | R6-AC1 |
| API proxy | Dev server → `GET /api/health` | FastAPI の `{status: "ok"}` が返る | FR-22, R6-AC2 |
| shadcn/ui | コンポーネント使用 | Tailwind CSS v4 スタイル適用 | FR-21, R6-AC4 |

## Playwright Smoke Tests

### Purpose

手動チェックリスト30項目のうち、リグレッションリスクが高い操作を自動化する。
CI スイートではなく、**Claude Code + Playwright MCP (`webapp-testing` skill) で実行する開発時検証ツール**。

### Execution

```bash
# Pre-condition: FastAPI backend running on port 3000
# Pre-condition: Frontend built (poe build-frontend) or dev server running

# Run all smoke tests
cd frontend && npx playwright test

# Run via Claude Code (recommended)
# webapp-testing skill が Playwright MCP 経由でブラウザ操作・スクリーンショット取得を実行
```

### Test Cases (8 cases)

| # | Test Name | Manual # | Steps | Expected | AC |
|---|-----------|----------|-------|----------|-----|
| S1 | Tab routing | #24, #25 | Navigate to each tab, verify URL sync | 4 tabs render, URL updates with ?tab= | R1-AC2, R1-AC3 |
| S2 | Invalid tab fallback | #26 | Navigate to `?tab=invalid` | Falls back to Designs tab | R1-AC3 |
| S3 | API error banner | #28 | Load page without backend running | ErrorBanner visible with retry button | R1-AC4 |
| S4 | Empty state | #30 | Load tabs with no data | EmptyState component visible | R1-AC5 |
| S5 | Create design dialog | #2 | Click "New Design", fill form, submit | Design appears in list | R2-AC4 |
| S6 | Status filter | #3 | Select "draft" filter | Only draft designs shown | R2-AC2 |
| S7 | Design detail expand | #4 | Click design row | Detail panel with sub-tabs visible | R2-AC3 |
| S8 | Source add with JSON validation | #12, #13 | Add source with invalid JSON | Error shown, valid JSON succeeds | R3-AC3 |

### Configuration

```typescript
// frontend/playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  baseURL: "http://localhost:3000",
  use: {
    headless: true,
  },
  webServer: {
    command: "npm run build && cd .. && uvx insight-blueprint --project /tmp/test-project",
    url: "http://localhost:3000",
    reuseExistingServer: true,
  },
});
```

### What Playwright Does NOT Cover (→ Manual)

以下は Playwright ではカバーせず、手動チェックリストで検証する:

- Review workflow (Submit for Review, コメント追加): 複数ステップの状態遷移
- Knowledge extraction/save: 非決定的な出力
- HMR / dev server: 開発環境固有
- Browser back/forward (popstate): Playwright の制約
- Loading spinners: タイミング依存

## Manual Verification Checklist

### Pre-condition

- FastAPI バックエンド起動済み (`uvx insight-blueprint --project /tmp/test-project`)
- フロントエンドビルド済み (`poe build-frontend`) or dev server 起動済み (`npm run dev`)

### Tab 1: Designs

| # | Operation | Steps | Expected | AC |
|---|-----------|-------|----------|-----|
| 1 | 初期表示 | Designs タブを開く | デザイン一覧テーブルが表示される（0件なら EmptyState） | R1-AC1, R2-AC1 |
| 2 | デザイン作成 | "New Design" → title/hypothesis 入力 → 送信 | ダイアログが閉じ、一覧に新デザインが反映 | R2-AC4, R2-AC5 |
| 3 | ステータスフィルタ | フィルタで "draft" を選択 | draft のみ表示される | R2-AC2 |
| 4 | 詳細展開 | デザイン行をクリック | 詳細パネルが展開、Overview サブタブ表示 | R2-AC3 |
| 5 | Overview 表示 | Overview サブタブ | title, hypothesis, status, metrics 等が表示。dict フィールドは JsonTree | R2-AC3 |
| 6 | Review 提出 | Review サブタブ → "Submit for Review" | ステータスが pending_review に変更 | R2-AC7 |
| 7 | Review 無効 | draft のデザインで Review サブタブ | "Submit for Review" ボタンが無効化 | R2-AC11 |
| 8 | コメント追加 | Review → comment 入力 + status 選択 → 送信 | コメントリストに反映、ステータス更新 | R2-AC8 |
| 9 | 知識抽出 | Knowledge → "Extract Knowledge" | プレビューリストが表示される | R2-AC9 |
| 10 | 知識保存 | "Save Knowledge" | 保存確認メッセージ表示 | R2-AC10 |

### Tab 2: Catalog

| # | Operation | Steps | Expected | AC |
|---|-----------|-------|----------|-----|
| 11 | 初期表示 | Catalog タブを開く | ソース一覧テーブル（0件なら EmptyState） | R3-AC1 |
| 12 | ソース追加 | "Add Source" → 情報入力 → 送信 | 一覧に反映 | R3-AC3 |
| 13 | JSON バリデーション | connection に不正 JSON 入力 | エラーメッセージ表示、送信ブロック | Error Handling #5 |
| 14 | スキーマ表示 | ソース行をクリック | カラムスキーマテーブルが表示 | R3-AC2 |
| 15 | カタログ検索 | 検索バーにクエリ入力 → 検索 | マッチ結果が表示される | R3-AC4 |
| 16 | 知識一覧 | ドメイン知識セクション | エントリが category/importance バッジ付きで表示 | R3-AC5 |

### Tab 3: Rules

| # | Operation | Steps | Expected | AC |
|---|-----------|-------|----------|-----|
| 17 | コンテキスト表示 | Rules タブを開く | Sources / Knowledge / Rules の3セクション + カウント | R4-AC1 |
| 18 | セクション展開 | 各セクションをクリック | 内容が展開/折りたたみ | R4-AC1 |
| 19 | Cautions 検索 | テーブル名入力 → 検索 | 関連する注意事項が表示される | R4-AC2 |
| 20 | 空の Cautions | 存在しないテーブル名で検索 | EmptyState 表示 | R4-AC3 |

### Tab 4: History

| # | Operation | Steps | Expected | AC |
|---|-----------|-------|----------|-----|
| 21 | タイムライン表示 | History タブを開く | 全デザインが updated_at 降順で表示 | R5-AC1 |
| 22 | 履歴展開 | エントリをクリック | レビューコメント履歴が展開 | R5-AC2 |
| 23 | 空の History | デザイン0件 | EmptyState 表示 | R5-AC3 |

### Cross-Tab: Navigation & Error Handling

| # | Operation | Steps | Expected | AC |
|---|-----------|-------|----------|-----|
| 24 | タブ切り替え | 各タブをクリック | 即座にコンテンツ切り替え | R1-AC2 |
| 25 | URL 保持 | `?tab=catalog` で直接アクセス | Catalog タブが初期表示 | R1-AC3 |
| 26 | 不正 URL | `?tab=invalid` でアクセス | Designs タブにフォールバック | Design: App.tsx |
| 27 | ブラウザ戻る | タブ切り替え後にブラウザバック | 前のタブに戻る | Design: App.tsx (popstate) |
| 28 | API エラー | バックエンド停止状態でタブ開く | ErrorBanner + 再試行ボタン | R1-AC4, Error Handling #1 |
| 29 | ローディング表示 | データ取得中 | スピナー or スケルトン表示 | NFR-Usability |
| 30 | 空データ | データ0件の各タブ | EmptyState 表示 | R1-AC5 |

## Acceptance Criteria Traceability

### Requirements → Test Mapping

| AC | Test Type | Verification |
|----|-----------|-------------|
| R1-AC1 (初期表示) | Playwright S1 + 手動 #1 | 4タブ + Designs 初期表示 |
| R1-AC2 (タブ切り替え) | **Playwright S1** | 各タブのコンテンツ切り替え |
| R1-AC3 (?tab= URL) | **Playwright S1, S2** + 手動 #27 | URL パラメータ同期 + popstate |
| R1-AC4 (API エラー) | **Playwright S3** | ErrorBanner 表示 |
| R1-AC5 (空データ) | **Playwright S4** | EmptyState 表示 |
| R2-AC1 (デザイン一覧) | 手動 #1 | テーブル表示 |
| R2-AC2 (フィルタ) | **Playwright S6** | ステータスフィルタ |
| R2-AC3 (詳細展開) | **Playwright S7** + 手動 #5 | マスター・ディテール |
| R2-AC4 (作成) | **Playwright S5** | ダイアログ → API → リスト更新 |
| R2-AC5 (作成バリデーション) | 手動 #2 | 必須項目チェック |
| R2-AC6 (Review タブ) | 手動 #6, #8 | コメント一覧 + 操作ボタン |
| R2-AC7 (Submit Review) | 手動 #6 | ステータス変更 |
| R2-AC8 (コメント追加) | 手動 #8 | コメントリスト反映 + ステータス更新 |
| R2-AC9 (Knowledge 抽出) | 手動 #9 | プレビュー表示 |
| R2-AC10 (Knowledge 保存) | 手動 #10 | 保存確認 |
| R2-AC11 (非 active 無効化) | 手動 #7 | ボタン無効化 |
| R3-AC1 (ソース一覧) | 手動 #11 | テーブル表示 |
| R3-AC2 (スキーマ) | 手動 #14 | カラムテーブル |
| R3-AC3 (ソース追加) | **Playwright S8** | ダイアログ + JSON バリデーション |
| R3-AC4 (検索) | 手動 #15 | 検索結果表示 |
| R3-AC5 (知識一覧) | 手動 #16 | バッジ付きリスト |
| R4-AC1 (コンテキスト) | 手動 #17, #18 | 3セクション + カウント |
| R4-AC2 (Cautions) | 手動 #19 | 検索結果 |
| R4-AC3 (空 Cautions) | 手動 #20 | EmptyState |
| R5-AC1 (タイムライン) | 手動 #21 | 降順表示 |
| R5-AC2 (履歴展開) | 手動 #22 | コメント履歴 |
| R5-AC3 (空 History) | 手動 #23 | EmptyState |
| R6-AC1 (dev server) | ビルド検証 | `npm run dev` 起動 |
| R6-AC2 (proxy) | ビルド検証 | `/api/health` proxy |
| R6-AC3 (build output) | ビルド検証 | `static/` 出力 |
| R6-AC4 (shadcn/ui) | ビルド検証 + 手動 | スタイル適用 |
| R6-AC5 (poe pipeline) | ビルド検証 | `poe build-frontend` 成功 |

## Regression Strategy

### SPEC-4a テストへの影響

SPEC-4b は `frontend/` ディレクトリのみを変更し、Python コードは一切変更しない。
したがって SPEC-4a の 341 テストへのリグレッションリスクはゼロ。

**検証**: SPEC-4b 実装後に `uv run pytest` で全 341 テスト通過を確認する。

### ビルドパイプラインのリグレッション

SPEC-4a で構築した `poe build-frontend` パイプラインとの互換性を維持する:
- `vite.config.ts` の `outDir` を変更しない
- `package.json` の `build` スクリプトを変更しない
- 新規依存の追加は `npm install` で解決可能であること

## Security Considerations

| Concern | Mitigation | Verification |
|---------|-----------|-------------|
| XSS | React のデフォルトエスケーピング | `dangerouslySetInnerHTML` の不使用を手動確認 |
| API injection | フォーム入力のバリデーション + バックエンド側チェック | 手動 #13 (JSON validation) |
| CORS | SPEC-4a で localhost のみ許可（設定変更なし） | SPEC-4a テスト (`test_cors_*`) |
| 秘密情報 | フロントエンドに API キー等を含めない | コードレビュー |

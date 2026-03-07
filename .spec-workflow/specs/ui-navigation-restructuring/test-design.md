# Test Design: UI Navigation Restructuring

## Overview

ui-navigation-restructuring のテスト設計。フロントエンド専用の変更（バックエンド変更なし）のため、テストは E2E (Playwright) とTypeScript コンパイラチェックが中心。requirements.md の REQ-1〜REQ-6 の全 Acceptance Criteria をカバーする。

## Test Scope

| 対象 | テストレベル | ファイル | 方針 |
|------|------------|---------|------|
| Top-level tab 削減 | E2E | `smoke.spec.ts` | UPDATE |
| URL fallback | E2E | `smoke.spec.ts` | UPDATE + ADD |
| Unified Knowledge in Catalog | E2E | `catalog.spec.ts` | UPDATE |
| CautionSearch in Catalog | E2E | `catalog.spec.ts` | ADD (rules.spec.ts から移植) |
| Design detail sub-tab 削減 | E2E | `design-detail.spec.ts` | UPDATE |
| Extract Knowledge 削除 | E2E | `design-detail.spec.ts` | DELETE |
| Auto-finding guide text | E2E | `design-detail.spec.ts` | ADD |
| Cross-tab navigation | E2E | `cross-tab.spec.ts` | UPDATE |
| Rules tab empty state | E2E | `cross-tab.spec.ts` | DELETE |
| History tab tests | E2E | `history.spec.ts` | DELETE (全体) |
| Rules tab tests | E2E | `rules.spec.ts` | DELETE (全体) |
| TypeScript types | Compiler | `types/api.ts` | TypeScript compiler check |
| Backend regression | Unit | `tests/` (Python) | 604 tests pass, 0 modified |

## Existing Test Mutation Plan

既存テストの変更・削除・追加を3層で整理する。

### DELETE (テスト削除)

| テスト | ファイル | 理由 |
|--------|---------|------|
| `#9: extract knowledge shows preview entries` | design-detail.spec.ts | Feature A (Extract Knowledge) 削除。KnowledgePanel 自体が存在しない |
| `#10: save knowledge shows confirmation` | design-detail.spec.ts | Feature A 削除 |
| `#30: empty state shown for rules tab` | cross-tab.spec.ts | Rules タブ削除 |
| `#30: empty state shown for history tab` | cross-tab.spec.ts | History タブ削除 |
| `#17: rules context shows three collapsible sections` | rules.spec.ts | Rules ページ削除。ファイルごと削除 |
| `#18: collapsible sections expand and collapse` | rules.spec.ts | 同上 |
| `#19: cautions search returns matching results` | rules.spec.ts | Catalog に移植後、元ファイル削除 |
| `#20: cautions search with no results shows empty state` | rules.spec.ts | 同上 |
| `#21: history timeline shows designs in descending order` | history.spec.ts | History ページ削除。ファイルごと削除 |
| `#22: clicking history entry shows review batches` | history.spec.ts | 同上 |
| `#23: empty history shows empty state` | history.spec.ts | 同上 |

### UPDATE (テスト修正)

| テスト | ファイル | 変更内容 |
|--------|---------|---------|
| `S1: tab routing syncs URL` | smoke.spec.ts | タブを `["catalog", "designs"]` の2つに削減。`rules`, `history` を除去 |
| `S7: clicking design row shows detail sub-tabs` | smoke.spec.ts | Knowledge タブの assertion を削除。Overview + History の2タブのみ検証 |
| `S8: source add validates JSON` | smoke.spec.ts | `mockKnowledgeList` → `mockUnifiedKnowledge` に変更（Catalog ページが unified endpoint を使うため） |
| `Tab Restructuring > tabs show Overview, History, Knowledge` | design-detail.spec.ts | Knowledge タブ assertion を削除。テスト名を `tabs show Overview and History` に変更 |
| `#14: clicking source row shows schema table` | catalog.spec.ts | `mockKnowledgeList` → `mockUnifiedKnowledge` に変更 |
| `#15: catalog search displays results` | catalog.spec.ts | `mockKnowledgeList` → `mockUnifiedKnowledge` に変更 |
| `#16: knowledge list shows entries with badges` | catalog.spec.ts | `mockKnowledgeList` → `mockUnifiedKnowledge` に変更。`finding` カテゴリのエントリを追加して badge 表示検証 |
| `#27: browser back navigates to previous tab` | cross-tab.spec.ts | 3タブ遷移 (designs→catalog→rules) を2タブ遷移 (designs→catalog) に変更。goBack 1回のみ |
| `#30: empty state shown for catalog tab` | cross-tab.spec.ts | `/api/catalog/knowledge` の直接モック → `mockUnifiedKnowledge` に変更 |

### Fixture Changes

**Endpoint migration strategy**: KnowledgeSection のデータソースが `GET /api/catalog/knowledge` → `GET /api/rules/context` に変わるため、全テストで `mockKnowledgeList` を `mockUnifiedKnowledge` に置き換える。マイグレーション完了後 `mockKnowledgeList` は api-routes.ts から削除する。

| ファイル | 変更内容 |
|---------|---------|
| `api-routes.ts` | `mockExtractKnowledge`, `mockSaveKnowledge`, `mockKnowledgeList` を削除 |
| `api-routes.ts` | `mockUnifiedKnowledge(page, entries)` を追加（内部で `mockRulesContext` を呼ぶ wrapper） |
| `api-routes.ts` | `mockAllRoutesEmpty` 内の `/api/catalog/knowledge` モックを削除（`/api/rules/context` モックは残す） |
| `mock-data.ts` | 変更なし（`makeKnowledgeEntry`, `makeRulesContext`, `makeCaution` は既存のまま再利用） |

---

## REQ-1: Remove Rules and History top-level tabs

### E2E Tests

#### T-1.1: Top-level navigation に Designs と Catalog のみ表示

```
AC: AC-1.1
File: smoke.spec.ts (S1 UPDATE)
Given: ダッシュボードがロードされた
When: ナビゲーションを確認する
Then: "Designs" と "Catalog" の2タブのみが visible であること
And: "Rules" タブが存在しないこと
And: "History" タブが存在しないこと
```

#### T-1.2: ?tab=rules が designs にフォールバック

```
AC: AC-1.2
File: smoke.spec.ts (ADD)
Given: URL に ?tab=rules が指定されている
When: ページがロードされる
Then: Designs タブが active であること
And: URL が ?tab=designs に変更されること（または designs がデフォルト表示されること）
```

#### T-1.3: ?tab=history が designs にフォールバック

```
AC: AC-1.2
File: smoke.spec.ts (ADD)
Given: URL に ?tab=history が指定されている
When: ページがロードされる
Then: Designs タブが active であること
```

#### T-1.4: ファイル削除の検証

```
AC: AC-1.3
File: (実装時に手動確認)
Given: ソースコードベース
When: RulesPage.tsx と HistoryPage.tsx を検索する
Then: 両ファイルとも存在しないこと
```

Note: ファイル存在チェックは E2E テストではなく実装時の確認事項。テストでは UI に Rules/History が表示されないことで間接検証する。

## REQ-2: Integrate Domain Knowledge into Catalog tab

### E2E Tests

#### T-2.1: Catalog の Domain Knowledge に finding エントリが表示される

```
AC: AC-2.1
File: catalog.spec.ts (#16 UPDATE + ADD)
Given: unified endpoint が finding カテゴリを含む knowledge entries を返す
When: Catalog タブの Domain Knowledge セクションを表示する
Then: finding エントリがテーブルに表示されること
```

#### T-2.2: finding カテゴリの badge が表示される

```
AC: AC-2.2
File: catalog.spec.ts (#16 UPDATE)
Given: category="finding" の knowledge entry が存在する
When: Domain Knowledge テーブルが描画される
Then: "finding" の badge が表示されること
```

#### T-2.3: catalog-registered と extracted 両方が統一テーブルに表示される

```
AC: AC-2.3
File: catalog.spec.ts (ADD)
Given: mockUnifiedKnowledge が methodology と finding の両カテゴリのエントリを返す
When: Catalog タブの Domain Knowledge セクションをロードする
Then: 両エントリが同一テーブルに表示されること
```

### Fixture Changes

#### T-2.F1: mockUnifiedKnowledge ヘルパー

```
File: api-routes.ts (ADD)
Purpose: GET /api/rules/context をモックし、KnowledgeSection が使う unified データを返す
Interface: mockUnifiedKnowledge(page, entries: KnowledgeEntry[])
Implementation: makeRulesContext({ knowledge_entries: entries, total_knowledge: entries.length }) を使って /api/rules/context をモック
```

## REQ-3: Integrate Caution Search into Catalog tab

### E2E Tests

#### T-3.1: Catalog タブで Caution Search が利用できる

```
AC: AC-3.1
File: catalog.spec.ts (ADD — rules.spec.ts #19 から移植)
Given: Catalog タブが表示されている
When: テーブル名を入力して Search をクリックする
Then: マッチする caution エントリが表示されること
```

#### T-3.2: マッチする caution がない場合の empty state

```
AC: AC-3.2
File: catalog.spec.ts (ADD — rules.spec.ts #20 から移植)
Given: 存在しないテーブル名を入力する
When: Search をクリックする
Then: empty state メッセージが表示されること
```

#### T-3.3: Caution Search の API エラー時に ErrorBanner 表示

```
AC: (design.md Error Handling)
File: catalog.spec.ts (ADD)
Given: Catalog タブで Caution Search セクションが表示されている
And: /api/rules/cautions が 500 エラーを返す
When: テーブル名を入力して Search をクリックする
Then: ErrorBanner がインラインで表示されること
```

Note: テストロジックは rules.spec.ts の #19, #20 と本質的に同じ。ページ遷移先が `/?tab=rules` → `/?tab=catalog` に変わるだけ。

## REQ-4: Remove Extract Knowledge feature (feature A)

### E2E Tests

#### T-4.1: Design detail に Overview と History の2タブのみ

```
AC: AC-4.1
File: design-detail.spec.ts (Tab Restructuring UPDATE)
Given: Design detail ページが開かれている
When: サブタブを確認する
Then: "Overview" と "History" の2タブのみが visible であること
And: "Knowledge" タブが存在しないこと
```

#### T-4.2: KnowledgePanel の不在確認

```
AC: AC-4.2
File: (実装時に手動確認)
Given: フロントエンドのソースコード
When: KnowledgePanel.tsx を検索する
Then: ファイルが存在しないこと
```

#### T-4.3: extractKnowledge / saveKnowledge の不在確認

```
AC: AC-4.3
File: (実装時に手動確認 / TypeScript compiler)
Given: client.ts のエクスポート一覧
When: extractKnowledge, saveKnowledge を検索する
Then: どちらもエクスポートされていないこと
```

Note: AC-4.2, AC-4.3 はファイル・関数の存在チェック。削除されたファイルを import しようとすると TypeScript コンパイルが失敗するため、`tsc --noEmit` で自動検証される。E2E では T-4.1 が UI 上の不在を間接検証する。

## REQ-5: Improve auto-finding visibility (feature B)

### E2E Tests

#### T-5.1: supported ステータスの workflow guide に自動 finding 記録が記載される

```
AC: AC-5.1
File: design-detail.spec.ts (ADD)
Given: status="supported" の design
When: Overview パネルの workflow guide を確認する
Then: finding の自動記録に言及するテキストが含まれること
And: "Knowledge tab" という文字列が含まれないこと
```

#### T-5.2: rejected ステータスの workflow guide

```
AC: AC-5.2
File: design-detail.spec.ts (ADD)
Given: status="rejected" の design
When: Overview パネルの workflow guide を確認する
Then: finding の自動記録に言及するテキストが含まれること
And: "Knowledge tab" という文字列が含まれないこと
```

#### T-5.3: inconclusive ステータスの workflow guide

```
AC: AC-5.3
File: design-detail.spec.ts (ADD)
Given: status="inconclusive" の design
When: Overview パネルの workflow guide を確認する
Then: finding の自動記録に言及するテキストが含まれること
And: "Knowledge tab" という文字列が含まれないこと
```

## REQ-6: Fix frontend type definitions

### TypeScript Compiler Check

#### T-6.1: referenced_knowledge フィールドの存在

```
AC: AC-6.1
File: types/api.ts (TypeScript compiler check)
Given: Design interface の定義
When: TypeScript コンパイラで型チェックする
Then: referenced_knowledge: Record<string, unknown>[] | null フィールドが存在すること
```

#### T-6.2: KnowledgeCategory に "finding" が含まれる

```
AC: AC-6.2
File: types/api.ts (TypeScript compiler check)
Given: KnowledgeCategory 型の定義
When: "finding" を KnowledgeCategory 型の変数に代入する
Then: 型エラーにならないこと
```

検証方法: `npx tsc --noEmit` をビルドステップで実行し、型定義の不整合を検出する。T-2.2 の finding badge 表示テストが E2E レベルで型の正しさを間接検証する。

## Cross-Cutting: Navigation Tests

### E2E Tests

#### T-CC.1: Browser back で2タブ間を正しく遷移

```
AC: (NFR-M1 関連)
File: cross-tab.spec.ts (#27 UPDATE)
Given: designs タブが表示されている
When: catalog タブに遷移し、goBack() する
Then: designs タブに戻ること
And: URL が ?tab=designs であること
```

#### T-CC.2: Catalog タブの empty state

```
AC: (NFR-M1 関連)
File: cross-tab.spec.ts (#30 catalog UPDATE)
Given: sources が0件、unified knowledge が0件
When: Catalog タブを表示する
Then: empty state が表示されること
```

## Backend Regression

#### T-REG.1: Python テスト全パス

```
AC: NFR-R2
Command: uv run pytest
Expectation: 604 tests pass, 0 failed, 0 modified
```

Note: フロントエンド専用の変更のため、Python テストコードの修正は一切不要。バックエンド API エンドポイントも変更しない (NFR-R1)。

## Test Independence

- 各 E2E テストは `page.route()` で API をモックし、実バックエンドに依存しない
- `mockUnifiedKnowledge` は `makeRulesContext` を内部で使い、テスト間でモックデータを共有しない
- 削除対象テスト (#9, #10, #30 rules/history) の import (`mockExtractKnowledge`, `mockSaveKnowledge`) も api-routes.ts から同時に削除し、未使用エクスポートを残さない
- history.spec.ts, rules.spec.ts はファイルごと削除

## Test Coverage Summary

| REQ | AC 数 | テストケース数 | カバー率 |
|-----|-------|--------------|---------|
| REQ-1 | 3 | 4 (T-1.1〜T-1.4) | 100% |
| REQ-2 | 3 | 3 (T-2.1〜T-2.3) + 1 fixture | 100% |
| REQ-3 | 2 | 3 (T-3.1〜T-3.3) | 100% |
| REQ-4 | 3 | 3 (T-4.1〜T-4.3) | 100% |
| REQ-5 | 3 | 3 (T-5.1〜T-5.3) | 100% |
| REQ-6 | 2 | 2 (T-6.1〜T-6.2) | 100% |
| Cross-cutting | - | 2 (T-CC.1〜T-CC.2) | - |
| Regression | - | 1 (T-REG.1) | - |
| **合計** | **16** | **22** | **100%** |

### E2E ファイル変更サマリー

| ファイル | DELETE | UPDATE | ADD |
|---------|--------|--------|-----|
| design-detail.spec.ts | 2 (#9, #10) | 1 (Tab Restructuring) | 3 (T-5.1〜T-5.3) |
| smoke.spec.ts | 0 | 3 (S1, S7, S8) | 2 (T-1.2, T-1.3) |
| cross-tab.spec.ts | 2 (#30 rules, #30 history) | 2 (#27, #30 catalog) | 0 |
| catalog.spec.ts | 0 | 3 (#14, #15, #16) | 4 (T-2.3, T-3.1, T-3.2, T-3.3) |
| rules.spec.ts | - | - | - (ファイル削除) |
| history.spec.ts | - | - | - (ファイル削除) |
| api-routes.ts | 3 関数 | 1 関数 | 1 関数 |
| mock-data.ts | 0 | 0 | 0 |

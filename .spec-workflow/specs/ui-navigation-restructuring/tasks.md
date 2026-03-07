# Tasks Document: UI Navigation Restructuring

- [x] 1.1. TypeScript 型定義 + client.ts API 関数変更
  - File: frontend/src/types/api.ts, frontend/src/api/client.ts
  - Purpose: フロントエンド型定義の修正と API クライアント関数の追加・削除
  - Leverage: 既存の KnowledgeCategory 型 (api.ts)、getRulesContext() (client.ts)
  - Requirements: REQ-6 (FR-6.1, FR-6.2), REQ-4 (FR-4.4)
  - Prompt: api.ts で KnowledgeCategory に "finding" を追加、Design interface に referenced_knowledge を追加。client.ts で extractKnowledge(), saveKnowledge() を削除し、getUnifiedKnowledge(signal?) を追加。getUnifiedKnowledge は getRulesContext() を呼んで knowledge_entries を抽出する adapter 関数。tsc --noEmit で型チェック通過を確認。

- [x] 2.1. App.tsx 2タブ化 + RulesPage / HistoryPage 削除
  - File: frontend/src/App.tsx, frontend/src/pages/RulesPage.tsx, frontend/src/pages/HistoryPage.tsx
  - Purpose: トップレベルナビゲーションを Designs + Catalog の2タブに削減し、不要ページを削除
  - Leverage: 既存の VALID_TABS / getTabFromUrl() ロジック (App.tsx)
  - Requirements: REQ-1 (FR-1.1〜FR-1.6)
  - Prompt: App.tsx の VALID_TABS を ["designs", "catalog"] に変更。Rules / History タブの JSX 要素と import を削除。getTabFromUrl() で unknown tab (rules, history 含む) が designs にフォールバックすることを確認。RulesPage.tsx と HistoryPage.tsx をファイルごと削除。

- [x] 3.1. CautionSearchSection コンポーネント作成
  - File: frontend/src/pages/catalog/CautionSearchSection.tsx
  - Purpose: RulesPage から Caution Search 機能を抽出し、Catalog タブ用の独立コンポーネントとして作成
  - Leverage: RulesPage の Caution Search カード (RulesPage.tsx)、getCautions() (client.ts)、DataTable / EmptyState / ErrorBanner コンポーネント
  - Requirements: REQ-3 (FR-3.1〜FR-3.3)
  - Prompt: RulesPage から CAUTION_COLUMNS 定義と Caution Search ロジックを抽出。CautionSearchSection は自己完結型 (own state, loading, error handling)。入力は comma-separated table names、getCautions() で API 呼び出し、結果を DataTable で表示。エラー時は ErrorBanner、空結果は EmptyState を使用。既存の section pattern (SearchSection 等) に合わせる。

- [x] 3.2. KnowledgeSection unified endpoint 対応 + CatalogPage 更新
  - File: frontend/src/pages/catalog/KnowledgeSection.tsx, frontend/src/pages/catalog/CatalogPage.tsx
  - Purpose: KnowledgeSection のデータソースを catalog-only → unified に切り替え、CatalogPage に CautionSearchSection を追加
  - Leverage: 既存の KnowledgeSection (getKnowledgeList 呼び出し部分)、getUnifiedKnowledge() (1.1 で追加)
  - Requirements: REQ-2 (FR-2.1〜FR-2.4), REQ-3 (FR-3.1 の CatalogPage 統合)
  - Dependencies: 1.1, 3.1
  - Prompt: KnowledgeSection のデータ取得を getKnowledgeList() → getUnifiedKnowledge() に変更。レスポンス shape の違い (entries/count) を adapter が吸収するので、KnowledgeSection 側の変更は最小限。knowledge_entries が欠損する場合に備えて `?? []` の防御を入れる。category 列に "finding" badge が表示されることを確認。CatalogPage に CautionSearchSection を import して SchemaSection の下 (または KnowledgeSection の下) に配置。

- [x] 4.1. DesignDetail 2サブタブ化 + KnowledgePanel 削除 + OverviewPanel ガイドテキスト更新
  - File: frontend/src/pages/design-detail/DesignDetail.tsx, frontend/src/pages/design-detail/KnowledgePanel.tsx, frontend/src/pages/design-detail/OverviewPanel.tsx
  - Purpose: Design detail のサブタブを Overview + History の2つに削減、KnowledgePanel を削除、terminal ステータスの workflow guide テキストを更新
  - Leverage: 既存の DesignDetail タブ構成、STATUS_GUIDE 定数 (OverviewPanel.tsx)
  - Requirements: REQ-4 (FR-4.1〜FR-4.3), REQ-5 (FR-5.1〜FR-5.2)
  - Dependencies: 1.1
  - Prompt: DesignDetail.tsx から Knowledge タブの JSX と import を削除。KnowledgePanel.tsx をファイルごと削除。OverviewPanel.tsx の STATUS_GUIDE で supported / rejected / inconclusive のガイドテキストに「finding が自動記録された」旨を追記し、「Knowledge tab」への言及を削除。注意: client.ts の extractKnowledge/saveKnowledge 削除 (1.1) と同時に KnowledgePanel を削除しないと tsc が失敗する。

- [x] 5.1. E2E テスト更新 (DELETE / UPDATE / ADD)
  - File: frontend/e2e/design-detail.spec.ts, frontend/e2e/smoke.spec.ts, frontend/e2e/cross-tab.spec.ts, frontend/e2e/catalog.spec.ts, frontend/e2e/rules.spec.ts, frontend/e2e/history.spec.ts, frontend/e2e/fixtures/api-routes.ts
  - Purpose: test-design.md の Mutation Plan に従い、既存 E2E テストの削除・修正・追加を実施
  - Leverage: test-design.md の DELETE / UPDATE / ADD テーブル、既存 fixture ヘルパー
  - Requirements: NFR-M1, test-design.md 全体
  - Dependencies: 2.1, 3.2, 4.1
  - Prompt: test-design.md の Existing Test Mutation Plan に従って実施。DELETE: #9, #10 (design-detail), #30 rules/history (cross-tab), rules.spec.ts 全体, history.spec.ts 全体。UPDATE: S1, S7, S8 (smoke), Tab Restructuring (design-detail), #14, #15, #16 (catalog), #27, #30 catalog (cross-tab)。ADD: T-1.2, T-1.3 (smoke), T-2.3, T-3.1〜T-3.3 (catalog), T-5.1〜T-5.3 (design-detail)。api-routes.ts: mockExtractKnowledge, mockSaveKnowledge, mockKnowledgeList を削除、mockUnifiedKnowledge を追加。mockAllRoutesEmpty から /api/catalog/knowledge モックを削除。全 E2E テストが pass することを確認。最後に `uv run pytest` で Python 604 tests が全パスすることも確認 (NFR-R2)。

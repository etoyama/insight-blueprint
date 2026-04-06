# SPEC-4b: webui-frontend — Tasks

- [x] 1.1 Initialize shadcn/ui and configure development environment
  - File: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/src/index.css`, `frontend/components.json`
  - Run `npx shadcn@latest init` in `frontend/` with CSS Variables enabled
  - Add `@` path alias to `tsconfig.json` (`paths: {"@/*": ["./src/*"]}`) and `vite.config.ts` (`resolve.alias`)
  - Add Vite proxy config: `server.proxy["/api"] = { target: "http://localhost:3000", changeOrigin: true }`
  - Install required shadcn/ui components: `npx shadcn@latest add tabs table badge button card dialog input textarea select alert`
  - Purpose: Establish the frontend development environment with all UI dependencies before any component work begins
  - Done When:
    1. `frontend/components.json` が存在し shadcn/ui 設定が記載されている
    2. `tsconfig.json` に `@/*` パスエイリアスが設定されている
    3. `vite.config.ts` に `resolve.alias` と `server.proxy` が設定されている
    4. 10個の shadcn/ui コンポーネントが `frontend/src/components/ui/` に存在する
    5. `npm run dev` がエラーなく起動する
    6. `npm run build` が `src/insight_blueprint/static/` にファイルを出力する
  - Verify:
    1. `ls frontend/src/components/ui/ | wc -l` → 10以上
    2. `cd frontend && npx tsc --noEmit` → exit 0
    3. `cd frontend && npm run build` → exit 0
    4. `ls src/insight_blueprint/static/index.html` → ファイル存在
    5. `grep '@/' frontend/tsconfig.json` → パスエイリアス確認
    6. `grep 'proxy' frontend/vite.config.ts` → proxy 設定確認
  - _Leverage: existing `frontend/` scaffold (Vite 6 + React 19 + Tailwind CSS v4), `.claude/docs/research/SPEC-4b-frontend-research.md`_
  - _Requirements: FR-21, FR-22, FR-23_
  - _Prompt: Role: Frontend Developer specializing in React + Vite + Tailwind CSS v4 + shadcn/ui setup | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Initialize shadcn/ui in the existing frontend scaffold. Add path alias, Vite proxy, and install all 10 shadcn/ui components. Verify dev server and production build both work. | Restrictions: Do not modify any Python files. Do not change the Vite build output directory (must remain `../src/insight_blueprint/static`). Do not add unnecessary dependencies. | Success: `npm run dev` starts without errors, `npm run build` produces output in `src/insight_blueprint/static/`, all 10 shadcn/ui components are installed, path alias `@/` resolves correctly. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 1.2 Create TypeScript type definitions and API client
  - File: `frontend/src/types/api.ts`, `frontend/src/api/client.ts`
  - Define all TypeScript types mirroring Python Pydantic models: `Design`, `DataSource`, `ColumnSchema`, `ReviewComment`, `KnowledgeEntry`, `RulesContext`, `SearchResult`, `Caution`
  - Define enum union types: `DesignStatus`, `SourceType`, `KnowledgeCategory`, `KnowledgeImportance`
  - Define request types: `CreateDesignRequest`, `AddCommentRequest`, `AddSourceRequest`
  - Implement `request\<T>()` shared helper with: JSON/non-JSON error handling, 422 normalization, AbortError passthrough, network error handling
  - Implement all 16 endpoint functions (excluding PUT endpoints per Out of Scope), each accepting optional `AbortSignal`
  - Purpose: Establish the type-safe API layer that all page components depend on
  - Done When:
    1. `frontend/src/types/api.ts` に 8 モデル型 + 4 enum 型 + 3 リクエスト型が定義されている
    2. `frontend/src/api/client.ts` に `request\<T>()` ヘルパーが実装されている
    3. `client.ts` に 16 エンドポイント関数が実装されている
    4. 全 GET 関数が `AbortSignal` パラメータを受け取る
    5. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `grep -c 'export type\|export interface' src/types/api.ts` → 15以上
    3. `grep -c 'export async function' src/api/client.ts` → 16
    4. `grep -c 'AbortSignal' src/api/client.ts` → GET 関数の数以上
    5. `grep 'request\<' src/api/client.ts` → request ヘルパーの存在確認
  - _Leverage: SPEC-4a `web.py` endpoint definitions, `models/design.py`, `models/catalog.py`, `models/review.py`_
  - _Requirements: FR-3, NFR-Security (XSS prevention via type safety)_
  - _Prompt: Role: TypeScript Developer specializing in API client design and type safety | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create complete TypeScript type definitions mirroring Python Pydantic models, and implement the API client with shared request\<T>() helper. Reference SPEC-4a web.py for exact endpoint signatures and response shapes. | Restrictions: Do not use any external HTTP client library (use native fetch). Do not add runtime type validation (trust backend contracts). Base URL must be empty string (same-origin serving). Include AbortSignal parameter on all GET endpoint functions. | Success: All types compile without errors, all 16 endpoint functions implemented, request\<T>() handles {error}, {detail} (422), non-JSON, and network errors correctly. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 2.1 Create shared UI components
  - File: `frontend/src/components/DataTable.tsx`, `frontend/src/components/StatusBadge.tsx`, `frontend/src/components/EmptyState.tsx`, `frontend/src/components/ErrorBanner.tsx`, `frontend/src/components/JsonTree.tsx`
  - `DataTable\<T>`: generic table with columns config, row click handler, selected row highlight. Wraps shadcn/ui Table
  - `StatusBadge`: DesignStatus → color mapping (draft=gray, active=blue, pending_review=yellow, supported=green, rejected=red, inconclusive=orange). Wraps shadcn/ui Badge
  - `EmptyState`: message + optional action button
  - `ErrorBanner`: error message + optional retry button. Wraps shadcn/ui Alert
  - `JsonTree`: recursive collapsible JSON viewer for dict fields (metrics, connection, etc.). No external library
  - Purpose: Provide reusable UI building blocks used across 4+ pages
  - Done When:
    1. 5つのコンポーネントファイルが `frontend/src/components/` に存在する
    2. 各コンポーネントが 100行以内である
    3. `DataTable` が TypeScript ジェネリクスを使用している
    4. `StatusBadge` が 6つの DesignStatus 値すべてに色をマッピングしている
    5. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `ls src/components/{DataTable,StatusBadge,EmptyState,ErrorBanner,JsonTree}.tsx | wc -l` → 5
    3. `wc -l src/components/DataTable.tsx` → 100行以下
    4. `grep -c 'draft\|active\|pending_review\|supported\|rejected\|inconclusive' src/components/StatusBadge.tsx` → 6
    5. `grep 'T extends\|<T>' src/components/DataTable.tsx` → ジェネリクス使用確認
  - _Leverage: shadcn/ui components installed in task 1.1_
  - _Requirements: FR-4, NFR-Usability (color coding, loading states)_
  - _Prompt: Role: React Component Developer specializing in reusable UI components | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create 5 shared UI components using shadcn/ui primitives. DataTable must be generic with TypeScript generics. StatusBadge must map all 6 DesignStatus values to specific colors. JsonTree must handle nested objects/arrays with expand/collapse. | Restrictions: Do not use external component libraries beyond shadcn/ui. Keep each component under 100 lines. Do not add global CSS — use Tailwind utility classes only. | Success: All 5 components render correctly, DataTable accepts generic type parameter, StatusBadge shows correct colors for all 6 statuses, JsonTree handles nested data with toggle. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 2.2 Create App shell with tab navigation
  - File: `frontend/src/App.tsx`, `frontend/src/main.tsx`
  - Implement App shell: header ("Insight Blueprint") + shadcn/ui Tabs for 4 tabs
  - Tab state management: useState\<Tab> synced with URL ?tab= parameter
  - Handle popstate event for browser back/forward navigation
  - Invalid ?tab= values fallback to "designs"
  - Update main.tsx to render App instead of placeholder
  - Purpose: Establish the application shell that hosts all page components
  - Done When:
    1. `App.tsx` が 4タブ（Designs/Catalog/Rules/History）を表示する
    2. タブクリックで URL の `?tab=` パラメータが更新される
    3. `?tab=invalid` がデフォルトの "designs" にフォールバックする
    4. popstate イベントハンドラが登録されている
    5. `main.tsx` が App コンポーネントをレンダーする
    6. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `cd frontend && npm run build` → exit 0
    3. `grep 'popstate' src/App.tsx` → イベントハンドラ存在
    4. `grep 'designs.*catalog.*rules.*history' src/App.tsx` → 4タブ定義確認（大文字小文字問わず）
    5. `grep 'replaceState\|pushState' src/App.tsx` → URL 同期処理確認
  - _Leverage: shadcn/ui Tabs component_
  - _Requirements: FR-1, FR-2_
  - _Prompt: Role: React Developer specializing in SPA navigation and URL state sync | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create App.tsx with header, 4-tab navigation using shadcn/ui Tabs, and URL ?tab= synchronization. Handle popstate for browser navigation. Render placeholder content for each tab (actual pages will be implemented in later tasks). Update main.tsx entry point. | Restrictions: Do not use react-router. Use history.replaceState (not pushState) for tab changes. Keep App.tsx under 80 lines. | Success: 4 tabs render and switch correctly, URL updates on tab change, page reload preserves tab selection, browser back/forward works, invalid ?tab= falls back to designs. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 3.1 Implement Designs page (master list + create dialog)
  - File: `frontend/src/pages/DesignsPage.tsx`
  - Fetch and display design list using DataTable with columns: title, status (StatusBadge), updated_at
  - Status filter dropdown (All + 6 status values) using shadcn/ui Select
  - "New Design" button → Dialog with form: title, hypothesis_statement, hypothesis_background, theme_id
  - Loading state, error handling (ErrorBanner), empty state (EmptyState)
  - AbortController in useEffect for list fetch, cleanup on unmount/filter change
  - Row click sets selectedId state, renders DesignDetail below (placeholder until 3.2)
  - Purpose: Implement the master half of the Designs master-detail view
  - Done When:
    1. `DesignsPage.tsx` が存在し 250行以内である
    2. `listDesigns` API を呼び出してデザイン一覧を表示する
    3. ステータスフィルタ（All + 6 status）が動作する
    4. "New Design" ダイアログが開き、送信後にリスト更新される
    5. Loading/Error/Empty の3状態が実装されている
    6. useEffect 内で AbortController を使用している
    7. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `wc -l src/pages/DesignsPage.tsx` → 250行以下
    3. `grep 'AbortController' src/pages/DesignsPage.tsx` → 存在確認
    4. `grep 'listDesigns\|createDesign' src/pages/DesignsPage.tsx` → API 呼び出し確認
    5. `grep 'ErrorBanner\|EmptyState' src/pages/DesignsPage.tsx` → エラー/空状態確認
    6. `grep 'Dialog' src/pages/DesignsPage.tsx` → 作成ダイアログ確認
  - _Leverage: `api/client.ts` (listDesigns, createDesign), shared components (DataTable, StatusBadge, EmptyState, ErrorBanner)_
  - _Requirements: FR-5, FR-7_
  - _Prompt: Role: React Developer specializing in data-driven UI with forms and filtering | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create DesignsPage with design list table, status filter, and create dialog. Use AbortController for fetch cancellation. Connect to API client for listDesigns and createDesign. | Restrictions: Do not implement the detail panel yet (that is task 3.2). Do not use any state management library. Keep the file under 250 lines. | Success: Design list loads and displays, status filter works, create dialog opens/submits/refreshes list, loading/error/empty states render correctly, AbortController cancels stale requests. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 3.2 Implement Design detail with sub-tabs (Overview / Review / Knowledge)
  - File: `frontend/src/pages/DesignDetail.tsx`
  - Fetch design detail via getDesign(designId)
  - Sub-tabs using shadcn/ui Tabs: Overview, Review, Knowledge
  - **OverviewPanel**: display all design fields, JsonTree for dict fields (metrics, explanatory, chart, next_action)
  - **ReviewPanel**: "Submit for Review" button (disabled when status !== "active"), comments list (DataTable), add comment form (textarea + status select + reviewer input)
  - **KnowledgePanel**: "Extract Knowledge" button → preview list, "Save Knowledge" button → persist
  - onDesignUpdated callback to trigger parent list refresh
  - Purpose: Implement the detail half of the Designs master-detail view with full review workflow
  - Done When:
    1. `DesignDetail.tsx` が存在し 400行以内である
    2. Overview / Review / Knowledge の3サブタブが実装されている
    3. OverviewPanel が dict フィールドに JsonTree を使用している
    4. ReviewPanel の "Submit for Review" ボタンが status !== "active" 時に無効化される
    5. KnowledgePanel の "Extract Knowledge" + "Save Knowledge" が実装されている
    6. `onDesignUpdated` コールバックが親に変更を通知する
    7. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `wc -l src/pages/DesignDetail.tsx` → 400行以下
    3. `grep 'Overview\|Review\|Knowledge' src/pages/DesignDetail.tsx` → 3サブタブ確認
    4. `grep 'disabled\|status.*active' src/pages/DesignDetail.tsx` → ボタン無効化ロジック確認
    5. `grep 'JsonTree' src/pages/DesignDetail.tsx` → JsonTree 使用確認
    6. `grep 'onDesignUpdated' src/pages/DesignDetail.tsx` → コールバック確認
  - _Leverage: `api/client.ts` (getDesign, submitReview, listComments, addComment, extractKnowledge, saveKnowledge), shared components (JsonTree, DataTable, StatusBadge)_
  - _Requirements: FR-6, FR-8, FR-9, FR-10, FR-11_
  - _Prompt: Role: React Developer specializing in complex multi-panel UI with forms | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create DesignDetail with 3 sub-tabs (Overview/Review/Knowledge). Each panel is a separate function component within the same file. Overview shows design fields with JsonTree for dicts. Review has submit button, comment list, and add comment form. Knowledge has extract preview and save functionality. | Restrictions: Keep DesignDetail as orchestrator (~150 lines) with panels (~60-80 lines each). Do not exceed 400 lines total. Disable "Submit for Review" when status is not "active". Use AbortController for all fetches. | Success: All 3 sub-tabs render with correct data, review submit changes status, comments add and refresh, knowledge extract shows preview and save persists, parent list refreshes on updates. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 3.3 Wire DesignsPage + DesignDetail together
  - File: `frontend/src/pages/DesignsPage.tsx` (modify), `frontend/src/App.tsx` (modify)
  - Import and render DesignDetail in DesignsPage when selectedId is set
  - Pass onDesignUpdated callback to refresh design list
  - Wire DesignsPage into App.tsx tab content (replace placeholder)
  - Purpose: Complete the Designs tab by connecting master and detail components
  - Done When:
    1. DesignsPage が `selectedId` 設定時に DesignDetail をレンダーする
    2. `onDesignUpdated` コールバックでデザインリストが再取得される
    3. App.tsx の Designs タブが DesignsPage を表示する
    4. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `cd frontend && npm run build` → exit 0
    3. `grep 'DesignDetail' src/pages/DesignsPage.tsx` → import + render 確認
    4. `grep 'DesignsPage' src/App.tsx` → import 確認
  - _Leverage: DesignsPage (task 3.1), DesignDetail (task 3.2)_
  - _Requirements: FR-5, FR-6, FR-8_
  - _Prompt: Role: React Developer | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Wire DesignDetail into DesignsPage (render below table when selectedId is set). Wire DesignsPage into App.tsx Designs tab. | Restrictions: Minimal changes only — import + render + callback wiring. Do not refactor existing components. | Success: Clicking a design row shows DesignDetail below, design updates refresh the list, Designs tab in App.tsx shows the full page. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 4.1 Implement Catalog page
  - File: `frontend/src/pages/CatalogPage.tsx`
  - Source list with DataTable: name, type (badge), description, tags, updated_at
  - Source detail: schema table (ColumnSchema fields) on row click
  - "Add Source" dialog: source_id, name, type (select), description, connection (JSON textarea)
  - Search bar: input + search button, results display
  - Domain knowledge list section
  - Internal sub-components: SourceListSection, SchemaSection, SearchSection, KnowledgeSection
  - AbortController for all fetches
  - Purpose: Implement the complete Catalog tab with all 4 sections
  - Done When:
    1. `CatalogPage.tsx` が存在し 350行以内である
    2. ソース一覧が DataTable で表示される
    3. ソースクリックでスキーマテーブルが表示される
    4. "Add Source" ダイアログで JSON バリデーションが動作する（不正 JSON → エラー表示、正当 JSON → 送信成功）
    5. 検索バーがカタログ検索を実行し結果を表示する
    6. ドメイン知識セクションが category/importance バッジ付きで表示される
    7. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `wc -l src/pages/CatalogPage.tsx` → 350行以下
    3. `grep 'AbortController' src/pages/CatalogPage.tsx` → 存在確認
    4. `grep 'JSON.parse' src/pages/CatalogPage.tsx` → JSON バリデーション確認
    5. `grep 'listSources\|addSource\|getSchema\|searchCatalog\|getKnowledgeList' src/pages/CatalogPage.tsx` → 5 API 呼び出し確認
    6. `grep 'SourceListSection\|SchemaSection\|SearchSection\|KnowledgeSection' src/pages/CatalogPage.tsx` → 4サブコンポーネント確認
  - _Leverage: `api/client.ts` (listSources, addSource, getSchema, searchCatalog, getKnowledgeList), shared components_
  - _Requirements: FR-12, FR-13, FR-14, FR-15, FR-16_
  - _Prompt: Role: React Developer specializing in multi-section data pages | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create CatalogPage with 4 internal sections (SourceList, Schema, Search, Knowledge). Each section is a sub-component in the same file. Source list shows all sources, clicking shows schema. Add Source opens dialog with JSON textarea for connection. Search bar triggers catalog search. Knowledge section shows all domain knowledge entries. | Restrictions: Keep total file under 350 lines. Validate JSON input for connection field before submit. Use AbortController for all fetches. | Success: Source list loads, schema displays on click, add source works with JSON validation, search returns results, knowledge entries display with category/importance badges. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 4.2 Implement Rules page
  - File: `frontend/src/pages/RulesPage.tsx`
  - Fetch and display project context (GET /api/rules/context) in 3 collapsible sections: Sources, Knowledge, Rules
  - Each section shows count in header and list/table of items
  - Cautions search: table names input (comma-separated) + search button
  - Search results display
  - Purpose: Implement the Rules tab for domain knowledge and cautions browsing
  - Done When:
    1. `RulesPage.tsx` が存在し 200行以内である
    2. Sources / Knowledge / Rules の3セクションが折りたたみ可能に表示される
    3. 各セクションヘッダーにアイテム数が表示される
    4. テーブル名入力 + 検索ボタンで Cautions 検索が動作する
    5. データなし時に EmptyState が表示される
    6. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `wc -l src/pages/RulesPage.tsx` → 200行以下
    3. `grep 'AbortController' src/pages/RulesPage.tsx` → 存在確認
    4. `grep 'getRulesContext\|getCautions' src/pages/RulesPage.tsx` → 2 API 呼び出し確認
    5. `grep 'Card' src/pages/RulesPage.tsx` → shadcn/ui Card 使用確認
  - _Leverage: `api/client.ts` (getRulesContext, getCautions), shared components_
  - _Requirements: FR-17, FR-18_
  - _Prompt: Role: React Developer | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create RulesPage with project context display (3 collapsible sections with counts) and cautions search form. | Restrictions: Keep file under 200 lines. Use shadcn/ui Card for sections. Use AbortController for fetches. | Success: Context loads with correct counts, sections expand/collapse, cautions search returns results for valid table names, empty state shows when no data. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 4.3 Implement History page
  - File: `frontend/src/pages/HistoryPage.tsx`
  - Fetch all designs, sort by updated_at descending
  - Display timeline: title, status (StatusBadge), updated_at, distinguish created vs updated
  - Click to expand: fetch and show review comments for that design
  - Comments show reviewer, comment text, status_after (StatusBadge), created_at
  - Purpose: Implement the History tab using existing API endpoints (no new backend needed)
  - Done When:
    1. `HistoryPage.tsx` が存在し 200行以内である
    2. デザイン一覧が updated_at 降順で表示される
    3. created と updated が視覚的に区別される
    4. エントリクリックでレビューコメント履歴が展開される
    5. コメントに reviewer, comment, status_after, created_at が表示される
    6. デザイン0件時に EmptyState が表示される
    7. `npx tsc --noEmit` がエラーゼロで通過する
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `wc -l src/pages/HistoryPage.tsx` → 200行以下
    3. `grep 'AbortController' src/pages/HistoryPage.tsx` → 存在確認
    4. `grep 'listDesigns\|listComments' src/pages/HistoryPage.tsx` → 2 API 呼び出し確認
    5. `grep 'StatusBadge\|EmptyState' src/pages/HistoryPage.tsx` → 共通コンポーネント使用確認
    6. `grep 'updated_at\|sort' src/pages/HistoryPage.tsx` → ソート処理確認
  - _Leverage: `api/client.ts` (listDesigns, listComments), shared components (StatusBadge, EmptyState)_
  - _Requirements: FR-19, FR-20_
  - _Prompt: Role: React Developer | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Create HistoryPage showing all designs sorted by updated_at desc as a timeline. Clicking an entry expands to show review comment history fetched via listComments. | Restrictions: Do not create new API endpoints. Keep file under 200 lines. Use AbortController for comment fetches. Distinguish "created" vs "updated" in the timeline display. | Success: Timeline shows all designs sorted by date, clicking expands to show comments with status badges, empty state renders when no designs exist. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 5.1 Wire all pages into App and verify full build
  - File: `frontend/src/App.tsx` (modify)
  - Import and wire CatalogPage, RulesPage, HistoryPage into App.tsx tab content
  - Verify `npm run build` succeeds with zero TypeScript errors
  - Verify `poe build-frontend` produces output in `src/insight_blueprint/static/`
  - Verify built SPA loads correctly when served by FastAPI StaticFiles
  - Purpose: Final integration and build verification to ensure the complete dashboard is deployable
  - Done When:
    1. App.tsx が 4タブすべてのページコンポーネントを import・レンダーしている
    2. `npm run build` が TypeScript エラーゼロで完了する
    3. `poe build-frontend` が `src/insight_blueprint/static/` にファイルを出力する
    4. ビルド時間が 30秒以内である
    5. FastAPI 起動時に `GET /` で `index.html` が返る
    6. SPEC-4a の全 341 テストが通過する（リグレッションなし）
  - Verify:
    1. `cd frontend && npx tsc --noEmit` → exit 0
    2. `cd frontend && npm run build` → exit 0（30秒以内）
    3. `poe build-frontend` → exit 0
    4. `ls src/insight_blueprint/static/index.html` → ファイル存在
    5. `ls src/insight_blueprint/static/assets/` → JS/CSS ファイル存在
    6. `grep 'CatalogPage\|RulesPage\|HistoryPage\|DesignsPage' frontend/src/App.tsx` → 4ページ import 確認
    7. `uv run pytest` → 341 tests passed
  - _Leverage: All page components (tasks 3.1-4.3), existing build pipeline (poe build-frontend)_
  - _Requirements: FR-23, NFR-Performance (build under 30s)_
  - _Prompt: Role: Frontend Developer specializing in build systems and integration | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Wire remaining pages (Catalog, Rules, History) into App.tsx. Run npm run build and poe build-frontend to verify the complete SPA builds successfully. Test that the built static files are served correctly by FastAPI. | Restrictions: Do not modify page components — only App.tsx imports. Do not change build configuration. Ensure zero TypeScript compile errors. | Success: All 4 tabs work in the built SPA, npm run build completes under 30s, poe build-frontend outputs to static/, FastAPI serves the SPA correctly at localhost. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

- [x] 5.2 Set up Playwright smoke tests
  - File: `frontend/playwright.config.ts`, `frontend/e2e/smoke.spec.ts`, `frontend/package.json` (modify)
  - Install Playwright: `npm install -D @playwright/test` and `npx playwright install chromium`
  - Create `playwright.config.ts` with baseURL `http://localhost:3000`, headless mode, webServer config
  - Implement 8 smoke test cases in `frontend/e2e/smoke.spec.ts`:
    - S1: Tab routing — navigate all 4 tabs, verify URL ?tab= sync
    - S2: Invalid tab fallback — `?tab=invalid` → designs
    - S3: API error banner — load without backend → ErrorBanner visible
    - S4: Empty state — load with no data → EmptyState visible
    - S5: Create design dialog — open, fill, submit, verify in list
    - S6: Status filter — select "draft", verify filtered results
    - S7: Design detail expand — click row, verify sub-tabs visible
    - S8: Source add with JSON validation — invalid JSON error, valid JSON success
  - Add `"test:e2e": "playwright test"` script to package.json
  - Purpose: Automate high-risk regression detection, runnable by Claude Code via Playwright MCP
  - Done When:
    1. `frontend/playwright.config.ts` が存在し baseURL が `http://localhost:3000` に設定されている
    2. `frontend/e2e/smoke.spec.ts` に 8 テストケースが実装されている
    3. `package.json` に `test:e2e` スクリプトが追加されている
    4. `npx playwright test` で 8/8 テストが通過する
    5. テスト実行時間が 30秒以内である
    6. flaky test がない（3回連続実行で全パス）
  - Verify:
    1. `ls frontend/playwright.config.ts` → ファイル存在
    2. `ls frontend/e2e/smoke.spec.ts` → ファイル存在
    3. `grep 'test:e2e' frontend/package.json` → スクリプト存在
    4. `cd frontend && npx playwright test` → 8 passed（FastAPI + ビルド済み SPA が必要）
    5. `cd frontend && npx playwright test` を 3回実行 → 全回パス（flaky test なし確認）
    6. `grep -c 'test(' e2e/smoke.spec.ts` → 8
  - _Leverage: Built SPA from task 5.1, all page components, Playwright MCP (webapp-testing skill)_
  - _Requirements: test-design.md Playwright Smoke Tests section_
  - _Prompt: Role: Frontend Test Engineer specializing in Playwright E2E testing | Task: Implement the task for spec SPEC-4b, first run spec-workflow-guide to get the workflow guide then implement the task: Set up Playwright with 8 smoke tests covering tab routing, error handling, empty states, design CRUD, and source validation. Tests should be concise (each under 20 lines) and reliable. | Restrictions: Only install Playwright (no other test frameworks). Only install chromium browser. Keep all tests in a single file. Tests must work with the built SPA served by FastAPI (not dev server). Do not test Review workflow or Knowledge extraction (these remain manual). | Success: All 8 smoke tests pass with `npx playwright test`, tests complete in under 30 seconds, no flaky tests. Mark task as in-progress `[-]` in tasks.md before starting, log implementation with log-implementation tool after completion, then mark as complete `[x]`._

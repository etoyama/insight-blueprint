# SPEC-4b: webui-frontend — Design

> **Spec ID**: SPEC-4b
> **Created**: 2026-02-28

---

## Overview

SPEC-4a で構築した FastAPI REST API (18 endpoints) を消費する React フロントエンドを
`frontend/` に実装する。既存の Vite + React + Tailwind CSS v4 scaffold に shadcn/ui を
追加し、4タブダッシュボード（Designs / Catalog / Rules / History）を構築する。
ビルド成果物は `src/insight_blueprint/static/` に出力され、既存の wheel 同梱パイプラインで配布される。

## Steering Document Alignment

### Technical Standards (tech.md)

- Frontend: React 19 + Vite 6 + Tailwind CSS + shadcn/ui（tech.md §WebUI 準拠）
- Static files: `src/insight_blueprint/static/` — hatch `artifacts` config で wheel に同梱
- ビルド: `poe build-frontend` → `cd frontend && npm install && npm run build`
- TypeScript strict mode（tech.md §YAGNI に基づき最小限の抽象化）

### Project Structure (structure.md)

- `frontend/` は structure.md §Repository Layout に定義済み
- `frontend/src/` 内のディレクトリ構成は SPEC-4b で新規定義
- `static/` はビルド成果物のみ（.gitignore 対象）

## Code Reuse Analysis

### Existing Components to Leverage

- **SPEC-4a frontend scaffold** (`frontend/`): Vite 6 + React 19 + Tailwind CSS v4 の
  基盤設定が完了済み。`vite.config.ts`, `tsconfig.json`, `index.html`, `main.tsx` を拡張する
- **SPEC-4a `web.py`**: REST API 契約（18 endpoints）がそのまま TypeScript 型定義のソース
- **SPEC-4a Pydantic リクエストモデル**: `CreateDesignRequest`, `AddCommentRequest`,
  `AddSourceRequest`, `SaveKnowledgeRequest` の構造を TypeScript 型に変換
- **SPEC-4a ビルドパイプライン**: `poe build-frontend`, `poe build` が既存。変更不要

### Integration Points

- **FastAPI REST API (SPEC-4a)**: `api/client.ts` から `fetch()` で呼び出し。
  開発時は Vite proxy、本番は同一オリジン配信
- **`static/` ディレクトリ**: `npm run build` の出力先。`web.py` の `StaticFiles` mount で配信
- **CORS 設定**: `web.py` で `localhost:5173`（Vite dev server）が既に許可済み

## Architecture

### 全体構成

```
frontend/src/
├── main.tsx                    # Entry point (React root)
├── App.tsx                     # Shell: Header + TabBar + Page routing
├── api/
│   └── client.ts               # fetch wrapper + all endpoint functions
├── components/
│   ├── DataTable.tsx           # Generic table (shadcn/ui Table)
│   ├── StatusBadge.tsx         # DesignStatus color badge (shadcn/ui Badge)
│   ├── EmptyState.tsx          # Zero-data placeholder
│   ├── ErrorBanner.tsx         # API error display (shadcn/ui Alert)
│   └── JsonTree.tsx            # Collapsible JSON viewer (for dict fields)
├── pages/
│   ├── DesignsPage.tsx         # Master list + detail panel
│   ├── DesignDetail.tsx        # Detail with sub-tabs (Overview/Review/Knowledge)
│   ├── CatalogPage.tsx         # Source list + schema + search + knowledge
│   ├── RulesPage.tsx           # Project context + cautions search
│   └── HistoryPage.tsx         # Recent activity timeline
└── types/
    └── api.ts                  # TypeScript type definitions for API responses
```

### Data Flow

```
User Action → Page Component → api/client.ts → fetch() → FastAPI REST API
                                                              ↓
User sees ← Page Component ← useState update ← JSON response ←┘
```

### Modular Design Principles

- **Single File Responsibility**: 1ファイル = 1コンポーネント or 1モジュール。
  ページコンポーネントは自身の API 呼び出しと状態管理を完結させる
- **Component Isolation**: ページ間で状態を共有しない。各ページは独立して `useState` +
  `useEffect` で API データを管理する。グローバル状態管理ライブラリは不要
- **Service Layer Separation**: API 呼び出しは `api/client.ts` に集約。
  ページコンポーネントから直接 `fetch()` を呼ばない
- **Utility Modularity**: 共通コンポーネント（`DataTable`, `StatusBadge` 等）は
  2箇所以上で使用されるもののみ切り出す。1箇所でしか使わないものはページ内で完結
- **Race Condition Prevention**: 全ての `useEffect` 内 fetch に `AbortController` を使用。
  コンポーネントのアンマウントや依存値の変更時にリクエストをキャンセルし、
  stale レスポンスによる誤表示を防ぐ:
  ```tsx
  useEffect(() => {
    const ctrl = new AbortController();
    listDesigns(statusFilter, ctrl.signal)
      .then(setDesigns)
      .catch(err => { if (err.name !== "AbortError") setError(err.message); });
    return () => ctrl.abort();
  }, [statusFilter]);
  ```

## Components and Interfaces

### Component 1: `App.tsx`

- **Purpose**: Application shell。ヘッダー + タブバー + ページルーティングを提供
- **Interfaces**:
  ```tsx
  type Tab = "designs" | "catalog" | "rules" | "history";

  function App(): JSX.Element
  // - useState<Tab> でアクティブタブを管理
  // - URLSearchParams で ?tab= パラメータと同期
  // - 不正な ?tab= 値は "designs" にフォールバック
  // - タブ切り替え時に history.replaceState で URL 更新
  // - popstate イベントをリッスンしてブラウザ戻る/進むに対応
  // - shadcn/ui Tabs で UI 描画
  ```
- **Dependencies**: shadcn/ui `Tabs`, 全ページコンポーネント
- **Reuses**: なし（新規）

### Component 2: `api/client.ts`

- **Purpose**: 全 REST API 呼び出しの集約。薄い fetch wrapper
- **Interfaces**:
  ```typescript
  // --- Core request helper ---
  // All endpoint functions delegate to this shared helper.
  // Handles: JSON parse, {error} extraction, 422 normalization, non-JSON fallback.
  async function request<T>(path: string, init?: RequestInit): Promise<T>
  // - Calls fetch(path, init)
  // - If !res.ok: tries JSON parse → extracts {error} or {detail} (FastAPI 422)
  //   → falls back to res.statusText for non-JSON responses → throws ApiError
  // - AbortError (from AbortController) is re-thrown as-is (not wrapped in ApiError)
  // - On network error (TypeError from fetch): throws ApiError with "サーバーに接続できません"

  // Error class
  class ApiError extends Error {
    status: number;   // HTTP status code (0 for network errors)
    detail: string;   // Server error message or fallback
  }

  // Design endpoints
  // All endpoint functions accept an optional AbortSignal for cancellation.
  // Design endpoints
  function listDesigns(status?: string, signal?: AbortSignal): Promise<{ designs: Design[]; count: number }>
  function createDesign(body: CreateDesignRequest): Promise<{ design: Design; message: string }>
  function getDesign(id: string, signal?: AbortSignal): Promise<Design>

  // Review endpoints
  function submitReview(designId: string): Promise<{ design_id: string; status: string; message: string }>
  function listComments(designId: string): Promise<{ design_id: string; comments: ReviewComment[]; count: number }>
  function addComment(designId: string, body: AddCommentRequest): Promise<{ comment_id: string; status_after: string; message: string }>
  function extractKnowledge(designId: string): Promise<{ entries: KnowledgeEntry[]; count: number; message: string }>
  function saveKnowledge(designId: string, entries: KnowledgeEntry[]): Promise<{ saved_entries: KnowledgeEntry[]; count: number; message: string }>

  // Catalog endpoints
  function listSources(): Promise<{ sources: DataSource[]; count: number }>
  function addSource(body: AddSourceRequest): Promise<{ source: DataSource; message: string }>
  function getSource(id: string): Promise<DataSource>
  function getSchema(sourceId: string): Promise<{ source_id: string; columns: ColumnSchema[] }>
  function searchCatalog(query: string, sourceId?: string): Promise<{ query: string; results: SearchResult[]; count: number }>
  function getKnowledgeList(): Promise<{ entries: KnowledgeEntry[]; count: number }>

  // Rules endpoints
  function getRulesContext(): Promise<RulesContext>
  function getCautions(tableNames: string[]): Promise<{ table_names: string[]; cautions: Caution[]; count: number }>

  // Health
  function healthCheck(): Promise<{ status: string; version: string }>
  ```
- **Dependencies**: `types/api.ts`
- **Reuses**: SPEC-4a `web.py` のエンドポイント定義を TypeScript に1:1マッピング

### Component 3: `types/api.ts`

- **Purpose**: API レスポンスの TypeScript 型定義。Python Pydantic モデルのミラー
- **Interfaces**:
  ```typescript
  // Enums
  type DesignStatus = "draft" | "active" | "pending_review" | "supported" | "rejected" | "inconclusive";
  type SourceType = "csv" | "api" | "sql";
  type KnowledgeCategory = "methodology" | "caution" | "definition" | "context";
  type KnowledgeImportance = "high" | "medium" | "low";

  // Models
  interface Design {
    id: string;
    theme_id: string;
    title: string;
    hypothesis_statement: string;
    hypothesis_background: string;
    status: DesignStatus;
    parent_id: string | null;
    metrics: Record<string, unknown>;
    explanatory: Record<string, unknown>[];
    chart: Record<string, unknown>[];
    source_ids: string[];
    next_action: Record<string, unknown> | null;
    created_at: string;  // ISO 8601
    updated_at: string;
  }

  interface DataSource {
    id: string;
    name: string;
    type: SourceType;
    description: string;
    connection: Record<string, unknown>;
    schema_info: { columns: ColumnSchema[] };
    tags: string[];
    created_at: string;
    updated_at: string;
  }

  interface ColumnSchema {
    name: string;
    type: string;
    description: string;
    nullable: boolean;
    examples: string[] | null;
    range: Record<string, unknown> | null;
    unit: string | null;
  }

  interface ReviewComment {
    id: string;
    design_id: string;
    comment: string;
    reviewer: string;
    status_after: DesignStatus;
    created_at: string;
    extracted_knowledge: string[];
  }

  interface KnowledgeEntry {
    key: string;
    title: string;
    content: string;
    category: KnowledgeCategory;
    importance: KnowledgeImportance;
    created_at: string;
    source: string | null;
    affects_columns: string[];
  }

  interface RulesContext {
    sources: { id: string; name: string; type: string; description: string; tags: string[] }[];
    knowledge_entries: KnowledgeEntry[];
    rules: Record<string, unknown>[];
    total_sources: number;
    total_knowledge: number;
    total_rules: number;
  }

  // Request types
  interface CreateDesignRequest {
    title: string;
    hypothesis_statement: string;
    hypothesis_background: string;
    theme_id?: string;
  }

  interface AddCommentRequest {
    comment: string;
    status: string;
    reviewer?: string;
  }

  interface AddSourceRequest {
    source_id: string;
    name: string;
    type: SourceType;         // enum-constrained (not raw string)
    description: string;
    connection: Record<string, unknown>;
    columns?: ColumnSchema[];
    tags?: string[];
  }

  // API-derived types (not direct Pydantic mirrors)
  interface SearchResult {
    source_id: string;
    column_name: string;
    description: string;
    [key: string]: unknown;   // FTS5 may return additional fields
  }

  interface Caution {
    key: string;
    title: string;
    content: string;
    category: KnowledgeCategory;
    importance: KnowledgeImportance;
    affects_columns: string[];
    [key: string]: unknown;
  }
  ```
- **Dependencies**: なし
- **Reuses**: SPEC-4a Pydantic モデル（`models/design.py`, `models/catalog.py`,
  `models/review.py`）を TypeScript に変換

### Component 4: `DesignsPage.tsx`

- **Purpose**: Designs タブのメインページ。マスター・ディテール構成
- **Interfaces**:
  ```tsx
  function DesignsPage(): JSX.Element
  // State:
  //   designs: Design[]          — API から取得した全デザイン
  //   selectedId: string | null  — 選択中のデザイン ID
  //   statusFilter: string       — ステータスフィルタ値
  //   loading: boolean
  //   error: string | null
  //
  // Layout:
  //   ┌─────────────────────────────────────────┐
  //   │ [Filter: All ▼]          [+ New Design] │
  //   │ ┌─────────────────────────────────────┐ │
  //   │ │ DataTable (designs list)            │ │
  //   │ └─────────────────────────────────────┘ │
  //   │ ┌─────────────────────────────────────┐ │
  //   │ │ DesignDetail (if selectedId)        │ │
  //   │ └─────────────────────────────────────┘ │
  //   └─────────────────────────────────────────┘
  ```
- **Dependencies**: `api/client.ts`, `DesignDetail`, `DataTable`, `StatusBadge`,
  `EmptyState`, `ErrorBanner`, shadcn/ui `Select`, `Button`, `Dialog`
- **Reuses**: なし（新規）

### Component 5: `DesignDetail.tsx`

- **Purpose**: 選択されたデザインの詳細表示。サブタブ (Overview / Review / Knowledge) を持つ
- **Interfaces**:
  ```tsx
  interface DesignDetailProps {
    designId: string;
    onDesignUpdated: () => void;  // 親リストの再取得トリガー
  }
  function DesignDetail(props: DesignDetailProps): JSX.Element
  // Sub-tabs rendered as separate child components:
  //   OverviewPanel  — design fields display (JsonTree for dict fields)
  //   ReviewPanel    — submit button, comments list, add comment form
  //   KnowledgePanel — extract preview, save button
  // Each panel is a separate function component in the same file,
  // keeping DesignDetail.tsx as orchestrator (~150 lines) with panels (~60 lines each)
  ```
- **Dependencies**: `api/client.ts`, `JsonTree`, `StatusBadge`, `DataTable`,
  shadcn/ui `Tabs`, `Card`, `Button`, `Textarea`, `Select`
- **Reuses**: なし（新規）

### Component 6: `CatalogPage.tsx`

- **Purpose**: Catalog タブ。ソース一覧、スキーマ表示、検索、ドメイン知識表示
- **Interfaces**:
  ```tsx
  function CatalogPage(): JSX.Element
  // State:
  //   sources: DataSource[]
  //   selectedSourceId: string | null
  //   schema: ColumnSchema[]
  //   searchQuery: string
  //   searchResults: SearchResult[]
  //   knowledge: KnowledgeEntry[]
  //   loading: boolean
  //   error: string | null
  //
  // Layout:
  //   ┌──────────────────────────────────────┐
  //   │ [Search: ___________] [+ Add Source] │
  //   │ ┌──────────────────────────────────┐ │
  //   │ │ DataTable (sources list)         │ │
  //   │ └──────────────────────────────────┘ │
  //   │ ┌──────────────────────────────────┐ │
  //   │ │ Schema table (if selected)       │ │
  //   │ └──────────────────────────────────┘ │
  //   │ ┌──────────────────────────────────┐ │
  //   │ │ Domain Knowledge list            │ │
  //   │ └──────────────────────────────────┘ │
  //   └──────────────────────────────────────┘
  //
  // Internal sub-components (same file):
  //   SourceListSection  — source table + add dialog
  //   SchemaSection      — selected source schema table
  //   SearchSection      — search bar + results
  //   KnowledgeSection   — domain knowledge list
  ```
- **Dependencies**: `api/client.ts`, `DataTable`, `StatusBadge`, `EmptyState`,
  `ErrorBanner`, shadcn/ui `Input`, `Button`, `Dialog`, `Select`
- **Reuses**: なし（新規）

### Component 7: `RulesPage.tsx`

- **Purpose**: Rules タブ。プロジェクトコンテキスト表示 + Cautions 検索
- **Interfaces**:
  ```tsx
  function RulesPage(): JSX.Element
  // State:
  //   context: RulesContext | null
  //   tableNames: string
  //   cautions: Caution[]
  //   loading: boolean
  //   error: string | null
  //
  // Layout:
  //   ┌──────────────────────────────────────┐
  //   │ Sources (N) | Knowledge (N) | Rules  │
  //   │ ┌──────────────────────────────────┐ │
  //   │ │ Context sections (collapsible)   │ │
  //   │ └──────────────────────────────────┘ │
  //   │ ┌──────────────────────────────────┐ │
  //   │ │ [Table names: ___] [Search]      │ │
  //   │ │ Cautions results                 │ │
  //   │ └──────────────────────────────────┘ │
  //   └──────────────────────────────────────┘
  ```
- **Dependencies**: `api/client.ts`, `DataTable`, `EmptyState`, `ErrorBanner`,
  shadcn/ui `Input`, `Button`, `Card`
- **Reuses**: なし（新規）

### Component 8: `HistoryPage.tsx`

- **Purpose**: History タブ。全デザインの最近の変更タイムライン + レビュー履歴展開
- **Interfaces**:
  ```tsx
  function HistoryPage(): JSX.Element
  // State:
  //   designs: Design[]           — updated_at 降順ソート
  //   expandedId: string | null   — 展開中のデザイン ID
  //   comments: ReviewComment[]   — 展開中デザインのコメント
  //   loading: boolean
  //   error: string | null
  ```
- **Dependencies**: `api/client.ts`, `StatusBadge`, `EmptyState`, `ErrorBanner`,
  shadcn/ui `Card`
- **Reuses**: `listDesigns()` と `listComments()` を組み合わせて History を構成
  （新規 API 不要）

### Component 9: Shared UI Components

- **`DataTable`**:
  ```tsx
  interface DataTableProps<T> {
    data: T[];
    columns: { key: keyof T; label: string; render?: (value: T[keyof T], row: T) => ReactNode }[];
    onRowClick?: (row: T) => void;
    selectedRow?: (row: T) => boolean;
  }
  ```
  shadcn/ui `Table` をラップ。4ページで使用

- **`StatusBadge`**:
  ```tsx
  interface StatusBadgeProps {
    status: DesignStatus;
  }
  ```
  カラーマッピング: draft=gray, active=blue, pending_review=yellow,
  supported=green, rejected=red, inconclusive=orange

- **`EmptyState`**:
  ```tsx
  interface EmptyStateProps {
    message: string;
    action?: { label: string; onClick: () => void };
  }
  ```

- **`ErrorBanner`**:
  ```tsx
  interface ErrorBannerProps {
    message: string;
    onRetry?: () => void;
  }
  ```
  shadcn/ui `Alert` ベース。再試行ボタン付き

- **`JsonTree`**:
  ```tsx
  interface JsonTreeProps {
    data: Record<string, unknown> | Record<string, unknown>[];
    defaultExpanded?: boolean;
  }
  ```
  `metrics`, `explanatory`, `chart`, `next_action`, `connection` の表示用。
  折りたたみ可能な JSON ツリービュー。外部ライブラリ不要、再帰レンダリングで実装

## Data Models

SPEC-4b では新規データモデルを作成しない。`types/api.ts` で Python Pydantic モデルの
TypeScript ミラーを定義する（Component 3 参照）。

### API レスポンスと TypeScript 型の対応

| Python Model | TypeScript Type | 使用場所 |
|---|---|---|
| `AnalysisDesign` | `Design` | DesignsPage, DesignDetail, HistoryPage |
| `DataSource` | `DataSource` | CatalogPage |
| `ColumnSchema` | `ColumnSchema` | CatalogPage (schema) |
| `ReviewComment` | `ReviewComment` | DesignDetail (Review tab), HistoryPage |
| `DomainKnowledgeEntry` | `KnowledgeEntry` | DesignDetail (Knowledge tab), CatalogPage, RulesPage |
| `DesignStatus` (enum) | `DesignStatus` (union type) | StatusBadge |
| `SourceType` (enum) | `SourceType` (union type) | CatalogPage |

## Error Handling

### Error Scenarios

1. **API 通信エラー（ネットワーク）**
   - Handling: `api/client.ts` の `fetch()` で `TypeError` をキャッチ → `ApiError` に変換
   - User Impact: `ErrorBanner` に「サーバーに接続できません」+ 再試行ボタン

2. **API エラーレスポンス（4xx/5xx）**
   - Handling: `api/client.ts` で `!res.ok` を検出 → `{error}` body をパースして `ApiError` を throw
   - User Impact: `ErrorBanner` にサーバーからのエラーメッセージを表示

3. **デザイン未存在（404）**
   - Handling: `getDesign()` が 404 → DesignDetail でエラー表示
   - User Impact: 「指定されたデザインが見つかりません」

4. **無効なフォーム入力**
   - Handling: フロントエンドでバリデーション（必須項目チェック）、送信前にブロック
   - User Impact: インラインエラーメッセージ（「タイトルは必須です」等）

5. **JSON パースエラー（connection フィールド）**
   - Handling: `JSON.parse()` の try-catch でバリデーション
   - User Impact: 「有効な JSON を入力してください」

6. **バックエンド未起動**
   - Handling: 初回 `healthCheck()` 失敗 → 全ページで接続エラー表示
   - User Impact: 「バックエンドサーバーが起動していません。`uvx insight-blueprint` を実行してください」

## Testing Strategy

### Unit Testing

SPEC-4b ではフロントエンド単体テストを実装しない。

**根拠**: このフロントエンドの責務は「API を呼んで表示する」のみであり、ビジネスロジックは
全て Python バックエンド側にある。SPEC-4a の 341 テストがビジネスロジックを十分にカバーしている。
フロントエンドのユニットテストを書いても ROI が低い。

### Integration Testing

**手動検証チェックリスト**（各タブの基本操作を手動で確認）:
- Designs: 一覧表示 → フィルタ → 作成 → 詳細展開 → レビュー → コメント → 知識抽出
- Catalog: ソース一覧 → スキーマ表示 → ソース追加 → 検索 → 知識表示
- Rules: コンテキスト表示 → Cautions 検索
- History: タイムライン表示 → レビュー履歴展開

### End-to-End Testing

v1 では Playwright 等の自動 E2E テストは実装しない。
将来的にリグレッション頻度が上がった段階で導入を検討する。

### Build Verification

- `npm run build` が TypeScript コンパイルエラーゼロで完了すること
- `poe build-frontend` で `src/insight_blueprint/static/` にビルド成果物が出力されること
- ビルド済みの SPA が FastAPI の StaticFiles mount で正しく配信されること

## Known Constraints

### Vite Dev Server と FastAPI の分離

開発時は Vite dev server (port 5173) と FastAPI (port 3000) を別プロセスで起動する必要がある。
Vite proxy (`/api/*` → `localhost:3000`) により CORS を回避する。

本番時は `npm run build` で `static/` にビルドし、FastAPI が同一オリジンで配信する。

### shadcn/ui + Tailwind CSS v4

shadcn/ui は Tailwind CSS v4 と完全互換。ただし v3 とは設定方法が異なる:
- `tailwind.config.js` は不要（CSS `@theme {}` ブロックで設定）
- `@tailwind` ディレクティブは廃止（`@import "tailwindcss"` に統一）
- `npx shadcn@latest init` で v4 対応設定が自動生成される
- `@` パスエイリアスが `tsconfig.json` と `vite.config.ts` の両方に必要

### dict フィールドの表示

`Design.metrics`, `Design.explanatory`, `Design.chart`, `Design.next_action`,
`DataSource.connection` は Python 側で untyped dict。フロントエンドでは `JsonTree`
コンポーネントで汎用的に表示する。構造固有の UI は v1 では作らない。

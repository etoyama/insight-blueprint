# SPEC-4b: webui-frontend — Requirements

> **Spec ID**: SPEC-4b
> **Feature Name**: webui-frontend
> **Status**: draft
> **Created**: 2026-02-28
> **Depends On**: SPEC-4a (webui-backend)

---

## Introduction

SPEC-4a で構築した REST API (18 endpoints) を消費する React フロントエンドを実装する。
4タブダッシュボード（Designs / Catalog / Rules / History）により、データサイエンティストが
ブラウザから分析設計の管理・レビュー・ドメイン知識の閲覧を行えるようにする。

## Alignment with Product Vision

- **MCP + WebUI によるEDA支援**: CLI (MCP) だけでなくブラウザからも同じ操作が可能になり、
  非エンジニアのアナリストにもアクセスしやすい GUI を提供する
- **Zero-install (`uvx insight-blueprint`)**: Vite でビルドした成果物を `static/` に配置し、
  SPEC-4a のビルドパイプライン（hatch artifacts）で wheel に同梱。エンドユーザーに Node.js 不要
- **Roadmap 進行**: SPEC-4b 完了で WebUI が全機能利用可能になり、SPEC-5 (skills-distribution)
  への前提条件を満たす

## Requirements

### Requirement 1: Application Shell & Navigation

**User Story:** データサイエンティストとして、ブラウザでダッシュボードを開いたとき、
4つのタブ（Designs / Catalog / Rules / History）を切り替えて各機能にアクセスしたい。

**FR-1: Application Shell**
- `App.tsx` にヘッダー（アプリ名 "Insight Blueprint"）+ タブバー + メインコンテンツ領域を配置
- タブは Designs / Catalog / Rules / History の4つ
- 初期表示タブは Designs

**FR-2: Tab Navigation**
- タブ切り替えは `useState` で管理（react-router 不要）
- URL の `?tab=` パラメータでタブ状態を保持（ブラウザリロード時に復元）
- タブ切り替え時に URL パラメータを更新（`history.replaceState`）

**FR-3: API Client Layer**
- `api/client.ts` に全 REST API 呼び出し関数を集約
- ベース URL は空文字列（同一オリジン配信）
- 開発時は Vite proxy で `/api/*` を FastAPI (localhost:3000) に転送
- エラーレスポンス (`{error: string}`) を統一的にハンドリング
- 全関数に TypeScript 型定義（`types/api.ts`）

**FR-4: Shared UI Components**
- `DataTable`: 汎用テーブルコンポーネント（shadcn/ui Table ベース）
- `StatusBadge`: `DesignStatus` の値に応じた色付きバッジ
- `EmptyState`: データ0件時のプレースホルダ表示
- `ErrorBanner`: API エラーの統一表示（shadcn/ui Alert ベース）

#### Acceptance Criteria

1. WHEN ブラウザで `/` を開く THEN ヘッダー + 4タブ + Designs タブ内容が表示される
2. WHEN タブを切り替える THEN 対応するページコンテンツが表示される
3. WHEN `?tab=catalog` 付きで URL を開く THEN Catalog タブが初期表示される
4. WHEN API 呼び出しが失敗する THEN `ErrorBanner` でエラーメッセージが表示される
5. WHEN データが0件 THEN `EmptyState` が表示される

### Requirement 2: Designs Tab (Master-Detail)

**User Story:** データサイエンティストとして、分析設計の一覧を見て、選択した設計の
詳細・レビュー・知識抽出を1つの画面で操作したい。

**FR-5: Design List (Master)**
- `GET /api/designs` で全デザイン一覧を取得・表示
- ステータスフィルタ（All / draft / active / pending_review / supported / rejected / inconclusive）
- 各行に: タイトル、ステータスバッジ、更新日時
- 行クリックで詳細パネルを展開

**FR-6: Design Detail (Detail)**
- `GET /api/designs/{id}` で選択デザインの詳細を取得
- 表示項目: title, hypothesis_statement, hypothesis_background, status, theme_id,
  metrics, explanatory, chart, source_ids, next_action, created_at, updated_at
- `metrics`, `explanatory`, `chart`, `next_action` は JSON ツリー表示（折りたたみ可能）

**FR-7: Design Create**
- "New Design" ボタンでダイアログ（shadcn/ui Dialog）を開く
- 入力: title (必須), hypothesis_statement (必須), hypothesis_background (必須),
  theme_id (任意、デフォルト "DEFAULT")
- `POST /api/designs` で作成、成功後にリストを再取得

**FR-8: Design Sub-tabs**
- 詳細パネル内にサブタブ: Overview / Review / Knowledge
- **Overview**: FR-6 の詳細情報表示
- **Review**: FR-9, FR-10 のレビュー機能
- **Knowledge**: FR-11 の知識抽出機能

**FR-9: Review — Submit & Comments**
- "Submit for Review" ボタン: `POST /api/designs/{id}/review`（status が `active` の場合のみ有効）
- コメント一覧: `GET /api/designs/{id}/comments` でレビューコメントを時系列表示
- 各コメント: reviewer, comment, status_after (バッジ), created_at

**FR-10: Review — Add Comment**
- コメント追加フォーム: comment (テキストエリア), status (セレクト), reviewer (任意)
- status の選択肢: supported / rejected / inconclusive / active
- `POST /api/designs/{id}/comments` で送信、成功後にコメントリストを再取得

**FR-11: Knowledge — Extract & Save**
- "Extract Knowledge" ボタン: `POST /api/designs/{id}/knowledge` (body なし) でプレビュー取得
- プレビュー表示: 抽出されたエントリ一覧（key, title, content, category, importance）
- "Save Knowledge" ボタン: `POST /api/designs/{id}/knowledge` (body あり) で保存
- 保存成功後に確認メッセージ表示

#### Acceptance Criteria

1. WHEN Designs タブを開く THEN 全デザイン一覧がテーブルに表示される
2. WHEN ステータスフィルタを選択する THEN 該当ステータスのデザインのみ表示される
3. WHEN デザイン行をクリックする THEN 詳細パネルが展開し Overview サブタブが表示される
4. WHEN "New Design" ボタンをクリックする THEN 作成ダイアログが開く
5. WHEN 必須項目を入力して送信する THEN デザインが作成され一覧に反映される
6. WHEN Review サブタブを開く THEN コメント一覧と操作ボタンが表示される
7. WHEN active なデザインで "Submit for Review" THEN ステータスが pending_review に変わる
8. WHEN コメントを追加する THEN コメントリストに反映され、デザインのステータスが更新される
9. WHEN "Extract Knowledge" をクリックする THEN 抽出プレビューが表示される
10. WHEN "Save Knowledge" をクリックする THEN 知識エントリが保存され確認が表示される
11. WHEN 非 active なデザインで "Submit for Review" THEN ボタンが無効化されている

### Requirement 3: Catalog Tab

**User Story:** データサイエンティストとして、登録されたデータソースの一覧・スキーマ・
ドメイン知識を閲覧し、新しいソースを追加したい。

**FR-12: Source List**
- `GET /api/catalog/sources` でソース一覧を取得・表示
- 各行に: name, type (バッジ), description, tags, updated_at
- 行クリックで詳細（スキーマ）を表示

**FR-13: Source Detail — Schema**
- `GET /api/catalog/sources/{id}/schema` でカラムスキーマを取得
- テーブル表示: name, type, description, nullable, unit, examples

**FR-14: Source Add**
- "Add Source" ボタンでダイアログを開く
- 入力: source_id (必須), name (必須), type (セレクト: csv/api/sql), description (必須),
  connection (JSON エディタ)
- `POST /api/catalog/sources` で追加、成功後にリストを再取得

**FR-15: Catalog Search**
- 検索バー: `GET /api/catalog/search?q={query}` で全文検索
- 結果表示: マッチしたカラム・ソース情報
- ソースフィルタ（任意）: `&source_id=` で絞り込み

**FR-16: Domain Knowledge List**
- `GET /api/catalog/knowledge` で全ドメイン知識エントリを取得・表示
- 各エントリ: key, title, content, category (バッジ), importance (バッジ), affects_columns

#### Acceptance Criteria

1. WHEN Catalog タブを開く THEN ソース一覧がテーブルに表示される
2. WHEN ソース行をクリックする THEN カラムスキーマがテーブルに表示される
3. WHEN "Add Source" で有効な情報を入力して送信する THEN ソースが追加され一覧に反映される
4. WHEN 検索バーにクエリを入力する THEN 全文検索結果が表示される
5. WHEN ドメイン知識セクションを表示する THEN 全エントリが category・importance 付きで表示される

### Requirement 4: Rules Tab

**User Story:** データサイエンティストとして、蓄積されたドメイン知識・ルール・注意事項を
一覧で確認し、特定テーブルに関連する注意事項を検索したい。

**FR-17: Project Context**
- `GET /api/rules/context` でプロジェクトコンテキストを取得・表示
- 3セクション構成:
  - Sources: ソース一覧サマリー（total_sources 件）
  - Knowledge: ドメイン知識一覧（total_knowledge 件）
  - Rules: ルール一覧（total_rules 件）

**FR-18: Cautions Search**
- テーブル名入力フィールド（カンマ区切り）
- "Search Cautions" ボタン: `GET /api/rules/cautions?table_names={names}`
- 結果表示: 該当する注意事項の一覧

#### Acceptance Criteria

1. WHEN Rules タブを開く THEN プロジェクトコンテキスト（Sources / Knowledge / Rules）が表示される
2. WHEN テーブル名を入力して検索する THEN 関連する注意事項が表示される
3. WHEN 知識エントリが0件 THEN EmptyState が表示される

### Requirement 5: History Tab

**User Story:** データサイエンティストとして、最近のデザイン変更やレビュー活動を
時系列で確認し、プロジェクト全体の進捗を把握したい。

**FR-19: Recent Activity Timeline**
- `GET /api/designs` で全デザインを取得し、`updated_at` の降順でソート表示
- 各エントリ: title, status (バッジ), updated_at
- 「更新日」と「作成日」を区別表示

**FR-20: Design Review History**
- タイムラインのエントリをクリックすると、該当デザインのレビューコメント履歴を展開
- `GET /api/designs/{id}/comments` でコメントを取得
- コメントごとに status_after の遷移を表示（ステータス変更のタイムライン）

#### Acceptance Criteria

1. WHEN History タブを開く THEN 全デザインが更新日時の降順で表示される
2. WHEN エントリをクリックする THEN レビューコメント履歴が展開される
3. WHEN デザインが0件 THEN EmptyState が表示される

### Requirement 6: shadcn/ui Integration & Build

**User Story:** 開発者として、shadcn/ui コンポーネントを Tailwind CSS v4 環境で使用し、
一貫性のある UI を構築したい。

**FR-21: shadcn/ui Setup**
- `npx shadcn@latest init` で shadcn/ui を初期化
- Tailwind CSS v4 対応の設定（CSS variables ベース）
- 使用コンポーネント: Tabs, Table, Badge, Button, Card, Dialog, Input, Textarea, Select, Alert

**FR-22: Development Server**
- `npm run dev` で Vite 開発サーバー起動（HMR 対応）
- Vite proxy: `/api/*` → `http://localhost:3000/api/*`（FastAPI バックエンド）
- 開発中は FastAPI (`uvx insight-blueprint`) と Vite dev server を別プロセスで起動

**FR-23: Production Build**
- `npm run build` で `src/insight_blueprint/static/` にビルド成果物を出力
- 既存の `poe build-frontend` タスクとの互換性を維持
- ビルド成果物は SPA 構成（`index.html` + JS/CSS バンドル）

#### Acceptance Criteria

1. WHEN `npm run dev` THEN Vite 開発サーバーが起動し HMR が動作する
2. WHEN 開発サーバーから `/api/health` にアクセスする THEN FastAPI の応答が proxy 経由で返る
3. WHEN `npm run build` THEN `src/insight_blueprint/static/` にビルド成果物が出力される
4. WHEN shadcn/ui コンポーネントを使用する THEN Tailwind CSS v4 のスタイルが正しく適用される
5. WHEN `poe build-frontend` THEN 既存パイプラインでビルドが成功する

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: 1ファイル = 1コンポーネント or 1モジュール
- **ファイル構成**: `pages/` (ページコンポーネント), `components/` (共通UI),
  `api/` (APIクライアント), `types/` (型定義) の4ディレクトリ
- **Component Isolation**: 各ページコンポーネントは自身の API 呼び出しと状態を持つ。
  ページ間で状態を共有しない
- **TypeScript strict mode**: `tsconfig.json` で `strict: true`
- 1ファイルあたり 200-400 行（最大 800 行）

### Performance

- 初期ロード: 3秒以内（localhost、ビルド済み static 配信時）
- タブ切り替え: 即座に描画（クライアントサイドのみ）
- API 呼び出し: SPEC-4a の 100ms 以内 + ネットワーク遅延（localhost なので無視可能）
- Vite ビルド: 30秒以内

### Security

- API 呼び出しは同一オリジン（localhost）のみ
- ユーザー入力は API リクエスト送信前にフロントエンドでバリデーション
- XSS 防止: React のデフォルトエスケーピングに依存（`dangerouslySetInnerHTML` 禁止）
- `connection` フィールドの JSON 入力: パース可能性の検証のみ（内容のバリデーションはバックエンド）

### Reliability

- API エラー時は `ErrorBanner` で表示（クラッシュしない）
- ネットワークエラー時は再試行ボタンを表示
- バックエンド未起動時は接続エラーメッセージを表示
- TypeScript コンパイルエラーゼロ

### Usability

- 日本語 UI（ラベル、プレースホルダ、エラーメッセージ）
- レスポンシブレイアウト（最小幅 1024px）
- ステータスバッジのカラーコーディング:
  draft=gray, active=blue, pending_review=yellow, supported=green, rejected=red, inconclusive=orange
- ローディング状態の表示（スピナー or スケルトン）
- フォームバリデーション: 必須項目の未入力時にインラインエラー表示

## Out of Scope

- WebSocket / リアルタイム更新（v1 はページ操作時の再取得で十分）
- 認証・認可（localhost シングルユーザー）
- ダークモード（v1 はライトモードのみ）
- i18n / 多言語対応（v1 は日本語固定）
- モバイル対応（最小幅 1024px、デスクトップ前提）
- フロントエンド単体テスト（ビジネスロジックは Python 側の 341 テストでカバー済み）
- デザインの編集（PUT /api/designs/{id}）— v1 は作成・閲覧・レビューに集中
- ソースの編集（PUT /api/catalog/sources/{id}）— v1 は追加・閲覧に集中
- ページネーション（データセットが小規模）
- オフライン対応

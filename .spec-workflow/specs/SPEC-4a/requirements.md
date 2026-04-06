# SPEC-4a: webui-backend — Requirements

> **Spec ID**: SPEC-4a
> **Feature Name**: webui-backend
> **Status**: draft
> **Created**: 2026-02-26
> **Depends On**: SPEC-1, SPEC-2, SPEC-3

---

## Introduction

既存の MCP ツール機能を REST API として公開する HTTP バックエンドを追加する。
サービス配線の共有レジストリ化、FastAPI アプリ（14 URL / 17 メソッド）、
uvicorn daemon thread、フロントエンドの wheel 同梱ビルドパイプラインを含む。

## Alignment with Product Vision

- **MCP + WebUI によるEDA支援**: REST API が全操作を HTTP 経由で公開し、
  ブラウザダッシュボード（SPEC-4b）から同じデータにアクセス可能にする
- **Zero-install (`uvx insight-blueprint`)**: hatch artifacts + poe タスクで
  ビルド済みフロントエンドを wheel に同梱。エンドユーザーに Node.js 不要
- **Roadmap 進行**: 旧 SPEC-4 を Backend/Frontend に2分割。SPEC-4b はこの
  REST API に依存する

## Requirements

### Requirement 1: Service Registry

**User Story:** 開発者として、MCP server (`server.py`) と HTTP server (`web.py`)
の両方が同じサービスインスタンスを共有できるよう、配線を一元管理したい。

**FR-1: Registry モジュール**
- `src/insight_blueprint/_registry.py` を新規作成
- module-level 変数: `design_service`, `catalog_service`, `review_service`,
  `rules_service`（全て初期値 `None`）
- typed getter: `get_design_service()` 等、未初期化時は `RuntimeError` を送出

**FR-2: server.py の移行**
- `server.py` の 4 つの module-level 変数と getter を削除
- 全 MCP tool 関数を `_registry.get_*_service()` 経由に変更

**FR-3: cli.py の配線変更**
- `_registry` への一括配線に変更:
  ```python
  import insight_blueprint._registry as registry
  registry.design_service = DesignService(project_path)
  ```

#### Acceptance Criteria

1. WHEN `_registry.get_design_service()` を配線前に呼ぶ THEN `RuntimeError` が発生する
2. WHEN `cli.py` が `_registry` に配線する THEN `server.py` と `web.py` の両方から同一インスタンスにアクセスできる
3. WHEN 既存テストを実行する THEN 全 183 テストが通る（import パス変更を除き修正不要）
4. WHEN `_registry.py` を確認する THEN サービス参照と getter のみで、ビジネスロジックを含まない

### Requirement 2: REST API Endpoints

**User Story:** フロントエンド開発者として、全操作を REST API で利用したい。

**FR-4: Design Endpoints**
- `GET /api/designs` — 一覧（`?status=` フィルタ任意）→ `{designs, count}`
- `POST /api/designs` — 作成 → 201 + `{design, message}`
- `GET /api/designs/{design_id}` — 取得 → `AnalysisDesign` or 404
- `PUT /api/designs/{design_id}` — 更新 → `AnalysisDesign` or 404

**FR-5: Catalog Endpoints**
- `GET /api/catalog/sources` — ソース一覧 → `{sources, count}`
- `POST /api/catalog/sources` — ソース追加 → 201 + `{source, message}`
- `GET /api/catalog/sources/{source_id}` — 取得 → `DataSource` or 404
- `PUT /api/catalog/sources/{source_id}` — 更新 → `DataSource` or 404
- `GET /api/catalog/sources/{source_id}/schema` — スキーマ取得 → `{source_id, columns}` or 404
- `GET /api/catalog/search?q={query}` — FTS5 検索（`&source_id=` 任意）→ `{query, results, count}`
- `GET /api/catalog/knowledge` — ドメイン知識一覧 → `{entries, count}`

**FR-6: Review Endpoints**
- `POST /api/designs/{design_id}/review` — レビュー提出 → `{design_id, status, message}` or error
- `GET /api/designs/{design_id}/comments` — コメント一覧 → `{design_id, comments, count}`
- `POST /api/designs/{design_id}/comments` — コメント追加 → `{comment_id, status_after, message}` or error
- `POST /api/designs/{design_id}/knowledge` — 知識抽出・保存
  - body なし → preview（抽出のみ、保存しない）
  - `{entries: [...]}` あり → 確認済みエントリを保存

**FR-7: Rules Endpoints**
- `GET /api/rules/context` — 蓄積されたドメイン知識・ルールの一覧取得
  - catalog 知識（`catalog/knowledge/*.yaml`）と review 抽出知識（`extracted_knowledge.yaml`）を集約して返す
  - Returns: `{sources, knowledge_entries, rules, total_sources, total_knowledge, total_rules}`
  - Maps to: `RulesService.get_project_context()`
- `GET /api/rules/cautions?design_id={id}` — 注意事項の提案（`&table_names=` 任意）
  - 指定テーブルに関連する注意事項を `affects_columns` マッチングで返す

**FR-8: エラーレスポンス**
- 統一フォーマット: `{error: str, detail?: str}`
- status code: 200/201/400/404/500
- `ValueError` → 400、`None` 返却 → 404、stack trace は公開しない

#### Acceptance Criteria

1. WHEN `GET /api/designs` THEN 全デザインが count 付きで返る
2. WHEN `POST /api/designs` + valid body THEN 201 で作成される
3. WHEN `GET /api/designs/nonexistent` THEN 404 + `{error}` が返る
4. WHEN `GET /api/catalog/search?q=keyword` THEN FTS5 検索結果が返る
5. WHEN `POST /api/designs/{id}/review` を非 active なデザインに THEN 400 が返る
6. WHEN `POST /api/designs/{id}/comments` + 無効な status THEN 400 が返る
7. WHEN `GET /api/rules/context` THEN 全ソースの集約知識が返る
8. WHEN `GET /api/rules/cautions?table_names=X,Y` THEN 該当する注意事項が返る
9. WHEN 予期しない例外が発生 THEN 500 + `{error: "Internal server error"}`（stack trace なし）
10. WHEN `POST /api/designs/{id}/knowledge` + body なし THEN 抽出 preview が返る
11. WHEN `POST /api/designs/{id}/knowledge` + `{entries}` THEN 保存されて確認が返る

### Requirement 3: HTTP Server & Process Model

**User Story:** データサイエンティストとして、`insight-blueprint` 起動時に
WebUI が自動で立ち上がり、ブラウザですぐにダッシュボードを開きたい。

**FR-9: FastAPI アプリケーション**
- `src/insight_blueprint/web.py` に FastAPI アプリを作成
- `static/` から静的ファイル配信（React ビルド成果物）
- `127.0.0.1` のみにバインド（外部アクセス不可）
- localhost 向け CORS middleware を設定

**FR-10: Daemon Thread 起動**
- `web.py` が `start_server(port: int = 3000) -> int` を公開:
  1. 指定ポートへのバインドを試行。失敗時は `socket.bind(('', 0))` で OS 自動割り当て
  2. `daemon=True` スレッドで uvicorn を起動
  3. 実際のポート番号を返す

**FR-11: CLI 統合**
- `cli.py` でサービス配線後、`mcp.run()` 前に `start_server()` を呼ぶ
- `--headless=False`（デフォルト）: `threading.Timer(1.5, webbrowser.open)` でブラウザ起動
- `--headless=True`: ブラウザ起動を抑制
- WebUI URL を stderr に出力（stdout は MCP stdio 専用）

**FR-12: Health Check**
- `GET /api/health` → `{status: "ok", version: str}`
- サービス初期化不要（常時応答可能）

#### Acceptance Criteria

1. WHEN `start_server(3000)` + port 3000 空き THEN port 3000 で起動
2. WHEN `start_server(3000)` + port 3000 使用中 THEN OS 割り当てポートで起動
3. WHEN `start_server()` 完了後 THEN `GET /api/health` が応答する
4. WHEN `--headless` なし THEN 1.5 秒後にブラウザが開く
5. WHEN `--headless` あり THEN ブラウザは開かない
6. WHEN MCP server 終了 THEN daemon thread も自動終了
7. WHEN `static/` にファイルがある THEN `GET /` で `index.html` が返る
8. WHEN `static/` が空（開発中）THEN `GET /` は 404（クラッシュしない）

### Requirement 4: Build Pipeline

**User Story:** 開発者として、React フロントエンドを Python wheel に同梱する
ビルドパイプラインを整備し、エンドユーザーに Node.js を要求しない配布を実現したい。

**FR-13: Hatch Artifacts 設定**
- `pyproject.toml` で `src/insight_blueprint/static/**` を wheel に含める
- `static/` は `.gitignore` 対象（ビルド成果物のみ）

**FR-14: Poe Build タスク**
- `build-frontend`: `cd frontend && npm install && npm run build`
  （出力先: `src/insight_blueprint/static/`）
- `build`: `build-frontend` → `uv build`（フルビルド）

**FR-15: Frontend Scaffold**
- `frontend/` に最小構成を作成:
  - `package.json`（React 19, Vite 6, Tailwind CSS, shadcn/ui）
  - `vite.config.ts`（`outDir: '../src/insight_blueprint/static'`）
  - `index.html` + `src/main.tsx`（プレースホルダ表示）
- SPEC-4b への引き渡しポイント

**FR-16: 依存追加**
- `fastapi>=0.115`, `uvicorn[standard]` を dependencies に追加
- `httpx>=0.27` を dev dependencies に追加（TestClient 用）

#### Acceptance Criteria

1. WHEN `poe build-frontend` 実行 THEN `src/insight_blueprint/static/` にビルド成果物が出力される
2. WHEN `poe build-frontend` 後に `uv build` THEN wheel に static ファイルが含まれる
3. WHEN ビルド済み wheel から `uvx insight-blueprint` THEN 静的ファイルが配信される
4. WHEN `frontend/` を確認 THEN 有効な Vite + React プロジェクトがある
5. WHEN `poe build` THEN frontend ビルド → Python パッケージビルドの順で実行される
6. WHEN Node.js なしで wheel をインストール THEN ビルド済み static が利用可能

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: `_registry.py` はサービス参照のみ、`web.py` は HTTP ルーティングのみ（薄いレイヤー）
- **3層分離**: web.py → core/ → storage/。web.py から storage/ への直接アクセス禁止
- **パターン再利用**: server.py と同じ getter ベースのサービスアクセスパターン
- 全関数に型注釈必須（`ty check` 通過）
- `ruff check` 通過、`web.py` と `_registry.py` のテストカバレッジ 80% 以上

### Performance

- 全 REST endpoint: 100ms 以内（localhost、シングルユーザー）
- `GET /api/catalog/search`: 200ms 以内（100 ソースまで）
- `start_server()`: 2 秒以内に完了

### Security

- `127.0.0.1` バインドのみ（外部アクセス不可）
- v1 は認証不要（localhost シングルユーザー）
- エラーレスポンスに内部パス・stack trace を含めない
- CORS は localhost origin のみ許可

### Reliability

- `daemon=True` でメインスレッド終了時に自動停止
- ポート競合時は OS 割り当てにフォールバック（クラッシュしない）
- `static/` 未配置時は 404（クラッシュしない）
- サービス未初期化時は全 endpoint が 500 + 明確なエラーを返す
- 既存 SPEC-1/2/3 テスト全通過（リグレッションなし）

### Usability

- 起動時に WebUI URL を stderr に出力
- デフォルトでブラウザ自動起動（`--headless` で抑制可）
- `poe build-frontend` / `poe build` は Node.js 未インストール時に明確なエラー
- 全 endpoint で統一 JSON フォーマット

## Out of Scope

- WebSocket（v1 はポーリングで十分）
- 認証・認可（localhost シングルユーザー）
- API バージョニング（v1 のみ）
- Rate limiting
- OpenAPI ドキュメントのカスタマイズ（FastAPI 自動生成で十分）
- フロントエンド実装（scaffold 以上は SPEC-4b）
- HTTPS/TLS（localhost のみ）
- API ページネーション（データセットが小規模）

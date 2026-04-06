# SPEC-4a: webui-backend — Tasks

> **Spec ID**: SPEC-4a
> **Status**: draft
> **Created**: 2026-02-27
> **Depends On**: SPEC-1, SPEC-2, SPEC-3

---

## Dependency Graph

```
1.1 ──→ 1.2 ──→ 2.1 ──→ 2.2 ──→ 2.3 ──→ 2.4 ──→ 2.5 ──┐
                  ↓                                        ↓
                 3.1 ──→ 3.2 ────────────────────────→ 5.1

4.1 (独立: 他タスクと並列可)
```

---

## 全体完了基準

| # | 基準 | 指標 |
|---|------|------|
| C1 | 全タスク完了 | 11/11 tasks marked `[x]` |
| C2 | 新規テスト通過 | 72 tests green |
| C3 | リグレッションなし | 既存 260 テスト全通過 |
| C4 | 品質ゲート通過 | `poe all` (ruff + ty + pytest) exit 0 |
| C5 | REST API 動作 | 18 endpoints (17 + health) 全応答 |
| C6 | 統合フロー通過 | `test_full_flow_create_to_knowledge` green |

## 全体確認手順

1. **品質ゲート**
   ```bash
   poe all
   ```
   exit 0、ruff 違反ゼロ、ty エラーゼロ、全テスト通過

2. **テスト数**
   ```bash
   uv run pytest --co -q | tail -1
   ```
   332 tests collected (260 既存 + 72 新規)

3. **カバレッジ**
   ```bash
   uv run pytest --cov=src/insight_blueprint/_registry --cov=src/insight_blueprint/web --cov-report=term-missing
   ```
   `_registry.py` と `web.py` 各 80% 以上

---

- [x] 1.1 `_registry.py` 新規作成 + テスト
  - File: `src/insight_blueprint/_registry.py` (新規), `tests/test_registry.py` (新規)
  - module-level 変数 4 つ（初期値 `None`）と typed getter 4 つを実装
  - 未初期化時に `RuntimeError` を送出
  - module 純度テスト: getter 以外の関数・クラスが存在しないことを検証
  - TDD: 9 テストを先に書く（Red → Green）
  - Purpose: サービス配線の一元管理モジュール。server.py と web.py の共有基盤
  - _Leverage: `server.py` 既存 getter パターン（`_design_service`, `get_design_service()` 等）_
  - _Requirements: FR-1, R1-AC1, R1-AC2, R1-AC4_
  - **完了基準**:
    - 4 つの module-level 変数と 4 つの getter が存在する
    - 未初期化 getter が `RuntimeError` を送出する（4 getter 全て）
    - 配線後の getter が同一インスタンスを返す（4 getter 全て）
    - module に getter 以外の関数・クラスが存在しない
    - 9 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_registry.py -v
    ```
    9 passed を確認
    ```bash
    uv run ruff check src/insight_blueprint/_registry.py && uv run ty check src/insight_blueprint/_registry.py
    ```
    違反ゼロ
  - _Prompt: Role: Python Developer with module design expertise | Task: Create `_registry.py` with 4 module-level service references (initial None) and 4 typed getters raising RuntimeError when uninitialized. Write 9 tests first (TDD): 4 uninitialized, 4 after-wiring, 1 module purity | Restrictions: No business logic. Use TYPE_CHECKING for service type imports. Only references + getters | Success: 9 tests pass, ruff + ty clean_

- [x] 1.2 server.py / cli.py / conftest.py の `_registry` 移行
  - File: `src/insight_blueprint/server.py` (変更), `src/insight_blueprint/cli.py` (変更), `tests/conftest.py` (変更), `tests/test_server.py` (変更)
  - `server.py`: module-level 変数 4 つと getter 4 つを削除。全 MCP tool を `_registry.get_*_service()` 経由に変更
  - `cli.py`: 配線先を `server._service` → `_registry.service` に変更
  - `conftest.py`: shared fixture の配線先を `_registry` 経由に変更
  - `test_server.py`: `_reset_service` fixture を `_registry` リセットに更新
  - Purpose: サービス配線を `_registry` に一本化し、web.py からも同一インスタンスにアクセス可能にする
  - _Leverage: 既存 `server._design_service` → `_registry.get_design_service()` の 1:1 置換_
  - _Requirements: FR-2, FR-3, R1-AC2, R1-AC3_
  - **完了基準**:
    - `server.py` から module-level サービス変数と getter が全て削除されている
    - `server.py` の全 MCP tool が `_registry.get_*_service()` を使用
    - `cli.py` が `_registry` 経由でサービスを配線
    - 既存 260 テスト全通過（リグレッションなし）
  - **確認手順**:
    ```bash
    uv run pytest -v
    ```
    260 passed を確認
    ```bash
    grep -c "get_design_service\|get_catalog_service\|get_review_service\|get_rules_service" src/insight_blueprint/server.py
    ```
    `_registry` 経由の getter 呼び出しが存在することを確認
    ```bash
    grep -c "_design_service\s*=" src/insight_blueprint/server.py
    ```
    module-level 代入が 0 件であることを確認
  - _Prompt: Role: Python Developer with refactoring expertise | Task: Migrate server.py from module-level service references to _registry.get_*_service(). Update cli.py wiring to _registry. Update conftest.py and test_server.py fixtures to reset _registry. All 260 existing tests must pass | Restrictions: Logic changes forbidden — import path changes only. Atomic migration (all files together) | Success: 260 existing tests pass, no module-level service references in server.py_

- [x] 2.1 FastAPI app 骨格 + 依存追加 + health check + error handler + CORS
  - File: `src/insight_blueprint/web.py` (新規), `pyproject.toml` (変更), `tests/test_web.py` (新規, 部分)
  - `pyproject.toml`: `fastapi>=0.115`, `uvicorn[standard]` を dependencies に、`httpx>=0.27` を dev dependencies に追加
  - `web.py`: FastAPI app、CORS middleware（localhost only）、custom HTTPException handler（`{"error": ...}` 形式）、`GET /api/health`
  - Pydantic request models 定義: `CreateDesignRequest`, `AddCommentRequest`, `AddSourceRequest`, `SaveKnowledgeRequest`
  - `test_web.py`: `_reset_registry` autouse fixture、`web_client` yield fixture
  - テスト: health 2 件 + error format 4 件 + CORS 2 件 = 8 件
  - Purpose: REST API 基盤を構築し、エラーハンドリングとセキュリティの土台を固める
  - _Leverage: server.py のエラーパターン（ValueError → 400, None → 404）_
  - _Requirements: FR-8, FR-9, FR-12, FR-16, R2-AC9, R3-AC3_
  - **完了基準**:
    - `fastapi`, `uvicorn[standard]`, `httpx` が依存に追加されている
    - `GET /api/health` が `{"status": "ok", "version": str}` を返す
    - health check がサービス未初期化でも 200 を返す
    - エラーレスポンスが `{"error": ...}` 形式（`{"detail": ...}` でない）
    - CORS が localhost origin のみ許可し、外部 origin を拒否する
    - 8 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web.py -v -k "health or error or cors"
    ```
    8 passed を確認
    ```bash
    uv run python -c "from insight_blueprint.web import app; print(app.title)"
    ```
    import 成功を確認
  - _Prompt: Role: Python Developer with FastAPI expertise | Task: Create web.py with FastAPI app, CORS middleware (localhost only), custom HTTPException handler converting detail to error format, health check endpoint returning status+version, Pydantic request models. Add dependencies to pyproject.toml. Write fixtures (\_reset\_registry autouse, web\_client yield with TestClient context manager) and 8 tests | Restrictions: Health check must work without service init. Error handler must convert ALL HTTPException. CORS must reject non-localhost | Success: 8 tests pass, health responds without services, errors use error format_

- [x] 2.2 Design endpoints 実装 + テスト
  - File: `src/insight_blueprint/web.py` (変更), `tests/test_web.py` (変更)
  - 4 endpoints: `GET /api/designs`、`POST /api/designs`、`GET /api/designs/{design_id}`、`PUT /api/designs/{design_id}`
  - Path パラメータ: `design_id: str = Path(pattern=r"[a-zA-Z0-9_-]+")`
  - `GET` は `?status=` フィルタ任意。`POST` は 201 を返す
  - TDD: 10 テスト (#1-10)
  - Purpose: Design CRUD を REST API で公開
  - _Leverage: `DesignService.list_designs()`, `create_design()`, `get_design()`, `update_design()`_
  - _Requirements: FR-4, R2-AC1, R2-AC2, R2-AC3_
  - **完了基準**:
    - 4 Design endpoints が正常動作
    - 一覧が `{designs, count}` 形式、`?status=` フィルタが動作
    - 作成が 201 + `{design, message}` で返る
    - 不正 ID → 422、存在しない ID → 404 + `{"error": ...}`
    - 10 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web.py -v -k "test_list_designs or test_create_design or test_get_design or test_update_design"
    ```
    10 passed を確認
  - _Prompt: Role: Python Developer with FastAPI REST API expertise | Task: Implement 4 Design endpoints: list (?status filter), create (201), get, update. Path validation: Path(pattern=r"[a-zA-Z0-9_-]+"). Write 10 tests per TDD | Restrictions: Thin layer — delegate to _registry.get_design_service(). ValueError→400, None→404 | Success: 10 tests pass_

- [x] 2.3 Catalog endpoints 実装 + テスト
  - File: `src/insight_blueprint/web.py` (変更), `tests/test_web.py` (変更)
  - 7 endpoints: sources CRUD + schema + search + knowledge 一覧
  - `GET /api/catalog/search`: `q` 必須、`source_id` 任意（service 呼び出し後に post-filter）
  - TDD: 17 テスト (#11-27)
  - Purpose: Data Catalog 操作を REST API で公開
  - _Leverage: `CatalogService.list_sources()`, `add_source()`, `get_source()`, `update_source()`, `get_schema()`, `search()`, `get_knowledge()`_
  - _Requirements: FR-5, R2-AC4_
  - **完了基準**:
    - 7 Catalog endpoints が正常動作
    - search が `q` 必須 + `source_id` post-filter で動作
    - 重複 source 追加 → 400、必須フィールド欠落 → 422
    - 17 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web.py -v -k "source or schema or search or test_get_knowledge_list"
    ```
    17 passed を確認
  - _Prompt: Role: Python Developer with FastAPI REST API expertise | Task: Implement 7 Catalog endpoints: list sources, add (201), get, update, get schema, search (?q required, &source_id post-filter), get knowledge. Write 17 tests per TDD | Restrictions: search source_id is post-filter after service.search(). Duplicate source→400. Missing fields→422 via Pydantic | Success: 17 tests pass_

- [x] 2.4 Review endpoints 実装 + テスト
  - File: `src/insight_blueprint/web.py` (変更), `tests/test_web.py` (変更)
  - 4 endpoints: review 提出 + comments 一覧・追加 + knowledge (preview/save)
  - knowledge: body なし → preview（抽出のみ）、`{entries}` あり → save（永続化）
  - TDD: 12 テスト (#28-39)
  - Purpose: Review workflow を REST API で公開
  - _Leverage: `ReviewService.submit_for_review()`, `list_comments()`, `save_review_comment()`, `extract_domain_knowledge()`, `save_extracted_knowledge()`_
  - _Requirements: FR-6, R2-AC5, R2-AC6, R2-AC10, R2-AC11_
  - **完了基準**:
    - 4 Review endpoints が正常動作
    - 非 active デザインへの review → 400
    - 無効 status コメント → 400、存在しない design → 404
    - knowledge の preview / save が body 有無で正しく分岐
    - 12 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web.py -v -k "review or comment or knowledge_preview or knowledge_save or knowledge_not_found or knowledge_invalid"
    ```
    12 passed を確認
  - _Prompt: Role: Python Developer with FastAPI REST API expertise | Task: Implement 4 Review endpoints: submit review, list comments, add comment, knowledge (preview if no body, save if entries body). Write 12 tests per TDD | Restrictions: Non-active to 400, invalid status to 400, not found to 404. Preview must NOT persist. Save persists confirmed entries | Success: 12 tests pass_

- [x] 2.5 Rules endpoints 実装 + テスト
  - File: `src/insight_blueprint/web.py` (変更), `tests/test_web.py` (変更)
  - 2 endpoints: `GET /api/rules/context`、`GET /api/rules/cautions?table_names=X,Y`
  - `table_names` は必須パラメータ（カンマ区切り → list に split）
  - TDD: 4 テスト (#40-43)
  - Purpose: ルール・知識集約を REST API で公開
  - _Leverage: `RulesService.get_project_context()`, `suggest_cautions(table_names)`_
  - _Requirements: FR-7, R2-AC7, R2-AC8_
  - **完了基準**:
    - 2 Rules endpoints が正常動作
    - context が全ソースの集約知識を返す
    - cautions が `table_names` でフィルタリング
    - `table_names` 未指定 → 422
    - 4 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web.py -v -k "context or caution"
    ```
    4 passed を確認
  - _Prompt: Role: Python Developer with FastAPI REST API expertise | Task: Implement 2 Rules endpoints: GET /api/rules/context, GET /api/rules/cautions?table_names=X,Y (required, comma-split). Write 4 tests per TDD | Restrictions: table_names required→422 if missing. v1 ignores design_id (service takes table_names only). Thin layer | Success: 4 tests pass_

- [x] 3.1 ThreadedUvicorn + `start_server()` + static files + テスト
  - File: `src/insight_blueprint/web.py` (変更), `tests/test_web_integration.py` (新規)
  - `ThreadedUvicorn(uvicorn.Server)`: `install_signal_handlers` 空実装、`log_level="warning"`, `access_log=False`
  - `start_server(host, port)`: ポート probe → フォールバック → daemon thread → readiness polling → port 返却
  - `_server_instance` module-level 参照（テストの shutdown 用）
  - `StaticFiles` mount（`static/` 存在時のみ）
  - `_server_lifecycle` fixture: `should_exit = True` で確実停止
  - テスト: server lifecycle 5 件 + static 2 件 = 7 件 (integration #2-8)
  - Purpose: HTTP サーバーの daemon thread 起動と静的ファイル配信
  - _Leverage: design.md Component 3 (ThreadedUvicorn), Component 5 (readiness polling)_
  - _Requirements: FR-9, FR-10, R3-AC1, R3-AC2, R3-AC3, R3-AC6, R3-AC7, R3-AC8_
  - **完了基準**:
    - `start_server(port=0)` が有効なポートを返す
    - ポート競合時に OS 割り当てポートへフォールバック
    - 起動後 `GET /api/health` が応答
    - `should_exit = True` でスレッド終了
    - `static/index.html` 存在時に `GET /` で配信
    - `static/` 未配置時に 404（クラッシュしない）
    - 7 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web_integration.py -v -k "not full_flow"
    ```
    7 passed を確認
  - _Prompt: Role: Python Developer with uvicorn and threading expertise | Task: Implement ThreadedUvicorn (empty install_signal_handlers, log_level=warning, access_log=False), start_server (port probe→fallback→daemon thread→readiness poll→return port), StaticFiles mount (only if dir exists), _server_lifecycle fixture (should_exit=True cleanup). Write 7 tests | Restrictions: host default "127.0.0.1". socket.bind for probing. Readiness poll via server.started. daemon=True thread. Static mount must not crash when dir missing | Success: 7 tests pass, clean start/stop, no CI port conflicts_

- [x] 3.2 CLI 統合（headless, browser, stderr）+ テスト
  - File: `src/insight_blueprint/cli.py` (変更), `tests/test_web_cli.py` (新規)
  - サービス配線後・`mcp.run()` 前に `start_server()` を呼び出し
  - `--headless` フラグ追加（default False）
  - ブラウザ起動: `threading.Timer(1.5, webbrowser.open, args=[url]).start()`
  - WebUI URL を stderr に出力
  - テスト: 4 件 (CLI #1-4)。`webbrowser.open`, `threading.Timer` を mock
  - Purpose: CLI 起動時に HTTP サーバーを自動起動し、ブラウザでダッシュボードを開く
  - _Leverage: design.md Component 5 (CLI 統合シーケンス)_
  - _Requirements: FR-11, R3-AC4, R3-AC5_
  - **完了基準**:
    - `--headless` なしでブラウザ起動（`threading.Timer` 経由）
    - `--headless` ありでブラウザ非起動
    - stderr に WebUI URL (`http://127.0.0.1:<port>`) を出力
    - uvicorn が `127.0.0.1` にバインド（`0.0.0.0` でない）
    - 4 テスト全通過
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web_cli.py -v
    ```
    4 passed を確認
  - _Prompt: Role: Python Developer with CLI integration expertise | Task: Add --headless flag to cli.py, call start_server() after wiring before mcp.run(), output URL to stderr, conditionally start browser via threading.Timer(1.5). Write 4 tests with mocked webbrowser.open and threading.Timer | Restrictions: stdout reserved for MCP stdio. Default headless=False. Timer 1.5s delay. start_server before mcp.run() | Success: 4 tests pass_

- [x] 4.1 Frontend scaffold + ビルドパイプライン
  - File: `frontend/` (新規), `pyproject.toml` (変更), `.gitignore` (変更)
  - `frontend/`: `package.json` (React 19, Vite 6, Tailwind CSS), `vite.config.ts` (`outDir: '../src/insight_blueprint/static'`), `tailwind.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx` (placeholder)
  - `pyproject.toml`: hatch `artifacts` 設定 (`src/insight_blueprint/static/**`)、poe `build-frontend` / `build` タスク
  - `.gitignore`: `src/insight_blueprint/static/` を追加
  - Purpose: SPEC-4b のフロントエンド開発基盤と wheel 同梱ビルドパイプラインを構築
  - _Leverage: design.md Component 4 (scaffold), Component 6 (build pipeline)_
  - _Requirements: FR-13, FR-14, FR-15, R4-AC1〜AC6_
  - **完了基準**:
    - `frontend/` に有効な Vite + React プロジェクトが存在
    - `cd frontend && npm install && npm run build` が成功（Node.js 環境）
    - ビルド成果物が `src/insight_blueprint/static/` に出力される
    - `pyproject.toml` に hatch artifacts と poe タスクが設定されている
    - `static/` が `.gitignore` に含まれている
  - **確認手順**:
    ```bash
    cd frontend && npm install && npm run build && ls ../src/insight_blueprint/static/index.html
    ```
    `index.html` の存在を確認
    ```bash
    grep -A2 "\[tool.hatch.build.targets.wheel\]" pyproject.toml
    ```
    artifacts 設定を確認
    ```bash
    grep "static" .gitignore
    ```
    `.gitignore` に含まれることを確認
  - _Prompt: Role: Frontend Developer with Vite + React expertise | Task: Create minimal frontend scaffold: package.json (React 19, Vite 6, Tailwind CSS), vite.config.ts (outDir '../src/insight_blueprint/static'), index.html, src/main.tsx (placeholder). Add hatch artifacts and poe tasks to pyproject.toml. Add static/ to .gitignore | Restrictions: Minimal scaffold — real implementation is SPEC-4b. outDir must point to static/. poe build = build-frontend then uv build | Success: npm run build works, static/index.html produced, pyproject.toml configured_

- [x] 5.1 Full flow 統合テスト + リグレッション確認
  - File: `tests/test_web_integration.py` (変更)
  - `test_full_flow_create_to_knowledge`: Design 作成 → activate → review → comment → knowledge preview → save → rules context 検証の全フロー
  - 全 332 テスト（260 既存 + 72 新規）通過を確認
  - `poe all` で最終品質ゲート通過
  - Purpose: 全 endpoint の統合動作を検証し、リグレッションなしを最終確認
  - _Leverage: test-design.md Full Flow Test コード_
  - _Requirements: R2-AC1〜AC11, R1-AC3_
  - **完了基準**:
    - full flow テストが Design → Review → Knowledge → Rules の全フローを通過
    - 332 テスト全通過（260 既存 + 72 新規）
    - `poe all` が exit 0
  - **確認手順**:
    ```bash
    uv run pytest tests/test_web_integration.py::test_full_flow_create_to_knowledge -v
    ```
    1 passed を確認
    ```bash
    uv run pytest --co -q | tail -1
    ```
    332 tests collected を確認
    ```bash
    poe all
    ```
    exit 0 を確認
  - _Prompt: Role: QA Engineer with integration testing expertise | Task: Write test_full_flow_create_to_knowledge: POST designs → PUT activate → POST review → POST comments → POST knowledge (preview) → POST knowledge (save) → GET rules/context. Run poe all for final gate | Restrictions: Real YAML (no mocks). Verify round-trip data integrity. Do not modify existing tests | Success: Full flow passes, 332 total tests pass, poe all succeeds_

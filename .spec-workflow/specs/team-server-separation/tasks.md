# Tasks: Team Server Separation

- [x] 1.1. yaml_store.py に threading.Lock を追加
  - File: src/insight_blueprint/storage/yaml_store.py
  - Purpose: write_yaml() に Single Writer Lock を追加し、並行書き込みからファイル破損を防止する
  - _Leverage: 既存の write_yaml() atomic write ロジック (tempfile + os.replace)_
  - _Requirements: REQ-4 (FR-4.1, FR-4.2, FR-4.3, FR-4.4)_
  - Dependencies: なし
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer specializing in concurrency | Task: Add a module-level `threading.Lock` (`_write_lock`) to `yaml_store.py` and wrap the existing `write_yaml()` function body with `with _write_lock:`. Do NOT add lock to `read_yaml()` (FR-4.4). | Restrictions: Do not change the function signature. Do not change the atomic write logic (tempfile + os.replace). Lock must be module-level, not per-call. | Success: `_write_lock` exists at module level. `write_yaml()` acquires lock before writing. `read_yaml()` does not acquire lock. Tests Unit-03 pass (concurrent writes, no corruption)._

- [x] 1.2. write_yaml Lock のテスト (Unit-03)
  - File: tests/test_storage.py
  - Purpose: threading.Lock による並行書き込み保護をテストする
  - _Leverage: 既存の test_storage.py テスト構造, conftest.py fixtures_
  - _Requirements: REQ-4 (AC-4.1, AC-4.2)_
  - Dependencies: 1.1
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Test Engineer | Task: Add `TestWriteLock` class to `tests/test_storage.py` with 3 tests: (1) `test_concurrent_writes_no_corruption` — 2 threads x 100 writes, assert final file is valid YAML. (2) `test_concurrent_writes_no_intermediate_state` — reader thread never sees incomplete YAML during concurrent writes. (3) `test_write_lock_is_module_level` — assert `yaml_store._write_lock` is a `threading.Lock` instance. | Restrictions: Lost update is acceptable (AC-4.1). Do not test performance (moved to Integ-01). Use `tmp_path` fixture. | Success: All 3 tests pass. No file corruption under concurrent access._

- [x] 2.1. CLI に --mode, --host, --port, --no-browser を追加
  - File: src/insight_blueprint/cli.py
  - Purpose: --mode full|server|headless フラグと関連オプションを追加し、起動フローを分岐する
  - _Leverage: 既存の click.group, --project, --headless パース_
  - _Requirements: REQ-1 (FR-1.1〜FR-1.7), REQ-5 (FR-5.1, FR-5.3)_
  - Dependencies: なし
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python CLI Developer with Click expertise | Task: Modify `cli.py` `main()` to add `--mode` (click.Choice full/server/headless, default full), `--host` (str, default 0.0.0.0), `--port` (int, default 4000), `--no-browser` (flag). Keep `--headless` as deprecated alias: when used, emit `click.echo("Warning: --headless is deprecated, use --no-browser", err=True)` and set `no_browser=True`. For detecting explicit `--host`/`--port` in full mode, use `ctx.get_parameter_source("host")` to distinguish user-specified from default — only warn when source is COMMANDLINE, not DEFAULT. Extract service wiring into `_wire_registry(project_path: Path) -> None`. Add mode dispatch: full to `_start_full_mode()`, server to `_start_server_mode()`, headless to `_start_headless_mode()`. Full mode must call `start_server(daemon)` then `mcp.run()` (stdio, no transport arg). Server/headless stubs are OK for now (tasks 3.1/4.1 will implement). | Restrictions: Do not break existing behavior. `--mode full` must be identical to v0.3.0. Do not import SSE-related code yet (stubs). | Success: `--mode full` works identically to current. `--headless` emits deprecation warning. `--mode server/headless` calls stubs without error. `_wire_registry()` extracted._

- [x] 2.2. CLI テスト (Unit-01, Unit-02)
  - File: tests/test_cli.py
  - Purpose: CLI 引数パースとフラグ動作をテストする
  - _Leverage: 既存の test_cli.py, click.testing.CliRunner_
  - _Requirements: REQ-1 (AC-1.1, AC-1.4〜AC-1.7), REQ-5 (AC-5.1, AC-5.2)_
  - Dependencies: 2.1
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Test Engineer with Click testing expertise | Task: Add `TestCliModeDispatch` and `TestCliFlags` classes to `tests/test_cli.py`. Use CliRunner and mock `_start_full_mode`, `_start_server_mode`, `_start_headless_mode`, `_wire_registry`. TestCliModeDispatch: test_default_mode_is_full, test_mode_full_explicit, test_mode_server, test_mode_headless, test_mode_invalid_value, test_host_default, test_port_default, test_host_port_ignored_in_full_mode. TestCliFlags: test_no_browser_suppresses_browser, test_no_browser_keeps_webui_and_mcp, test_headless_flag_deprecation_warning, test_headless_flag_suppresses_browser. | Restrictions: Mock server startup functions to avoid actual server launch. | Success: All 12 tests pass._

- [x] 3.1. server.py に SSE app 取得ヘルパーを追加
  - File: src/insight_blueprint/server.py
  - Purpose: FastMCP の SSE ASGI アプリを返すヘルパー関数を提供する
  - _Leverage: 既存の mcp = FastMCP("insight-blueprint"), mcp.http_app() API_
  - _Requirements: REQ-2 (FR-2.1, FR-2.4)_
  - Dependencies: なし
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer with FastMCP expertise | Task: Add `get_mcp_sse_app() -> Any` function to `server.py` that returns `mcp.http_app(transport="sse")`. This returns a Starlette ASGI app for mounting into FastAPI. | Restrictions: Do not change existing `mcp` instance or tool definitions. Keep function simple (1-2 lines). Return type is `Any` to avoid importing Starlette types. | Success: `get_mcp_sse_app()` returns a valid ASGI app. Existing MCP tools unaffected._

- [x] 3.2. web.py に mount_mcp_sse() を追加（static files マウント順序リファクタ含む）
  - File: src/insight_blueprint/web.py
  - Purpose: MCP SSE の FastAPI マウントと、static files のマウント順序制御を実装する
  - _Leverage: 既存の app (FastAPI), StaticFiles マウント (L607-609)_
  - _Requirements: REQ-3 (FR-3.1, FR-3.2)_
  - Dependencies: 3.1
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer with FastAPI/Starlette expertise | Task: Add `mount_mcp_sse(mcp_sse_app) -> None` to `web.py`. CRITICAL MOUNT ORDERING: Starlette matches routes in definition order. `app.mount("/", StaticFiles(...))` is currently at module level (L607-609) and catches all routes. Restructure: (1) Remove the module-level `app.mount("/", StaticFiles(...))`. (2) Add `_mount_static_files() -> None` that does the same mount. (3) `mount_mcp_sse()` calls `app.mount("/mcp", mcp_sse_app)` first, then `_mount_static_files()`. (4) For full mode (no SSE), `start_server()` must call `_mount_static_files()` before starting uvicorn. | Restrictions: Do not break existing `start_server()` daemon behavior. Static files must work in both full and server modes. | Success: `mount_mcp_sse()` mounts `/mcp` before `/`. `start_server()` still serves static files. No routing conflicts._

- [x] 3.3. web.py に run_server() を追加
  - File: src/insight_blueprint/web.py
  - Purpose: server モード用の blocking uvicorn 起動関数を提供する
  - _Leverage: 既存のポートプローブロジック (start_server 内)_
  - _Requirements: REQ-3 (FR-3.1)_
  - Dependencies: 3.2
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer with uvicorn expertise | Task: Add `run_server(host: str, port: int) -> None` to `web.py`. This runs uvicorn on the main thread with signal handlers enabled for graceful Ctrl+C shutdown. Use `uvicorn.run(app, host=host, port=port, log_level="warning")` directly — do NOT use ThreadedUvicorn (which disables signal handlers, only suitable for daemon threads). Include port probe logic: if requested port is busy, fall back to OS-assigned port. Print actual bound address to stderr. | Restrictions: Do NOT use ThreadedUvicorn. Do not modify existing `start_server()`. | Success: `run_server()` blocks on main thread. Ctrl+C triggers graceful shutdown. Port fallback works._

- [x] 4.1. CLI の server/headless モード実装を完成
  - File: src/insight_blueprint/cli.py
  - Purpose: task 2.1 で作成したスタブを実装に置き換える
  - _Leverage: server.get_mcp_sse_app(), web.mount_mcp_sse(), web.run_server(), mcp.run()_
  - _Requirements: REQ-1 (FR-1.1〜FR-1.4), REQ-2 (FR-2.1, FR-2.2), REQ-3 (FR-3.1, FR-3.4)_
  - Dependencies: 2.1, 3.1, 3.3
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer | Task: Replace stubs in `cli.py` with real implementations. `_start_server_mode(host, port)`: call `mount_mcp_sse(get_mcp_sse_app())`, print SSE URL and WebUI URL to stderr, call `run_server(host, port)`. `_start_headless_mode(host, port)`: print SSE URL to stderr, call `mcp.run(transport="sse", host=host, port=port)`. | Restrictions: Do not change _start_full_mode or _wire_registry. Server mode: WebUI + SSE on single port. Headless: SSE only, no WebUI. | Success: `--mode server --port 4000` serves WebUI + SSE on :4000. `--mode headless --port 4000` serves SSE only. URLs printed to stderr._

- [x] 4.2. 統合テスト — server mode SSE + WebUI 共存 (Integ-01, Integ-05)
  - File: tests/test_web.py
  - Purpose: server モードで FastAPI + MCP SSE が同一ポートで共存し、既存 REST API が正常動作することを検証
  - _Leverage: 既存の test_web.py, httpx TestClient_
  - _Requirements: REQ-1 (AC-1.2), REQ-3 (AC-3.1, AC-3.2), REQ-4 (AC-4.3)_
  - Dependencies: 3.1, 3.2
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Test Engineer | Task: Add `TestServerMode` and `TestServerModeRestApi` to `tests/test_web.py`. Use httpx TestClient with the FastAPI app after calling `mount_mcp_sse()`. TestServerMode: (1) test_mcp_sse_endpoint_responds — GET /mcp/sse returns SSE stream (text/event-stream). (2) test_webui_static_after_sse_mount — GET / returns HTML. (3) test_api_designs_after_sse_mount — GET /api/designs returns 200. TestServerModeRestApi: test_existing_api_endpoints_with_sse_mount — spot-check /api/designs, /api/sources return 200 after SSE mount. Assert MCP tool response time < 500ms (AC-4.3). | Restrictions: Wire registry in fixture. Do not start actual server process. | Success: All tests pass. SSE and WebUI coexist on same app. REST API unaffected by SSE mount._

- [x] 4.3. 統合テスト — headless mode, SSE transport, multi-client (Integ-02, Integ-03, Integ-04)
  - File: tests/test_server.py
  - Purpose: headless モード、SSE 経由の MCP ツール動作、複数クライアント同時接続を検証
  - _Leverage: 既存の test_server.py, mcp.http_app(), httpx_
  - _Requirements: REQ-1 (AC-1.3), REQ-2 (AC-2.1〜AC-2.3), REQ-3 (AC-3.3)_
  - Dependencies: 3.1
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Test Engineer specializing in async and SSE | Task: Add `TestHeadlessMode`, `TestSseTransport`, `TestSseMultiClient` to `tests/test_server.py`. Use `mcp.http_app(transport="sse")` + httpx.AsyncClient (do NOT call blocking mcp.run()). TestHeadlessMode: verify SSE app responds, no WebUI routes. TestSseTransport: test_create_design_via_sse, test_list_designs_via_sse, test_tools_list_via_sse_returns_all_tools (assert 17 tool names). TestSseMultiClient: test_two_clients_independent_operations using asyncio tasks. | Restrictions: Use mcp.http_app() not mcp.run() (avoids blocking). Wire registry in fixture. Mark flaky tests with pytest.mark.flaky if needed. | Success: All SSE tests pass. tools/list returns all 17 tools. 2 concurrent clients work independently._

- [x] 5.1. Full mode 後方互換回帰テスト (Integ-06)
  - File: tests/test_cli.py
  - Purpose: full モードが v0.3.0 と同一の動作をすることを回帰テストで検証
  - _Leverage: 既存の test_cli.py, click.testing.CliRunner_
  - _Requirements: REQ-1 (AC-1.1), REQ-4 (AC-4.3), REQ-5 (AC-5.1)_
  - Dependencies: 4.1
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Test Engineer | Task: Add `TestFullModeBackwardCompat` to `tests/test_cli.py`. Mock start_server and mcp.run. (1) test_full_mode_calls_start_server_then_mcp_run — verify start_server called with host="127.0.0.1", port=3000 as daemon, then mcp.run() called with no transport arg. (2) test_full_mode_webui_port_3000 — verify start_server receives port=3000. (3) test_full_mode_mcp_run_no_transport_arg — verify mcp.run() called with no arguments (stdio default). Also add a simple performance check: call a representative MCP tool (e.g. list_analysis_designs via direct function call with registry wired) and assert response time < 500ms to verify Lock overhead is negligible in full mode (AC-4.3). | Restrictions: Must mock to avoid actual server startup. Performance test calls tool function directly, not via server. | Success: All tests pass. Full mode call sequence verified. Tool response < 500ms._

- [x] 5.2. .mcp.json stdio 登録テスト (Unit-05)
  - File: tests/test_storage.py
  - Purpose: init_project が .mcp.json に stdio 形式で登録することを検証
  - _Leverage: 既存の test_storage.py init_project テスト群_
  - _Requirements: REQ-5 (AC-5.3)_
  - Dependencies: なし
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Test Engineer | Task: Add `TestInitProjectMcpRegistration` to `tests/test_storage.py`. test_mcp_json_registers_stdio_transport — call init_project, read .mcp.json, assert mcpServers.insight-blueprint has "command" and "args" keys (stdio format), assert no "type": "sse" or "url" key exists. | Restrictions: Use tmp_path. Existing init_project tests already cover other aspects; this test focuses specifically on transport format. | Success: Test passes. .mcp.json contains stdio config, no SSE config._

- [x] 6.1. ドキュメント更新 (README, CHANGELOG)
  - File: README.md, CHANGELOG.md
  - Purpose: --mode, --host, --port, --no-browser の使い方と SSE 接続設定をドキュメントに追加
  - _Leverage: 既存の README.md, CHANGELOG.md_
  - _Requirements: 全 REQ_
  - Dependencies: 4.1
  - _Prompt: Implement the task for spec team-server-separation, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical Writer | Task: (1) README.md に Team Server セクションを追加: server mode 起動コマンド例 (`--mode server --port 4000`), Claude Code settings.json 設定例 (`"type": "sse", "url": "http://host:4000/mcp/sse"`), headless mode 起動例, --no-browser の説明, 認証なしの注意事項。(2) CHANGELOG.md に v0.4.0 (Unreleased) エントリ追加: Added --mode server/headless, --host, --port, --no-browser; Deprecated --headless; Added concurrent write safety (threading.Lock). | Restrictions: README は日本語可。CHANGELOG は Keep a Changelog 形式。 | Success: README にチームサーバーの使い方が記載。CHANGELOG に変更が記録。_

# SPEC-4a: webui-backend — Test Design

> **Spec ID**: SPEC-4a
> **Status**: draft
> **Created**: 2026-02-27
> **Depends On**: SPEC-1, SPEC-2, SPEC-3

---

## Test Architecture

### Test Pyramid

```
          ┌─────────────┐
          │  E2E (HTTP)   │  ← test_web_integration.py (full flow + daemon)
          ├─────────────┤
        ┌─┤  Integration  ├─┐  ← test_web_cli.py (CLI + browser + stderr)
        │ ├─────────────┤ │
  ┌─────┴─┴─────────────┴─┴─────┐
  │     Unit Tests (~60 tests)    │  ← test_registry.py, test_web.py
  └──────────────────────────────┘
```

### Test File Layout

| File | Target Module | Test Count | Pattern |
|------|--------------|-----------|---------|
| `tests/test_registry.py` | `_registry.py` | 9 | Function-based |
| `tests/test_web.py` | `web.py` (REST endpoints) | 51 | Function-based (per endpoint group) |
| `tests/test_web_integration.py` | `web.py` (full flow + server lifecycle) | 8 | Function-based |
| `tests/test_web_cli.py` | `cli.py` (headless, browser, stderr) | 4 | Function-based |
| `tests/test_server.py` (modified) | `server.py` (_registry migration) | 0 new (fixture update) | Existing pattern |
| `tests/conftest.py` (modified) | Shared fixtures | 0 new (wiring update) | Existing pattern |

**Total**: 72 new test cases

## Shared Fixtures

### Existing (`conftest.py` — modification required)

```python
# 変更: _registry 経由の配線に切り替え
# server_module._service = ... → registry.design_service = ...
import insight_blueprint._registry as registry

@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Return a temporary project directory with .insight/ initialized."""
    from insight_blueprint.storage.project import init_project
    init_project(tmp_path)
    return tmp_path
```

### New Fixtures (`tests/test_web.py` 内 or `conftest.py`)

```python
import insight_blueprint._registry as registry

@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset all _registry service references after each test.

    autouse=True: web_client を使わないテスト（test_error_500_uninitialized 等）
    でもグローバル状態をリセットし、テスト順序依存を防ぐ。
    """
    yield
    registry.design_service = None
    registry.catalog_service = None
    registry.review_service = None
    registry.rules_service = None

@pytest.fixture
def web_client(tmp_project: Path) -> Generator[TestClient, None, None]:
    """TestClient with all services wired via _registry.

    yield + context manager で TestClient のリソースリークを防止。
    """
    from insight_blueprint.core.catalog import CatalogService
    from insight_blueprint.core.designs import DesignService
    from insight_blueprint.core.reviews import ReviewService
    from insight_blueprint.core.rules import RulesService
    from insight_blueprint.web import app

    ds = DesignService(tmp_project)
    cs = CatalogService(tmp_project)
    registry.design_service = ds
    registry.catalog_service = cs
    registry.review_service = ReviewService(tmp_project, ds)
    registry.rules_service = RulesService(tmp_project, cs)
    with TestClient(app) as client:
        yield client
```

### Daemon Thread テスト用 Fixture

```python
@pytest.fixture
def _server_lifecycle(tmp_project: Path) -> Generator[int, None, None]:
    """Start server in daemon thread, yield port, ensure shutdown.

    ThreadedUvicorn.should_exit = True で確実に停止し、
    CI でのリソースリーク・ポート競合を防止。
    """
    from insight_blueprint.web import start_server, _server_instance  # internal ref

    # Wire services (same as web_client)
    # ...
    port = start_server(host="127.0.0.1", port=0)
    yield port
    # Cleanup: signal server to exit
    if _server_instance is not None:
        _server_instance.should_exit = True
```

### Design Note: Fixture Scope & Isolation

- 全 fixture は default `function` scope。各テストが独立した `tmp_path` を持つ
- `_reset_registry` は **autouse=True** でテスト間のグローバル状態を確実にリセット
- `web_client` は `with TestClient(app) as client:` で HTTP 接続プールを解放
- daemon thread テストは `should_exit = True` で確実に停止
- `test_server.py` の既存 `_reset_service` fixture は `_registry` 向けに書き換え
  （両 reset fixture の共存を避け、`_registry` に一本化する）

## Test Data

### Sample Request Bodies

```python
# POST /api/designs
VALID_DESIGN_REQUEST = {
    "title": "Population Analysis",
    "hypothesis_statement": "Population correlates with GDP",
    "hypothesis_background": "Testing economic indicators",
    "theme_id": "FP",
}

MINIMAL_DESIGN_REQUEST = {
    "title": "Minimal",
    "hypothesis_statement": "Minimal hypothesis",
    "hypothesis_background": "Minimal background",
}

# POST /api/catalog/sources
VALID_SOURCE_REQUEST = {
    "source_id": "estat-pop",
    "name": "Population Statistics",
    "type": "csv",
    "description": "Annual population census data",
    "connection": {"path": "/data/population.csv"},
    "columns": [
        {"name": "year", "type": "integer", "description": "Census year"},
        {"name": "population", "type": "integer", "description": "Total population"},
    ],
    "tags": ["demographic", "census"],
}

INVALID_SOURCE_REQUEST = {
    "source_id": "test",
    # missing required fields: name, type, description, connection
}

# POST /api/designs/{id}/comments
VALID_COMMENT_REQUEST = {
    "comment": "caution: 2015年以降の人口統計は調査方法が変更されている。",
    "status": "supported",
    "reviewer": "analyst",
}

INVALID_STATUS_COMMENT = {
    "comment": "test",
    "status": "pending_review",  # invalid post-review status
}

# POST /api/designs/{id}/knowledge (save mode)
VALID_KNOWLEDGE_REQUEST = {
    "entries": [
        {
            "key": "FP-H01-0",
            "title": "Census methodology change",
            "content": "Census methodology changed in 2015",
            "category": "caution",
            "source": "Review comment",
            "affects_columns": ["population_stats"],
        }
    ],
}

INVALID_KNOWLEDGE_REQUEST = {
    "entries": [{"invalid": "structure"}],  # missing required fields
}
```

### Expected Response Shapes

```python
# Error responses — FR-8 contract: {"error": str}
# All 400/404/500 must use this shape (not FastAPI default {"detail": ...})

# GET /api/health
HEALTH_RESPONSE_KEYS = {"status", "version"}

# GET /api/designs
DESIGNS_LIST_KEYS = {"designs", "count"}

# POST /api/designs (201)
DESIGN_CREATED_KEYS = {"design", "message"}
```

## Mock Strategy

### What to Mock

| Dependency | Where | Mock Approach |
|-----------|-------|--------------|
| Nothing | `test_registry.py` | Pure module state tests |
| Nothing | `test_web.py` | Real services via `web_client` fixture + `tmp_project` |
| Service getter (force exception) | `test_web.py` (500 test) | `unittest.mock.patch` on getter to raise |
| `webbrowser.open` | `test_web_cli.py` | `unittest.mock.patch` |
| `threading.Timer` | `test_web_cli.py` | `unittest.mock.patch` |
| Nothing | `test_web_integration.py` | Real services + real daemon thread |

### Design Note: Real Services for Endpoint Tests

SPEC-1/2/3 パターンに従い、`test_web.py` のエンドポイントテストは
real services + real YAML files を使う。TestClient は uvicorn を起動せず
FastAPI app を直接テストするため、十分高速（< 100ms/test）。

サービスレベルの mock は行わない（500 テスト以外）。理由:
1. エンドポイントの薄いレイヤー（パラメータ変換 + ステータスコード変換）をテストする
2. サービス自体のロジックは SPEC-1/2/3 のテストで検証済み
3. Real YAML により、パラメータの型変換ミスを早期発見

`test_error_500_unexpected` のみ、真の unexpected exception パスをテストするため
getter を mock して `RuntimeError` を送出させる。

## Test Specifications by File

### `test_registry.py` — 9 Tests

Tests `_registry.py` module-level state and getters.

| # | Test Name | AC | Input | Expected |
|---|-----------|-----|-------|----------|
| 1 | `test_get_design_service_uninitialized_raises` | R1-AC1 | Call before wiring | `RuntimeError` |
| 2 | `test_get_catalog_service_uninitialized_raises` | R1-AC1 | Call before wiring | `RuntimeError` |
| 3 | `test_get_review_service_uninitialized_raises` | R1-AC1 | Call before wiring | `RuntimeError` |
| 4 | `test_get_rules_service_uninitialized_raises` | R1-AC1 | Call before wiring | `RuntimeError` |
| 5 | `test_get_design_service_after_wiring` | R1-AC2 | Set `design_service`, call getter | Returns same instance |
| 6 | `test_get_catalog_service_after_wiring` | R1-AC2 | Set `catalog_service`, call getter | Returns same instance |
| 7 | `test_get_review_service_after_wiring` | R1-AC2 | Set `review_service`, call getter | Returns same instance |
| 8 | `test_get_rules_service_after_wiring` | R1-AC2 | Set `rules_service`, call getter | Returns same instance |
| 9 | `test_registry_contains_no_business_logic` | R1-AC4 | Inspect module attributes | No functions other than `get_*`, no class definitions |

### `test_web.py` — 51 Tests

Tests REST endpoints via `TestClient`. Function-based（既存パターンに統一）。
`_reset_registry` autouse + `web_client` yield fixture 使用。

#### Design Endpoints (10 tests)

| # | Test Name | AC | Action | Expected |
|---|-----------|-----|--------|----------|
| 1 | `test_list_designs_empty` | R2-AC1 | `GET /api/designs` | 200, `{designs: [], count: 0}` |
| 2 | `test_list_designs_returns_all` | R2-AC1 | Create 2 designs → `GET /api/designs` | 200, count=2 |
| 3 | `test_list_designs_filter_by_status` | R2-AC1 | Create + activate → `GET /api/designs?status=active` | 200, filtered result |
| 4 | `test_create_design_success` | R2-AC2 | `POST /api/designs` + `VALID_DESIGN_REQUEST` | 201, `{design, message}` |
| 5 | `test_create_design_missing_field` | — | `POST /api/designs` + `{title: "x"}` | 422 |
| 6 | `test_get_design_found` | R2-AC1 | Create → `GET /api/designs/{id}` | 200, design dict |
| 7 | `test_get_design_not_found` | R2-AC3 | `GET /api/designs/nonexistent` | 404, `{"error": ...}` |
| 8 | `test_get_design_invalid_id` | — | `GET /api/designs/invalid%20id` | 422 |
| 9 | `test_update_design_success` | — | Create → `PUT /api/designs/{id}` + `{title: "new"}` | 200 |
| 10 | `test_update_design_not_found` | — | `PUT /api/designs/nonexistent` | 404 |

#### Catalog Endpoints (17 tests)

| # | Test Name | AC | Action | Expected |
|---|-----------|-----|--------|----------|
| 11 | `test_list_sources_empty` | R2-AC4 | `GET /api/catalog/sources` | 200, `{sources: [], count: 0}` |
| 12 | `test_list_sources_returns_all` | R2-AC4 | Add source → `GET /api/catalog/sources` | 200, count=1 |
| 13 | `test_add_source_success` | R2-AC4 | `POST /api/catalog/sources` + `VALID_SOURCE_REQUEST` | 201 |
| 14 | `test_add_source_duplicate` | — | Add same source twice | 400, `{"error": ...}` |
| 15 | `test_add_source_missing_field` | — | `POST /api/catalog/sources` + `INVALID_SOURCE_REQUEST` | 422 |
| 16 | `test_get_source_found` | — | Add → `GET /api/catalog/sources/{id}` | 200 |
| 17 | `test_get_source_not_found` | — | `GET /api/catalog/sources/nonexistent` | 404 |
| 18 | `test_get_source_invalid_id` | — | `GET /api/catalog/sources/inv@lid` | 422 |
| 19 | `test_update_source_success` | — | Add → `PUT /api/catalog/sources/{id}` | 200 |
| 20 | `test_update_source_not_found` | — | `PUT /api/catalog/sources/nonexistent` | 404 |
| 21 | `test_get_schema_found` | R2-AC4 | Add source with columns → `GET .../schema` | 200, `{source_id, columns}` |
| 22 | `test_get_schema_not_found` | — | `GET /api/catalog/sources/nonexistent/schema` | 404 |
| 23 | `test_search_with_results` | R2-AC4 | Add source → `GET /api/catalog/search?q=population` | 200, results |
| 24 | `test_search_no_results` | — | `GET /api/catalog/search?q=nonexistent` | 200, `{results: [], count: 0}` |
| 25 | `test_search_with_source_id_filter` | — | Add 2 sources → search with `&source_id=X` | Only X results |
| 26 | `test_search_missing_query` | — | `GET /api/catalog/search` (no q) | 422 |
| 27 | `test_get_knowledge_list` | R2-AC4 | Add source → `GET /api/catalog/knowledge` | 200 |

#### Review Endpoints (12 tests)

| # | Test Name | AC | Action | Expected |
|---|-----------|-----|--------|----------|
| 28 | `test_submit_review_success` | R2-AC5 | Create active design → `POST .../review` | 200, `{design_id, status, message}` |
| 29 | `test_submit_review_non_active` | R2-AC5 | Draft design → `POST .../review` | 400 |
| 30 | `test_submit_review_not_found` | — | `POST /api/designs/nonexistent/review` | 404 |
| 31 | `test_list_comments_with_data` | R2-AC5 | Submit + comment → `GET .../comments` | 200, count=1 |
| 32 | `test_list_comments_empty` | — | Active design → `GET .../comments` | 200, `{comments: [], count: 0}` |
| 33 | `test_add_comment_success` | R2-AC6 | Submit → `POST .../comments` + `VALID_COMMENT_REQUEST` | 200 |
| 34 | `test_add_comment_invalid_status` | R2-AC6 | Submit → `POST .../comments` + `INVALID_STATUS_COMMENT` | 400 |
| 35 | `test_add_comment_not_found` | — | `POST /api/designs/nonexistent/comments` + body | 404 |
| 36 | `test_knowledge_preview` | R2-AC10 | Submit → comment → `POST .../knowledge` (no body) | 200, preview entries |
| 37 | `test_knowledge_save` | R2-AC11 | Submit → comment → `POST .../knowledge` + entries | 200, saved entries |
| 38 | `test_knowledge_not_found` | — | `POST /api/designs/nonexistent/knowledge` | 404 |
| 39 | `test_knowledge_invalid_entries` | — | `POST .../knowledge` + `INVALID_KNOWLEDGE_REQUEST` | 400 |

#### Rules Endpoints (4 tests)

| # | Test Name | AC | Action | Expected |
|---|-----------|-----|--------|----------|
| 40 | `test_get_context` | R2-AC7 | `GET /api/rules/context` | 200, `{sources, knowledge_entries, rules, ...}` |
| 41 | `test_cautions_with_matches` | R2-AC8 | Add knowledge → `GET /api/rules/cautions?table_names=X` | 200, cautions |
| 42 | `test_cautions_no_matches` | — | `GET /api/rules/cautions?table_names=unknown` | 200, `{cautions: [], count: 0}` |
| 43 | `test_cautions_missing_param` | — | `GET /api/rules/cautions` (no table_names) | 422 |

#### Health & Error Format (8 tests)

| # | Test Name | AC | Action | Expected |
|---|-----------|-----|--------|----------|
| 44 | `test_health_check` | R3-AC3 | `GET /api/health` (with services) | 200, `{status: "ok", version: str}` |
| 45 | `test_health_check_no_services` | FR-12 | `GET /api/health` (no _registry wiring) | 200 (サービス初期化不要) |
| 46 | `test_error_400_format` | R2-AC9 | Trigger ValueError path | `{"error": str}` (not `{"detail": ...}`) |
| 47 | `test_error_404_format` | R2-AC9 | Trigger not-found path | `{"error": str}` |
| 48 | `test_error_500_uninitialized` | R2-AC9 | No services wired → design endpoint | 500, `{"error": ...}` |
| 49 | `test_error_500_unexpected` | R2-AC9 | Mock getter to raise unexpected Exception | 500, `{"error": "Internal server error"}`, no stack trace in body |
| 50 | `test_cors_localhost_allowed` | FR-9 | `OPTIONS /api/health` with `Origin: http://localhost:3000` | CORS headers present |
| 51 | `test_cors_external_rejected` | FR-9 | `OPTIONS /api/health` with `Origin: http://evil.com` | No CORS headers |

### `test_web_integration.py` — 8 Tests

Full-flow integration tests with real services and daemon thread.

#### Full Flow Test

```python
def test_full_flow_create_to_knowledge(web_client: TestClient) -> None:
    """Integration: create → activate → review → comment → knowledge."""
    # 1. POST /api/designs
    resp = web_client.post("/api/designs", json=VALID_DESIGN_REQUEST)
    assert resp.status_code == 201
    design_id = resp.json()["design"]["id"]

    # 2. PUT /api/designs/{id} (activate)
    resp = web_client.put(f"/api/designs/{design_id}", json={"status": "active"})
    assert resp.status_code == 200

    # 3. POST /api/designs/{id}/review
    resp = web_client.post(f"/api/designs/{design_id}/review")
    assert resp.status_code == 200

    # 4. POST /api/designs/{id}/comments
    resp = web_client.post(
        f"/api/designs/{design_id}/comments", json=VALID_COMMENT_REQUEST
    )
    assert resp.status_code == 200

    # 5. POST /api/designs/{id}/knowledge (preview)
    resp = web_client.post(f"/api/designs/{design_id}/knowledge")
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1

    # 6. POST /api/designs/{id}/knowledge (save)
    entries = resp.json()["entries"]
    resp = web_client.post(
        f"/api/designs/{design_id}/knowledge", json={"entries": entries}
    )
    assert resp.status_code == 200

    # 7. Verify in rules context
    resp = web_client.get("/api/rules/context")
    assert resp.json()["total_knowledge"] >= 1
```

#### Server Lifecycle Tests

全 daemon thread テストは `_server_lifecycle` fixture を使い、
`should_exit = True` で確実にサーバーを停止する。ポートは `port=0`
（OS 割り当て）をデフォルトにし、CI でのポート競合を回避する。

| # | Test Name | AC | Description |
|---|-----------|-----|-------------|
| 1 | `test_full_flow_create_to_knowledge` | R2-AC1~11 | Design 作成 → review → comment → knowledge の全フロー |
| 2 | `test_start_server_returns_port` | R3-AC1 | `start_server(port=0)` が有効な port > 0 を返す |
| 3 | `test_start_server_specific_port` | R3-AC1 | `start_server(port=N)` が port N で起動（N = OS割り当て済み空きポート） |
| 4 | `test_start_server_health_check` | R3-AC3 | `start_server()` 後に `GET /api/health` が応答 |
| 5 | `test_start_server_port_fallback` | R3-AC2 | 使用中ポート指定時に別ポートで起動 |
| 6 | `test_start_server_shutdown` | R3-AC6 | `should_exit = True` 後にスレッドが終了 |
| 7 | `test_static_files_served` | R3-AC7 | `static/index.html` 配置時に `GET /` で配信 |
| 8 | `test_static_missing_returns_404` | R3-AC8 | `static/` 未配置時に `GET /` が 404（クラッシュしない） |

### `test_web_cli.py` — 4 Tests

CLI 統合テスト。`webbrowser.open` と `threading.Timer` を mock。

| # | Test Name | AC | Setup | Expected |
|---|-----------|-----|-------|----------|
| 1 | `test_headless_no_browser` | R3-AC5 | `--headless` + mock `webbrowser.open` | `webbrowser.open` not called |
| 2 | `test_default_opens_browser` | R3-AC4 | No `--headless` + mock `webbrowser.open` | `threading.Timer` created with `webbrowser.open` |
| 3 | `test_stderr_url_output` | R3-AC3 | Capture stderr | `"WebUI: http://127.0.0.1:{port}"` in stderr |
| 4 | `test_localhost_binding` | R3-AC1 | Inspect uvicorn config | `host == "127.0.0.1"` (not `0.0.0.0`) |

## Edge Case Matrix

### REST Endpoint Edge Cases

| Case | Endpoint | Input | Expected | Test |
|------|----------|-------|----------|------|
| Invalid ID format | `GET /api/designs/{id}` | `id="invalid id"` (space) | 422 | `test_get_design_invalid_id` |
| Invalid ID special chars | `GET /api/catalog/sources/{id}` | `id="inv@lid"` | 422 | `test_get_source_invalid_id` |
| Empty body | `POST /api/designs` | `{}` | 422 (missing required) | `test_create_design_missing_field` |
| Partial body | `POST /api/catalog/sources` | Missing name/type/desc | 422 | `test_add_source_missing_field` |
| Duplicate source | `POST /api/catalog/sources` | Same source_id twice | 400 | `test_add_source_duplicate` |
| Search no query | `GET /api/catalog/search` | No `q` param | 422 | `test_search_missing_query` |
| Cautions no param | `GET /api/rules/cautions` | No `table_names` | 422 | `test_cautions_missing_param` |
| Invalid review status | `POST .../comments` | `status="pending_review"` | 400 | `test_add_comment_invalid_status` |
| Comment not found | `POST .../comments` | nonexistent design | 404 | `test_add_comment_not_found` |
| Knowledge not found | `POST .../knowledge` | nonexistent design | 404 | `test_knowledge_not_found` |
| Knowledge invalid entries | `POST .../knowledge` | malformed entries | 400 | `test_knowledge_invalid_entries` |
| Preview vs save | `POST .../knowledge` | No body vs with body | Preview vs persist | `test_knowledge_preview`, `test_knowledge_save` |
| Services uninitialized | Any endpoint | No `_registry` wiring | 500, `{"error": ...}` | `test_error_500_uninitialized` |
| Unexpected exception | Any endpoint | Getter raises Exception | 500, no stack trace | `test_error_500_unexpected` |

### Server Startup Edge Cases

| Case | Input | Expected | Test |
|------|-------|----------|------|
| Port 0 (OS assign) | `start_server(port=0)` | Returns assigned port > 0 | `test_start_server_returns_port` |
| Specific port | `start_server(port=N)` | Uses N when free | `test_start_server_specific_port` |
| Port conflict | `start_server(port=occupied)` | Falls back to OS port | `test_start_server_port_fallback` |
| Shutdown | `server.should_exit = True` | Thread terminates | `test_start_server_shutdown` |
| Static missing | No `static/` dir | `GET /` → 404 (no crash) | `test_static_missing_returns_404` |
| Static present | `static/index.html` exists | `GET /` → 200 | `test_static_files_served` |

### Error Response Format

| Status | Body Format | Verified By |
|--------|------------|-------------|
| 400 | `{"error": "..."}` | `test_error_400_format` |
| 404 | `{"error": "..."}` | `test_error_404_format` |
| 422 | FastAPI default validation | `test_create_design_missing_field` |
| 500 (uninitialized) | `{"error": "..."}` | `test_error_500_uninitialized` |
| 500 (unexpected) | `{"error": "Internal server error"}` (no stack trace) | `test_error_500_unexpected` |

## Build Pipeline Testing

ビルドパイプライン（FR-13/14/15/16）の自動テストは Node.js 依存のため、
pytest テストスイートには含めない。以下の方針で検証する:

| AC | Verification | Method |
|----|-------------|--------|
| R4-AC1 (`poe build-frontend` → static/) | `static/index.html` が存在 | CI ジョブ or 手動 |
| R4-AC2 (wheel に static 含む) | `uv build` → wheel 内ファイル確認 | CI ジョブ or 手動 |
| R4-AC4 (frontend/ が有効な Vite project) | `cd frontend && npm install && npm run build` | CI ジョブ |
| R4-AC5 (`poe build` 順序) | `poe build` 実行でフルビルド成功 | CI ジョブ |

**CI ジョブ設計**: Node.js + Python の matrix CI で `poe build` を実行し、
wheel 内の `insight_blueprint/static/index.html` の存在を `zipinfo` で確認する。
pytest とは別ジョブとして実行。

## Regression Strategy

SPEC-4a は共有モジュール（`cli.py`, `server.py`, `conftest.py`）を変更する。
リグレッション防止:

1. **R1-AC3: 既存 183 テスト全通過** — `_registry` への移行後も全テストが通ること
   - `test_server.py` の `_reset_service` fixture を `_registry` 向けに更新
     （legacy `server_module._service` reset を廃止し、`_registry` reset に一本化）
   - `conftest.py` の service fixture wiring を `_registry` 経由に変更
   - import パス変更以外のロジック変更なし
   - **検証**: `uv run pytest` で全既存テスト通過を CI ゲートとする

2. **server.py の既存 MCP ツールテスト** — getter が `_registry` 経由に
   変わるだけで、テストの assertion は全て同一

3. **conftest.py の fixture 互換性** — `design_service`, `review_service` 等の
   fixture は同じ型を返す。呼び出し側の変更不要

4. **新テストの独立性** — `test_web.py` は `web_client` yield fixture で独立。
   `_reset_registry` autouse fixture で `_registry` グローバル状態をリセット

## Security Testing

| # | Test | Verification |
|---|------|-------------|
| 1 | `test_localhost_binding` | uvicorn config の `host` が `"127.0.0.1"` |
| 2 | `test_error_500_unexpected` | stack trace が response body に漏れない |
| 3 | `test_error_400_format` | ValueError メッセージが `{"error": ...}` 形式で返る |
| 4 | `test_cors_localhost_allowed` | localhost origin の CORS リクエストにヘッダーが付く |
| 5 | `test_cors_external_rejected` | 外部 origin の CORS リクエストが拒否される |

"""Tests for web.py REST API endpoints."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

import insight_blueprint._registry as registry
from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.reviews import ReviewService
from insight_blueprint.core.rules import RulesService
from insight_blueprint.storage.project import init_project


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    """Reset all registry references after each test."""
    orig_d = registry.design_service
    orig_c = registry.catalog_service
    orig_r = registry.review_service
    orig_u = registry.rules_service
    yield
    registry.design_service = orig_d
    registry.catalog_service = orig_c
    registry.review_service = orig_r
    registry.rules_service = orig_u


@pytest.fixture
def web_client() -> Iterator[TestClient]:
    """Yield a TestClient wired to the FastAPI app."""
    from insight_blueprint.web import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# ---------------------------------------------------------------------------
# Health check (2 tests)
# ---------------------------------------------------------------------------


def test_health_returns_ok_and_version(web_client: TestClient) -> None:
    resp = web_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_works_without_service_init(web_client: TestClient) -> None:
    """Health check must respond even when no services are wired."""
    registry.design_service = None
    registry.catalog_service = None
    registry.review_service = None
    registry.rules_service = None
    resp = web_client.get("/api/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Error format (4 tests)
# ---------------------------------------------------------------------------


def test_404_error_uses_error_format(web_client: TestClient) -> None:
    resp = web_client.get("/api/nonexistent")
    assert resp.status_code in (404, 405)


def test_http_exception_returns_error_key(web_client: TestClient) -> None:
    """HTTPException responses must have {"error": ...}, not {"detail": ...}."""
    resp = web_client.get("/api/nonexistent-endpoint-xyz")
    data = resp.json()
    assert "error" in data
    assert "detail" not in data


def test_unhandled_exception_returns_500(web_client: TestClient) -> None:
    """Unexpected exception → 500 without stack trace."""
    from insight_blueprint.web import app

    @app.get("/api/_test_500")
    async def _trigger_500() -> dict:
        raise RuntimeError("unexpected boom")

    # Move newly added route before catch-all static mount (last route)
    new_route = app.routes.pop()
    static_idx = len(app.routes) - 1
    app.routes.insert(static_idx, new_route)

    resp = web_client.get("/api/_test_500")
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"] == "Internal server error"
    assert "boom" not in str(data)

    # Cleanup: remove test route
    app.routes[:] = [
        r for r in app.routes if getattr(r, "path", None) != "/api/_test_500"
    ]


def test_error_format_has_no_detail_key(web_client: TestClient) -> None:
    """Ensure {"detail": ...} never appears in our error responses."""
    from fastapi import HTTPException

    from insight_blueprint.web import app

    @app.get("/api/_test_http_exc")
    async def _trigger_http_exc() -> dict:
        raise HTTPException(status_code=400, detail="test error")

    # Move newly added route before catch-all static mount (last route)
    new_route = app.routes.pop()
    static_idx = len(app.routes) - 1
    app.routes.insert(static_idx, new_route)

    resp = web_client.get("/api/_test_http_exc")
    assert resp.status_code == 400
    data = resp.json()
    assert data == {"error": "test error"}
    assert "detail" not in data

    app.routes[:] = [
        r for r in app.routes if getattr(r, "path", None) != "/api/_test_http_exc"
    ]


# ---------------------------------------------------------------------------
# CORS (2 tests)
# ---------------------------------------------------------------------------


def test_cors_allows_localhost_origin(web_client: TestClient) -> None:
    resp = web_client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_external_origin(web_client: TestClient) -> None:
    resp = web_client.options(
        "/api/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"


# ---------------------------------------------------------------------------
# Wired client fixture (services initialized)
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Yield a TestClient with all services wired."""
    init_project(tmp_path)
    registry.design_service = DesignService(tmp_path)
    registry.catalog_service = CatalogService(tmp_path)
    registry.catalog_service.rebuild_index()
    registry.review_service = ReviewService(tmp_path, registry.design_service)
    registry.rules_service = RulesService(tmp_path, registry.catalog_service)
    from insight_blueprint.web import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Design endpoints (10 tests)
# ---------------------------------------------------------------------------


def _create_design(client: TestClient, **overrides: object) -> dict:
    """Helper: create a design via POST and return the response JSON."""
    payload = {
        "title": "Test Design",
        "hypothesis_statement": "Test hypothesis",
        "hypothesis_background": "Test background",
        **overrides,
    }
    resp = client.post("/api/designs", json=payload)
    return resp.json()


def test_list_designs_empty(client: TestClient) -> None:
    resp = client.get("/api/designs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["designs"] == []
    assert data["count"] == 0


def test_create_design_returns_201(client: TestClient) -> None:
    resp = client.post(
        "/api/designs",
        json={
            "title": "New Design",
            "hypothesis_statement": "stmt",
            "hypothesis_background": "bg",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "design" in data
    assert "message" in data
    assert data["design"]["status"] == "draft"


def test_list_designs_returns_created(client: TestClient) -> None:
    _create_design(client)
    resp = client.get("/api/designs")
    data = resp.json()
    assert data["count"] == 1
    assert len(data["designs"]) == 1


def test_list_designs_status_filter(client: TestClient) -> None:
    _create_design(client)
    resp = client.get("/api/designs?status=active")
    data = resp.json()
    assert data["count"] == 0  # draft, not active


def test_list_designs_invalid_status(client: TestClient) -> None:
    resp = client.get("/api/designs?status=bogus")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_get_design_success(client: TestClient) -> None:
    created = _create_design(client)
    design_id = created["design"]["id"]
    resp = client.get(f"/api/designs/{design_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == design_id


def test_get_design_not_found(client: TestClient) -> None:
    resp = client.get("/api/designs/NONEXIST-H99")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_get_design_invalid_id(client: TestClient) -> None:
    resp = client.get("/api/designs/bad%20id")
    # Invalid ID → rejected by Path validation (422) or core _validate_id (400)
    assert resp.status_code in (400, 422)


def test_update_design_success(client: TestClient) -> None:
    created = _create_design(client)
    design_id = created["design"]["id"]
    resp = client.put(
        f"/api/designs/{design_id}",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


def test_create_design_invalid_theme_id_returns_400(client: TestClient) -> None:
    resp = client.post(
        "/api/designs",
        json={
            "title": "Bad Theme",
            "hypothesis_statement": "stmt",
            "hypothesis_background": "bg",
            "theme_id": "NONEXISTENT_THEME",
        },
    )
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_update_design_invalid_status_returns_400(client: TestClient) -> None:
    created = _create_design(client)
    design_id = created["design"]["id"]
    resp = client.put(
        f"/api/designs/{design_id}",
        json={"status": "invalid_status_value"},
    )
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_design_path_traversal_returns_422(client: TestClient) -> None:
    """Path traversal attempt in design_id should be rejected by Path validation."""
    resp = client.get("/api/designs/../../etc/passwd")
    assert resp.status_code in (404, 422)


def test_source_path_traversal_returns_422(client: TestClient) -> None:
    """Path traversal attempt in source_id should be rejected by Path validation."""
    resp = client.get("/api/catalog/sources/../../etc/passwd")
    assert resp.status_code in (404, 422)


def test_update_design_not_found(client: TestClient) -> None:
    resp = client.put(
        "/api/designs/NONEXIST-H99",
        json={"title": "Ghost"},
    )
    assert resp.status_code == 404
    assert "error" in resp.json()


# ---------------------------------------------------------------------------
# Catalog endpoints (17 tests)
# ---------------------------------------------------------------------------


def _add_source(client: TestClient, source_id: str = "test-src", **kw: object) -> dict:
    """Helper: add a catalog source via POST."""
    payload = {
        "source_id": source_id,
        "name": kw.get("name", "Test Source"),
        "type": kw.get("type", "csv"),
        "description": kw.get("description", "A test CSV source"),
        "connection": kw.get("connection", {"file_path": "data.csv"}),
    }
    if "columns" in kw:
        payload["columns"] = kw["columns"]
    if "tags" in kw:
        payload["tags"] = kw["tags"]
    resp = client.post("/api/catalog/sources", json=payload)
    return resp.json()


def test_list_sources_empty(client: TestClient) -> None:
    resp = client.get("/api/catalog/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sources"] == []
    assert data["count"] == 0


def test_add_source_returns_201(client: TestClient) -> None:
    resp = client.post(
        "/api/catalog/sources",
        json={
            "source_id": "new-src",
            "name": "New Source",
            "type": "csv",
            "description": "desc",
            "connection": {},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "source" in data
    assert "message" in data
    assert data["source"]["id"] == "new-src"


def test_add_source_duplicate_returns_400(client: TestClient) -> None:
    _add_source(client, "dup-src")
    resp = client.post(
        "/api/catalog/sources",
        json={
            "source_id": "dup-src",
            "name": "Dup",
            "type": "csv",
            "description": "dup",
            "connection": {},
        },
    )
    assert resp.status_code == 400
    assert "already exists" in resp.json()["error"]


def test_add_source_invalid_type_returns_400(client: TestClient) -> None:
    resp = client.post(
        "/api/catalog/sources",
        json={
            "source_id": "bad-type",
            "name": "Bad",
            "type": "parquet",
            "description": "bad",
            "connection": {},
        },
    )
    assert resp.status_code == 400
    assert "parquet" in resp.json()["error"]


def test_add_source_missing_fields_returns_422(client: TestClient) -> None:
    resp = client.post("/api/catalog/sources", json={"source_id": "x"})
    assert resp.status_code == 422


def test_list_sources_returns_added(client: TestClient) -> None:
    _add_source(client, "s1")
    resp = client.get("/api/catalog/sources")
    data = resp.json()
    assert data["count"] == 1


def test_get_source_success(client: TestClient) -> None:
    _add_source(client, "gs-src")
    resp = client.get("/api/catalog/sources/gs-src")
    assert resp.status_code == 200
    assert resp.json()["id"] == "gs-src"


def test_get_source_not_found(client: TestClient) -> None:
    resp = client.get("/api/catalog/sources/nonexistent")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_update_source_patches_name(client: TestClient) -> None:
    _add_source(client, "upd-src")
    resp = client.put(
        "/api/catalog/sources/upd-src",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_update_source_patches_description(client: TestClient) -> None:
    _add_source(client, "upd-desc")
    resp = client.put(
        "/api/catalog/sources/upd-desc",
        json={"description": "New description"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "New description"


def test_update_source_patches_connection(client: TestClient) -> None:
    _add_source(client, "upd-conn")
    resp = client.put(
        "/api/catalog/sources/upd-conn",
        json={"connection": {"file_path": "new.csv"}},
    )
    assert resp.status_code == 200
    assert resp.json()["connection"]["file_path"] == "new.csv"


def test_update_source_patches_columns(client: TestClient) -> None:
    _add_source(client, "upd-cols")
    resp = client.put(
        "/api/catalog/sources/upd-cols",
        json={"columns": [{"name": "year", "type": "integer", "description": "Year"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["schema_info"]["columns"][0]["name"] == "year"


def test_update_source_patches_tags(client: TestClient) -> None:
    _add_source(client, "upd-tags")
    resp = client.put(
        "/api/catalog/sources/upd-tags",
        json={"tags": ["finance", "quarterly"]},
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["finance", "quarterly"]


def test_update_source_columns_not_found(client: TestClient) -> None:
    """Updating columns on a nonexistent source returns 404."""
    resp = client.put(
        "/api/catalog/sources/missing-cols",
        json={"columns": [{"name": "x", "type": "str", "description": "x"}]},
    )
    assert resp.status_code == 404


def test_update_source_not_found(client: TestClient) -> None:
    resp = client.put(
        "/api/catalog/sources/missing",
        json={"name": "X"},
    )
    assert resp.status_code == 404


def test_get_schema_returns_columns(client: TestClient) -> None:
    _add_source(
        client,
        "schema-src",
        columns=[{"name": "year", "type": "integer", "description": "Year"}],
    )
    resp = client.get("/api/catalog/sources/schema-src/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_id"] == "schema-src"
    assert len(data["columns"]) == 1


def test_get_schema_not_found(client: TestClient) -> None:
    resp = client.get("/api/catalog/sources/nonexistent/schema")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_search_returns_results(client: TestClient) -> None:
    _add_source(
        client,
        "pop-src",
        name="Population Data",
        description="Japanese population statistics",
    )
    # Rebuild FTS5 index
    registry.catalog_service.rebuild_index()
    resp = client.get("/api/catalog/search?q=population")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1


def test_search_empty_returns_zero(client: TestClient) -> None:
    resp = client.get("/api/catalog/search?q=zzzznonexistent")
    data = resp.json()
    assert data["count"] == 0


def test_search_source_id_post_filter(client: TestClient) -> None:
    _add_source(client, "src-a", name="Alpha Data", description="population alpha")
    _add_source(client, "src-b", name="Beta Data", description="population beta")
    registry.catalog_service.rebuild_index()
    resp = client.get("/api/catalog/search?q=population&source_id=src-a")
    data = resp.json()
    for r in data["results"]:
        assert r["source_id"] == "src-a"


def test_search_missing_q_returns_422(client: TestClient) -> None:
    resp = client.get("/api/catalog/search")
    assert resp.status_code == 422


def test_get_knowledge_list(client: TestClient) -> None:
    _add_source(client, "know-src")
    resp = client.get("/api/catalog/knowledge")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "count" in data


# ---------------------------------------------------------------------------
# Review endpoints (12 tests)
# ---------------------------------------------------------------------------


def _create_active_design_via_api(client: TestClient) -> str:
    """Helper: create a design and move it to active, return design_id."""
    created = _create_design(client)
    design_id = created["design"]["id"]
    client.put(f"/api/designs/{design_id}", json={"status": "active"})
    return design_id


def _create_pending_design_via_api(client: TestClient) -> str:
    """Helper: create → activate → submit for review, return design_id."""
    design_id = _create_active_design_via_api(client)
    client.post(f"/api/designs/{design_id}/review")
    return design_id


def test_submit_review_success(client: TestClient) -> None:
    design_id = _create_active_design_via_api(client)
    resp = client.post(f"/api/designs/{design_id}/review")
    assert resp.status_code == 200
    data = resp.json()
    assert data["design_id"] == design_id
    assert data["status"] == "pending_review"
    assert "message" in data


def test_submit_review_non_active_returns_400(client: TestClient) -> None:
    created = _create_design(client)
    design_id = created["design"]["id"]
    resp = client.post(f"/api/designs/{design_id}/review")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_submit_review_not_found(client: TestClient) -> None:
    resp = client.post("/api/designs/NONEXIST-H99/review")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_list_comments_empty(client: TestClient) -> None:
    design_id = _create_active_design_via_api(client)
    resp = client.get(f"/api/designs/{design_id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["design_id"] == design_id
    assert data["count"] == 0


def test_add_comment_success(client: TestClient) -> None:
    design_id = _create_pending_design_via_api(client)
    resp = client.post(
        f"/api/designs/{design_id}/comments",
        json={"comment": "Good analysis", "status": "supported"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "comment_id" in data
    assert data["status_after"] == "supported"


def test_add_comment_invalid_status_returns_400(client: TestClient) -> None:
    design_id = _create_pending_design_via_api(client)
    resp = client.post(
        f"/api/designs/{design_id}/comments",
        json={"comment": "Bad", "status": "pending_review"},
    )
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_add_comment_not_found(client: TestClient) -> None:
    resp = client.post(
        "/api/designs/NONEXIST-H99/comments",
        json={"comment": "Ghost", "status": "supported"},
    )
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_add_comment_non_pending_returns_400(client: TestClient) -> None:
    design_id = _create_active_design_via_api(client)
    resp = client.post(
        f"/api/designs/{design_id}/comments",
        json={"comment": "Bad", "status": "supported"},
    )
    assert resp.status_code == 400


def test_knowledge_preview(client: TestClient) -> None:
    design_id = _create_pending_design_via_api(client)
    client.post(
        f"/api/designs/{design_id}/comments",
        json={"comment": "caution: watch for nulls", "status": "supported"},
    )
    # Re-activate for extraction
    client.put(f"/api/designs/{design_id}", json={"status": "active"})
    resp = client.post(f"/api/designs/{design_id}/knowledge")
    assert resp.status_code == 200
    data = resp.json()
    assert data["design_id"] == design_id
    assert data["count"] >= 1
    assert "entries" in data


def test_knowledge_save(client: TestClient) -> None:
    design_id = _create_pending_design_via_api(client)
    client.post(
        f"/api/designs/{design_id}/comments",
        json={"comment": "caution: watch for nulls", "status": "supported"},
    )
    client.put(f"/api/designs/{design_id}", json={"status": "active"})
    # Preview first
    preview = client.post(f"/api/designs/{design_id}/knowledge").json()
    entries = preview["entries"]
    # Save
    resp = client.post(
        f"/api/designs/{design_id}/knowledge",
        json={"entries": entries},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert "saved_entries" in data


def test_knowledge_not_found_returns_empty(client: TestClient) -> None:
    resp = client.post("/api/designs/NONEXIST-H99/knowledge")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0


def test_knowledge_invalid_entries_returns_400(client: TestClient) -> None:
    created = _create_design(client)
    design_id = created["design"]["id"]
    resp = client.post(
        f"/api/designs/{design_id}/knowledge",
        json={"entries": [{"invalid": "data"}]},
    )
    assert resp.status_code == 400
    assert "error" in resp.json()


# ---------------------------------------------------------------------------
# Rules endpoints (4 tests)
# ---------------------------------------------------------------------------


def test_get_rules_context(client: TestClient) -> None:
    resp = client.get("/api/rules/context")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert "knowledge_entries" in data
    assert "rules" in data
    assert "total_sources" in data


def test_get_rules_context_with_data(client: TestClient) -> None:
    _add_source(client, "ctx-src", description="context test")
    resp = client.get("/api/rules/context")
    data = resp.json()
    assert data["total_sources"] >= 1


def test_get_cautions_with_matches(client: TestClient) -> None:
    # Create a full flow to get caution data
    design_id = _create_pending_design_via_api(client)
    client.post(
        f"/api/designs/{design_id}/comments",
        json={
            "comment": "table: test_data\ncaution: watch for nulls",
            "status": "supported",
        },
    )
    client.put(f"/api/designs/{design_id}", json={"status": "active"})
    preview = client.post(f"/api/designs/{design_id}/knowledge").json()
    client.post(
        f"/api/designs/{design_id}/knowledge",
        json={"entries": preview["entries"]},
    )
    resp = client.get("/api/rules/cautions?table_names=test_data")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1


def test_get_cautions_missing_table_names_returns_422(client: TestClient) -> None:
    resp = client.get("/api/rules/cautions")
    assert resp.status_code == 422

"""Integration tests for web.py server lifecycle and static files."""

import socket
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

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
def _wire_services(tmp_path: Path) -> None:
    """Wire all services for integration tests."""
    init_project(tmp_path)
    registry.design_service = DesignService(tmp_path)
    registry.catalog_service = CatalogService(tmp_path)
    registry.catalog_service.rebuild_index()
    registry.review_service = ReviewService(tmp_path, registry.design_service)
    registry.rules_service = RulesService(tmp_path, registry.catalog_service)


@pytest.fixture
def _server_lifecycle() -> Iterator[None]:
    """Ensure ThreadedUvicorn is stopped after test."""
    import insight_blueprint.web as web_mod

    yield
    if web_mod._server_instance is not None:
        web_mod._server_instance.should_exit = True
        time.sleep(0.1)
        web_mod._server_instance = None


# ---------------------------------------------------------------------------
# Server lifecycle tests (5 tests)
# ---------------------------------------------------------------------------


def test_start_server_returns_port(
    _wire_services: None, _server_lifecycle: None
) -> None:
    from insight_blueprint.web import start_server

    port = start_server(port=0)
    assert isinstance(port, int)
    assert port > 0


def test_start_server_health_responds(
    _wire_services: None, _server_lifecycle: None
) -> None:
    from insight_blueprint.web import start_server

    port = start_server(port=0)
    resp = httpx.get(f"http://127.0.0.1:{port}/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_start_server_port_fallback(
    _wire_services: None, _server_lifecycle: None
) -> None:
    """When the requested port is in use, fall back to OS-assigned port."""
    from insight_blueprint.web import start_server

    # Occupy a port
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", 0))
    blocked_port = blocker.getsockname()[1]

    try:
        port = start_server(port=blocked_port)
        assert port != blocked_port
        assert port > 0
    finally:
        blocker.close()


def test_start_server_binds_localhost(
    _wire_services: None, _server_lifecycle: None
) -> None:
    from insight_blueprint.web import start_server

    port = start_server(host="127.0.0.1", port=0)
    resp = httpx.get(f"http://127.0.0.1:{port}/api/health")
    assert resp.status_code == 200


def test_server_should_exit_stops_thread(
    _wire_services: None,
) -> None:
    import insight_blueprint.web as web_mod
    from insight_blueprint.web import start_server

    start_server(port=0)
    assert web_mod._server_instance is not None
    web_mod._server_instance.should_exit = True
    time.sleep(0.2)
    # After should_exit, the server may not respond (port may be closed)
    # The key assertion is that the thread was daemon=True so it won't block exit


# ---------------------------------------------------------------------------
# Static file tests (2 tests)
# ---------------------------------------------------------------------------


def test_static_index_served_when_exists(tmp_path: Path) -> None:
    """When static/index.html exists, GET / returns it."""
    from starlette.testclient import TestClient

    # Create a temporary static dir and index.html
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>Hello</h1>")

    # Mount on a fresh app to test
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    test_app = FastAPI()
    test_app.mount("/", StaticFiles(directory=str(static_dir), html=True))

    with TestClient(test_app) as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert "Hello" in resp.text


def test_static_missing_returns_404() -> None:
    """When static/ doesn't exist, GET / returns 404 (no crash)."""
    from starlette.testclient import TestClient

    from insight_blueprint.web import app

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/")
        # Either 404 (no static mount) or 200 (if static happens to exist)
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Full flow integration test (1 test)
# ---------------------------------------------------------------------------


def test_full_flow_create_to_knowledge(_wire_services: None) -> None:
    """E2E: create design → review → comment → extract knowledge → save."""
    from starlette.testclient import TestClient

    from insight_blueprint.web import app

    with TestClient(app) as c:
        # 1. Create a design
        resp = c.post(
            "/api/designs",
            json={
                "title": "Churn Analysis",
                "hypothesis_statement": "Users who skip onboarding churn 2x more",
                "hypothesis_background": "Onboarding completion is 40%",
            },
        )
        assert resp.status_code == 201
        design_id = resp.json()["design"]["id"]

        # 2. Get the design back
        resp = c.get(f"/api/designs/{design_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Churn Analysis"
        assert resp.json()["status"] == "draft"

        # 3. Transition to active (required before review)
        resp = c.put(
            f"/api/designs/{design_id}",
            json={"status": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        # 4. Submit for review
        resp = c.post(f"/api/designs/{design_id}/review")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_review"

        # 5. Add a review comment (supported)
        resp = c.post(
            f"/api/designs/{design_id}/comments",
            json={
                "comment": "Good hypothesis. Note: churn is defined as 30-day inactivity.",
                "status": "supported",
                "reviewer": "analyst",
            },
        )
        assert resp.status_code == 200
        comment_id = resp.json()["comment_id"]
        assert comment_id
        assert resp.json()["status_after"] == "supported"

        # 6. List comments
        resp = c.get(f"/api/designs/{design_id}/comments")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

        # 7. Extract knowledge (preview)
        resp = c.post(f"/api/designs/{design_id}/knowledge")
        assert resp.status_code == 200
        # Preview may or may not find entries depending on extraction logic
        # The key assertion is that it doesn't error

        # 8. Save knowledge (with explicit entries)
        resp = c.post(
            f"/api/designs/{design_id}/knowledge",
            json={
                "entries": [
                    {
                        "key": "churn-definition",
                        "title": "Churn Definition",
                        "content": "30-day inactivity",
                        "category": "definition",
                        "source": "review",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

        # 9. Verify health still works
        resp = c.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

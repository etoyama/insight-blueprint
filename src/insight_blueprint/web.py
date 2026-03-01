"""FastAPI HTTP server for insight-blueprint REST API."""

from __future__ import annotations

import socket
import threading
import time
import warnings
from pathlib import Path as FilePath

import uvicorn
from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from insight_blueprint import __version__

# Path parameter validation pattern (matches core layer _SAFE_ID_PATTERN)
_ID_PATTERN = r"[a-zA-Z0-9_-]+"

app = FastAPI(title="insight-blueprint")

# CORS: allow localhost origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Convert HTTPException to {error: ...} format (FR-8)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Convert ValueError to 400 (matches MCP server pattern)."""
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return 500 without stack trace."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Health check (FR-12) — works without service initialization
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class CreateDesignRequest(BaseModel):
    title: str
    hypothesis_statement: str
    hypothesis_background: str
    parent_id: str | None = None
    theme_id: str = "DEFAULT"
    metrics: dict | None = None
    explanatory: list[dict] | None = None
    chart: list[dict] | None = None
    next_action: dict | None = None


class AddCommentRequest(BaseModel):
    comment: str
    status: str
    reviewer: str = "analyst"


class AddSourceRequest(BaseModel):
    source_id: str
    name: str
    type: str
    description: str
    connection: dict
    columns: list[dict] | None = None
    tags: list[str] | None = None


class UpdateDesignRequest(BaseModel):
    title: str | None = None
    hypothesis_statement: str | None = None
    hypothesis_background: str | None = None
    status: str | None = None
    metrics: dict | None = None
    explanatory: list[dict] | None = None
    chart: list[dict] | None = None
    next_action: dict | None = None


class UpdateSourceRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    connection: dict | None = None
    columns: list[dict] | None = None
    tags: list[str] | None = None


class SubmitBatchRequest(BaseModel):
    status_after: str
    reviewer: str = "analyst"
    comments: list[dict]


class SaveKnowledgeRequest(BaseModel):
    entries: list[dict]


# ---------------------------------------------------------------------------
# Design endpoints (FR-4)
# ---------------------------------------------------------------------------


@app.get("/api/designs")
async def list_designs(status: str | None = None) -> dict:
    """List all designs, optionally filtered by status."""
    from insight_blueprint._registry import get_design_service
    from insight_blueprint.models.design import DesignStatus

    svc = get_design_service()
    status_filter = None
    if status is not None:
        try:
            status_filter = DesignStatus(status)
        except ValueError:
            raise HTTPException(400, detail=f"Invalid status '{status}'") from None

    designs = svc.list_designs(status=status_filter)
    return {
        "designs": [d.model_dump(mode="json") for d in designs],
        "count": len(designs),
    }


@app.post("/api/designs", status_code=201)
async def create_design(body: CreateDesignRequest) -> dict:
    """Create a new analysis design."""
    from insight_blueprint._registry import get_design_service

    svc = get_design_service()
    try:
        design = svc.create_design(
            title=body.title,
            hypothesis_statement=body.hypothesis_statement,
            hypothesis_background=body.hypothesis_background,
            parent_id=body.parent_id,
            theme_id=body.theme_id,
            metrics=body.metrics,
            explanatory=body.explanatory,
            chart=body.chart,
            next_action=body.next_action,
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from None

    return {
        "design": design.model_dump(mode="json"),
        "message": f"Analysis design '{design.id}' created successfully.",
    }


@app.get("/api/designs/{design_id}")
async def get_design(design_id: str = Path(pattern=_ID_PATTERN)) -> dict:
    """Get a single design by ID."""
    from insight_blueprint._registry import get_design_service

    svc = get_design_service()
    design = svc.get_design(design_id)
    if design is None:
        raise HTTPException(404, detail=f"Design '{design_id}' not found")
    return design.model_dump(mode="json")


@app.put("/api/designs/{design_id}")
async def update_design(
    body: UpdateDesignRequest,
    design_id: str = Path(pattern=_ID_PATTERN),
) -> dict:
    """Update an existing design."""
    from insight_blueprint._registry import get_design_service
    from insight_blueprint.models.design import DesignStatus

    svc = get_design_service()
    updates: dict = {
        k: v
        for k, v in {
            "title": body.title,
            "hypothesis_statement": body.hypothesis_statement,
            "hypothesis_background": body.hypothesis_background,
            "metrics": body.metrics,
            "explanatory": body.explanatory,
            "chart": body.chart,
            "next_action": body.next_action,
        }.items()
        if v is not None
    }

    if body.status is not None:
        try:
            updates["status"] = DesignStatus(body.status)
        except ValueError:
            raise HTTPException(400, detail=f"Invalid status '{body.status}'") from None

    design = svc.update_design(design_id, **updates)
    if design is None:
        raise HTTPException(404, detail=f"Design '{design_id}' not found")
    return design.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Catalog endpoints (FR-5)
# ---------------------------------------------------------------------------


@app.get("/api/catalog/sources")
async def list_sources() -> dict:
    """List all data sources."""
    from insight_blueprint._registry import get_catalog_service

    svc = get_catalog_service()
    sources = svc.list_sources()
    return {
        "sources": [s.model_dump(mode="json") for s in sources],
        "count": len(sources),
    }


@app.post("/api/catalog/sources", status_code=201)
async def add_source(body: AddSourceRequest) -> dict:
    """Register a new data source."""
    from insight_blueprint._registry import get_catalog_service
    from insight_blueprint.models.catalog import DataSource, SourceType

    svc = get_catalog_service()
    try:
        source_type = SourceType(body.type)
    except ValueError:
        raise HTTPException(400, detail=f"Invalid source type '{body.type}'") from None

    schema_info: dict = {"columns": body.columns or []}
    source = DataSource(
        id=body.source_id,
        name=body.name,
        type=source_type,
        description=body.description,
        connection=body.connection,
        schema_info=schema_info,
        tags=body.tags or [],
    )
    result = svc.add_source(source)
    return {
        "source": result.model_dump(mode="json"),
        "message": f"Source '{result.id}' registered successfully.",
    }


@app.get("/api/catalog/sources/{source_id}")
async def get_source(source_id: str = Path(pattern=_ID_PATTERN)) -> dict:
    """Get a single data source by ID."""
    from insight_blueprint._registry import get_catalog_service

    svc = get_catalog_service()
    source = svc.get_source(source_id)
    if source is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")
    return source.model_dump(mode="json")


@app.put("/api/catalog/sources/{source_id}")
async def update_source(
    body: UpdateSourceRequest,
    source_id: str = Path(pattern=_ID_PATTERN),
) -> dict:
    """Update an existing data source."""
    from insight_blueprint._registry import get_catalog_service

    svc = get_catalog_service()
    updates: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.connection is not None:
        updates["connection"] = body.connection
    if body.columns is not None:
        current = svc.get_source(source_id)
        if current is None:
            raise HTTPException(404, detail=f"Source '{source_id}' not found")
        schema_info = {**current.schema_info, "columns": body.columns}
        updates["schema_info"] = schema_info
    if body.tags is not None:
        updates["tags"] = body.tags

    result = svc.update_source(source_id, **updates)
    if result is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")
    return result.model_dump(mode="json")


@app.get("/api/catalog/sources/{source_id}/schema")
async def get_schema(source_id: str = Path(pattern=_ID_PATTERN)) -> dict:
    """Get column schema for a data source."""
    from insight_blueprint._registry import get_catalog_service

    svc = get_catalog_service()
    source = svc.get_source(source_id)
    if source is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")
    schema = svc.get_schema(source_id)
    return {
        "source_id": source_id,
        "columns": [col.model_dump() for col in (schema or [])],
    }


@app.get("/api/catalog/search")
async def search_catalog(
    q: str = Query(..., min_length=1),
    source_id: str | None = None,
) -> dict:
    """Full-text search the catalog."""
    from insight_blueprint._registry import get_catalog_service

    svc = get_catalog_service()
    results = svc.search(q)

    if source_id is not None:
        results = [r for r in results if r.get("source_id") == source_id]

    return {
        "query": q,
        "results": results,
        "count": len(results),
    }


@app.get("/api/catalog/knowledge")
async def get_knowledge_list() -> dict:
    """Get all domain knowledge entries across all sources."""
    from insight_blueprint._registry import get_catalog_service

    svc = get_catalog_service()
    sources = svc.list_sources()
    entries: list[dict] = []
    for source in sources:
        dk = svc.get_knowledge(source.id)
        if dk is not None:
            for entry in dk.entries:
                entries.append(entry.model_dump(mode="json"))
    return {
        "entries": entries,
        "count": len(entries),
    }


# ---------------------------------------------------------------------------
# Review endpoints (FR-6)
# ---------------------------------------------------------------------------


@app.post("/api/designs/{design_id}/review")
async def submit_review(design_id: str = Path(pattern=_ID_PATTERN)) -> dict:
    """Submit a design for review."""
    from insight_blueprint._registry import get_review_service

    svc = get_review_service()
    result = svc.submit_for_review(design_id)
    if result is None:
        raise HTTPException(404, detail=f"Design '{design_id}' not found")
    return {
        "design_id": result.id,
        "status": result.status.value,
        "message": f"Design '{design_id}' submitted for review.",
    }


@app.get("/api/designs/{design_id}/comments")
async def list_comments(design_id: str = Path(pattern=_ID_PATTERN)) -> dict:
    """List review comments for a design."""
    from insight_blueprint._registry import get_review_service

    svc = get_review_service()
    comments = svc.list_comments(design_id)
    return {
        "design_id": design_id,
        "comments": [c.model_dump(mode="json") for c in comments],
        "count": len(comments),
    }


@app.post("/api/designs/{design_id}/comments")
async def add_comment(
    design_id: str = Path(pattern=_ID_PATTERN), *, body: AddCommentRequest
) -> dict:
    """Add a review comment and transition design status."""
    from insight_blueprint._registry import get_review_service

    svc = get_review_service()
    result = svc.save_review_comment(
        design_id, body.comment, body.status, body.reviewer
    )
    if result is None:
        raise HTTPException(404, detail=f"Design '{design_id}' not found")
    return {
        "comment_id": result.id,
        "status_after": result.status_after.value,
        "message": f"Review comment saved. Design status: {result.status_after.value}.",
    }


@app.post("/api/designs/{design_id}/knowledge")
async def knowledge_endpoint(
    design_id: str = Path(pattern=_ID_PATTERN),
    body: SaveKnowledgeRequest | None = None,
) -> dict:
    """Extract or save domain knowledge from review comments.

    - No body / empty entries → preview (extract only, no persist)
    - Body with entries → save confirmed entries
    """
    from insight_blueprint._registry import get_review_service

    svc = get_review_service()

    if body is None or not body.entries:
        # Preview mode: extract only
        entries = svc.extract_domain_knowledge(design_id)
        return {
            "design_id": design_id,
            "entries": [e.model_dump(mode="json") for e in entries],
            "count": len(entries),
            "message": f"Extracted {len(entries)} knowledge entries (preview).",
        }

    # Save mode: persist confirmed entries
    from insight_blueprint.models.catalog import DomainKnowledgeEntry

    parsed = [DomainKnowledgeEntry(**e) for e in body.entries]
    saved = svc.save_extracted_knowledge(design_id, parsed)
    return {
        "design_id": design_id,
        "saved_entries": [e.model_dump(mode="json") for e in saved],
        "count": len(saved),
        "message": f"Saved {len(saved)} knowledge entries.",
    }


# ---------------------------------------------------------------------------
# Review batch endpoints (Inline Review Comments)
# ---------------------------------------------------------------------------


@app.post("/api/designs/{design_id}/review-batches", status_code=201)
async def submit_review_batch(
    design_id: str = Path(pattern=_ID_PATTERN),
    *,
    body: SubmitBatchRequest,
) -> dict:
    """Submit a batch of review comments and transition design status."""
    from pydantic import ValidationError

    from insight_blueprint._registry import get_review_service

    svc = get_review_service()
    try:
        result = svc.save_review_batch(
            design_id, body.status_after, body.comments, body.reviewer
        )
    except ValidationError as e:
        raise HTTPException(422, detail=str(e)) from None
    except ValueError as e:
        error_msg = str(e)
        if "target_section" in error_msg or "comments" in error_msg:
            raise HTTPException(422, detail=error_msg) from None
        raise
    if result is None:
        raise HTTPException(404, detail=f"Design '{design_id}' not found")
    return {
        "batch_id": result.id,
        "status_after": result.status_after.value,
        "comment_count": len(result.comments),
    }


@app.get("/api/designs/{design_id}/review-batches")
async def list_review_batches(
    design_id: str = Path(pattern=_ID_PATTERN),
) -> dict:
    """List all review batches for a design."""
    from insight_blueprint._registry import get_review_service

    svc = get_review_service()
    batches = svc.list_review_batches(design_id)
    return {
        "design_id": design_id,
        "batches": [b.model_dump(mode="json") for b in batches],
        "count": len(batches),
    }


# ---------------------------------------------------------------------------
# Rules endpoints (FR-7)
# ---------------------------------------------------------------------------


@app.get("/api/rules/context")
async def get_rules_context() -> dict:
    """Get aggregated project context including all domain knowledge."""
    from insight_blueprint._registry import get_rules_service

    svc = get_rules_service()
    return svc.get_project_context()


@app.get("/api/rules/cautions")
async def get_cautions(
    table_names: str = Query(..., min_length=1),
) -> dict:
    """Suggest cautions for the given table/source names."""
    from insight_blueprint._registry import get_rules_service

    svc = get_rules_service()
    names = [t.strip() for t in table_names.split(",") if t.strip()]
    cautions = svc.suggest_cautions(names)
    return {
        "table_names": names,
        "cautions": cautions,
        "count": len(cautions),
    }


# ---------------------------------------------------------------------------
# Static file serving + ThreadedUvicorn + start_server (FR-9, FR-10)
# ---------------------------------------------------------------------------

# Server configuration constants
_POLL_INTERVAL_S = 1e-3
_STARTUP_TIMEOUT_S = 10.0
_BROWSER_DELAY_S = 1.5

# Mount static files if directory exists
_STATIC_DIR = FilePath(__file__).parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")


class ThreadedUvicorn(uvicorn.Server):
    """Uvicorn server that runs in a daemon thread."""

    def install_signal_handlers(self) -> None:
        """Disable signal handlers (only valid on main thread)."""


# Module-level server reference for testing cleanup
_server_instance: ThreadedUvicorn | None = None


def start_server(host: str = "127.0.0.1", port: int = 3000) -> int:
    """Start the HTTP server in a daemon thread and return the actual port.

    If the requested port is in use, falls back to an OS-assigned port.
    """
    global _server_instance  # noqa: PLW0603

    # Suppress uvicorn's use of legacy websockets API (upstream fix pending)
    # See: https://github.com/encode/uvicorn/issues/2483
    warnings.filterwarnings(
        "ignore", message=r"websockets\.legacy", category=DeprecationWarning
    )
    warnings.filterwarnings(
        "ignore",
        message=r"websockets\.server\.WebSocketServerProtocol",
        category=DeprecationWarning,
    )

    # Probe port availability
    actual_port = port
    if port != 0:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
        except OSError:
            # Port in use — fall back to OS-assigned
            actual_port = 0

    config = uvicorn.Config(
        app,
        host=host,
        port=actual_port,
        log_level="warning",
        access_log=False,
    )
    server = ThreadedUvicorn(config)
    _server_instance = server

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Readiness polling with timeout
    deadline = time.monotonic() + _STARTUP_TIMEOUT_S
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError(f"Server failed to start within {_STARTUP_TIMEOUT_S}s")
        time.sleep(_POLL_INTERVAL_S)

    # Read actual port from the server's sockets
    for s in server.servers:
        for sock in s.sockets:
            addr = sock.getsockname()
            if addr[1] > 0:
                return addr[1]

    return actual_port

# Quality Review Report: SPEC-4a (webui-backend)

## Summary

| Severity | Count |
|----------|-------|
| High     | 2     |
| Medium   | 7     |
| Low      | 4     |

---

## High Severity

### H1: `update_source` accepts raw `dict` body instead of Pydantic model

- **File**: `src/insight_blueprint/web.py:286`
- **Current**:
  ```python
  @app.put("/api/catalog/sources/{source_id}")
  async def update_source(body: dict, source_id: str) -> dict:
  ```
- **Suggested**: Create an `UpdateSourceRequest` Pydantic model:
  ```python
  class UpdateSourceRequest(BaseModel):
      name: str | None = None
      description: str | None = None
      connection: dict | None = None
      columns: list[dict] | None = None
      tags: list[str] | None = None

  @app.put("/api/catalog/sources/{source_id}")
  async def update_source(body: UpdateSourceRequest, source_id: str) -> dict:
  ```
- **Rationale**: Using a raw `dict` bypasses FastAPI's automatic request validation. Any payload shape is accepted, including unexpected keys. This is inconsistent with all other endpoints which use Pydantic models. It also violates the security rule for input validation. The manual `if "key" in body` checks on lines 292-305 replicate what Pydantic does automatically.

### H2: Missing path parameter validation in `web.py` (design_id, source_id)

- **File**: `src/insight_blueprint/web.py` (lines 179, 191, 274, 286, 313, 375, 391, 404, 422)
- **Current**: Path parameters like `design_id: str` and `source_id: str` are used directly without validation.
  ```python
  @app.get("/api/designs/{design_id}")
  async def get_design(design_id: str) -> dict:
      svc = get_design_service()
      design = svc.get_design(design_id)
  ```
- **Suggested**: Add a path parameter validation dependency or use `Annotated` with a regex constraint:
  ```python
  from fastapi import Path as PathParam

  RESOURCE_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"

  @app.get("/api/designs/{design_id}")
  async def get_design(
      design_id: str = PathParam(..., pattern=RESOURCE_ID_PATTERN),
  ) -> dict:
  ```
- **Rationale**: `server.py` already validates IDs with `_validate_design_id()` / `_validate_source_id()` using regex `[a-zA-Z0-9_-]+`. The REST API in `web.py` has no equivalent validation, creating an inconsistency between MCP and HTTP interfaces. Unvalidated path params could lead to path traversal if the storage layer uses them in file paths.

---

## Medium Severity

### M1: Repeated import pattern inside every endpoint function

- **File**: `src/insight_blueprint/web.py` (lines 133-134, 154, 183, 197, 234, 248, 277, 335, 377, 395, 407, 433, 446, 467, 478)
- **Current**: Every endpoint repeats:
  ```python
  async def list_designs(status: str | None = None) -> dict:
      from insight_blueprint._registry import get_design_service
      ...
      svc = get_design_service()
  ```
- **Suggested**: Use FastAPI's `Depends()` mechanism:
  ```python
  from fastapi import Depends
  from insight_blueprint._registry import get_design_service, get_catalog_service

  @app.get("/api/designs")
  async def list_designs(
      status: str | None = None,
      svc: DesignService = Depends(get_design_service),
  ) -> dict:
  ```
- **Rationale**: The deferred import pattern is used (likely to avoid circular imports at module load time), but FastAPI's dependency injection system handles this natively and is the idiomatic approach. It also improves testability (easy to override dependencies in tests). Currently 15+ endpoints repeat the same import boilerplate.

### M2: Magic number `1e-3` in readiness polling and `1.5` in browser timer

- **File**: `src/insight_blueprint/web.py:542`
- **Current**:
  ```python
  while not server.started:
      time.sleep(1e-3)
  ```
- **File**: `src/insight_blueprint/cli.py:62`
- **Current**:
  ```python
  threading.Timer(1.5, webbrowser.open, args=[url]).start()
  ```
- **Suggested**:
  ```python
  _POLL_INTERVAL_SEC = 0.001
  _BROWSER_OPEN_DELAY_SEC = 1.5

  while not server.started:
      time.sleep(_POLL_INTERVAL_SEC)
  ```
- **Rationale**: Violates the "No Magic Numbers" coding principle. `1e-3` is especially non-obvious as a sleep duration. Named constants communicate intent.

### M3: `start_server` function does too many things (30+ lines)

- **File**: `src/insight_blueprint/web.py:510-551`
- **Current**: `start_server` handles port probing, config creation, server instantiation, thread management, readiness polling, and port extraction.
- **Suggested**: Extract port probing and port extraction into separate functions:
  ```python
  def _probe_port(host: str, port: int) -> int:
      """Return port if available, else 0 for OS-assigned."""
      if port == 0:
          return 0
      try:
          with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
              sock.bind((host, port))
          return port
      except OSError:
          return 0

  def _get_actual_port(server: ThreadedUvicorn, fallback: int) -> int:
      """Extract actual port from server sockets."""
      for s in server.servers:
          for sock in s.sockets:
              addr = sock.getsockname()
              if addr[1] > 0:
                  return addr[1]
      return fallback
  ```
- **Rationale**: The function has 3 distinct responsibilities. Extracting them improves testability and readability. Each sub-function becomes independently testable.

### M4: `global` statement for mutable module state

- **File**: `src/insight_blueprint/web.py:515`
- **Current**:
  ```python
  global _server_instance  # noqa: PLW0603
  ```
- **Suggested**: Use a module-level container class or a simple namespace:
  ```python
  class _ServerState:
      instance: ThreadedUvicorn | None = None

  _state = _ServerState()
  ```
- **Rationale**: `global` with mutable state is fragile and the `# noqa` suppression confirms it triggered a linter warning. A simple container makes the state access explicit without suppressing linter rules.

### M5: `knowledge_endpoint` handles two distinct operations in one function

- **File**: `src/insight_blueprint/web.py:422-455`
- **Current**: The function conditionally does extract-preview OR save based on request body content.
  ```python
  if body is None or not body.entries:
      # Preview mode
      ...
  # Save mode
  ...
  ```
- **Suggested**: Split into two endpoints:
  ```python
  @app.get("/api/designs/{design_id}/knowledge")
  async def preview_knowledge(design_id: str) -> dict:
      """Preview extracted knowledge entries."""

  @app.post("/api/designs/{design_id}/knowledge")
  async def save_knowledge(design_id: str, body: SaveKnowledgeRequest) -> dict:
      """Save confirmed knowledge entries."""
  ```
- **Rationale**: Violates Single Responsibility. The current POST endpoint behaves like a GET when no body is provided, which is semantically incorrect for REST. Splitting by HTTP method makes the API more predictable and self-documenting.

### M6: `_registry.py` getters are repetitive (DRY violation)

- **File**: `src/insight_blueprint/_registry.py:24-49`
- **Current**: Four identical getter functions that only differ in the service name:
  ```python
  def get_design_service() -> DesignService:
      if design_service is None:
          raise RuntimeError("design_service not initialized. Wire via cli.py first.")
      return design_service
  ```
- **Suggested**: This is a borderline finding. The current approach is explicit and type-safe (each getter returns a specific type). A generic helper would lose type information. **Keep as-is** but note the pattern for awareness.
- **Rationale**: While technically repetitive, the explicitness aids IDE support and type checking. The cost of abstraction outweighs the cost of repetition here. Flagged as Medium because it's 4 instances — if more services are added, consider a generic pattern.

### M7: No readiness timeout in `start_server`

- **File**: `src/insight_blueprint/web.py:541-542`
- **Current**:
  ```python
  while not server.started:
      time.sleep(1e-3)
  ```
- **Suggested**:
  ```python
  _STARTUP_TIMEOUT_SEC = 10.0
  deadline = time.monotonic() + _STARTUP_TIMEOUT_SEC
  while not server.started:
      if time.monotonic() > deadline:
          raise RuntimeError(f"Server failed to start within {_STARTUP_TIMEOUT_SEC}s")
      time.sleep(_POLL_INTERVAL_SEC)
  ```
- **Rationale**: If the server fails to bind or crashes during startup, this loop will spin forever (blocking the daemon thread's caller). A timeout prevents indefinite hangs.

---

## Low Severity

### L1: Return type `dict` is overly broad

- **File**: `src/insight_blueprint/web.py` (all endpoints)
- **Current**: All endpoints declare `-> dict` return type.
- **Suggested**: Use Pydantic response models or `TypedDict` for precise return types:
  ```python
  class DesignListResponse(BaseModel):
      designs: list[dict]
      count: int

  @app.get("/api/designs", response_model=DesignListResponse)
  async def list_designs(...) -> DesignListResponse:
  ```
- **Rationale**: `-> dict` provides no schema information. FastAPI can auto-generate OpenAPI docs from response models. This is a low priority enhancement since the API works correctly.

### L2: Inconsistent error handling between `web.py` and `server.py`

- **File**: `src/insight_blueprint/web.py` vs `src/insight_blueprint/server.py`
- **Current**: `web.py` uses `HTTPException` (raises), `server.py` returns `{"error": ...}` dicts.
- **Rationale**: This is by design (HTTP vs MCP have different error conventions), but worth documenting. Not a bug, but the pattern difference should be noted in a docstring or design doc.

### L3: CORS origins list could be a named constant

- **File**: `src/insight_blueprint/web.py:26-31`
- **Current**:
  ```python
  allow_origins=[
      "http://localhost:3000",
      "http://127.0.0.1:3000",
      "http://localhost:5173",
      "http://127.0.0.1:5173",
  ],
  ```
- **Suggested**:
  ```python
  _ALLOWED_ORIGINS = [
      "http://localhost:3000",
      "http://127.0.0.1:3000",
      "http://localhost:5173",
      "http://127.0.0.1:5173",
  ]
  ```
- **Rationale**: Minor naming improvement. Makes it clear this is a configuration constant. Port numbers `3000` and `5173` are also unnamed but are well-known defaults (Express/Vite).

### L4: `install_signal_handlers` has empty body without explicit `pass`

- **File**: `src/insight_blueprint/web.py:502-503`
- **Current**:
  ```python
  def install_signal_handlers(self) -> None:
      """Disable signal handlers (only valid on main thread)."""
  ```
- **Suggested**: Add explicit `pass` or keep as-is (docstring serves as body in Python). This is stylistic.
- **Rationale**: The docstring acts as the function body (valid Python), but some style guides prefer explicit `pass` for clarity. Very minor.

---

## Overall Assessment

### Strengths
- Clean separation between MCP (`server.py`) and REST (`web.py`) interfaces
- Consistent use of Pydantic models for request validation (except H1)
- Good docstrings on all endpoint functions
- Exception handlers provide consistent error response format
- `_registry.py` is a clean service locator pattern
- `cli.py` is concise and well-structured
- Early return pattern is used well throughout

### web.py Structure (551 lines)
The file is at 551 lines, within the 800-line max but above the 200-400 target range. The structure is logical with clear section comments (FR-4, FR-5, FR-6, FR-7). Consider splitting into a router-per-domain pattern if the file continues to grow:
- `web/designs.py` — Design CRUD
- `web/catalog.py` — Catalog CRUD
- `web/reviews.py` — Review workflow
- `web/rules.py` — Rules endpoints
This is not urgent at 551 lines but should be planned.

### Priority Recommendations
1. **Fix H1** (raw dict body) — Security and consistency issue
2. **Fix H2** (path param validation) — Security gap between MCP and REST
3. **Address M5** (split knowledge endpoint) — REST semantics
4. **Address M7** (startup timeout) — Reliability

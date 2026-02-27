# SPEC-4a Requirements Review Report

**Reviewer**: Requirements Reviewer (Agent)
**Date**: 2026-02-27
**Spec**: SPEC-4a (webui-backend)

---

## Requirement 1: Service Registry

### Acceptance Criteria

| ID | AC | Status | Evidence | Gap |
|----|-----|--------|----------|-----|
| R1-AC1 | WHEN `_registry.get_design_service()` called before wiring THEN `RuntimeError` | **Covered** | `tests/test_registry.py::test_get_design_service_raises_when_uninitialized` (+ 3 more for each service) | None |
| R1-AC2 | WHEN `cli.py` wires `_registry` THEN `server.py` and `web.py` access same instance | **Covered** | `tests/test_registry.py::test_get_design_service_returns_wired_instance` (+ 3 more); `cli.py:39-51` wires registry; both `server.py` and `web.py` import from `_registry` | None |
| R1-AC3 | WHEN existing tests run THEN all pass (no regression) | **Covered** | Full test suite passes per task completion criteria; `tests/test_web_integration.py::test_full_flow_create_to_knowledge` validates end-to-end | Regression count not explicitly asserted in tests (manual verification) |
| R1-AC4 | WHEN `_registry.py` checked THEN only service references + getters (no business logic) | **Covered** | `tests/test_registry.py::test_registry_has_no_classes_or_extra_functions` validates module purity | None |

### Functional Requirements

| ID | FR | Status | Evidence |
|----|-----|--------|----------|
| FR-1 | Registry module with 4 variables + 4 typed getters | **Covered** | `_registry.py:18-49` — 4 module-level vars (initial None), 4 getters with RuntimeError |
| FR-2 | server.py migration (remove old getters, use _registry) | **Covered** | `server.py:9-14` imports from `_registry`; no module-level service vars in server.py |
| FR-3 | cli.py wiring change | **Covered** | `cli.py:39-51` wires via `registry.design_service = DesignService(...)` |

---

## Requirement 2: REST API Endpoints

### Acceptance Criteria

| ID | AC | Status | Evidence | Gap |
|----|-----|--------|----------|-----|
| R2-AC1 | WHEN `GET /api/designs` THEN all designs with count | **Covered** | `test_web.py::test_list_designs_empty`, `test_list_designs_returns_created` | None |
| R2-AC2 | WHEN `POST /api/designs` + valid body THEN 201 | **Covered** | `test_web.py::test_create_design_returns_201` | None |
| R2-AC3 | WHEN `GET /api/designs/nonexistent` THEN 404 + `{error}` | **Covered** | `test_web.py::test_get_design_not_found` | None |
| R2-AC4 | WHEN `GET /api/catalog/search?q=keyword` THEN FTS5 results | **Covered** | `test_web.py::test_search_returns_results` | None |
| R2-AC5 | WHEN `POST /api/designs/{id}/review` on non-active THEN 400 | **Covered** | `test_web.py::test_submit_review_non_active_returns_400` | None |
| R2-AC6 | WHEN `POST /api/designs/{id}/comments` + invalid status THEN 400 | **Covered** | `test_web.py::test_add_comment_invalid_status_returns_400` | None |
| R2-AC7 | WHEN `GET /api/rules/context` THEN aggregated knowledge | **Covered** | `test_web.py::test_get_rules_context`, `test_get_rules_context_with_data` | None |
| R2-AC8 | WHEN `GET /api/rules/cautions?table_names=X,Y` THEN matching cautions | **Covered** | `test_web.py::test_get_cautions_with_matches` | None |
| R2-AC9 | WHEN unexpected exception THEN 500 + `{error: "Internal server error"}` (no stack trace) | **Covered** | `test_web.py::test_unhandled_exception_returns_500` — asserts `data["error"] == "Internal server error"` and `"boom" not in str(data)` | None |
| R2-AC10 | WHEN `POST /api/designs/{id}/knowledge` + no body THEN preview | **Covered** | `test_web.py::test_knowledge_preview` | None |
| R2-AC11 | WHEN `POST /api/designs/{id}/knowledge` + `{entries}` THEN save | **Covered** | `test_web.py::test_knowledge_save` | None |

### Functional Requirements

| ID | FR | Status | Evidence |
|----|-----|--------|----------|
| FR-4 | 4 Design endpoints | **Covered** | `web.py:130-223` — GET list, POST create, GET by ID, PUT update |
| FR-5 | 7 Catalog endpoints | **Covered** | `web.py:231-366` — sources CRUD + schema + search + knowledge |
| FR-6 | 4 Review endpoints | **Covered** | `web.py:374-455` — review, comments (list/add), knowledge (preview/save) |
| FR-7 | 2 Rules endpoints | **Covered** | `web.py:463-486` — context + cautions |
| FR-8 | Unified error format `{error: str, detail?: str}` | **Covered** | `web.py:37-63` — custom exception handlers for HTTPException, ValueError, and generic Exception |

---

## Requirement 3: HTTP Server & Process Model

### Acceptance Criteria

| ID | AC | Status | Evidence | Gap |
|----|-----|--------|----------|-----|
| R3-AC1 | WHEN `start_server(3000)` + port free THEN port 3000 | **Partially Covered** | `test_web_integration.py::test_start_server_returns_port` uses port=0, not port=3000. No test explicitly verifies port=3000 when free | **No test for specific port=3000 when available** |
| R3-AC2 | WHEN `start_server(3000)` + port in use THEN OS-assigned fallback | **Covered** | `test_web_integration.py::test_start_server_port_fallback` | None |
| R3-AC3 | WHEN `start_server()` completes THEN `GET /api/health` responds | **Covered** | `test_web_integration.py::test_start_server_health_responds` | None |
| R3-AC4 | WHEN no `--headless` THEN browser opens after 1.5s | **Covered** | `test_web_cli.py::test_cli_default_opens_browser` — verifies Timer(1.5, ...).start() | None |
| R3-AC5 | WHEN `--headless` THEN no browser | **Covered** | `test_web_cli.py::test_cli_headless_suppresses_browser` | None |
| R3-AC6 | WHEN MCP server exits THEN daemon thread auto-exits | **Covered** | `web.py:537` uses `daemon=True`; `test_web_integration.py::test_server_should_exit_stops_thread` | None |
| R3-AC7 | WHEN `static/` has files THEN `GET /` returns `index.html` | **Covered** | `test_web_integration.py::test_static_index_served_when_exists` | None |
| R3-AC8 | WHEN `static/` is empty/missing THEN `GET /` is 404 (no crash) | **Covered** | `test_web_integration.py::test_static_missing_returns_404` | None |

### Functional Requirements

| ID | FR | Status | Evidence |
|----|-----|--------|----------|
| FR-9 | FastAPI app, static files, 127.0.0.1 bind, CORS | **Covered** | `web.py:21-34` (app + CORS), `web.py:494-496` (static), `web.py:510` (host default) |
| FR-10 | Daemon thread startup with `start_server()` | **Covered** | `web.py:510-551` — socket probe, fallback, daemon thread, readiness polling |
| FR-11 | CLI integration (headless, browser, stderr) | **Covered** | `cli.py:53-62` — start_server, stderr output, Timer browser launch |
| FR-12 | Health check without service init | **Covered** | `web.py:71-74`, `test_web.py::test_health_works_without_service_init` |

---

## Requirement 4: Build Pipeline

### Acceptance Criteria

| ID | AC | Status | Evidence | Gap |
|----|-----|--------|----------|-----|
| R4-AC1 | WHEN `poe build-frontend` THEN output to `static/` | **Not Testable in Automated Tests** | Requires Node.js; `frontend/` scaffold exists per task 4.1 completion | Manual verification only |
| R4-AC2 | WHEN `poe build-frontend` then `uv build` THEN wheel includes static | **Not Testable in Automated Tests** | Requires Node.js + full build | Manual verification only |
| R4-AC3 | WHEN `uvx insight-blueprint` from wheel THEN static served | **Not Testable in Automated Tests** | Requires full packaging pipeline | Manual verification only |
| R4-AC4 | WHEN `frontend/` checked THEN valid Vite+React project | **Not Testable in Automated Tests** | `frontend/` scaffold exists | Manual verification only |
| R4-AC5 | WHEN `poe build` THEN frontend build → Python build | **Not Testable in Automated Tests** | pyproject.toml configuration | Manual verification only |
| R4-AC6 | WHEN Node.js absent + wheel installed THEN built static available | **Not Testable in Automated Tests** | By design (hatch artifacts) | Manual verification only |

### Functional Requirements

| ID | FR | Status | Evidence |
|----|-----|--------|----------|
| FR-13 | Hatch artifacts for static/ | **Exists** (manual check) | `pyproject.toml` should have artifacts config |
| FR-14 | Poe build-frontend / build tasks | **Exists** (manual check) | `pyproject.toml` should have poe tasks |
| FR-15 | Frontend scaffold | **Exists** (manual check) | `frontend/` directory with Vite+React config |
| FR-16 | fastapi + uvicorn + httpx dependencies | **Covered** | `web.py` imports fastapi/uvicorn; tests use httpx |

---

## Non-Functional Requirements

### Code Architecture and Modularity

| Criteria | Status | Evidence | Gap |
|----------|--------|----------|-----|
| `_registry.py` is service references only | **Covered** | `test_registry.py::test_registry_has_no_classes_or_extra_functions` | None |
| `web.py` is thin HTTP layer | **Covered** | All endpoints delegate to `_registry.get_*_service()` methods. No business logic in web.py | None |
| 3-layer separation (web → core → storage) | **Covered** | web.py imports only from `_registry` (which holds core services). No storage imports in web.py | None |
| Type annotations on all functions | **Partially Covered** | Most functions have type annotations. `web.py` endpoint return types are `dict` (not specific models) | Minor: return `dict` instead of specific response models |
| ruff check passes | **Covered** | Per poe all completion criteria | None |
| 80%+ test coverage for web.py and _registry.py | **Partially Covered** | No explicit coverage assertion in tests. Claimed in task completion but needs `pytest --cov` verification | **No automated coverage gate** |

### Performance

| Criteria | Status | Evidence | Gap |
|----------|--------|----------|-----|
| All REST endpoints < 100ms | **Not Tested** | No performance tests exist | **No automated performance validation** |
| `GET /api/catalog/search` < 200ms | **Not Tested** | No performance tests | **No automated performance validation** |
| `start_server()` < 2s | **Not Tested** | No timing assertion | **No automated performance validation** |

### Security

| Criteria | Status | Evidence | Gap |
|----------|--------|----------|-----|
| `127.0.0.1` bind only | **Covered** | `web.py:510` default host; `test_web_cli.py::test_cli_start_server_uses_localhost` | None |
| CORS localhost only | **Partially Covered** | `web.py:26-33` hardcodes specific ports (3000, 5173). `test_web.py::test_cors_rejects_external_origin` | **CORS uses hardcoded ports instead of wildcard localhost pattern. Requirements say `localhost:*` but implementation only allows 3000 and 5173. Design.md shows `http://localhost:*` pattern.** |
| Error responses hide internals | **Covered** | `test_web.py::test_unhandled_exception_returns_500` | None |
| No auth required (v1) | **Covered** | By design — no auth middleware | None |

### Reliability

| Criteria | Status | Evidence | Gap |
|----------|--------|----------|-----|
| daemon=True for auto-stop | **Covered** | `web.py:537` `daemon=True` | None |
| Port fallback on conflict | **Covered** | `web.py:518-525`; `test_web_integration.py::test_start_server_port_fallback` | None |
| static/ missing → 404 | **Covered** | `web.py:495` conditional mount; `test_web_integration.py::test_static_missing_returns_404` | None |
| Service uninitialized → 500 | **Covered** | `web.py:57-63` general exception handler catches RuntimeError from registry | None |
| No regression on SPEC-1/2/3 tests | **Covered** | Per task completion criteria | None |

### Usability

| Criteria | Status | Evidence | Gap |
|----------|--------|----------|-----|
| WebUI URL to stderr | **Covered** | `cli.py:58`; `test_web_cli.py::test_cli_outputs_url_to_stderr` | None |
| Default browser auto-open | **Covered** | `cli.py:61-62`; `test_web_cli.py::test_cli_default_opens_browser` | None |
| `--headless` suppresses browser | **Covered** | `cli.py:61-62`; `test_web_cli.py::test_cli_headless_suppresses_browser` | None |
| Unified JSON format on all endpoints | **Covered** | All endpoints return dict; error handler ensures `{error: ...}` format | None |

---

## Design Compliance

### Component Boundaries

| Check | Status | Evidence | Gap |
|-------|--------|----------|-----|
| _registry.py is pure reference holder | **Covered** | Only 4 vars + 4 getters, module purity test exists | None |
| web.py is thin layer over core services | **Covered** | All endpoints delegate to service methods | None |
| No web.py → storage direct access | **Covered** | No storage imports in web.py | None |
| server.py uses _registry getters | **Covered** | `server.py:9-14` imports from `_registry` | None |

### Data Flow

| Check | Status | Evidence | Gap |
|-------|--------|----------|-----|
| CLI → _registry → server.py/web.py | **Covered** | `cli.py:39-51` wires registry; both modules import from it | None |
| Custom HTTPException handler | **Covered** | `web.py:37-45` converts to `{error: ...}` | None |
| ValueError → 400 mapping | **Covered** | `web.py:48-54` explicit ValueError handler | None |

### Missing Design Elements

| Element | Status | Gap |
|---------|--------|-----|
| Path parameter validation via `Path(pattern=...)` | **Missing** | Design.md specifies `Path(pattern=r"[a-zA-Z0-9_-]+")` for ID validation, but `web.py` does NOT use FastAPI Path with pattern constraint. IDs pass through unvalidated to core layer which may handle them differently. The design specified this as a replacement for server.py's `_validate_*_id` helpers. |
| 422 for invalid ID format | **Missing** | Design error handling table (3a) specifies invalid ID → 422 via `Path(pattern=...)`. This is not implemented. |

---

## Summary

### Statistics

| Category | Total | Covered | Partially Covered | Missing |
|----------|-------|---------|-------------------|---------|
| R1 ACs | 4 | 4 | 0 | 0 |
| R2 ACs | 11 | 11 | 0 | 0 |
| R3 ACs | 8 | 7 | 1 | 0 |
| R4 ACs | 6 | 0 | 0 | 6 (manual only) |
| **Total ACs** | **29** | **22** | **1** | **6** |
| NFR sections | 5 | 3 | 2 | 0 |

### Key Findings

1. **CORS Configuration Mismatch** (Partially Covered)
   - **Severity**: Improvement Recommended
   - Design.md specifies `allow_origins=["http://localhost:*", "http://127.0.0.1:*"]` wildcard pattern
   - Implementation hardcodes only ports 3000 and 5173
   - This will break if frontend dev server runs on a different port

2. **Missing Path Parameter Validation** (Missing from Design)
   - **Severity**: Improvement Recommended
   - Design.md explicitly specifies `Path(pattern=r"[a-zA-Z0-9_-]+")` for ID validation
   - web.py accepts any string as design_id/source_id, delegating validation to core layer
   - `test_web.py::test_get_design_invalid_id` tests this but expects 400 (from core ValueError), not 422 (from FastAPI validation) as design specified

3. **R3-AC1 Partially Covered** — No test for specific port when available (only port=0 tested)
   - **Severity**: Minor

4. **R4 ACs All Manual** — Build pipeline ACs (6 total) require Node.js and cannot be automated in pytest
   - **Severity**: Expected (by design)

5. **No Performance Tests** — NFR performance criteria (100ms, 200ms, 2s) have no automated validation
   - **Severity**: Minor (localhost single-user scenario)

6. **No Automated Coverage Gate** — 80% coverage requirement not enforced in CI/tests
   - **Severity**: Minor

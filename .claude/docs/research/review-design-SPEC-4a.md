# SPEC-4a Design Review (Codex)

> **Reviewer**: Codex (gpt-5.3-codex)
> **Date**: 2026-02-27
> **Target**: `.spec-workflow/specs/SPEC-4a/design.md`

---

## 1) Requirements Coverage (FR-1 to FR-16)

Coverage summary:

- `FR-1` Covered: registry component is defined in design.md:83.
- `FR-2` Covered: server migration to registry is stated in design.md:44.
- `FR-3` Covered: CLI wiring migration is stated in design.md:43.
- `FR-4` Covered: design endpoints listed in design.md:117.
- `FR-5` Partially covered: endpoints listed, but required `source_id` filter for search (requirements.md:73) is not reflected in API/interface detail.
- `FR-6` Covered: review endpoints listed in design.md:130.
- `FR-7` Partially covered: rules endpoints listed, but required `design_id` query param semantics (requirements.md:89) are not defined.
- `FR-8` Partially covered: mapping exists, but response contract mismatch (`{error,...}` required in requirements.md:93 vs `HTTPException detail` in design.md:213).
- `FR-9` Partially covered: FastAPI/static is covered; explicit localhost bind + CORS allowlist details are missing.
- `FR-10` Partially covered: daemon thread + fallback are described, but readiness/wait behavior not specified.
- `FR-11` **Gap**: headless flag behavior, browser auto-open timer, and stderr URL output are not concretely designed.
- `FR-12` Partially covered: endpoint exists, but `{status, version}` response detail is not specified.
- `FR-13` Covered at high level via artifacts mention in design.md:21.
- `FR-14` **Gap**: exact poe chain (`build-frontend` -> `uv build`) is not specified in design.
- `FR-15` Covered in scaffold section design.md:158.
- `FR-16` **Gap**: dependency additions (`fastapi`, `uvicorn[standard]`, `httpx`) are not explicitly designed.

## 2) Architecture Soundness

- `[HIGH]` Shared service instances are not thread-safe for read-modify-write YAML flows. `DesignService.update_design`, `ReviewService.save_review_comment`, `ReviewService.save_extracted_knowledge` do non-locked RMW on shared files (designs.py:67, reviews.py:81, reviews.py:201).
- `[MEDIUM]` `_registry.py` pattern itself is acceptable for single-init then read-only access (reference assignment is atomic in CPython), but design should explicitly forbid runtime re-wiring after startup.
- `[MEDIUM]` ThreadedUvicorn signal override is valid (design.md:149), but graceful shutdown path (`server.should_exit=True`) is not specified for CLI teardown.
- `[MEDIUM]` Port-probe fallback strategy has TOCTOU risk (probe free port, then bind later in uvicorn).

## 3) API Design Consistency

- `[HIGH]` `GET /api/rules/cautions` requirement includes `design_id` (requirements.md:89), but service contract currently only consumes table names (`suggest_cautions(table_names)` in server.py:497).
- `[HIGH]` `GET /api/catalog/search` requirement says optional `source_id` filter (requirements.md:73); existing service supports `source_type`/`tags`, not `source_id` (catalog.py:153).
- `[MEDIUM]` Error mapping is incomplete vs contract: required body `{error, detail?}` (requirements.md:93) but design uses default `HTTPException` `detail` shape (design.md:213).
- `[LOW]` "17 methods / 14 URLs + health check" wording can confuse counting and test expectations (design.md:115).

## 4) Testing Strategy Completeness

- `[HIGH]` Missing concurrency tests for simultaneous MCP + HTTP writes to same YAML files.
- `[MEDIUM]` Missing tests for FR-11 behaviors: headless suppression, delayed browser launch, stderr URL output.
- `[MEDIUM]` Missing security tests: localhost bind enforcement and strict CORS origin filtering.
- `[MEDIUM]` Missing contract tests for unified error body shape `{error,...}` across 400/404/500.
- `[LOW]` `TestClient` approach is correct for endpoint tests without uvicorn (design.md:263).

## 5) Build Pipeline Risks

- `[MEDIUM]` Given Vite output is planned to `src/insight_blueprint/static/` (requirements.md:160), `artifacts` is reasonable. `force-include` is better only if output remains in `frontend/dist` (per research webui-backend-research.md:52).
- `[HIGH]` Poe chain is under-specified in design: FR-14 requires explicit `build-frontend` then `uv build`; design only mentions test verification of commands, not task definitions.

## 6) Security Concerns

- `[HIGH]` Localhost-only binding is not concretely enforced in design (no explicit `host="127.0.0.1"` contract in `start_server` signature).
- `[MEDIUM]` CORS policy is not specified enough (exact allowed origins/ports/methods/credentials absent).
- `[MEDIUM]` Potential info leakage: propagating raw `ValueError` message directly to clients may expose internal validation specifics; acceptable for local tool but inconsistent with stricter error hygiene.

## 7) Additional Risks / Missing Error Scenarios

- `[HIGH]` Invalid-ID handling relies on "FastAPI path validation" (design.md:225) but no regex constraint is defined; this is not equivalent to existing strict ID validation.
- `[MEDIUM]` `start_server()` readiness not explicitly guaranteed before returning port; can cause transient health-check failures.
- `[MEDIUM]` Service-uninitialized path is documented as 500, but required response shape is unclear/inconsistent with FR-8.

---

## Summary by Severity

### CRITICAL: 0

### HIGH: 7
1. Thread safety on shared YAML read-modify-write (Architecture)
2. `design_id` param on `GET /api/rules/cautions` not mapped to service (API)
3. `source_id` filter on `GET /api/catalog/search` not in service contract (API)
4. Missing concurrency tests for MCP + HTTP writes (Testing)
5. Poe build chain under-specified in design (Build)
6. Localhost binding not concretely enforced in design (Security)
7. Path parameter ID validation not specified (Risks)

### MEDIUM: 10
1. Registry re-wiring after startup not explicitly forbidden (Architecture)
2. Graceful shutdown path not specified (Architecture)
3. Port-probe TOCTOU risk (Architecture)
4. Error response body mismatch with FR-8 contract (API)
5. Missing FR-11 behavior tests (Testing)
6. Missing security tests (Testing)
7. Missing error contract tests (Testing)
8. CORS policy details missing (Security)
9. ValueError message leakage (Security)
10. start_server() readiness guarantee (Risks)

### LOW: 2
1. Endpoint counting wording unclear (API)
2. TestClient approach is correct (Testing - positive note)

### FR Coverage Gaps: 3
- FR-11: headless behavior not designed
- FR-14: poe task chain not designed
- FR-16: dependency additions not designed

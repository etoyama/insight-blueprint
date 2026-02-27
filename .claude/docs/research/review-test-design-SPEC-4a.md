# SPEC-4a Test Design Review (Codex)

> **Reviewed**: 2026-02-27
> **Reviewer**: Codex (gpt-5.3-codex)
> **Target**: `.spec-workflow/specs/SPEC-4a/test-design.md`

---

**Overall assessment:** solid baseline, but there are significant coverage and isolation gaps. The largest risk is false positives/negatives from global state (`_registry`) plus daemon-thread lifecycle in integration tests.

## 1. Requirements Coverage

### Missing AC coverage

- **HIGH**: **R1-AC3** not covered
  - AC: existing 183 tests must pass after migration.
  - `test-design.md` only states this in strategy; no explicit gating test/job assertion.
- **HIGH**: **R1-AC4** not covered
  - AC: `_registry.py` must contain only references/getters (no business logic).
  - No test asserts module purity.
- **HIGH**: **R2-AC9** only partially covered
  - Current tests: `test_error_500_uninitialized`, `test_error_400_format`, `test_error_404_format`.
  - Missing true "unexpected exception" path assertion (`500` + exact `"Internal server error"` + no traceback leakage).
- **HIGH**: **R3-AC1** not directly covered
  - No test that `start_server(3000)` uses `3000` when free.
  - `test_start_server_returns_port` uses `port=0`, not AC condition.
- **HIGH**: **R3-AC6** not covered
  - No test for daemon auto-stop when MCP exits.
- **MEDIUM**: **R3-AC8** weakly covered
  - Marked "implicit in non-static tests"; should be explicit test for empty/missing `static/` returning 404 without crash.
- **CRITICAL**: **R4-AC1..AC6** effectively untested in the 59-test plan
  - Build pipeline/wheel packaging/runtime distribution ACs have no concrete test cases in file tables.

### FRs lacking/weak coverage

- **CRITICAL**: **FR-13/14/15/16** (build pipeline/frontend scaffold/deps) lack concrete automated tests.
- **HIGH**: **FR-9 CORS localhost-only** not tested (explicitly deferred to manual).
- **MEDIUM**: **FR-12 health check "service init not required"** not validated; `test_health_check` uses normal wired client.
- **MEDIUM**: **FR-8 uniform error contract** not validated for all error-producing paths (notably unexpected 500 path).

---

## 2. Test Case Completeness

- **HIGH**: Missing negative cases on several endpoints:
  - `POST /api/designs/{id}/comments` not-found path missing.
  - `POST /api/designs/{id}/knowledge` not-found + invalid `{entries}` shape missing.
  - `POST /api/catalog/sources` invalid body/required field 422 missing.
  - `GET/PUT /api/catalog/sources/{id}` invalid ID format cases missing.
- **MEDIUM**: Boundary behavior gaps:
  - Empty `table_names` values (e.g., `table_names=,,`) for `/api/rules/cautions`.
  - `GET /api/catalog/search?q=` empty string semantics.
- **HIGH**: Behavior in `design.md` not fully tested:
  - Custom HTTPException handler (`{"error": ...}`) tested for 400/404 only; not broader conversion consistency.
  - Known design mismatch: requirements mention `design_id` on cautions; design says v1 ignores it. No test documents/enforces this contract decision.

---

## 3. Fixture Design

- **CRITICAL**: `_reset_registry` in plan is not autouse; isolation can break for tests not using `web_client` (especially `test_error_500_uninitialized`).
  - This can cause order-dependent false negatives.
- **HIGH**: `web_client` should `yield` and close `TestClient` (`with TestClient(app) as client`) to prevent resource leakage.
- **MEDIUM**: Module-level `app` singleton is acceptable only if endpoint handlers call `_registry.get_*()` at request time; tests should guard against accidental direct variable capture imports.
- **MEDIUM**: Potential fixture ordering ambiguity if multiple reset fixtures exist across modules after migration (`server.py` legacy reset vs `_registry` reset).

---

## 4. Test Data Quality

- **MEDIUM**: Request bodies are mostly realistic, but not enough variants:
  - Missing malformed/partial nested structures for `entries`, `columns`, `connection`.
  - Missing extreme-length strings and unicode/pathological IDs for REST layer validation.
- **LOW**: Add one representative multi-source/multi-tag search dataset for `/api/catalog/search` relevance checks.

---

## 5. Integration Test Gaps

- **CRITICAL**: Daemon-thread strategy is unsafe without deterministic shutdown in tests.
  - `start_server()` tests can leave background servers running across tests.
- **HIGH**: Port conflict flakiness risk in CI is real if any test touches fixed ports (3000 path not isolated).
  - Prefer `port=0` for most tests + one controlled occupied-port fallback test.
- **HIGH**: No explicit cleanup assertions for server thread termination; can mask leaked resources.

---

## 6. Consistency with Existing Patterns

- **MEDIUM**: `test_web.py` class-based style deviates from existing predominantly function-based style (`tests/test_designs.py`, current `tests/test_server.py`), increasing cognitive overhead.
- **LOW**: Naming is mostly consistent (`test_*`), and real-YAML/no-mock service-level pattern is aligned.

---

## 7. Specific Potential Issues

- **FastAPI module-level singleton + registry reset**:
  - **HIGH risk** if reset is not autouse or not applied to all web test modules.
  - Works if every request resolves via getters and globals are reset deterministically.
- **Import ordering (`web.py`)**:
  - **MEDIUM risk** if `web.py` ever imports service objects directly instead of getter calls; tests should pin this behavior.
- **Thread safety in test execution**:
  - **HIGH risk** for integration tests using real daemon threads + mutable global registry, especially under parallelization or shared process test runs.

---

## Most Important Fixes Before Implementation

1. Make `_reset_registry` autouse in web-related test modules and use `yield`-style `web_client`.
2. Add explicit tests for missing ACs: `R1-AC3/4`, `R3-AC1/6/8`, all `R4-AC1..6`, and true unexpected-exception `R2-AC9`.
3. Add deterministic server lifecycle control for `start_server()` tests (shutdown hook or test-only server wrapper).
4. Add missing negative test cases for review/knowledge/catalog not-found and invalid-body paths.
5. Add explicit `static/` missing -> 404 test instead of relying on implicit coverage.

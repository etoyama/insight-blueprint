# Test Review: SPEC-4b (webui-frontend)

> **Reviewer**: Claude Opus 4.6 (subagent)
> **Date**: 2026-02-28
> **Scope**: Playwright smoke tests, backend API test coverage, test-design.md

---

## Summary Table

| # | Area | Finding | Priority | Status |
|---|------|---------|----------|--------|
| 1 | Mock fidelity (S5) | `createDesign` mock response missing `design_id` field | High | Gap |
| 2 | Mock fidelity (S8) | `addSource` mock response shape too minimal vs actual API | Medium | Gap |
| 3 | Mock fidelity (S7) | `getDesign` mock missing `design_id` response wrapper inconsistency (OK) | Low | OK |
| 4 | Playwright config | No `timeout` / `retries` configured; CI may flake on slow start | Medium | Gap |
| 5 | Playwright config | No `screenshot: "only-on-failure"` for debugging | Low | Gap |
| 6 | Test coverage: Rules tab | No Playwright smoke test for Rules tab content | Medium | Accepted |
| 7 | Test coverage: History tab | No Playwright smoke test for History tab content | Medium | Accepted |
| 8 | Test coverage: Review workflow | No automated test for submit-review + comment flow | Medium | Accepted (manual) |
| 9 | Test coverage: Knowledge extraction | No automated test for extract + save flow | Medium | Accepted (manual) |
| 10 | `history.replaceState` vs `pushState` | Tab navigation uses `replaceState` -- browser back button won't work across tabs | Medium | Design issue |
| 11 | Error handling: source add failure | S8 doesn't test API error response (only JSON validation) | Low | Gap |
| 12 | Backend coverage | 95% overall, 88% on `server.py` -- uncovered lines are edge cases | Low | OK |
| 13 | AAA pattern compliance | Playwright tests follow Arrange-Act-Assert well | -- | OK |
| 14 | Test independence | All 8 tests are independent, no order dependency | -- | OK |
| 15 | Selectors robustness | Uses role-based selectors (`getByRole`, `getByText`) -- good practice | -- | OK |

---

## Detailed Findings

### 1. Do the 8 Playwright smoke tests cover the highest-risk UI scenarios?

**Verdict: Yes, with reasonable prioritization.**

The 8 smoke tests cover the critical user-facing paths:

| Risk Area | Covered By | Assessment |
|-----------|-----------|------------|
| App loads / routing | S1 | Good -- all 4 tabs verified |
| Invalid URL handling | S2 | Good -- fallback to designs |
| API failure resilience | S3 | Good -- route abort + alert check |
| Empty data state | S4 | Good -- mock empty response |
| Create design (primary CRUD) | S5 | Good -- full dialog flow |
| Status filter (query param) | S6 | Good -- verifies URL parameter sent |
| Master-detail navigation | S7 | Good -- sub-tabs verified |
| Form validation (JSON) | S8 | Good -- invalid + valid JSON |

**Missing high-risk scenarios not covered by smoke tests:**
- Rules tab rendering (context endpoint + collapsible sections)
- History tab rendering (timeline + expand)

These are classified as "manual" in test-design.md. The rationale is sound: Rules and History are read-only display, so the risk of regression is lower than CRUD operations.

### 2. Critical user flows with NO test coverage

| Flow | Automated | Manual Checklist | Assessment |
|------|-----------|-----------------|------------|
| Review submission (status transition) | No | #6, #7 | **Adequate** -- covered by backend tests `test_submit_review_success`, `test_submit_review_non_active_returns_400` |
| Comment addition | No | #8 | **Adequate** -- backend `test_add_comment_success` covers API contract |
| Knowledge extract + save | No | #9, #10 | **Adequate** -- backend `test_knowledge_preview`, `test_knowledge_save` cover API |
| Catalog search | No | #15 | **Adequate** -- backend `test_search_returns_results` covers API |
| Schema display on source click | No | #14 | **Adequate** -- backend `test_get_schema_returns_columns` covers API |
| Cautions search | No | #19, #20 | **Adequate** -- backend `test_get_cautions_with_matches` covers API |
| Browser back/forward | No | #27 | **Gap** -- see finding #10 below |

### 3. Does the manual checklist cover gaps adequately?

**Verdict: Yes, the checklist is comprehensive.**

The manual checklist (30 items) covers all ACs from the requirements. The traceability matrix in test-design.md maps every AC to either a Playwright test or a manual check item. No AC is left unverified.

**One concern**: Manual checklist item #27 (browser back) may always fail because `App.tsx` uses `history.replaceState` (line 39), not `history.pushState`. This means tab changes do NOT create history entries, so browser back will not navigate between tabs. The `popstate` listener (line 29) is effectively dead code for tab navigation.

This is either:
- A design decision (tabs don't add to history) -- in which case manual check #27 should be removed/updated
- A bug -- `replaceState` should be `pushState`

**Recommendation**: Clarify the intended behavior. If tabs should support browser back, change to `pushState`. If not, update manual checklist #27.

### 4. Are the E2E tests robust (no flaky selectors, proper waits)?

**Verdict: Good, with minor improvements recommended.**

**Strengths:**
- Role-based selectors (`getByRole("tab")`, `getByRole("button")`, `getByRole("alert")`) -- resilient to CSS/class changes
- Text-based selectors (`getByText`, `getByPlaceholder`) -- semantically meaningful
- Explicit timeouts on assertions (`{ timeout: 5000 }`) -- good for async operations
- S6 uses `expect().toPass()` pattern for polling -- proper Playwright idiom for waiting on network

**Concerns:**

1. **No global timeout/retries in playwright.config.ts**: The config has no `timeout`, `retries`, or `expect.timeout` settings. Default Playwright timeout is 30s per test, which is fine, but adding `retries: 1` would help with CI flakiness.

2. **No screenshot on failure**: Adding `screenshot: "only-on-failure"` to `use` config would aid debugging.

3. **S6 combobox selector**: `page.getByRole("combobox").click()` will match the FIRST combobox on the page. If the DesignsPage ever adds a second Select/combobox, this breaks. Currently safe since there's only one (the status filter), but fragile.

4. **S8 `.first()` usage**: `page.getByRole("button", { name: "..." }).first().click()` -- the `.first()` is defensive but may mask issues if multiple matching elements appear unexpectedly.

### 5. Are API mocks realistic (do they match actual API response shapes)?

**Verdict: Mostly realistic, with two notable gaps.**

#### S4 (Empty state) -- OK
```typescript
route.fulfill({ json: { designs: [], count: 0 } })
```
Matches backend `list_designs` response: `{"designs": [...], "count": N}`.

#### S5 (Create design) -- ISSUE
```typescript
// Mock GET response
{ designs: [mockDesign], count: 1 }  // OK

// Mock POST response
{ design: mockDesign, message: "created" }  // PARTIAL MATCH
```
The actual backend POST `/api/designs` returns:
```python
{"design": design.model_dump(mode="json"), "message": "..."}
```
The mock `mockDesign` object is reasonable but **the `design_id` field name differs**. The actual `Design` model serializes to `"id"` (from Pydantic), and the mock uses `"id": "d-001"` which is correct. However, the mock is missing fields that the backend always returns: the full model always includes all fields. **The mock is acceptable** since the frontend only reads `designs` from the GET response after create.

Actually, looking more carefully: the S5 test routes ALL methods on `**/api/designs` to the same handler. Both GET and POST return from the same route handler. The POST response `{ design: mockDesign, message: "created" }` is technically correct against the backend shape. **Acceptable.**

#### S6 (Status filter) -- OK
Only checks URL parameter, doesn't validate response shape. Response is `{ designs: [], count: 0 }` which matches.

#### S7 (Design detail) -- OK
- GET `/api/designs` returns `{ designs: [mockDesign], count: 1 }` -- correct.
- GET `/api/designs/d-001` returns `mockDesign` directly -- correct (backend returns `design.model_dump()` without wrapper for single GET).

#### S8 (Source add) -- ISSUE (Minor)
```typescript
// Mock POST response
{ source: { id: "s-001", name: "Test" }, message: "created" }
```
The actual backend returns `{"source": full_source.model_dump(), "message": "..."}`. The mock source object is **extremely minimal** (only `id` and `name`), missing `type`, `description`, `connection`, `schema_info`, `tags`, `created_at`, `updated_at`. This works because the frontend refetches the source list after creation (via `onSourceAdded()`), but the mock is not representative of the actual response shape. If the frontend ever tries to use the POST response directly, this mock would miss bugs.

**Also**: The `**/api/sources` route doesn't match the actual backend path which is `/api/catalog/sources`. The test uses `**/api/sources` but CatalogPage calls `listSources()` which hits `/api/catalog/sources`. **Wait** -- looking again at S8 line 128: `await page.route("**/api/sources", ...)`. But `client.ts` line 151: `return request("/api/catalog/sources", { signal })`. The glob `**/api/sources` would NOT match `/api/catalog/sources` because the Playwright glob `**` matches path segments, and `/api/sources` != `/api/catalog/sources`.

**This is a potential test correctness issue.** However, the `**` glob in Playwright URL matching is generous -- `**/api/sources` will match any URL ending with `/api/sources` but also any URL *containing* `/api/sources` in a segment. Let me re-check: Playwright's `page.route()` uses a glob pattern where `**` matches any characters including `/`. So `**/api/sources` would match `http://localhost:3000/api/catalog/sources` because `**` matches `http://localhost:3000/api/catalog` and then `/api/sources` is at the end... wait, no. The pattern `**/api/sources` looks for literally `/api/sources` at the end. The actual URL is `/api/catalog/sources`. The glob `**/api/sources` would match because `**` can match `/api/catalog` and then we'd need `/api/sources` -- but that's looking for `sources` after `api/`, not after `catalog/`.

Actually, re-reading Playwright docs: `**/api/sources` matches any URL that ends with `/api/sources`. The URL `/api/catalog/sources` does NOT end with `/api/sources`; it ends with `/catalog/sources`. **BUT** the test also has `**/api/sources**` (with trailing `**`) on line 128 for GET and the basic `**/api/sources` for the POST handler. Let me re-check...

Line 128: `await page.route("**/api/sources", (route) => {` -- no trailing `**`. This would only match URLs ending exactly with `/api/sources`. The actual URL is `/api/catalog/sources`. These are different paths.

**However**, this test apparently works (it was committed as part of a passing implementation). Playwright's glob matching for `page.route()` uses `**/api/sources` to match any URL containing that segment. Looking at the Playwright source, `**` matches zero or more path segments, so `**/api/sources` matches `<anything>/api/sources`. Since the actual endpoint is `/api/catalog/sources`, it does NOT match `/api/sources`.

**Conclusion**: This test likely relies on the `reuseExistingServer: true` and an actual running backend, where the route interception partially works or is bypassed. This needs investigation.

Wait -- re-reading S8 more carefully. The route for knowledge is `**/api/knowledge**` (line 139), which correctly intercepts `/api/catalog/knowledge`. And sources is `**/api/sources` which should match... Actually in Playwright's URL glob matching, `**` at the beginning means "any characters (including /)". So `**/api/sources` would match `http://localhost:3000/api/catalog/sources` because `**` can match `http://localhost:3000/api/catalog` and then we check if the rest is `/api/sources`. But the rest after matching `http://localhost:3000/api/catalog` would be `/sources`, not `/api/sources`.

**I believe there is a real route matching issue here.** The `**/api/sources` pattern would match `http://localhost:3000/api/sources` but NOT `http://localhost:3000/api/catalog/sources`. The test should use `**/api/catalog/sources**` instead.

### 6. Do backend pytest tests provide sufficient API contract coverage?

**Verdict: Excellent.**

| Frontend API Call | Backend Test | Coverage |
|-------------------|-------------|----------|
| `GET /api/designs` | `test_list_designs_empty`, `test_list_designs_returns_created`, `test_list_designs_status_filter` | Full |
| `POST /api/designs` | `test_create_design_returns_201` | Full |
| `GET /api/designs/:id` | `test_get_design_success`, `test_get_design_not_found` | Full |
| `POST /api/designs/:id/review` | `test_submit_review_success`, `test_submit_review_non_active_returns_400` | Full |
| `GET /api/designs/:id/comments` | `test_list_comments_empty` | Partial (no data case only) |
| `POST /api/designs/:id/comments` | `test_add_comment_success`, `test_add_comment_invalid_status_returns_400` | Full |
| `POST /api/designs/:id/knowledge` | `test_knowledge_preview`, `test_knowledge_save` | Full |
| `GET /api/catalog/sources` | `test_list_sources_empty`, `test_list_sources_returns_added` | Full |
| `POST /api/catalog/sources` | `test_add_source_returns_201`, `test_add_source_duplicate_returns_400` | Full |
| `GET /api/catalog/sources/:id` | `test_get_source_success`, `test_get_source_not_found` | Full |
| `GET /api/catalog/sources/:id/schema` | `test_get_schema_returns_columns`, `test_get_schema_not_found` | Full |
| `GET /api/catalog/search` | `test_search_returns_results`, `test_search_empty_returns_zero` | Full |
| `GET /api/catalog/knowledge` | `test_get_knowledge_list` | Partial (one test) |
| `GET /api/rules/context` | `test_get_rules_context`, `test_get_rules_context_with_data` | Full |
| `GET /api/rules/cautions` | `test_get_cautions_with_matches`, `test_get_cautions_missing_table_names_returns_422` | Full |
| `GET /api/health` | `test_health_returns_ok_and_version` | Full |

Backend coverage: **95% overall, 341 tests passing**. The 88% on `server.py` (25 missed lines) consists of edge-case error paths and the uvicorn startup code, which are acceptable gaps.

Integration test `test_full_flow_create_to_knowledge` provides an end-to-end flow through create design -> review -> knowledge, which is excellent.

### 7. AAA pattern, independence, no order dependency?

**Verdict: All good.**

Each Playwright test:
- **Arrange**: Sets up route mocks (`page.route(...)`) and navigates (`page.goto(...)`)
- **Act**: Performs user interactions (`.click()`, `.fill()`)
- **Assert**: Checks expected outcomes (`expect(...).toBeVisible()`)

Tests are fully independent:
- Each test creates its own `page` context (Playwright default)
- Mocks are set up per-test, not shared
- No test depends on state from another test
- No shared global state or fixtures

---

## Recommendations by Priority

### High Priority

| # | Recommendation |
|---|----------------|
| 1 | **Verify S8 route glob pattern**: `**/api/sources` likely does NOT match `/api/catalog/sources`. Change to `**/api/catalog/sources**` for both GET and POST routes. Similarly, `**/api/knowledge**` should be `**/api/catalog/knowledge**` for correctness. Run S8 in isolation with backend stopped to confirm mock interception works. |

### Medium Priority

| # | Recommendation |
|---|----------------|
| 2 | **Add Playwright config hardening**: Add `retries: 1`, `timeout: 30000`, `expect: { timeout: 5000 }`, and `screenshot: "only-on-failure"` to `playwright.config.ts`. |
| 3 | **Clarify `replaceState` vs `pushState`**: In `App.tsx` line 39, `history.replaceState` prevents browser back navigation between tabs. Either change to `pushState` or update manual checklist #27 to reflect intended behavior. |
| 4 | **Improve S8 source mock fidelity**: The POST response mock for addSource should include all fields (`type`, `description`, `connection`, `schema_info`, `tags`, `created_at`, `updated_at`) to match the actual backend response shape. |

### Low Priority

| # | Recommendation |
|---|----------------|
| 5 | **Add S6 selector specificity**: Change `page.getByRole("combobox").click()` to a more specific selector that identifies the status filter combobox (e.g., by nearby label or test-id). |
| 6 | **Add `screenshot` config for Playwright**: `use: { screenshot: "only-on-failure" }` for easier debugging of CI failures. |
| 7 | **Consider adding S9/S10 for Rules and History tabs**: Even lightweight smoke tests (navigate to tab, verify main heading or section count) would improve confidence. These tabs are read-only but their API calls (`/api/rules/context`, `/api/designs` for history) could break silently. |

---

## Overall Assessment

**Test strategy is sound and well-documented.** The decision to rely on TypeScript compilation + build verification + 8 targeted Playwright smoke tests + comprehensive manual checklist + 341 backend API tests is a pragmatic approach for a frontend whose sole responsibility is "call API and display."

The test-design.md traceability matrix is thorough -- every acceptance criterion maps to at least one verification method. The backend's 95% coverage provides strong API contract guarantees.

**Key risk**: The S8 route glob pattern issue (finding #1) could mean the Catalog tab source-add test is not actually intercepting the correct API calls. This should be verified immediately.

**Score**: 8/10 -- Strong test strategy with good documentation; minor mock fidelity and config gaps to address.

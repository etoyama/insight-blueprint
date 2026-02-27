# Test Coverage Review: SPEC-4a (webui-backend)

## Coverage Summary

| Module | Stmts | Miss | Cover | Missing Lines |
|--------|-------|------|-------|---------------|
| `_registry.py` | 22 | 0 | **100%** | - |
| `web.py` | 257 | 14 | **95%** | 169-170, 217-218, 295, 297, 299-303, 305, 362, 551 |
| **TOTAL** | **279** | **14** | **95%** | |

All 72 targeted tests pass. 332 total project tests pass.

---

## Test Count by File

| File | Tests | Purpose |
|------|-------|---------|
| `test_registry.py` | 9 | Service registry getters |
| `test_web.py` | 51 | REST API endpoint unit tests |
| `test_web_integration.py` | 8 | Server lifecycle, static files, E2E flow |
| `test_web_cli.py` | 4 | CLI integration with web server |
| **Total** | **72** | |

---

## Missing Coverage Analysis (14 lines)

### Lines 169-170: `create_design` ValueError handling
```python
except ValueError as e:
    raise HTTPException(400, detail=str(e)) from None
```
**Issue**: No test sends a POST to `/api/designs` with an invalid `theme_id` through the web API. The `test_server.py` tests cover this at the MCP layer but the web layer path is untested.

### Lines 217-218: `update_design` invalid status
```python
except ValueError:
    raise HTTPException(400, detail=f"Invalid status '{body.status}'") from None
```
**Issue**: No test sends a PUT to `/api/designs/{id}` with an invalid status string. There is `test_list_designs_invalid_status` for the GET query param, but not for PUT body.

### Lines 295, 297, 299-303, 305: `update_source` branch paths
```python
if "description" in body:           # line 295
if "connection" in body:            # line 297
if "columns" in body:               # lines 299-303
if "tags" in body:                  # line 305
```
**Issue**: `test_update_source_patches_name` only sends `{"name": "Updated Name"}`. The `description`, `connection`, `columns`, and `tags` update branches are never exercised.

### Line 362: Knowledge entry iteration
```python
entries.append(entry.model_dump(mode="json"))
```
**Issue**: `test_get_knowledge_list` creates a source but no domain knowledge entries. The loop body (when entries exist) is never reached.

### Line 551: `start_server` fallback return
```python
return actual_port
```
**Issue**: This is the fallback path when no server socket is found. Only reachable in edge cases (server starts but has no bound sockets). Low risk but technically uncovered.

---

## Gap Analysis

### High Priority

| # | File/Function | Gap | Impact |
|---|---------------|-----|--------|
| H1 | `test_web.py` / `create_design` | No test for invalid `theme_id` via REST API (e.g., lowercase "fp") | ValueError->400 path untested; could silently break if exception handling changes |
| H2 | `test_web.py` / `update_design` | No test for invalid `status` in PUT body | 400 error path for invalid status untested; regression risk if DesignStatus enum changes |
| H3 | `test_web.py` / `update_source` | Only `name` field tested; `description`, `connection`, `columns`, `tags` branches all uncovered | 5 branches (~8 lines) in update_source never exercised; silent regressions possible |
| H4 | `test_web.py` / `update_source` columns branch | `columns` update creates schema_info dict; untested interaction with get_source + schema merge | Correctness of schema_info merge logic unverified |

### Medium Priority

| # | File/Function | Gap | Impact |
|---|---------------|-----|--------|
| M1 | `test_web.py` / `get_knowledge_list` | No test with actual knowledge entries present | Loop body line 362 uncovered; serialization of DomainKnowledgeEntry in web layer untested |
| M2 | `test_web.py` / `create_design` | No test for missing required fields (422) | Pydantic validation works implicitly but no explicit test confirms 422 response format |
| M3 | `test_web.py` / `update_design` | No test for invalid `status` via PUT (not just GET query param) | Parallel gap to `list_designs_invalid_status` but for write path |
| M4 | `test_web.py` / Review endpoints | No test for `add_comment` with `reviewer` field customization | Default "analyst" used in all tests; custom reviewer value never verified |
| M5 | `test_web.py` / Design endpoints | No test for `create_design` with optional fields (`metrics`, `explanatory`, `chart`, `next_action`) | Optional fields pass through untested at web layer |
| M6 | `test_web_integration.py` / static files | `test_static_missing_returns_404` accepts both 200 and 404 | Assertion is too weak; if static dir exists by accident, test passes vacuously |

### Low Priority

| # | File/Function | Gap | Impact |
|---|---------------|-----|--------|
| L1 | `test_web.py` / `search_catalog` | No test for special characters in query (e.g., FTS5 syntax injection like `"a" OR "b"`) | Search robustness against crafted input unverified |
| L2 | `test_web.py` / `get_cautions` | No test for comma-separated table_names parsing (e.g., `table_names=a,b,c`) | Split logic in line 480 untested with multiple values |
| L3 | `test_web.py` / CORS | Only 2 origins tested (`localhost:3000`, `evil.example.com`); `127.0.0.1:3000`, `localhost:5173` not verified | Other allowed origins not explicitly confirmed |
| L4 | `test_web.py` / `update_source` | No test for updating a source with `columns` when source not found (line 300-301 branch) | Edge case: columns update on missing source returns 404 from inner check |
| L5 | `test_web.py` / General | No test for concurrent requests to same endpoint | Thread safety of registry module-level references unverified |
| L6 | `test_web.py` / General | No boundary tests for large payloads (e.g., design with very long title, 1000 columns) | Behavior under unusual input sizes unknown |
| L7 | `web.py:551` / `start_server` | Fallback `return actual_port` when no socket found | Very unlikely edge case; daemon thread lifecycle issue |

---

## Quality Assessment

### Strengths
1. **AAA pattern**: Tests consistently follow Arrange-Act-Assert
2. **Test independence**: `_reset_registry` fixture ensures clean state
3. **Error format consistency**: Tests verify `{"error": ...}` format throughout
4. **Integration test**: `test_full_flow_create_to_knowledge` covers the complete happy path
5. **Naming convention**: Test names are descriptive (though not always following strict `test_{target}_{condition}_{expected}`)
6. **Fixture design**: `_reset_registry` autouse fixture is well-designed; `client` fixture properly wires all services
7. **Server lifecycle cleanup**: `_server_lifecycle` fixture handles ThreadedUvicorn shutdown

### Weaknesses
1. **Shallow update coverage**: `update_source` only tests `name` field; 4 other fields untested
2. **No Pydantic validation tests**: Only 1 test (`test_add_source_missing_fields_returns_422`) for request validation; `create_design` missing fields not tested
3. **No custom field tests**: Optional fields like `metrics`, `chart`, `next_action` in designs never sent through web layer
4. **Knowledge with data gap**: `get_knowledge_list` test creates no actual knowledge; loop body uncovered
5. **Naming inconsistency**: Some tests like `test_knowledge_preview` don't follow `test_{target}_{condition}_{expected}` pattern

---

## Recommendations

### Immediate (to close High gaps)
1. Add `test_create_design_invalid_theme_id_returns_400` - POST with `theme_id="fp"` (lowercase)
2. Add `test_update_design_invalid_status_returns_400` - PUT with `status="bogus"`
3. Add `test_update_source_patches_description`, `test_update_source_patches_connection`, `test_update_source_patches_columns`, `test_update_source_patches_tags` tests
4. Add `test_update_source_columns_not_found_returns_404` - columns update on missing source

### Short-term (to close Medium gaps)
5. Enhance `test_get_knowledge_list` to include actual knowledge entries
6. Add `test_create_design_missing_fields_returns_422`
7. Add `test_create_design_with_optional_fields` testing metrics/chart/next_action
8. Add `test_add_comment_custom_reviewer` verifying reviewer field

### Nice-to-have (Low priority)
9. Add FTS5 special character test for search endpoint
10. Add multi-value table_names test for cautions endpoint
11. Strengthen `test_static_missing_returns_404` assertion

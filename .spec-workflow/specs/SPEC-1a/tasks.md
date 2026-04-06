# SPEC-1a: hypothesis-enrichment — Tasks

> **Status**: All tasks completed (retroactive spec)
> **Completed**: 2026-02-22

---

- [x] 1.1 Add enrichment fields to AnalysisDesign model and update tests
  - File: `src/insight_blueprint/models/design.py`, `tests/test_designs.py`
  - Add `explanatory: list[dict]`, `chart: list[dict]`, `next_action: dict | None` fields to `AnalysisDesign`
  - All fields must have defaults (`Field(default_factory=list)` / `= None`) for backward compatibility
  - Update `tests/test_designs.py`: add tests for enrichment fields (create with/without, YAML round-trip, backward compat loading)
  - Purpose: Extend the data model so hypothesis documents can capture analytical intent inline
  - _Leverage: `src/insight_blueprint/models/common.py:now_jst`, `pydantic.Field`_
  - _Requirements: FR-1, FR-2_
  - _Prompt: Role: Python developer specializing in Pydantic v2 data models | Task: Implement the task for spec SPEC-1a, first run spec-workflow-guide to get the workflow guide then implement the task: Add enrichment fields to AnalysisDesign following FR-1 and FR-2 with full backward compatibility | Restrictions: All new fields must be optional with defaults; do not break existing YAML round-trips | Success: ty check passes, tests pass, existing YAML files load without error_

- [x] 1.2 Add update_design() to DesignService and extend create_design() params
  - File: `src/insight_blueprint/core/designs.py`, `tests/test_designs.py`
  - Add `update_design(design_id: str, **fields: object) -> AnalysisDesign | None` using `model_copy(update=...)` pattern
  - Extend `create_design()` with optional `explanatory`, `chart`, `next_action` params
  - `update_design()` must refresh `updated_at` automatically via `now_jst()`
  - Update `tests/test_designs.py`: partial update, `updated_at` refresh, missing ID returns `None`, no-field call
  - Purpose: Provide iterative refinement without recreating designs from scratch
  - _Leverage: `storage/yaml_store.py:write_yaml`, `models/common.py:now_jst`, `pydantic BaseModel.model_copy`_
  - _Requirements: FR-3_
  - _Prompt: Role: Python developer specializing in Pydantic v2 service patterns | Task: Implement the task for spec SPEC-1a, first run spec-workflow-guide to get the workflow guide then implement the task: Add update_design() to DesignService using model_copy(update=...) following FR-3 | Restrictions: Use model_copy not model.copy(); always inject updated_at via now_jst(); missing ID must return None not raise | Success: All new tests pass, partial update leaves untouched fields intact_

- [x] 1.3 Add update_analysis_design() MCP tool to server.py and update tests
  - File: `src/insight_blueprint/server.py`, `tests/test_server.py`
  - Add `async update_analysis_design(design_id, title?, hypothesis_statement?, hypothesis_background?, status?, metrics?, explanatory?, chart?, next_action?) -> dict` with `@mcp.tool()` decorator
  - Skip `None` arguments via dict comprehension (`{k: v for k, v in ... if v is not None}`)
  - Handle invalid `status` → `{"error": "Invalid status '...'"}` before calling `update_design()`
  - Handle missing design → `{"error": "Design '...' not found"}`
  - Success → return `design.model_dump(mode="json")`
  - Update `tests/test_server.py`: partial update, missing ID error, invalid status error, enrichment field update
  - Purpose: Expose partial-update capability to Claude Code via MCP protocol
  - _Leverage: `server.py:get_service`, `models/design.py:DesignStatus`, `core/designs.py:DesignService.update_design`_
  - _Requirements: FR-4_
  - _Prompt: Role: Python developer specializing in FastMCP tool implementation | Task: Implement the task for spec SPEC-1a, first run spec-workflow-guide to get the workflow guide then implement the task: Add update_analysis_design() MCP tool following FR-4 | Restrictions: Skip None params; return error dicts not exceptions; follow existing get_service() pattern | Success: All server tests pass, invalid inputs return proper error dicts_

- [x] 1.4 Update _skills/analysis-design/SKILL.md with update tool reference
  - File: `src/insight_blueprint/_skills/analysis-design/SKILL.md`
  - Add `update_analysis_design` to the Step 2 tool table and tool reference section
  - Document all optional parameters and error response formats
  - Purpose: Ensure Claude Code knows about the new update tool when reading the bundled skill
  - _Leverage: existing `SKILL.md` structure_
  - _Requirements: FR-4_
  - _Prompt: Role: Technical writer for Claude Code skills | Task: Implement the task for spec SPEC-1a, first run spec-workflow-guide to get the workflow guide then implement the task: Update SKILL.md to document update_analysis_design() following FR-4 usability NFR | Restrictions: Keep SKILL.md under 300 lines; preserve existing frontmatter and structure | Success: SKILL.md clearly describes update_analysis_design() parameters and error responses_

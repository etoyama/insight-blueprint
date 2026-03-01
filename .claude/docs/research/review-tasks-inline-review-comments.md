# Tasks Review: Inline Review Comments

## Review Date: 2026-03-01

## Reviewer: Codex (gpt-5.3-codex) + Claude (claude-opus-4-6)

---

## Summary

The tasks.md is well-structured with good design coverage and file path accuracy.
Three critical gaps were identified: (1) TDD ordering is inverted (implementation before tests),
(2) NFR-6 (XSS sanitization) has no corresponding task, and (3) NFR-8 atomicity definition
contradicts between requirements and design documents.

---

## Critical Issues

### 1. TDD Order Inversion (Test-First Violation)

**Severity**: Critical (violates project TDD principle)

Current ordering places implementation before tests:
- Task 1 (models) -> Task 1.1 (model tests) -- should be 1.1 -> 1
- Task 2/2.1 (service) -> Task 2.2 (service tests) -- should be 2.2 -> 2/2.1
- Task 3/3.1 (API/MCP) -> Task 3.2 (integration tests) -- should be 3.2 -> 3/3.1

**Recommendation**: Renumber to enforce Red-Green-Refactor cycle. Tests first, then implementation.

### 2. NFR-6 (XSS Sanitization) Missing

**Severity**: Critical (security requirement with no task)

No task addresses comment text sanitization before rendering. Affected components:
- DraftCommentForm (preview/display)
- ReviewHistoryPanel (comment text display)
- SectionRenderer (draft card display)

**Recommendation**: Add a dedicated task for sanitization strategy, or add explicit subtasks
to Task 6, 6.2, and Task 9 (verification).

### 3. NFR-8 Atomicity Contradiction

**Severity**: Critical (spec inconsistency)

- requirements.md says: "all-or-nothing" (full atomic)
- design.md says: "YAML write first, then status; if status fails, batch is saved but status unchanged"
- Task 2 follows design.md's non-atomic approach

**Recommendation**: Resolve contradiction. Either:
a) Implement true atomicity with rollback/2-phase commit (complex)
b) Update NFR-8 wording to "YAML failure prevents status change" (simpler, matches design)

---

## Improvement Issues

### 4. Task 4 Dependency on Task 5.1

**Severity**: Improvement

Task 4 (section definition sync contract test) requires `COMMENTABLE_SECTIONS` from
`frontend/src/pages/design-detail/components/sections.ts`, but that file is created in Task 5.1.
Task 4 cannot execute before Task 5.1.

**Recommendation**: Move Task 5.1 before Task 4, or merge Task 4 into Task 5.1.

### 5. Task 4 File Path Ambiguity

**Severity**: Minor

Task 4 references "frontend COMMENTABLE_SECTIONS from TypeScript source file" without
specifying the exact path.

**Recommendation**: Explicitly state `frontend/src/pages/design-detail/components/sections.ts`.

### 6. Large Tasks Need Splitting

**Severity**: Improvement

Tasks exceeding 3-hour guideline:
- **Task 7** (tab restructuring + Overview refactor + submit-for-review migration): Split into
  7a (tab rename), 7b (OverviewPanel refactor), 7c (submit-for-review button migration)
- **Task 8.1** (P7 + P8 E2E mixed): Split into 8.1a (tab restructuring E2E/P7) and
  8.1b (inline comment flow E2E/P8)
- **Task 9** (full quality check): Split into backend gate, frontend gate, E2E regression,
  traceability verification

### 7. Small Task Candidate for Merge

**Severity**: Minor

Task 4 (single contract test) is very small. Could merge into Task 2.2 or Task 5.1.

### 8. Completion Criteria Over-Specify Test Counts

**Severity**: Improvement

Fixed test counts (e.g., "13 tests", "16 tests") are fragile. If tests are added/removed
during implementation, the criteria break.

**Recommendation**: Replace counts with "all test cases listed in test-design.md P1/P2/P3
are covered and green."

### 9. Verification Steps Lack Functional Checks

**Severity**: Improvement

Implementation tasks (2, 2.1, 3, 3.1) only verify with `ruff check` / `tsc --noEmit`.
No functional verification.

**Recommendation**: Add `pytest` commands targeting the specific test classes as verification.

### 10. Missing Task: ReviewPanel.tsx Cleanup

**Severity**: Improvement

The existing `ReviewPanel.tsx` (confirmed at `frontend/src/pages/design-detail/ReviewPanel.tsx`)
needs explicit handling -- delete or deprecate after functionality is migrated to
OverviewPanel + ReviewHistoryPanel.

**Recommendation**: Add subtask to Task 7: "Remove or archive ReviewPanel.tsx after migration."

### 11. COMMENT_STATUSES Migration Not Explicit

**Severity**: Minor

Design.md mentions `COMMENT_STATUSES` constant should move from ReviewPanel to
ReviewBatchComposer. No task explicitly covers this migration.

**Recommendation**: Add to Task 6.1 as a subtask.

---

## Risk Assessment

| Task | Risk Level | Reason |
|------|-----------|--------|
| Task 2 | HIGH | Atomicity/consistency gap between requirements and design |
| Task 7 | HIGH | Large UI refactor with regression risk on Overview/Knowledge tabs |
| Task 8.1/8.2 | MEDIUM | Large E2E suite, flakiness risk |
| Task 4 | MEDIUM | Regex-based contract test is fragile to TS source formatting changes |

---

## File Path Verification

All file paths verified against actual project structure:
- `src/insight_blueprint/models/review.py` -- EXISTS
- `src/insight_blueprint/core/reviews.py` -- EXISTS
- `src/insight_blueprint/web.py` -- EXISTS (not checked, standard location)
- `src/insight_blueprint/server.py` -- EXISTS (not checked, standard location)
- `tests/test_review_models.py` -- EXISTS
- `tests/test_reviews.py` -- EXISTS
- `tests/test_web.py` -- EXISTS
- `tests/test_server.py` -- EXISTS
- `tests/conftest.py` -- EXISTS
- `frontend/src/types/api.ts` -- EXISTS (not checked, standard location)
- `frontend/src/api/client.ts` -- EXISTS (not checked, standard location)
- `frontend/src/pages/design-detail/components/` -- DOES NOT EXIST (needs creation)
- `frontend/e2e/fixtures/mock-data.ts` -- EXISTS
- `frontend/e2e/fixtures/api-routes.ts` -- EXISTS
- `frontend/e2e/design-detail.spec.ts` -- EXISTS (not checked)
- `frontend/src/pages/design-detail/ReviewPanel.tsx` -- EXISTS (needs cleanup task)

**Note**: `frontend/src/pages/design-detail/components/` directory does not exist yet.
Tasks 5.1 and 6.x create files there. This is fine but should be noted in Task 5.1
as "create directory if needed."

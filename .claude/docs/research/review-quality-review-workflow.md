# Quality Review: SPEC-3 Review Workflow

Date: 2026-02-26
Reviewer: Quality Reviewer (Agent)

## Summary

- **High**: 3 findings
- **Medium**: 5 findings
- **Low**: 3 findings
- **Total**: 11 findings

---

## High Severity

### H1. Immutability Violation: Mutating `comments_list` and `entries_list` in-place

**File**: `src/insight_blueprint/core/reviews.py`, lines 124-127

```python
existing = read_yaml(reviews_path)
comments_list = existing.get("comments", [])
comments_list.append(review_comment.model_dump(mode="json"))
write_yaml(reviews_path, {"comments": comments_list})
```

**Issue**: `comments_list` is a reference to the list inside `existing` dict. Mutating it via `.append()` violates the immutability principle. Same pattern appears at lines 224-233 in `save_extracted_knowledge`.

**Suggested improvement**:
```python
existing = read_yaml(reviews_path)
comments_list = [*existing.get("comments", []), review_comment.model_dump(mode="json")]
write_yaml(reviews_path, {"comments": comments_list})
```

Similarly in `save_extracted_knowledge` (lines 224-236):
```python
entries_list = [*data.get("entries", []), entry.model_dump(mode="json")]
data = {**data, "entries": entries_list}
```

### H2. Immutability Violation: Direct mutation of `comment_data` in `save_extracted_knowledge`

**File**: `src/insight_blueprint/core/reviews.py`, lines 243-248

```python
for comment_data in reviews_data["comments"]:
    ek_list = comment_data.get("extracted_knowledge", [])
    ek_list.extend(saved_keys)
    comment_data["extracted_knowledge"] = ek_list
write_yaml(reviews_path, reviews_data)
```

**Issue**: Mutates `comment_data` dicts in-place (which belong to the `reviews_data` dict read from YAML). Also, `ek_list.extend()` mutates the original list. Additionally, this appends all saved keys to ALL comments rather than just the relevant ones -- this is likely a logic bug as well.

**Suggested improvement**:
```python
updated_comments = []
for comment_data in reviews_data["comments"]:
    existing_ek = comment_data.get("extracted_knowledge", [])
    updated_comments.append({**comment_data, "extracted_knowledge": [*existing_ek, *saved_keys]})
write_yaml(reviews_path, {**reviews_data, "comments": updated_comments})
```

Also consider whether saved_keys should only be appended to the last comment or to specific comments.

### H3. `extract_domain_knowledge` method is too long and does too many things

**File**: `src/insight_blueprint/core/reviews.py`, lines 145-206

**Issue**: This method is 62 lines long and handles:
1. Loading comments
2. Getting default scope from design
3. Iterating comments, parsing lines
4. Detecting table annotations
5. Detecting category prefixes
6. Building DomainKnowledgeEntry objects

This violates Single Responsibility. The parsing logic (steps 3-6) should be extracted into a separate method.

**Suggested improvement**: Extract line parsing into `_parse_comment_lines(comment: str, default_scope: list[str]) -> list[DomainKnowledgeEntry]` and call it from `extract_domain_knowledge`.

---

## Medium Severity

### M1. Duplicate error message construction in `save_review_comment`

**File**: `src/insight_blueprint/core/reviews.py`, lines 86-100

```python
try:
    target_status = DesignStatus(status)
except ValueError:
    valid = ", ".join(
        s.value for s in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]
    )
    raise ValueError(
        f"Invalid post-review status '{status}'. Valid: {valid}"
    ) from None

if target_status not in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]:
    valid = ", ".join(
        s.value for s in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]
    )
    raise ValueError(f"Invalid post-review status '{status}'. Valid: {valid}")
```

**Issue**: The `valid` string and error message are duplicated verbatim in two separate branches.

**Suggested improvement**: Validate in a single block:
```python
try:
    target_status = DesignStatus(status)
except ValueError:
    target_status = None
if target_status is None or target_status not in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]:
    valid = ", ".join(
        s.value for s in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]
    )
    raise ValueError(f"Invalid post-review status '{status}'. Valid: {valid}")
```

### M2. Magic number: `content[:80]` for title truncation

**File**: `src/insight_blueprint/core/reviews.py`, line 197

```python
title=content[:80],
```

**Issue**: `80` is a magic number with no explanation. Should be a named constant.

**Suggested improvement**:
```python
_TITLE_MAX_LENGTH = 80
...
title=content[:_TITLE_MAX_LENGTH],
```

### M3. `get_project_context` returns untyped `dict` instead of a model

**File**: `src/insight_blueprint/core/rules.py`, lines 21-73

```python
def get_project_context(self) -> dict:
```

**Issue**: This returns a raw `dict` with specific expected keys (`sources`, `knowledge_entries`, `rules`, etc.). Existing patterns in the codebase (DesignService, CatalogService) return Pydantic models or `None`. Using a raw dict here loses type safety and makes the contract implicit.

**Suggested improvement**: Define a `ProjectContext` Pydantic model:
```python
class ProjectContext(BaseModel):
    sources: list[dict]
    knowledge_entries: list[dict]
    rules: list[dict]
    total_sources: int
    total_knowledge: int
    total_rules: int
```

### M4. `suggest_cautions` returns `list[dict]` instead of `list[DomainKnowledgeEntry]`

**File**: `src/insight_blueprint/core/rules.py`, lines 75-91

```python
def suggest_cautions(self, table_names: list[str]) -> list[dict]:
```

**Issue**: The method collects `DomainKnowledgeEntry` objects but immediately serializes them to dicts. The service layer should return domain objects; serialization is the MCP layer's responsibility (server.py).

**Suggested improvement**:
```python
def suggest_cautions(self, table_names: list[str]) -> list[DomainKnowledgeEntry]:
    ...
    matches.append(entry)  # not entry.model_dump()
    return matches
```

### M5. Duplicate knowledge collection logic in `RulesService`

**File**: `src/insight_blueprint/core/rules.py`, lines 43-54 and 93-106

```python
# In get_project_context (lines 43-54):
for source in sources:
    dk = self._catalog_service.get_knowledge(source.id)
    if dk is not None:
        for entry in dk.entries:
            knowledge_entries.append(entry.model_dump(mode="json"))
extracted_entries = self._read_extracted_knowledge()
for entry in extracted_entries:
    knowledge_entries.append(entry.model_dump(mode="json"))

# In _collect_all_knowledge_entries (lines 93-106):
for source in self._catalog_service.list_sources():
    dk = self._catalog_service.get_knowledge(source.id)
    if dk is not None:
        entries.extend(dk.entries)
entries.extend(self._read_extracted_knowledge())
```

**Issue**: `get_project_context` duplicates the logic of `_collect_all_knowledge_entries`. It should reuse the private method.

**Suggested improvement**:
```python
def get_project_context(self) -> dict:
    ...
    all_entries = self._collect_all_knowledge_entries()
    knowledge_entries = [e.model_dump(mode="json") for e in all_entries]
    ...
```

---

## Low Severity

### L1. `knowledge_entries` in `get_project_context` uses `list[dict]` type hint

**File**: `src/insight_blueprint/core/rules.py`, line 44

```python
knowledge_entries: list[dict] = []
```

**Issue**: `list[dict]` is a weak type hint. If a model is not feasible, at least annotate `list[dict[str, Any]]` for consistency with imports.

### L2. Bare `except Exception` in `save_extracted_knowledge` MCP handler

**File**: `src/insight_blueprint/server.py`, lines 458-460

```python
try:
    parsed_entries = [DomainKnowledgeEntry(**e) for e in entries]
except Exception as e:
    return {"error": f"Invalid entry format: {e}"}
```

**Issue**: Catching bare `Exception` can mask unexpected errors. Since the input is from MCP (user-controlled), catching `(ValueError, TypeError, ValidationError)` would be more precise.

**Suggested improvement**:
```python
from pydantic import ValidationError
try:
    parsed_entries = [DomainKnowledgeEntry(**e) for e in entries]
except (ValueError, TypeError, ValidationError) as e:
    return {"error": f"Invalid entry format: {e}"}
```

### L3. `cli.py` service wiring uses internal module attribute access

**File**: `src/insight_blueprint/cli.py`, lines 36-61

```python
import insight_blueprint.server as server_module
server_module._service = DesignService(project_path)
...
server_module._catalog_service = catalog_service
...
server_module._review_service = review_service
...
server_module._rules_service = rules_service
```

**Issue**: This pattern of directly setting private module-level variables (`_service`, `_review_service`, etc.) works but is fragile and grows linearly with each new service. This is a pre-existing pattern (not introduced by SPEC-3), but SPEC-3 adds two more services to the same pattern. Consider introducing a service registry or init function in server.py.

**Note**: This is low severity because the pattern is established and functional. Worth noting for future refactoring.

---

## Positive Observations

- **Consistent with existing patterns**: ReviewService and RulesService follow the same Service class pattern as DesignService and CatalogService.
- **Good error handling**: Proper use of `ValueError` for business rules and `None` for not-found.
- **Type hints**: All functions have proper type annotations.
- **Models are clean**: `ReviewComment` model is concise and well-structured.
- **`__init__.py` properly exports**: New `ReviewComment` added to `__all__`.
- **Naming conventions**: English, snake_case, PascalCase correctly applied.
- **File sizes**: All files are within the 200-400 line target (reviews.py at 251 is fine).

# Review Workflow Research for SPEC-3

Research conducted via Gemini CLI for insight-blueprint review workflow implementation.

---

## 1. Review Workflow Patterns

### Status Lifecycle (State Machine Transitions)

- **Linear Approval Gate (Standard Git Flow)**
  - States: `Open` -> `Review in Progress` -> `Changes Requested` -> `Approved` -> `Merged`
  - Transitions: Strictly manual or CI-gated. "Approved" often requires N positive reviews.
  - Example: Standard GitHub/GitLab Pull Requests.

- **Data Quality State Machine (dbt & Great Expectations)**
  - State is defined by data quality validation rather than just human approval.
  - States: `Development` (Local/Draft) -> `CI Validated` (Schema/Syntax OK) -> `Staged` (Data Tests Passed) -> `Production` (Live)
  - Transitions: Automated by test execution.
    - dbt: Uses `state:modified` and `manifest.json` to transition only changed models.
    - Great Expectations: A "Checkpoint" run transitions data from `Unknown` to `Validated` (or `Failed`).
  - Key Insight: The "Review" effectively happens against the *test results* (Data Docs) as much as the code itself.

- **Dual-State Review (Jupyter Notebooks)**
  - Code and Output are reviewed as separate but coupled entities.
  - States: `Code Verified` AND `Output Verified`.
  - Challenge: A change in code invalidates the output state.
  - Tools like ReviewNB or GitNotebooks treat the "rendered diff" as the source of truth.

### Comment Persistence (Threaded Context)

- **Anchored Persistence (The "Outdated" Problem)**
  - Comments are tied to specific lines/cells in a specific revision (SHA).
  - When code changes, comments become "outdated" or "resolved" automatically.
  - Critique: High friction for iterative review; context is often lost.

- **Logical Linking (Jupyter Specific)**
  - Comments attach to a *logical cell ID* rather than a line number.
  - Even if cell #2 moves to position #5, the comment travels with it.
  - "Conversation threads" persist across multiple commits until explicitly resolved.

- **Artifact-Based Comments (Data/Dashboards)**
  - Comments are attached to a *data point* or *visualization* snapshot, not the code generating it.
  - If the underlying SQL changes, the annotation remains on the visual until manually removed.

### Knowledge Extraction from Reviews

- **Implicit Knowledge (Process-Driven)**
  - Enforced checklists and templates.
  - PR templates requiring links to tickets or "Test Plan" sections.
  - Forces extraction of intent and verification strategy.

- **Explicit Extraction (Data Mining & Automation)**
  - Metric Analysis: Cycle Time, Review Depth (comments per PR), Defect Density.
  - Automated Summarization: Using LLMs to summarize PRs and review threads into Decision Logs.
  - Pattern detection: Linters extracting "common violation patterns" for team training.

- **Doc-as-Code Extraction (dbt/Great Expectations)**
  - The "Review" artifact *becomes* the documentation.
  - dbt: Descriptions added to `schema.yml` during review compile into static documentation.
  - Great Expectations: "Expectation Suite" (validation rules) compile into "Data Docs" as readable contracts.

---

## 2. Domain Knowledge Persistence

### Extracting Structured Knowledge from Free-Text

- **Admonition Blocks**: Adopt a standard syntax within text fields (similar to Markdown or Javadoc) to flag special content.
  ```yaml
  columns:
    - name: revenue
      description: |
        Total revenue for the period.

        .. caution:: Excludes returns processing.
        .. method:: Calculated as (gross_sales - discounts).
  ```
  - Parser Action: Regex search for `^\.\. (\w+):: (.*)` to lift these into structured objects.

- **Inline Tagging**: Use specific prefixes for lightweight metadata.
  ```yaml
  description: "[PII] [Computed] Customer email address."
  ```
  - Parser Action: Extract `[...]` tags into a `tags` array.

- **Key-Value Extraction**: Define "Magic Comment" syntax for annotations.
  - Best practice: Move these to real YAML fields rather than parsing comments.

### Categorizing Knowledge Entries

Recommended Taxonomy:
- **`definition`**: Business glossary terms (e.g., "Active User")
- **`logic` / `methodology`**: Formulas or transformation rules
- **`caution` / `warning`**: Critical data quality issues or "gotchas" (e.g., "Do not sum this column")
- **`lineage`**: Upstream dependencies
- **`context`**: Historical reasons for design decisions

Implementation Pattern:
```yaml
knowledge:
  - type: definition
    content: "Users who logged in within the last 30 days."
  - type: caution
    content: "Data before 2023-01-01 is unreliable due to migration."
    severity: high
```

### Relating Knowledge to Data

- **Anchor at the Atomic Level:**
  - Table Level: Broad context, grain definitions, and filters.
  - Column Level: Data types, specific business logic, and PII flags.
  - Value Level (Enums): Meaning of specific codes (e.g., `status: 5`).

- **Cross-Referencing Strategy:**
  - Use relative paths for portability: `columns.user_id`
  - Use URNs/URIs for global linking: `urn:datasource:schema:table:column`

- **Example Structure:**
  ```yaml
  tables:
    - name: orders
      description: "All customer orders."
      knowledge:
        - type: methodology
          content: "Orders are created only after payment confirmation."
      columns:
        - name: status
          knowledge:
            - type: caution
              content: "Status '99' indicates a legacy system error state."
              related_columns: [error_log_id]
  ```

### Summary of Best Practices

1. **Structure over Parsing**: Prefer dedicated YAML fields over parsing text/comments.
2. **Standardize Markers**: If parsing text, use rigid markers like `.. type::` or `[TAG]`.
3. **Typed Knowledge**: Categorize entries (Caution vs. Definition) for better UI display.
4. **Deep Linking**: Attach knowledge directly to the specific column or value it describes.

---

## 3. Status Lifecycle Best Practices

### Core Principles

1. **Use `StrEnum` for States**: Provides string compatibility (for APIs/DBs) with type safety.
2. **Centralize Transition Logic**: Define valid transitions in a single dictionary, not scattered `if/else` checks.
3. **Event-Driven Updates**: Prefer explicit methods (e.g., `approve()`) or events over direct attribute assignment.
4. **Atomic Operations**: Validate transitions *before* applying changes or triggering side effects.

### Implementation Pattern

```python
from enum import StrEnum
from dataclasses import dataclass
from typing import Dict, Set

# 1. Define States using StrEnum (Python 3.11+)
class ReviewStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# 2. Define Valid Transitions (Source -> {Destinations})
VALID_TRANSITIONS: Dict[ReviewStatus, Set[ReviewStatus]] = {
    ReviewStatus.DRAFT: {ReviewStatus.PENDING},
    ReviewStatus.PENDING: {ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.DRAFT},
    ReviewStatus.APPROVED: {ReviewStatus.PENDING},
    ReviewStatus.REJECTED: {ReviewStatus.DRAFT},
}

class InvalidTransitionError(Exception):
    """Raised when a status transition is not allowed."""
    pass

@dataclass
class ReviewItem:
    title: str
    status: ReviewStatus = ReviewStatus.DRAFT

    def can_transition_to(self, new_status: ReviewStatus) -> bool:
        """Check if a transition is valid without executing it."""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        return new_status in allowed

    def transition_to(self, new_status: ReviewStatus, reason: str = "") -> None:
        """Execute a state transition with validation and event hooks."""
        if not self.can_transition_to(new_status):
            raise InvalidTransitionError(
                f"Cannot transition from {self.status} to {new_status}"
            )
        old_status = self.status
        self.status = new_status
        self._handle_state_change(old_status, new_status, reason)

    def _handle_state_change(self, old: ReviewStatus, new: ReviewStatus, reason: str):
        """Dispatches events based on the new state."""
        match new:
            case ReviewStatus.PENDING:
                self.on_submit_for_review()
            case ReviewStatus.APPROVED:
                self.on_approved(reason)
            case ReviewStatus.REJECTED:
                self.on_rejected(reason)

    def on_submit_for_review(self):
        print("Trigger: Notify reviewers...")

    def on_approved(self, reason):
        print(f"Trigger: Publish content. Reason: {reason}")

    def on_rejected(self, reason):
        print(f"Trigger: Email author. Reason: {reason}")
```

### Key Takeaways

- **Pydantic Integration**: The ReviewItem class can be a `pydantic.BaseModel`. The logic remains identical.
- **Database Consistency**: Wrap `transition_to` logic in a transaction for atomic status updates + side effects.
- **API Exposure**: API endpoints should call `transition_to` rather than updating the field directly.
- **`can_transition_to` method**: Expose this for UI to enable/disable buttons based on valid next states.

---

## Applicability to SPEC-3 (insight-blueprint)

### Recommended Status Lifecycle

```
draft -> active -> pending_review -> reviewed -> completed
```

This maps well to the data analysis domain:
- `draft`: Analysis design being created/refined
- `active`: Analysis is underway
- `pending_review`: Submitted for domain expert review
- `reviewed`: Review complete, feedback incorporated
- `completed`: Analysis finalized

### Key Design Decisions for SPEC-3

1. **State transitions**: Use a centralized `VALID_TRANSITIONS` dict with `StrEnum` for the 5-state lifecycle
2. **Review comments**: Use logical linking (attach to analysis design ID, not line numbers) since analysis designs are atomic units
3. **Knowledge extraction**: Categorize extracted knowledge using typed entries (caution, definition, methodology, context)
4. **YAML persistence**: Use structured fields, not parsed comments -- each knowledge entry gets type, content, severity, and related_columns
5. **Event hooks**: `submit_for_review` triggers status transition; `save_review_comment` can trigger auto-extraction

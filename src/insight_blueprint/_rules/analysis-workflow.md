---
version: "1.0.0"
paths:
  - ".insight/designs/**"
---

# Hypothesis Design Workflow

## Status Flow

Designs follow a strict status progression:

```
draft → active → pending_review → supported | rejected | inconclusive
```

- **draft**: Initial creation. Editable freely.
- **active**: Hypothesis is being tested. Data collection in progress.
- **pending_review**: Analysis complete, awaiting peer review.
- **supported / rejected / inconclusive**: Final disposition after review.

Status transitions MUST use `design_update` MCP tool with valid `status` field.
Skipping states (e.g., draft → supported) is not allowed.

## Theme ID Rules

- Every design MUST have a `theme_id` linking it to a research theme.
- Theme IDs should be short, descriptive identifiers (e.g., `churn-analysis`, `pricing-impact`).
- Use `/analysis-design` skill to create designs with proper theme association.

## Derived Hypotheses

- A design may reference `parent_id` to indicate it derives from another hypothesis.
- Parent must exist and be in `supported` or `active` status.
- This creates a hypothesis tree for tracking research lineage.

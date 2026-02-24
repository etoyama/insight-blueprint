---
name: spec-start
description: Creates structured specifications through multi-agent collaboration using spec-workflow-mcp. Use when starting new features, defining requirements, creating design documents, or establishing formal development workflows. Triggers on "create spec", "requirements definition", "design document", or "/spec-start".
---

# Spec-Driven Development Workflow

Creates comprehensive specifications through orchestrated collaboration between Claude, Codex, Gemini, and spec-workflow-mcp.

## Template Reference

Always read templates before composing spec documents:
- Requirements: `.spec-workflow/templates/requirements-template.md`
- Design: `.spec-workflow/templates/design-template.md`
- Tasks: `.spec-workflow/templates/tasks-template.md`

Use the template's exact section names and structure as the skeleton.

## When to Use

Use this skill when:
- Starting a new feature or project that needs formal specification
- Converting informal requirements into structured documentation
- Establishing design-before-implementation workflows
- Creating approval-gated development processes
- User mentions "spec", "requirements", "design document", or invokes `/spec-start`

## Workflow

### Step 1: Research (Gemini via Subagent)

Launch subagent to conduct technical research:
- Similar implementation patterns
- Recommended libraries and frameworks
- Security considerations
- Performance implications

Save output to `.claude/docs/research/<feature-name>-research.md`

### Step 2: Requirements Gathering (Claude)

Before writing requirements, read `.spec-workflow/templates/requirements-template.md`.

Interview user to define:
1. **Introduction**: Feature purpose and value (2-4 sentences)
2. **Alignment with Product Vision**: How this supports goals in product.md (3 key points)
3. **Requirements** (group per cluster — each cluster must contain):
   - User Story: As a [role], I want [feature], so that [benefit]
   - Functional Requirements (FR-N): Specific behaviors the system must exhibit
   - Acceptance Criteria: WHEN [event] THEN [system] SHALL [response]
4. **Non-Functional Requirements** (5 subsections):
   - Code Architecture and Modularity
   - Performance
   - Security
   - Reliability
   - Usability
5. **Out of Scope**: Features explicitly excluded from this spec

### Step 3: Create Requirements (spec-workflow MCP)

Before composing content, read `.spec-workflow/templates/requirements-template.md`
and follow its exact section names and nesting structure.

Call MCP tools:
```
create_spec(name="<feature-name>", description="...")
create_requirements(spec_id="...", content="...")
```

Output: `.spec-workflow/specs/<feature-name>/requirements.md`

### Step 4: Technical Risk Analysis (Codex via Subagent)

Launch subagent with requirements document to analyze:
- Architectural risks and mitigations
- Implementation complexity (S/M/L/XL)
- Alternative approaches
- Dependencies and integration points

Save to `.claude/docs/DESIGN.md`

### Step 5: Create Design Document (spec-workflow MCP)

Before composing content, read `.spec-workflow/templates/design-template.md`
and follow its exact section names and nesting structure.

Generate design incorporating Codex analysis:
```
create_design(spec_id="...", content="...")
```

Include:
- Overview: 2-3 sentences describing the feature's place in the system
- Steering Document Alignment: technical standards (tech.md) + project structure (structure.md)
- Code Reuse Analysis: existing components to leverage + integration points
- Architecture: overall patterns + Modular Design Principles subsection
- Components and Interfaces: per-component with Purpose / Interfaces / Dependencies / Reuses
- Data Models: data structures
- Error Handling: numbered scenarios each with Handling + User Impact
- Testing Strategy: Unit Testing, Integration Testing, End-to-End Testing

Output: `.spec-workflow/specs/<feature-name>/design.md`

### Step 6: Task Breakdown

Before composing tasks, read `.spec-workflow/templates/tasks-template.md`
and follow its field structure.

Decompose design into implementation tasks:
```
create_tasks(spec_id="...", tasks=[...])
```

Task format per item:
- [ ] N.M Task title
  - File: path(s) to create/modify
  - Implementation detail lines
  - Purpose: one sentence explaining why this task exists
  - _Leverage: existing code paths to reuse_
  - _Requirements: FR-N, NFR-N references_
  - _Prompt: Role: ... | Task: ... | Restrictions: ... | Success: ..._

Task design principles:
- 1 task = 1-3 hours of work
- Tasks within requirements.md (ACs belong there, not in tasks.md)
- Explicit dependencies between tasks
- Include test implementation

### Step 7: Request Approval

```
request_approval(spec_id="...", message="Specification complete, ready for review")
```

Dashboard at http://localhost:5000 for review/approval.

After approval, choose an implementation strategy:

**Option A: Parallel (Agent Teams — 推奨)**
```
/team-implement --spec <spec-id>
```
Then: `/team-review --spec <spec-id>` for parallel review.

**Option B: Sequential (Single-Task TDD)**
```
/tdd --spec <spec-id> <task-id>
```
Execute tasks individually in dependency order.

## Context Management

**Critical for maintaining orchestrator context budget:**
- Always route Gemini/Codex calls through subagents
- Save all outputs to files before referencing
- Use `/checkpointing` after each major step
- Avoid loading large outputs into main context

## Completion Checklist

Before requesting approval:
- [ ] requirements.md follows requirements-template.md section structure
- [ ] design.md follows design-template.md section structure
- [ ] tasks.md uses Purpose/Leverage/Requirements/Prompt fields
- [ ] Introduction and Product Vision alignment documented
- [ ] Acceptance criteria in WHEN/THEN/SHALL format
- [ ] Non-functional requirements cover all 5 subsections
- [ ] Design includes Modular Design Principles
- [ ] All tasks have Purpose and Prompt fields
- [ ] Approval obtained via dashboard
- [ ] Post-approval pipeline documented (team-implement → team-review)

## Post-Approval Pipeline

```
/spec-start → /team-implement --spec <id> → /team-review --spec <id>
                        ↓ (alternative)
               /tdd --spec <id> <task-id>
```

**Triggers next workflows:**
- After approval → `/team-implement --spec <id>` for parallel implementation
- After implementation → `/team-review --spec <id>` for parallel review
- Between sessions → `/checkpointing` for state persistence

**Single-task alternative:**
- `/tdd --spec <id> <task-id>` for sequential task execution

**Collaborating agents:**
- Gemini: Technical research, pattern discovery
- Codex: Design review, risk analysis
- spec-workflow-mcp: Document management, progress tracking

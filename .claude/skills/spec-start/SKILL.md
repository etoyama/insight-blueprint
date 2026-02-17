---
name: spec-start
description: Creates structured specifications through multi-agent collaboration using spec-workflow-mcp. Use when starting new features, defining requirements, creating design documents, or establishing formal development workflows. Triggers on "create spec", "requirements definition", "design document", or "/spec-start".
---

# Spec-Driven Development Workflow

Creates comprehensive specifications through orchestrated collaboration between Claude, Codex, Gemini, and spec-workflow-mcp.

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

Interview user to define:
1. **User Stories**: Who uses this and why
2. **Functional Requirements**: What it must do
3. **Non-Functional Requirements**: Performance, security, scalability
4. **Constraints**: Integration points, technology limitations
5. **Acceptance Criteria**: Definition of Done

### Step 3: Create Requirements (spec-workflow MCP)

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

Generate design incorporating Codex analysis:
```
create_design(spec_id="...", content="...")
```

Include:
- System architecture
- Data models
- API design
- Error handling strategy
- Testing approach

Output: `.spec-workflow/specs/<feature-name>/design.md`

### Step 6: Task Breakdown

Decompose design into implementation tasks:
```
create_tasks(spec_id="...", tasks=[
  {"id": "1.1", "title": "...", "description": "...", "acceptance_criteria": [...]},
  ...
])
```

Task design principles:
- 1 task = 1-3 hours of work
- Clear acceptance criteria for each
- Explicit dependencies between tasks
- Include test implementation

### Step 7: Request Approval

```
request_approval(spec_id="...", message="Specification complete, ready for review")
```

Dashboard at http://localhost:5000 for review/approval.

After approval, use `/tdd --spec <spec-id> <task-id>` to begin implementation.

## Context Management

**Critical for maintaining orchestrator context budget:**
- Always route Gemini/Codex calls through subagents
- Save all outputs to files before referencing
- Use `/checkpointing` after each major step
- Avoid loading large outputs into main context

## Completion Checklist

Before requesting approval:
- [ ] User stories clearly documented
- [ ] Acceptance criteria testable
- [ ] Non-functional requirements defined
- [ ] Design includes architecture diagram
- [ ] All tasks have dependency information
- [ ] Approval obtained via dashboard

## Integration Points

**Triggers next workflows:**
- After approval → `/tdd --spec <id>` for implementation
- During development → `/checkpointing` for state persistence
- Post-implementation → `update_task_status` via dashboard

**Collaborating agents:**
- Gemini: Technical research, pattern discovery
- Codex: Design review, risk analysis
- spec-workflow-mcp: Document management, progress tracking

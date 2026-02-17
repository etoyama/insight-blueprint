---
name: migrate-to-spec
description: Converts lightweight /startproject implementations into formal spec-workflow specifications with requirements, design, and tracked tasks. Use when simple work grows complex and needs approval, task tracking, or team coordination. Triggers on "migrate to spec", "formalize this", "convert to spec", "need approval workflow", or "/migrate-to-spec".
---

# Migrate to Spec-Workflow

Converts work started with `/startproject` into formal spec-workflow with requirements, design, and tracked tasks.

## When to Use

- `/startproject` implementation became more complex than expected
- Stakeholder approval is now required
- Multiple developers need coordination
- Task tracking and progress visibility needed
- User says "migrate to spec", "formalize", or invokes `/migrate-to-spec`

## Quick Start

```bash
# Run automated migration
python scripts/extract_docs.py .claude/docs/
python scripts/generate_spec.py --output .spec-workflow/specs/
```

For common patterns, see `references/migration-patterns.md`

## Workflow

### Step 1: Extract Existing Work

Analyze current state:
```bash
# Use bundled extraction script
python scripts/extract_docs.py .claude/docs/ --format json > migration-data.json
```

The script identifies:
- Implementation files (code, tests)
- Design decisions in `.claude/docs/DESIGN.md`
- Research notes in `.claude/docs/research/`
- Gemini/Codex consultation logs

### Step 2: Generate Requirements Document

Use extracted data to create formal requirements:

```bash
# Generate requirements from extraction
python scripts/generate_spec.py \
  --input migration-data.json \
  --spec-name <feature-name> \
  --type requirements
```

Or manually via MCP:
```
create_spec(name="<feature-name>", description="...")
create_requirements(spec_id="...", content="...")
```

Requirements include:
- User Stories (from implementation context)
- Functional Requirements (reverse-engineered from code)
- Non-Functional Requirements (inferred from decisions)
- Acceptance Criteria (derived from tests)

### Step 3: Document Current Design

Convert `.claude/docs/DESIGN.md` to spec-workflow format:

```bash
python scripts/generate_spec.py \
  --input migration-data.json \
  --spec-name <feature-name> \
  --type design
```

Or via MCP:
```
create_design(spec_id="...", content="...")
```

### Step 4: Create Task List

Break down completed and remaining work:

```bash
# Auto-generate task list
python scripts/generate_spec.py \
  --input migration-data.json \
  --spec-name <feature-name> \
  --type tasks
```

Task structure:
```
1.1 Initial implementation (DONE)
1.2 Add error handling (TODO)
1.3 Write integration tests (TODO)
```

### Step 5: Mark Completed Tasks

Update status for finished work:
```
update_task_status(spec_id="...", task_id="1.1", status="done")
```

### Step 6: Request Approval

```
request_approval(
  spec_id="...",
  message="Formalized existing work. Approval needed for remaining tasks."
)
```

Dashboard: http://localhost:5000

## Bundled Resources

### Scripts

**`scripts/extract_docs.py`** - Extracts implementation details from `.claude/docs/`
```bash
python scripts/extract_docs.py .claude/docs/ --format json
```

**`scripts/generate_spec.py`** - Converts extracted data to spec-workflow format
```bash
python scripts/generate_spec.py --input data.json --type requirements
```

### References

**`references/migration-patterns.md`** - Common migration patterns:
- Bug fix → Security audit
- Feature → Multi-phase project
- Prototype → Production system

See file for detailed examples and templates.

### Assets

**`assets/spec-template.md`** - Template for manual migration
**`assets/task-checklist.md`** - Verification checklist

## Output

After migration:
- `.spec-workflow/specs/<feature>/requirements.md`
- `.spec-workflow/specs/<feature>/design.md`
- `.spec-workflow/specs/<feature>/tasks.md`
- Dashboard tracking at http://localhost:5000

## Best Practices

**Preserve history:**
- Link to original `.claude/docs/` for context
- Document why migration was needed
- Note implementation decisions from `/startproject`

**Realistic status:**
- Mark truly completed work as "done"
- Don't claim more progress than exists
- Document technical debt or shortcuts

**Clear next steps:**
- Highlight remaining work
- Note areas needing refactoring
- Document open questions

## Common Patterns

See `references/migration-patterns.md` for:
- **Bug Fix → Security Audit**: Simple fix revealed wider issues
- **Feature → Multi-Phase**: Initial implementation needs expansion
- **Prototype → Production**: POC needs formal approval

## Integration Points

**Before:**
- Started with `/startproject`
- Docs in `.claude/docs/`
- No approval workflow

**After:**
- Full spec-workflow integration
- Dashboard tracking
- Approval required for new work
- Use `/tdd --spec <id>` for tasks

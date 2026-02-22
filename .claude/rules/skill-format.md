# Skill Format Rules

Guidelines for creating Claude Code skills (`.claude/skills/<name>/SKILL.md`).

## File Structure

Each skill lives in its own directory:

```
.claude/skills/<skill-name>/
├── SKILL.md          # Main instructions (required)
└── references/       # Supplemental docs (optional)
    └── *.md
```

- `SKILL.md` should stay under **300 lines**. Move supplemental content to `references/`.
- File naming: directory name = slash command name (e.g., `tdd/` → `/tdd`)

## YAML Frontmatter (Required)

Every SKILL.md MUST begin with YAML frontmatter:

```yaml
---
name: <skill-name>          # Required. Lowercase, hyphens allowed (max 64 chars).
description: |              # Required. Claude reads this to decide when to auto-invoke.
  What this skill does and when to use it.
  Include Japanese trigger phrases if skill is for Japanese users.
  (e.g., "仮説を立てたい", "create analysis design")
disable-model-invocation: true   # See Invocation Mode below
argument-hint: "[arg1] [arg2]"   # Optional. Shown in autocomplete.
---
```

### Required Fields

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Must match directory name |
| `description` | **Yes** | Claude uses this for auto-detection; include trigger phrases |

### Invocation Mode

Choose ONE of:

| Pattern | When to Use | Example Skills |
|---------|------------|----------------|
| `disable-model-invocation: true` | User explicitly types `/command`. Claude won't auto-invoke. | `/tdd`, `/plan`, `/analysis-design` |
| *(omit)* | Claude can proactively suggest/invoke based on user intent. | `/startproject`, `/spec-start` |

**Rule of thumb**: If the skill is a workflow the user starts on purpose (not something
Claude should detect automatically), use `disable-model-invocation: true`.

## Body Structure

Recommended sections in order:

```markdown
# /<skill-name> — Short Title

One-line purpose statement.

## When to Use
- Bullet list of triggering scenarios

## When NOT to Use          # Include when ambiguity exists
- Bullet list of exclusions

## Workflow
Step-by-step numbered instructions Claude should follow.
Include concrete examples (tool calls, expected output).

## Notes / Constraints      # Rename as appropriate
Key rules, error handling, or caveats.

## Language Rules           # Always include for this project
- Respond to users in Japanese
- Code, IDs, and tool names stay in English
```

## Language Policy

- All Skill definitions (SKILL.md content) must be written in **English**
- `description` field: include Japanese trigger phrases alongside English ones
- User-facing responses from skills: follow project language rules (Japanese)

## Common Mistakes to Avoid

- No frontmatter at all (missing `---` delimiters)
- `description` too vague — Claude can't match user intent
- Missing `disable-model-invocation` decision — be explicit about invocation mode
- Skill body over 300 lines without splitting to `references/`
- Hardcoding paths or versions in SKILL.md (use `$ARGUMENTS` for dynamic values)

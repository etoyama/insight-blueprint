# Spec-Workflow Mode for Team Implement

`/team-implement --spec <spec-id>` で起動された場合の追加手順。

## Source Detection

1. Tasks: `.spec-workflow/specs/<spec-id>/tasks.md` から読む
   - `[ ]` = pending, `[-]` = in-progress, `[x]` = completed
   - Dependency Graph セクションで並列化可能なタスクを特定
2. Design: `.spec-workflow/specs/<spec-id>/design.md` から読む
3. Requirements: `.spec-workflow/specs/<spec-id>/requirements.md` から読む

## Prerequisites

- `/spec-start` が完了し、spec-workflow ダッシュボードで承認済み
- 上記3ファイルが `.spec-workflow/specs/<spec-id>/` に存在すること

## Teammate Prompt Enrichment

各 Teammate の prompt に以下を追加:

```
Read these files for context:
- CLAUDE.md (project context)
- .spec-workflow/specs/<spec-id>/design.md (architecture)
- .spec-workflow/specs/<spec-id>/requirements.md (acceptance criteria)

Your assigned tasks (from tasks.md):
{task list — use _Prompt: field as base instruction}

After completing each task:
1. Mark task [x] in .spec-workflow/specs/<spec-id>/tasks.md
2. Call log-implementation MCP tool with artifacts
3. Reference acceptance criteria from requirements.md
```

## Completion Verification

全タスク完了後、追加で以下を確認:
1. `tasks.md` の全タスクが `[x]` であること
2. 各タスクの `log-implementation` が呼び出されていること
3. `spec-status` で全体進捗を確認
4. `/team-review --spec <spec-id>` への引き継ぎ

# CLAUDE.md — Multi-Agent Spec-Driven Development

## Agent Architecture

```
spec-workflow-mcp (Requirements → Design → Tasks)
        ↕  MCP Protocol
Claude Code (Orchestrator)   ← You are here
  ├─ Codex CLI  (design review, deep reasoning, debugging)
  ├─ Gemini CLI (research, multimodal, large-scale analysis)
  └─ Subagents  (parallel task execution, independent context)
```

## Context Management (Critical)

メインオーケストレーターのコンテキストを節約することが最優先。

| 状況 | 推奨方法 |
|------|---------|
| 大きな出力が予想される | サブエージェント経由 |
| 短い質問・短い回答 | 直接呼び出しOK |
| Codex/Gemini相談 | サブエージェント経由 |
| 詳細な分析が必要 | サブエージェント経由 → ファイル保存 |
| スペック作成・更新 | spec-workflow MCP ツール経由 |

---

## Spec-Driven Development Workflow

本格開発は spec-workflow-mcp を起点とした以下のフェーズで進める。

### Phase 1: Specification

```
/spec-start <機能名>
```

1. **Gemini**（サブエージェント経由）→ 技術リサーチ・類似実装調査
2. **Claude** → 要件ヒアリング・ユーザーストーリー収集
3. **spec-workflow MCP** → Requirements ドキュメント作成
4. **Codex**（サブエージェント経由）→ 技術リスク分析・設計レビュー
5. **spec-workflow MCP** → Design ドキュメント作成
6. **spec-workflow MCP** → Tasks 分解・Approval リクエスト
7. ダッシュボード（http://localhost:5000）で承認

### Phase 2: Implementation

```
/tdd --spec <spec-id> <task-id>
```

8. **Subagents**（並列）→ タスク単位のRed-Green-Refactorサイクル
9. テスト完了後 **spec-workflow MCP** でタスクステータス更新
10. `/checkpointing` でセッション状態を保存

---

## Workflow Selection

Choose the appropriate workflow based on implementation complexity:

| Criteria | `/startproject` (Agile) | `/spec-start` (Spec-Driven) |
|----------|------------------------|----------------------------|
| **Time** | < 1 day | 1+ days |
| **Files** | < 5 files | 5+ files |
| **Impact** | Isolated | Cross-system |
| **Approval** | Not needed | Required |
| **Examples** | Bug fixes, UI tweaks, utilities | New features, APIs, auth systems |

### When to Use Spec-Driven Workflow (Mandatory)

**必ずspec-workflowに従うべき状況:**
- ユーザーが spec 文書（requirements.md / design.md / tasks.md）や
  steering 文書（product.md / tech.md / structure.md）に基づいて開発を指示しているとき
- 新機能・API・システム横断変更（5+ files, 1+ days）

**spec-workflowが不要な状況:**
- バグ修正（typo, 単純なロジック修正）
- Chore（lint設定, CI調整, ドキュメント微修正）
- 孤立した小変更（< 5 files, < 1 day, approval不要）

**判断が曖昧な場合:**
→ **必ずユーザーに確認する。** 実装を先に進めてはならない。

---

## Skills

### `/startproject` — Quick Start (Agile)
Lightweight workflow for simple implementations without formal specs.
Use for: bug fixes, UI adjustments, small features (< 1 day, < 5 files).
詳細: `.claude/skills/startproject/`

### `/spec-start` — Spec-Driven Development
spec-workflow-mcp + マルチエージェント協調でスペックを作成。
Use for: new features, architecture changes (1+ days, 5+ files, approval required).
詳細: `.claude/skills/spec-start/SKILL.md`

**Migration:** Use `/migrate-to-spec` to convert `/startproject` work into formal spec.

### `/plan` — 実装計画
要件を具体的なステップに分解。`--spec` オプションで spec-workflow に登録可。
詳細: `.claude/skills/plan/`

### `/tdd` — テスト駆動開発
Red-Green-Refactorサイクル。`--spec <id>` でspec-workflowタスクと連携。
詳細: `.claude/skills/tdd/`

### `/checkpointing` — セッション永続化
```
/checkpointing              # 基本
/checkpointing --full       # git履歴・ファイル変更含む
/checkpointing --analyze    # 再利用パターン発見
```

### `/codex-system` — Codex CLI 連携
設計・デバッグ・トレードオフ分析。必ずサブエージェント経由で呼び出す。

**トリガー:**
- 「どう設計すべき？」「アーキテクチャを検討して」
- 「なぜ動かない？」「エラーを分析して」
- 「どちらがいい？」「比較して」

### `/gemini-system` — Gemini CLI 連携
リサーチ・大規模分析・マルチモーダル。必ずサブエージェント経由で呼び出す。

**トリガー:**
- 「調べて」「リサーチして」「最新動向を調査して」
- 「このPDF/画像を分析して」
- 「コードベース全体を理解して」

### Skill Format Standards
新しいスキルを作成する際は `.claude/rules/skill-format.md` に従う。

---

## spec-workflow MCP Tools

spec-workflow-mcp が提供する主要ツール（Claude Codeから直接利用可能）：

| ツール | 用途 |
|--------|------|
| `create_spec` | 新しいスペック作成 |
| `list_specs` | スペック一覧取得 |
| `create_requirements` | 要件ドキュメント作成 |
| `create_design` | 設計ドキュメント作成 |
| `create_tasks` | タスクリスト作成 |
| `update_task_status` | タスク進捗更新 |
| `request_approval` | Approval リクエスト |
| `log_implementation` | 実装ログ記録 |

ダッシュボード: `npx -y @pimzino/spec-workflow-mcp@latest --dashboard`
URL: http://localhost:5000

---

## Development Standards

### Tech Stack
| ツール | 用途 |
|--------|------|
| **uv** | パッケージ管理（pip禁止） |
| **ruff** | リント・フォーマット |
| **mypy** | 型チェック |
| **pytest** | テスト |
| **poethepoet** | タスクランナー |

### Commands
```bash
uv add <package>       # パッケージ追加
uv add --dev <package> # 開発依存追加
poe lint               # ruff check + format
poe typecheck          # mypy
poe test               # pytest
poe all                # 全チェック実行
```

---

## Hooks

| フック | トリガー | 動作 |
|--------|---------|------|
| `agent-router.py` | ユーザー入力 | Codex/Geminiへのルーティング提案 |
| `lint-on-save.py` | ファイル保存 | 自動lint実行 |
| `check-codex-before-write.py` | ファイル書き込み前 | Codex相談提案 |
| `log-cli-tools.py` | Codex/Gemini実行 | 入出力ログ記録 |
| `spec-task-complete.py` | テスト全通過 | spec-workflowタスク完了通知 |

---

## Language Rules

- **コード・思考・推論**: English
- **ユーザーへの応答**: 日本語
- **技術ドキュメント**: English
- **スペック文書**: 日本語可（spec-workflow内）

# Spec Workflow Rules

## スペック作成の原則

### 1. スペックの粒度
- **1スペック = 1機能領域**（ユーザー認証、決済処理など）
- 大きな機能は複数スペックに分割する
- スペック間の依存関係は requirements.md に明記

### 2. 要件ドキュメント (requirements.md)

テンプレート: `.spec-workflow/templates/requirements-template.md`

必須セクション:
- `## Introduction` - 機能の目的と価値（2〜4文）
- `## Alignment with Product Vision` - product.md のゴールとの対応（3つのポイント）
- `## Requirements` — 要件クラスタごとのネスト構造、各クラスタに必須:
  - `**User Story:**` As a [role], I want [feature], so that [benefit]
  - 機能要件 (FR-N) の箇条書き
  - `#### Acceptance Criteria` — WHEN/THEN/SHALL フォーマット
- `## Non-Functional Requirements` — 5つのサブセクション必須:
  - Code Architecture and Modularity
  - Performance
  - Security
  - Reliability
  - Usability
- `## Out of Scope` （推奨: テンプレートには無いが有用なため追加を許可）

### 3. 設計ドキュメント (design.md)

テンプレート: `.spec-workflow/templates/design-template.md`

必須セクション:
- `## Overview` - 機能のシステム内の位置づけ（2〜3文）
- `## Steering Document Alignment` — サブセクション必須:
  - Technical Standards (tech.md)
  - Project Structure (structure.md)
- `## Code Reuse Analysis` — Existing Components to Leverage + Integration Points
- `## Architecture` — Modular Design Principles サブセクション必須
- `## Components and Interfaces` — コンポーネントごとに Purpose / Interfaces / Dependencies / Reuses
- `## Data Models` - データ構造
- `## Error Handling` - 番号付きシナリオ、各シナリオに Handling + User Impact
- `## Testing Strategy` — Unit Testing / Integration Testing / End-to-End Testing

### 4. タスク設計

テンプレート: `.spec-workflow/templates/tasks-template.md`

- タスクIDは `<major>.<minor>` 形式（例: 1.1, 1.2, 2.1）
- 1タスクの実装時間目安: 1〜3時間
- 各タスクに明示する情報:
  - `File:` 作成・変更するファイルパス
  - 実装の詳細行
  - `Purpose:` このタスクが存在する理由（1文）
  - `_Leverage:_` 再利用する既存コードパス
  - `_Requirements:_` FR-N、NFR-N の参照
  - `_Prompt:_` Role: ... | Task: ... | Restrictions: ... | Success: ...
- **注意**: acceptance_criteria はタスクに書かない（ACs は requirements.md に属する）

### 5. Approval フロー
- スペック完成前に実装を開始しない
- 要件変更は必ず requirements.md を更新してから
- 設計変更は Codex レビュー後に design.md を更新

---

## マルチエージェント連携ルール

### Gemini 呼び出しのタイミング
- 要件定義前の技術リサーチ
- 設計オプションの調査
- セキュリティ脆弱性の確認
- パフォーマンス最適化パターンの調査

### Codex 呼び出しのタイミング
- 設計レビュー（要件→設計の妥当性確認）
- コードレビュー（実装完了後）
- デバッグ（原因不明のバグ）
- トレードオフ分析（設計の選択肢比較）

### サブエージェント使用基準
- Gemini/Codex の呼び出しは**常にサブエージェント経由**
- 予想出力が 500行 を超えるタスクはサブエージェントへ
- 独立して実行可能なタスクは並列でサブエージェントに委譲

---

## ファイル保存規則

| 成果物 | 保存先 |
|--------|--------|
| 技術リサーチ | `.claude/docs/research/<機能名>-research.md` |
| 設計決定記録 | `.claude/docs/DESIGN.md` |
| スペック文書 | `.spec-workflow/specs/<spec-id>/` |
| 実装ログ | `.spec-workflow/logs/` |
| Checkpointing | `.claude/logs/` |

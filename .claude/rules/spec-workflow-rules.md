# Spec Workflow Rules

## スペック作成の原則

### 1. スペックの粒度
- **1スペック = 1機能領域**（ユーザー認証、決済処理など）
- 大きな機能は複数スペックに分割する
- スペック間の依存関係は requirements.md に明記

### 2. 要件ドキュメント (requirements.md)
必須セクション:
- `## User Stories` - As a..., I want..., So that...
- `## Functional Requirements` - 機能要件リスト
- `## Non-Functional Requirements` - 性能・セキュリティ・可用性
- `## Acceptance Criteria` - テスト可能な受け入れ条件
- `## Out of Scope` - 対象外の機能（明示的に除外）

### 3. 設計ドキュメント (design.md)
必須セクション:
- `## Architecture` - システム構成図
- `## Data Model` - エンティティと関係
- `## API Design` - エンドポイント定義
- `## Error Handling` - エラー種別と対処方針
- `## Testing Strategy` - テストレベルと方針

### 4. タスク設計
- タスクIDは `<major>.<minor>` 形式（例: 1.1, 1.2, 2.1）
- 1タスクの実装時間目安: 1〜3時間
- 各タスクに明示する情報:
  - `title`: 動詞始まりの短い説明（例: "Implement JWT token generation"）
  - `description`: 実装の詳細と技術的考慮事項
  - `acceptance_criteria`: テスト可能な完了条件（箇条書き）
  - `dependencies`: 先行タスクのID

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

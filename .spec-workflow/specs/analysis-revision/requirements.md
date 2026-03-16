# Requirements: analysis-revision

## Introduction

Issue #44 で報告されたレビュー→修正サイクルの断絶を解消する。現状、`save_review_batch` で `_reviews.yaml` にレビューコメントが書かれるが、Claude がそのコメントを読み取る MCP tool が存在しない（read/write 非対称）。本機能は、レビューコメントの読み取り用 MCP tool の追加、修正ワークフローを担う新スキル `analysis-revision` の作成、コメント単位の対応状態追跡を実現する。

## Alignment with Product Vision

- **Claude Code First**: MCP ツール経由でレビューコメントの読み取りを可能にし、Claude Code が自律的にレビュー→修正サイクルを回せるようにする
- **ステートマシンによるワークフロー制御**: `revision_requested → in_review` の遷移をスキルで構造化し、修正漏れなくレビューサイクルを完走させる
- **Success Metrics (レビューサイクル時間)**: 修正ワークフローの構造化により、revision_requested → in_review の遷移をスムーズにし、サイクル時間短縮に寄与する

## Requirements

### REQ-1: レビューコメント読み取り MCP tool

**User Story:** As Claude Code, I want to read review comments for a design via MCP, so that I can understand what needs to be fixed without relying on file path conventions.

#### Functional Requirements

- FR-1.1: MCP tool `get_review_comments(design_id)` を追加し、指定した design のレビューバッチ一覧を返す
- FR-1.2: 戻り値は `{design_id, batches: [...], count}` 形式とし、REST API `GET /api/designs/{id}/review-batches` と同等の情報量を提供する
- FR-1.3: バッチは `created_at` 降順でソートする（最新が先頭）
- FR-1.4: 各バッチには `id`, `design_id`, `status_after`, `reviewer`, `comments`, `created_at` を含める
- FR-1.5: 各コメントには `comment`, `target_section`（任意）, `target_content`（任意）を含める

#### Acceptance Criteria

- AC-1.1: WHEN `get_review_comments(design_id)` が呼ばれた THEN システムは `ReviewService.list_review_batches()` を呼び出し、バッチ一覧を JSON dict として返す SHALL
- AC-1.2: WHEN `design_id` に対するレビューが存在しない THEN システムは `{design_id, batches: [], count: 0}` を返す SHALL
- AC-1.3: WHEN `design_id` が空文字列 THEN システムは `{error: ...}` を返す SHALL
- AC-1.4: WHEN `_reviews.yaml` が破損している THEN システムは空リストを返し、エラーにならない SHALL（`ReviewService.list_review_batches()` の既存の堅牢性に依存）
- AC-1.5: WHEN `design_id` が valid 形式だが存在しない THEN システムは `{design_id, batches: [], count: 0}` を返す SHALL
- AC-1.6: WHEN `ReviewService` が予期しない例外を投げた THEN システムは `{error: ...}` を返す SHALL

### REQ-2: analysis-revision スキル

**User Story:** As a data analyst, I want a structured revision workflow that reads review comments and guides me through fixing each one, so that I don't miss any review feedback and can track my progress across sessions.

#### Functional Requirements

- FR-2.1: スキル `analysis-revision` を `src/insight_blueprint/_skills/analysis-revision/SKILL.md` に作成する
- FR-2.2: スキルは `get_analysis_design(design_id)` で design を取得し、`status == revision_requested` を確認する
- FR-2.3: スキルは `get_review_comments(design_id)` で最新のレビューバッチを取得する
- FR-2.4: スキルは各コメントを `target_section` ごとにグルーピングし、design の該当セクション内容と並べて提示する
- FR-2.5: スキルはコメントごとに修正方針をユーザーと対話し、`update_analysis_design` で修正を反映する
- FR-2.6: 全コメントへの対応完了後、`transition_design_status(design_id, "in_review")` で in_review に戻すことを提案する
- FR-2.7: スキルチェーンに組み込む: `analysis-design → [WebUI review] → analysis-revision → analysis-design(再提出)`

#### Acceptance Criteria

- AC-2.1: WHEN ユーザーが「レビューを直して」「指摘を反映して」「revision対応して」と発話した THEN スキルが発動する SHALL
- AC-2.2: WHEN design の status が `revision_requested` でない THEN スキルはエラーメッセージを表示して終了する SHALL
- AC-2.3: WHEN レビューコメントが取得できた THEN スキルは target_section ごとにグルーピングして一覧表示する SHALL
- AC-2.4: WHEN 各コメントへの対応が完了した THEN スキルは tracking file を更新する SHALL
- AC-2.5: WHEN 全コメントが addressed または wontfix になった THEN スキルは in_review への遷移を提案する SHALL
- AC-2.6: WHEN セッションが中断され再開された THEN スキルは tracking file から対応状態を復元し、未対応コメントから再開する SHALL

### REQ-3: コメント対応状態の追跡（tracking file）

**User Story:** As a data analyst, I want my revision progress to be tracked persistently, so that if I close the session and come back later, I can resume from where I left off.

#### Functional Requirements

- FR-3.1: tracking file を `.insight/designs/{design_id}_revision.yaml` に保存する
- FR-3.2: tracking file のフォーマットは `batch_id`, `created_at`, `items[]` を含み、各 item は `index`, `fingerprint`（comment + target_section の安定ハッシュ）, `comment_summary`, `target_section`, `status`（open/addressed/wontfix）, `addressed_at` を持つ
- FR-3.3: スキル起動時、tracking file が存在しない場合は最新のレビューバッチから新規作成する
- FR-3.4: スキル起動時、tracking file が存在し `batch_id` が最新バッチと一致する場合は再利用する（セッションまたぎ対応）
- FR-3.5: tracking file の `batch_id` が最新バッチと異なる場合（新しいレビューラウンド）、tracking file を上書きリセットする
- FR-3.6: コメント対応時に `status` を `addressed` に更新し、`addressed_at` にタイムスタンプを記録する
- FR-3.7: ユーザーが対応しないと判断したコメントは `wontfix` にマークできる
- FR-3.8: tracking file の書き込みはアトミックに行う（tempfile + os.replace）

#### Acceptance Criteria

- AC-3.1: WHEN スキルが初回起動し tracking file が存在しない THEN 最新バッチの全コメントを `status: open` で tracking file を作成する SHALL
- AC-3.2: WHEN スキルが再起動し tracking file の `batch_id` が最新バッチと一致する THEN 既存の tracking file をそのまま使い、未対応コメントから再開する SHALL
- AC-3.3: WHEN 新しいレビューバッチが追加された後にスキルが起動した THEN tracking file を新バッチで上書きリセットする SHALL
- AC-3.4: WHEN コメントが addressed に更新された THEN tracking file に `addressed_at` タイムスタンプが記録される SHALL
- AC-3.5: WHEN tracking file の全 items が addressed または wontfix THEN スキルは「全対応完了」と判定する SHALL

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility**: `get_review_comments` MCP tool は ReviewService への薄いラッパー。新しいビジネスロジックを含まない
- **レイヤー遵守**: `server.py → core/reviews.py → storage/ → models/` の依存方向を維持
- **Skill の独立性**: `analysis-revision` スキルは SKILL.md のみで構成。Python コードの追加は不要（tracking file の読み書きは Claude が直接行う）

### Performance

- `get_review_comments` の応答時間: 500ms 以内（既存の `list_review_batches` と同等）

### Security

- `design_id` のバリデーション: 既存の `_validate_design_id` を再利用
- tracking file のパスインジェクション防止: design_id に `..` や `/` を含む場合のバリデーション（既存の `_validate_id` に依存）

### Reliability

- `_reviews.yaml` が存在しない・破損している場合、空リストを返す（既存の ReviewService の堅牢性を継承）
- tracking file が破損している場合、最新バッチから再作成する

### Usability

- スキルのトリガーワードは日本語（「レビューを直して」「指摘を反映して」）と英語（"fix review", "address comments"）の両方に対応
- コメント一覧表示はセクション単位でグルーピングし、design の現在値と並べて表示する

## Out of Scope

- WebUI への変更（Extension Policy により WebUI UX は Fix）
- `BatchComment` モデルへのフィールド追加（レビューは不変レコードとして維持）
- 旧形式の `ReviewComment`（`comments` キー）の読み取り対応（`batches` キーのみ対象）
- analysis-revision スキル内での自動修正（修正はユーザーとの対話を通じて行う）

## Glossary

| 用語 | 定義 |
|------|------|
| ReviewBatch | レビュアーが一度に提出するレビューコメントのまとまり。`_reviews.yaml` の `batches` キーに格納 |
| BatchComment | ReviewBatch 内の個別コメント。`comment`, `target_section`, `target_content` を持つ |
| tracking file | `.insight/designs/{id}_revision.yaml`。コメント単位の対応状態を追跡するスキル管理ファイル |
| revision round | 1回の `revision_requested` → 修正 → `in_review` のサイクル |

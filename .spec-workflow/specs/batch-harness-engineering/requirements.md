# Requirements Document

## Introduction

`batch-harness-engineering` は、夜間無人で走る `/batch-analysis` を「朝起きたら結果ができている」状態で安定稼働させるためのハーネスエンジニアリング機能群である。2026-04-09 のインシデント（LiNGAM の 2 時間ハング → PC 強制終了 → session.log 空 0 bytes → 手動リカバリ 1 時間）を契機に、pre-flight premortem の自動化と crash resilience の Claude Code 公式機能への結線を統合的に設計する。

中核は 3 点:

1. **`/premortem` skill の新設** — design を事前にスキャンし、履歴ベース外挿で HIGH/MEDIUM/LOW を判定、承認トークンを発行する
2. **Manifest I/O の per-design atomic 化** — `.insight/runs/YYYYMMDD_HHmmss/{design_id}/manifest.yaml` を design 完走ごとに 1 回で書き切り、history 検索の主役にする
3. **公式 harness との結線** — `--output-format stream-json` と `--resume <session-id>` を採用し、自前 `progress.json` とテキスト session.log を廃止する

既存 `/batch-analysis` v1.0 (insight-blueprint v0.4.x) を **破壊しない add-only** で進化させ、`--approved-by TOKEN` フラグの追加と stream-json 切替により段階的自動化（manual → review → auto）を支える。

## Alignment with Product Vision

本 spec は `.spec-workflow/steering/product.md` の Product Principles と以下のように整合する:

- **Claude Code First** — 承認ゲートは CLI 1 画面（stdout）+ `--yes` フラグで無人運転と対話運転の双方をサポート。WebUI 拡張はしない
- **YAML as Source of Truth** — `run.yaml` / per-design `manifest.yaml` / `.insight/premortem/TIMESTAMP.yaml` / `methodology_vocab.yaml` は全て人間可読 YAML。SQLite インデックスは YAGNI
- **ステートマシン制御** — `automation: manual | review | auto` と status enum (`success | error | timeout | skipped | incomplete`) を明示的状態として定義。バイパスを許さない
- **後方互換の優先** — 既存 `/batch-analysis` コマンド・既存 `next_action.type = batch_execute` キュー・既存 journal schema は一切破壊せず、新フラグ `--approved-by` と新 YAML ファイルの add-only で拡張

関連 issue:
- [#97](https://github.com/etoyama/insight-blueprint/issues/97) (crash resilience — L1 timeout / L2 checkpoint / L3 recovery、2026-04-09 インシデントの根本原因)
- [#108](https://github.com/etoyama/insight-blueprint/issues/108) (pre-flight premortem automation — Two-Tier + Exception、11 項目 check items、履歴ベース外挿)
- [#107](https://github.com/etoyama/insight-blueprint/issues/107) (BQ location 検証 — 項目5 HARD_BLOCK 条件に吸収)

## Requirements

### Requirement 1: `/premortem` skill の新設

**User Story:** As a data analyst running overnight batches, I want a pre-flight premortem check that runs before `/batch-analysis` launches, so that heavy or unexecutable designs are detected and blocked before they consume hours of CPU time.

**Functional Requirements:**
- FR-1.1: `/premortem` は独立した skill として実装し、`/batch-analysis` から chain 呼び出しされる（`/batch-analysis --approved-by TOKEN`）
- FR-1.2: `/premortem` の責務は「design 読込 / 履歴外挿 / risk 判定 / 承認トークン発行」に限定する。notebook 生成（`/batch-analysis` の責務）や design 書換（`/analysis-design` の責務）、automation mode 判定（config 読むのは batch 側）は行わない
- FR-1.3: `/premortem` は `--queued`（キュー全部）/ `--design <id>`（単体）/ `--all`（全キュー）/ `--yes`（非対話実行）のオプションを受け付ける。`--yes` の意味は「対話プロンプトを表示せず automation mode の規則に従って承認処理を実行する」であり、mode を上書きするものではない（mode 別の HIGH 扱いは FR-7 に一元化）
- FR-1.4: 結果は **stdout の CLI 1 画面** に表示し、承認トークン YAML を `.insight/premortem/TIMESTAMP.yaml` に書き出す

#### Acceptance Criteria

1. WHEN ユーザーが `/premortem --queued` を実行する THEN `/premortem` SHALL `list_analysis_designs` から `next_action.type == "batch_execute"` のキューを取得し、各 design に対し risk 判定を行う
2. WHEN `/premortem` が risk 判定を完了する THEN 画面に `design_id / intent / estimated_rows / strategy / risk (LOW|MEDIUM|HIGH) / 判定理由` を 1 行ずつ表示し、HIGH があれば `[s]kip [e]dit [a]bort [c]ontinue` の選択肢を提示する SHALL
3. WHEN ユーザーが `--yes` フラグ付きで実行する THEN `/premortem` SHALL 対話プロンプトを表示せず、HIGH/MEDIUM/LOW の扱いは `batch.automation` mode（FR-7）に従ってトークンを発行する（`--yes` 単独で HIGH を強制 skip することはしない）
4. WHEN `/premortem` がトークン発行を完了する THEN stdout の最終行に `Launch with: /batch-analysis --approved-by <TOKEN_ID>` を表示する SHALL
5. WHEN `/premortem` が実行される THEN SHALL `notebook.py` / marimo セッション / `_journal.yaml` / design YAML へのいかなる書き込みも発生せず、MCP 呼び出しも `list_analysis_designs / get_analysis_design / get_table_schema / search_catalog` の読み取り系に限定される（責務逸脱は observable な I/O 契約で禁止）

### Requirement 2: Risk 判定ロジック

**User Story:** As the premortem engine, I need a deterministic risk decision tree that classifies each design into HARD_BLOCK / HIGH / MEDIUM / LOW based on executability, execution history, and static data profile, so that the decision is reproducible and auditable.

**Functional Requirements:**
- FR-2.1: 判定ツリーは 3 段階の優先順位で評価する: (a) 終端 status の SKIP、(b) 実行不能系の HARD_BLOCK、(c) history or static fallback による HIGH/MEDIUM/LOW
- FR-2.2: 終端 status 判定 — design の status が `supported | rejected | inconclusive` なら SKIP（判定対象外）
- FR-2.3: HARD_BLOCK 条件 — (a) source 未登録、(b) package allowlist 外、(c) BQ location 検証失敗（#107）のいずれかが成立するなら HARD_BLOCK（承認ゲート外で即停止、対話でも continue 不可）
- FR-2.4: 履歴ベース判定 — 同一 `source_ids` で過去 run が `history_min_samples`（default 3）以上あるなら、`success_rate < success_rate_high_threshold` または `extrapolated_time > time_high_min` なら HIGH、`extrapolated_time > time_medium_min` なら MEDIUM、それ以外は LOW
- FR-2.5: 外挿式 — `extrapolated_time = median(history.elapsed_min) × (new_design.estimated_rows / median(history.input_profile.estimated_rows)) × history_extrapolation_buffer`（default 1.3、悲観中央値）
- FR-2.6: Static fallback — history 不足（n < 3）なら、`estimated_rows > static_rows_high`（default 10M）なら HIGH、それ未満は MEDIUM（新規は慎重に）。両ケースとも `flag=history_insufficient` を付与
- FR-2.7: 閾値は `.insight/config.yaml` の `premortem:` セクションで上書き可能。デフォルト値は handoff 記載の値を採用

#### Acceptance Criteria

1. WHEN design の status が `supported | rejected | inconclusive` のいずれか THEN `/premortem` SHALL 当該 design を `SKIP` 扱いとし、トークンの `approved_designs` にも `skipped_designs` にも含めない
2. WHEN design の `source_ids` に catalog 未登録ソースが含まれる OR design が要求するパッケージが `batch-analysis` の package allowlist 外 THEN `/premortem` SHALL 当該 design を `HARD_BLOCK` とし、対話モードでも `[c]ontinue` を選択肢に出さず `[s]kip [e]dit [a]bort` のみ提示する
3. WHEN 同一 `source_ids` の過去 run が 3 件以上存在 AND その中央値 elapsed_min × (new_rows / median_rows) × 1.3 > `time_high_min` THEN risk は `HIGH` と SHALL 判定する
3b. WHEN 同一 `source_ids` の過去 run が 3 件以上存在 AND `success_rate < success_rate_high_threshold`（default 0.6） THEN risk は `HIGH` と SHALL 判定する（上記 AC-2.3 と並列、どちらか成立で HIGH）
3c. WHEN 同一 `source_ids` の過去 run が 3 件以上存在 AND 上記 HIGH 条件のいずれも満たさず AND `extrapolated_time > time_medium_min` THEN risk は `MEDIUM` と SHALL 判定する
4. WHEN 同一 `source_ids` の過去 run が 0-2 件 AND `estimated_rows > static_rows_high` THEN risk は `HIGH` + `flag=history_insufficient` と SHALL 判定する
5. WHEN 同一 `source_ids` の過去 run が 0-2 件 AND `estimated_rows <= static_rows_high` THEN risk は `MEDIUM` + `flag=history_insufficient` と SHALL 判定する
6. IF `.insight/config.yaml` に `premortem:` セクションが存在しない THEN `/premortem` SHALL 以下のデフォルト値を使用する:
   - `time_high_min: 120` — extrapolated_time がこれを超えると HIGH
   - `time_medium_min: 45` — extrapolated_time がこれを超えると MEDIUM
   - `history_min_samples: 3` — history_based 判定に必要な最小件数
   - `history_extrapolation_buffer: 1.3` — 悲観バッファ倍率
   - `success_rate_high_threshold: 0.6` — success_rate がこれを下回ると HIGH
   - `static_rows_high: 10000000` — history 不足時に HIGH と判定する行数閾値
   - `token_ttl_hours: 24` — 承認トークンの TTL
   - `approved_by_required: false` — Phase A 期間中の default。Phase B 移行時に true に切替（FR-5.4 / AC-5.3b）
   
   注: `static_rows_medium` は handoff Q1.5 で定義されていたが本 spec の判定ツリーでは使用しない（history 不足時は static_rows_high の境界で HIGH / MEDIUM に二分）。将来の細分化のため予約はしない（YAGNI、使用時に再定義）

### Requirement 3: 承認トークンのライフサイクル

**User Story:** As the batch launcher, I need an approval token that proves each design was checked and authorized, with tamper detection via design_hash and TTL-based expiry, so that audit evidence exists even in fully automated `auto` mode.

**Functional Requirements:**
- FR-3.1: トークンファイル形式 — `.insight/premortem/{TIMESTAMP}.yaml`（例: `20260418_183015.yaml`）
- FR-3.2: トークン内容 — `token_id / created_at / expires_at / approved_by (human|auto) / risk_summary / approved_designs[] / skipped_designs[]`
- FR-3.3: 各 `approved_designs` エントリは `design_id / design_hash / risk_at_approval / est_min` を持つ
- FR-3.4: `design_hash` — 対象フィールド `hypothesis, intent, methodology, source_ids, metrics, acceptance_criteria` を sorted JSON 化し sha256 で算出。除外フィールド `updated_at, status, next_action, review_history`
- FR-3.5: TTL 検証 — `/batch-analysis --approved-by TOKEN` 起動時に `expires_at` を検証。default 24h (`token_ttl_hours`)。超過時は起動を拒否
- FR-3.6: design_hash 検証 — 承認後に design が書き換えられた場合は `/batch-analysis` が当該 design の実行を skip し `manifest.yaml` に `skip_reason: hash_mismatch` を記録
- FR-3.7: `auto` モードでも常にトークンを発行する（監査証跡、将来の信頼度判定のインプット）

#### Acceptance Criteria

1. WHEN `/premortem` がトークン発行を完了する THEN トークンファイル `.insight/premortem/{TIMESTAMP}.yaml` SHALL 存在し、`approved_by` は対話承認なら `human`、`--yes` or `auto` モード起点なら `auto` に設定される
2. WHEN `/batch-analysis --approved-by TOKEN` が起動する AND トークンの `expires_at < now()` THEN `/batch-analysis` SHALL 起動を拒否し、stderr に `token expired` を出力して exit code 1 で終了する
3. WHEN `/batch-analysis --approved-by TOKEN` が design を処理開始する AND その design の現在の hash がトークン内 `design_hash` と不一致 THEN `/batch-analysis` SHALL 当該 design を skip し、per-design `manifest.yaml` に `status: skipped / skip_reason: hash_mismatch` を記録する
4. WHEN `automation: auto` モードで `/batch-analysis` が起動される THEN `/premortem` SHALL 自動実行されトークンが発行され、HIGH / MEDIUM / LOW は全て `approved_designs` に入り（HIGH については `risk_at_approval: HIGH` として記録）、`summary.md` への warning 記録は `/batch-analysis` 側（FR-7.4 / AC-7.4）で行う
5. IF `.insight/premortem/` ディレクトリが存在しない THEN `/premortem` SHALL トークン書き出し時に atomic に作成する

### Requirement 4: Run / Design Manifest Schema

**User Story:** As the batch harness, I need a two-level manifest structure (`run.yaml` for run-wide metadata and per-design `manifest.yaml` for execution records) that is written atomically at design boundaries, so that history-based extrapolation can query past runs and crash recovery can detect incomplete runs.

**Functional Requirements:**
- FR-4.1: ディレクトリ構造 — `.insight/runs/{YYYYMMDD_HHmmss}/` の直下に `run.yaml`、`events.jsonl`、`summary.md` を配置し、配下に `{design_id}/` サブディレクトリを作り `notebook.py`、`manifest.yaml`、`__marimo__/session/notebook.py.json` を置く
- FR-4.2: `run.yaml` — run 開始時に基本情報（run_id, session_id, started_at, automation_mode, premortem_token）を書き、run 終了時に cost_total, ended_at, status を追記する
- FR-4.3: Per-design `manifest.yaml` — design 完走ごとに **全体を atomic に 1 回で書き切る**（append ではない、tempfile + `os.replace()`）
- FR-4.4: Per-design 必須フィールド — `design_id / run_id / started_at / ended_at / design_snapshot (hash, source_ids, intent, methodology) / methodology_tags / input_profile (estimated_rows, column_count, data_volume_strategy) / execution (elapsed_min, cost_usd, api_retries, tool_calls, status, error_category, skip_reason) / verdict (direction, confidence, events_recorded)`
- FR-4.5: `status` enum — 5 種: `success / error / timeout / skipped / incomplete`。`incomplete` は crash 検出時に次回起動で付与
- FR-4.6: `methodology_tags` — batch agent が notebook 生成時に `.insight/rules/methodology_vocab.yaml` の predefined vocab から 1-3 個選択。事前定義語彙は 10 種（correlation_analysis, regression, time_series, classification, clustering, hypothesis_test, descriptive, segmentation, causal_inference, ab_test）
- FR-4.7: `verdict` 非正規化 — journal.yaml の `direction / confidence` を manifest に重複コピー（history 検索時に journal open 不要、クエリ高速化）
- FR-4.8: Skip / error 時も manifest は欠落させない（`status=skipped/error` で必ず書く）

#### Acceptance Criteria

1. WHEN `/batch-analysis` が run を開始する THEN `.insight/runs/{YYYYMMDD_HHmmss}/run.yaml` SHALL `run_id`, `session_id`, `started_at`, `automation_mode`, `premortem_token` の 5 フィールドを持って存在する
2. WHEN `/batch-analysis` が 1 つの design の処理を完了（success / error / timeout / skipped のいずれか）する THEN `.insight/runs/{YYYYMMDD_HHmmss}/{design_id}/manifest.yaml` SHALL FR-4.4 の全フィールドを持って atomic に書き出される（部分書き込み禁止）
3. WHEN design が `status: success` で完了する THEN manifest の `verdict.direction` は `supports | contradicts | question` のいずれかであり、かつ当該値は `{design_id}_journal.yaml` の direction と一致する SHALL
4. WHEN batch agent が notebook を生成する THEN 当該 design の manifest `methodology_tags` SHALL `.insight/rules/methodology_vocab.yaml` に定義された 10 種から 1-3 個のみを含む
5. WHEN `/premortem` が history 検索を実行する THEN SHALL 当該プロセスから SQLite への接続は 0 回、`.insight/runs/*/*/manifest.yaml` のグロブ + YAML read のみでデータ取得が完結する（観測可能条件）

### Requirement 5: 公式 Claude Code Harness との結線

**User Story:** As the batch operator, I want the launcher to use Claude Code's official `--output-format stream-json` and session persistence instead of the current `> session.log 2>&1`, so that crash-safe NDJSON events are captured and `--resume <session-id>` works out of the box.

**Functional Requirements:**
- FR-5.1: 起動コマンドを `--output-format stream-json --include-hook-events --fallback-model sonnet` に切り替え、出力先を `{RUN_DIR}/events.jsonl` にする（拡張子 `.jsonl` は NDJSON を明示）
- FR-5.2: 廃止項目 — 自前 `progress.json` ロジック、自前 resume ロジック、`> session.log 2>&1` の raw text 出力
- FR-5.3: `session_id` は `events.jsonl` の `{"type":"system","subtype":"init"}` 行から抽出し、`run.yaml` に保存する
- FR-5.4: `/batch-analysis` のコマンドラインに `--approved-by TOKEN` フラグを追加する。本 spec では 2 段階で段階導入する:
  - **Phase A (transitional)** — 未指定起動は warning を stderr に出すのみで実行は続行。`run.yaml` の `premortem_token: null` + `automation_mode: legacy` として記録。切替期限: 本 spec の `/premortem` 実装が merge された日から 14 日間 (Phase A 期間)
  - **Phase B (final)** — Phase A 終了後は未指定起動は拒否 (exit 1)。切替は `.insight/config.yaml` の `batch.approved_by_required: true` で能動的に有効化する（default: Phase A 期間中は false、期間後に true へ変更するマイグレーションタスクを Tasks に含める）
  - この段階導入により既存 `/batch-analysis` 呼び出し手順を即座に破壊せず、add-only 方針と整合させる
- FR-5.5: `--max-budget-usd 10`（既存）、`--max-turns`（新規、config `batch.max_turns` default 200）を併用する

#### Acceptance Criteria

1. WHEN `/batch-analysis` が起動する THEN launcher コマンド SHALL `--output-format stream-json` と `--include-hook-events` の両オプションを含み、stdout/stderr は `{RUN_DIR}/events.jsonl` に `>` でリダイレクトされる
2. WHEN `events.jsonl` に 1 行以上書き込まれる THEN その最初の `{"type":"system","subtype":"init"}` 行から `session_id` を抽出し、`run.yaml` に `session_id:` として書く SHALL
3. WHEN `/batch-analysis` が `--approved-by` フラグなしで起動される AND `.insight/config.yaml` の `batch.approved_by_required: true` THEN SHALL stderr に `--approved-by required; run /premortem first` を出力し exit code 1 で終了する
3b. WHEN `/batch-analysis` が `--approved-by` フラグなしで起動される AND `batch.approved_by_required: false`（Phase A 期間、default） THEN SHALL stderr に `WARNING: running without /premortem approval (Phase A transitional)` を出力した上で実行を続行し、`run.yaml` に `premortem_token: null / automation_mode: legacy` を記録する
4. WHEN 既存の `/batch-analysis` skill の launch 手順（`skills/batch-analysis/SKILL.md` L215-226）が更新される THEN 新コマンドは `session.log` ではなく `events.jsonl` に書き出し、`progress.json` の生成ロジックは存在しない SHALL
5. IF `--max-budget-usd` または `--max-turns` の上限に達する THEN Claude Code は session を終了し、`/batch-analysis` の incomplete 検出（FR-6）に引き継がれる SHALL

### Requirement 6: Crash Recovery

**User Story:** As the data analyst waking up to an interrupted overnight batch, I want the next launch of `/batch-analysis` to detect incomplete runs and resume them from the last completed design, so that no design is re-executed needlessly and no incomplete state is silently ignored.

**Functional Requirements:**
- FR-6.1: 中断検出 — `/batch-analysis` 起動時に `.insight/runs/*/run.yaml` をスキャンし、`status: incomplete` または `ended_at` 未設定の run が存在すれば検出対象とする
- FR-6.2: 完了 design 判定 — 中断 run 配下の各 design サブディレクトリで `manifest.yaml` が存在し `status != incomplete` なら完了扱い、それ以外は未完了
- FR-6.3: Resume — 未完了 design のうち「design が `--approved-by` トークンで承認済み」かつ「トークンが TTL 内」のもののみ、`claude -p ... --resume <session_id>` で再開する（新規 session を使わない）
- FR-6.4: Incomplete マーキング — 完了 design なし or トークン失効 の design は `manifest.yaml` を `status: incomplete` + `skip_reason: token_expired_or_crashed` で確定記録する
- FR-6.5: Run 完了時の `status` 更新 — 全 design 処理後、`run.yaml` の `ended_at` と `status: completed` を追記する

#### Acceptance Criteria

1. WHEN `/batch-analysis` が起動する AND 既存の `.insight/runs/` 配下に `run.yaml.status` が `incomplete` または未設定の run が存在する THEN SHALL stderr に `detected incomplete run: {run_id}` を表示し、resume を試みる
2. WHEN 中断 run 配下の design サブディレクトリに `manifest.yaml` が存在せず、かつ承認トークンが TTL 内 THEN `/batch-analysis` SHALL `claude -p ... --resume {session_id}` で再開し、新規 `events.jsonl` には `>>`（append）でリダイレクトする
3. WHEN 承認トークンが TTL 超過 THEN resume は行わず、未完了 design の `manifest.yaml` を `status: incomplete / skip_reason: token_expired_or_crashed` で書き確定する SHALL
4. WHEN run が全 design を処理完了する THEN `run.yaml` の `ended_at` と `status: completed` が追記され、以降の起動で当該 run は中断検出の対象にならない SHALL
5. IF 中断検出で複数 run が見つかった THEN `/batch-analysis` SHALL 最新 1 件のみを resume 対象とし、それ以前の中断 run は `status: incomplete` 固定で確定する

### Requirement 7: Automation Mode 3 段階

**User Story:** As the data analyst progressing from manual oversight toward unattended operation, I want three automation modes (`manual` / `review` / `auto`) that differ only in how HIGH-risk items are handled, so that I can ratchet up autonomy without changing risk threshold definitions.

**Functional Requirements:**
- FR-7.1: Mode は `.insight/config.yaml` の `batch.automation: manual | review | auto`（default: `review`）で指定する
- FR-7.2: `manual` — `/premortem` を対話実行必須（`--yes` 禁止）、HIGH/MEDIUM/LOW の全てで対話承認を求める
- FR-7.3: `review` — `/batch-analysis` 起動時に `/premortem` を自動実行、HIGH があれば停止して人間の承認を要求、LOW/MEDIUM は自動承認して続行
- FR-7.4: `auto` — `/premortem` を起動時に自動実行、HIGH は warning を `summary.md` に記録して続行（自動 skip は行わず、設計者の判断を尊重）、LOW/MEDIUM は自動承認して続行
- FR-7.5: 閾値と mode は **直交** — 閾値は「HIGH の定義」、mode は「HIGH の扱い方」。連動させない
- FR-7.6: 全 mode でトークンを発行する（監査証跡、将来の信頼度判定のインプット）

#### Acceptance Criteria

1. WHEN `automation: manual` で `/batch-analysis` が起動される THEN `/premortem` SHALL `--yes` を受け付けず、全 design について対話で承認を求める
2. WHEN `automation: review` で `/batch-analysis` が起動される AND HIGH risk が 1 件以上ある THEN `/batch-analysis` SHALL 停止し、stdout に HIGH 一覧と `[s]kip [e]dit [a]bort [c]ontinue` 選択肢を表示する
3. WHEN `automation: review` で `/batch-analysis` が起動される AND HIGH risk が 0 件 THEN `/batch-analysis` SHALL LOW/MEDIUM を全自動承認し、batch 本体の実行に進む
4. WHEN `automation: auto` で `/batch-analysis` が起動される AND HIGH risk が 1 件以上ある THEN `/batch-analysis` SHALL 該当 design を実行対象に含め、`summary.md` に `WARNING: HIGH risk executed without human approval` を記録する
5. IF `batch.automation` キーが `.insight/config.yaml` に存在しない THEN default は `review` と SHALL なる

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility** — `/premortem` と `/batch-analysis` は責務が重ならない（Q1.2 の境界を厳守）。manifest writer、token manager、risk evaluator、premortem skill body は独立モジュール
- **Modular Design** — 閾値定義 (`.insight/config.yaml`) と methodology vocab (`.insight/rules/methodology_vocab.yaml`) は外部化し、コードから参照する
- **Dependency Management** — `batch-harness-engineering` 系のコードは既存 insight-blueprint の storage/models 層に直接依存しない（skill 側は `.insight/` YAML の直接読み書きで完結、MCP tool 経由で既存データにアクセスする）
- **Clear Interfaces** — `/premortem` と `/batch-analysis` の契約は「承認トークン YAML ファイル」1 点のみ。関数コール境界は持たない（skill 独立性）

### Performance

- `/premortem` の実行時間目標: 10 designs × history 30 runs の条件で **30 秒以内**（グロブ + YAML load のみで SQLite index 不要）
- Manifest atomic write の所要時間: **100ms 以内** / design
- `events.jsonl` からの `session_id` 抽出: **500ms 以内**（最初の system/init 行のみ読む）

### Security

- 承認トークンは機密情報を含まない（design_id, design_hash, 実行時間推定値のみ）。`.insight/premortem/` は `.gitignore` 対象とする
- `design_hash` は sha256、追跡目的であり暗号論的認証ではない（改竄検知レベル）
- `/batch-analysis` が `bypassPermissions` で起動する前提は既存 v1.0 を継承（trusted-analyst 仮定）。本 spec はこれを変えない

### Reliability

- **Atomic writes** — `run.yaml`, `manifest.yaml`, premortem token はすべて tempfile + `os.replace()` で atomic 書き込み
- **Crash safety** — events.jsonl は NDJSON 行フラッシュのため最後に書かれた行までは残る前提（公式仕様に明示保証はないが、`--output-format stream-json` の実装準拠）
- **Budget ceiling** — `--max-budget-usd 10` と `--max-turns 200` のダブルガード
- **TTL enforcement** — 承認トークン 24h 超過で自動失効、design_hash 不一致で個別失効

#### 代表障害シナリオと期待挙動（定量）

| シナリオ | 検出手段 | 検出時間目標 | 復旧手段 | 許容データ損失 |
|---|---|---|---|---|
| Claude Code プロセス強制終了（PC シャットダウン等） | 次回 `/batch-analysis` 起動時に `run.yaml.status != completed` を検出 | 次回起動時即時（< 1 秒 / run） | `--resume {session_id}` で未完了 design から再開 | 最大 1 design 分の中間状態（notebook.py は残るが session JSON は失われる可能性） |
| 子プロセス孤児化（scipy 最適化ハング等） | `--max-turns` / `--max-budget-usd` 超過で session 終了 | ハング開始からハード上限まで（最大 30min/design 想定） | 当該 design を `status: timeout` で manifest 確定、次 design に進む | なし（孤児プロセスは OS レベルで残留する可能性あり、本 spec のスコープ外の二次防御） |
| 承認トークン期限切れ（run 途中で 24h 経過） | `/batch-analysis` の design 処理開始時に TTL 検証 | 検証時即時 | 未処理 design を `status: incomplete / skip_reason: token_expired_or_crashed` で確定、run 終了 | なし（処理済み design は完了扱いで保全） |
| design_hash 不一致（承認後に design が書き換えられた） | `/batch-analysis` の design 処理開始時に hash 比較 | 処理開始時即時 | 当該 design を `status: skipped / skip_reason: hash_mismatch` で確定、次 design に進む | なし |
| `events.jsonl` 書き込み途中のクラッシュ | 最終行が壊れた NDJSON の場合、次回起動時に `session_id` 抽出ロジックで警告 | 次回起動時即時 | 壊れた最終行を無視して 1 行手前の `session_id` を採用（fallback） | 最大 1 stream event |

### Usability

- **1 画面 CLI** — `/premortem` の出力は 80 カラム幅の stdout で完結、TUI や WebUI 拡張は不要
- **段階的自動化** — `manual → review → auto` の進化パスが config 1 行で切替可能
- **エラーメッセージ** — HARD_BLOCK 時は理由を具体的に表示（例: `source orders_big has no past run`、`package lingam not in allowlist`）
- **既存 CLI 互換** — 既存の `/batch-analysis` 呼び出し手順（`update_analysis_design(id, next_action={"type":"batch_execute"})`）は引き続き動作する

## Out of Scope

Issue #108 からの継承:

- フル自動化の最終形（段階移行前提、`manual → review → auto` で進化。信頼度ベース自動判定は履歴 30+ run 蓄積後の将来拡張）
- 新規 knowledge base 構築（既存 `.insight/rules/` + LLM 知識で十分）
- 外部調査（Gemini / 論文）の自動統合（手運用でも使用頻度低）

本 spec 固有:

- SQLite によるインデックス化（`.insight/runs/*/manifest.yaml` グロブで当面十分、entries < 1000 想定）
- spec-workflow dashboard 拡張（batch の周期とレビューの関心がズレるため、CLI 1 画面で足りる）
- `PreToolUse` hook による重いライブラリの early-decline (#97 L1) — プロセスレベルのタイムアウト改善は本 spec のスコープ外（将来、premortem で防げなかったケースの二次防御として検討）
- 高カーディナリティ検出 / 不均衡チェック / 収束保証の明示判定 (#108 項目 3, 4, 7) — 今回は rows ベースで近似、将来拡張
- 類似 design の既知落とし穴検索 (#108 項目 11) — journal/rules 横断検索の UI を持たないため今回は手運用継続
- `/premortem` の `[e]dit` オプション経由の design 自動書換 — 対話から `/analysis-design {id}` を呼び出すハンドオフのみ、本体の書換ロジックは既存 skill に委譲

## Glossary

| 用語 | 定義 |
|---|---|
| Harness | `/batch-analysis` を取り巻く事前チェック・永続化・復旧の総称。Claude Code 公式機能 + 自前 YAML の組合せで構成 |
| Premortem | Gary Klein の事前失敗分析。本 spec では Tier 1（機械チェック）+ Tier 2（推奨生成）+ Tier 3（例外エスカレーション）の Two-Tier + Exception 構造を指す |
| Risk level | `LOW / MEDIUM / HIGH / HARD_BLOCK / SKIP` の 5 値。HARD_BLOCK は実行不能系（承認ゲート外、対話でも continue 不可）、SKIP は終端 status 済みで判定対象外 |
| skipped (manifest status) | per-design `manifest.yaml` の `status: skipped`。pre-flight HARD_BLOCK or 未承認 or hash_mismatch の場合に付与。Risk level の SKIP（終端 status 済み）とは別概念 |
| skipped_designs (token field) | 承認トークン内の配列。`/premortem` が発行時点で skip と判定した design の一覧（HARD_BLOCK、`--yes` 時の一部 mode など） |
| run_status | `run.yaml.status` の値。`running / completed / incomplete` の 3 値。per-design `manifest.yaml.status` の 5 値とは独立した別 enum |
| Automation mode | `manual / review / auto` の 3 値。HIGH の扱い方を規定する。閾値とは直交 |
| Run | `.insight/runs/{YYYYMMDD_HHmmss}/` 単位の実行セッション。1 run = N designs |
| Manifest | Per-design の実行記録 YAML (`{design_id}/manifest.yaml`)。history 検索の主役 |
| Approval token | `.insight/premortem/{TIMESTAMP}.yaml`。`/premortem` が発行、`/batch-analysis --approved-by` が検証 |
| `design_hash` | sha256 of sorted JSON of {hypothesis, intent, methodology, source_ids, metrics, acceptance_criteria}。承認後の書換検知用 |
| methodology_vocab | `.insight/rules/methodology_vocab.yaml`。predefined 10 種の分析手法タグ |
| Verdict | journal.yaml の `direction (supports\|contradicts\|question)` + `confidence (high\|medium\|ambiguous)` を manifest に非正規化コピーしたもの |

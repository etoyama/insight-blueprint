# Tasks Document

TDD (Red → Green → Refactor) 順序で実装計画を組む。タスク ID は spec-workflow-rules.md 準拠の `<major>.<minor>` 形式。1 タスク = 1-3 ファイル / 1-3 時間を目安。

## 共通 Restrictions（全タスク適用、以下 CR-N で参照）

- **CR-1**: 既存 `/batch-analysis` の `skills/batch-analysis/SKILL.md` と `references/batch-prompt.md` を破壊せず、**add-only** で拡張する
- **CR-2**: MCP server 側 (`src/insight_blueprint/`) のコードは一切変更しない
- **CR-3**: skills 間で直接 Python import を行わず、共通ロジックは `skills/_shared/` に集約し両 skill がそこを import する
- **CR-4**: `pip` 直接使用禁止、依存追加は `uv add`
- **CR-5**: テストコードは仕様として扱い、実装コードのみを修正対象とする（TDD 原則）

---

## Group 1: Foundation（atomic write + vocab + data models + config loader）

- [x] 1.1 atomic write helper と methodology vocab を新設
  - File: `skills/_shared/_atomic.py`, `skills/_shared/__init__.py`, `.insight/rules/methodology_vocab.yaml`, `tests/batch_harness/test_atomic.py`
  - `atomic_write_yaml(path, data)` と `atomic_write_text(path, text)` を tempfile + os.replace + filelock で実装（同ディレクトリに temp、`os.replace` で atomic rename、filelock で同プロセス内/プロセス間排他）
  - ディレクトリ未作成時は `parents=True, exist_ok=True` で mkdir
  - `methodology_vocab.yaml` に 10 種 tag を list 定義（correlation_analysis, regression, time_series, classification, clustering, hypothesis_test, descriptive, segmentation, causal_inference, ab_test）— Git 管理対象
  - Unit テスト: 正常 write / 書込失敗時の既存ファイル保持 / 並行 2 プロセスで片方勝ち / dir 未作成時の自動作成
  - Purpose: 後続すべての YAML I/O に atomic + vocab の基盤を提供
  - _Leverage: `src/insight_blueprint/storage/yaml_store.py`（パターン参考、import せずコピー移植）, `filelock`（既存依存）, `ruamel.yaml`（既存依存）_
  - _Requirements: FR-4.3 (atomic), FR-4.6 (vocab), NFR Reliability_
  - _Prompt: Role: Python 永続化と並行制御に強いエンジニア | Task: atomic write helper と methodology_vocab.yaml を実装、pytest で 4 ケース以上の Unit テストを先に書いて Red → 実装で Green。CR-1〜5 を遵守 | Restrictions: `src/insight_blueprint` を import しない（CR-2, CR-3）、`pip install` 禁止（CR-4）、tempfile は同ディレクトリに作る（cross-device rename 回避） | Success: `tests/batch_harness/test_atomic.py` の全ケースが pass、methodology_vocab.yaml が ruamel.yaml でロードでき 10 種の tag を返す_

- [x] 1.2 Data Models (StrEnum + dataclass + config loader) を実装
  - File: `skills/_shared/models.py`, `skills/_shared/config_loader.py`, `tests/batch_harness/test_premortem_config.py`
  - StrEnum: `RiskLevel`, `RunStatus`, `ManifestStatus`, `AutomationMode` — design.md Data Models 通りの **メンバ名 UPPER_SNAKE_CASE / 値 lower_snake_case**（例: `RiskLevel.HARD_BLOCK = "hard_block"`）
  - dataclass (frozen=True): `DesignHashInput`, `DesignEntry`, `Token`, `TokenVerifyResult`, `HistoryStats`, `RiskDecision`, `SourceChecks`, `PremortemConfig`, `DesignManifest`, `RunManifest`, `RunRef`
  - `config_loader.load_premortem_config(path: Path) -> PremortemConfig` — `.insight/config.yaml` を read、premortem / batch セクションに default merge
  - Unit-08 (test_premortem_config.py) 先に書く → Red → 実装で Green
  - Purpose: 後続タスクが共通の型に依存、StrEnum で YAML シリアライズが自然
  - _Leverage: `ruamel.yaml`, `dataclasses`, `typing`, `enum.StrEnum`_
  - _Requirements: AC-2.6, AC-7.5, AC-5.3b, Data Models セクション全体_
  - _Prompt: Role: Python 型システム & YAML ライブラリ精通者 | Task: design.md Data Models 通りに StrEnum / dataclass / config loader を実装。config 未設定時に handoff default 値（time_high_min=120, time_medium_min=45, history_min_samples=3, buffer=1.3, success_rate_high_threshold=0.6, static_rows_high=10000000, token_ttl_hours=24, batch.automation=review, approved_by_required=false, max_turns=200, max_budget_usd=10）を merge。CR-1〜5 を遵守 | Restrictions: pydantic は使わず dataclass のみ（CR-3 の skill 独立性維持）、**StrEnum のメンバ名は UPPER_SNAKE_CASE、値は lower_snake_case**（Python 慣例準拠）、frozen=True 必須 | Success: Unit-08 の 4 ケース（defaults / partial override / batch.automation default / approved_by_required default）がすべて pass_

---

## Group 2: Shared libraries (token_manager / manifest_writer / crash_recovery)

- [x] 2.1 token_manager の issue / verify / TTL 検証を実装（Red: Unit-09, 10, 14）
  - File: `skills/_shared/token_manager.py`, `tests/batch_harness/test_token_manager.py`
  - Unit-09 (issue 5 ケース), Unit-10 (verify 4 ケース), **Unit-14 (atomic dir create 2 ケース)** を先に書いて Red → 実装で Green
  - `issue(approved, skipped, approved_by, automation_mode, ttl_hours) -> str` — `.insight/premortem/` ディレクトリ未作成なら作成 + atomic write
  - `verify(token_id, now) -> TokenVerifyResult` — 期限切れ判定は `<` 厳密比較
  - Purpose: token の発行・検証・atomic ディレクトリ作成の基盤
  - _Leverage: `skills/_shared/_atomic.py`, `skills/_shared/models.py`_
  - _Requirements: AC-3.1, AC-3.2, AC-3.5, AC-1.3_
  - _Prompt: Role: TDD を厳守する Python 開発者 | Task: Unit-09, 10, 14 をテスト先行で実装。issue の token_id は `YYYYMMDD_HHmmss` 形式（JST）、expires_at = created_at + ttl_hours、verify は 4 条件（ok / expired / not_found / 境界）。CR-1〜5 遵守 | Restrictions: design_hash は次タスク（2.2）で実装、issue 内で hash を compute しない、token file 名は `{token_id}.yaml` に限定 | Success: Unit-09 (5) + Unit-10 (4) + Unit-14 (2) の計 11 ケースが pass、書き出し後のファイルが ApprovalToken schema 通り_

- [x] 2.2 token_manager の design_hash canonicalization と auto mode 分配（Red: Unit-11, 12, 13）
  - File: `skills/_shared/token_manager.py` (continue), `tests/batch_harness/test_token_manager.py` (continue)
  - Unit-11 (3), Unit-12 (10), Unit-13 (3) を先に書いて Red → 実装で Green
  - `compute_design_hash(design: dict) -> str` — design.md "Design Hash Canonicalization" 通り:
    1. 含む: hypothesis, intent, methodology, source_ids, metrics, acceptance_criteria
    2. 除外: id, created_at, updated_at, status, next_action, review_history
    3. source_ids を sorted()、metrics / acceptance_criteria 内の dict も key ソート
    4. `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))`
    5. `hashlib.sha256(...).hexdigest()` を `sha256:` prefix 付きで返す
  - `verify_design_hash(token, design_id, current_hash) -> bool`
  - `issue` に auto mode 分配を追加: automation_mode=auto かつ risk=HIGH → approved_designs[] に `risk_at_approval=HIGH` で入れる（skipped には入れない）
  - Purpose: 改竄検知と auto mode の承認配分を確立
  - _Leverage: task 2.1 成果物, `hashlib`, `json`_
  - _Requirements: AC-3.3, AC-3.4, FR-3.4_
  - _Prompt: Role: JSON canonicalization と暗号ハッシュに詳しい Python 開発者 | Task: Unit-11/12/13 先行実装。canonicalization は source_ids sorted + json.dumps sort_keys + separators(",",":") で whitespace 無関係にする。CR-1〜5 遵守 | Restrictions: `hypothesis`, `intent`, `methodology`, `source_ids`, `metrics`, `acceptance_criteria` 以外をハッシュ入力に含めない、metrics の dict 内部も再帰的に key ソート | Success: Unit-11 (3) + Unit-12 (10、`id`/`created_at`/`updated_at`/`status`/`next_action` 除外と source_ids 順序不変すべて) + Unit-13 (3) が pass、同一内容 × 異なる key 順 / whitespace で hash 完全一致_

- [x] 2.3 manifest_writer を実装（Red: Unit-15〜18, 23）
  - File: `skills/_shared/manifest_writer.py`, `tests/batch_harness/test_manifest_writer.py`
  - Unit-15 (3), Unit-16 (5), Unit-17 (4), Unit-18 (6), Unit-23 (3) を先に書いて Red → 実装で Green
  - `init_run(run_id, session_id, automation_mode, token_id)` — run.yaml 初期化（status=running）
  - `update_run_session_id(run_id, session_id)` — 部分更新（既存フィールド保持）
  - `finalize_run(run_id, status, cost_total_usd, ended_at)` — ended_at / status / cost_total 追記
  - `write_design_manifest(run_id, design_id, manifest)` — vocab validation → atomic whole-file write
  - `load_vocab() -> set[str]` + `MethodologyTagError`
  - Purpose: run/per-design 永続化レイヤの完成
  - _Leverage: `skills/_shared/_atomic.py`, `skills/_shared/models.py`, `.insight/rules/methodology_vocab.yaml`_
  - _Requirements: AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-5.2, AC-6.3, AC-6.4_
  - _Prompt: Role: Python 永続化レイヤ専門、YAML round-trip 保持に慣れた開発者 | Task: 5 公開関数を実装、vocab 検証は raise 方式（空配列書き出しは禁止、design.md Error #8 準拠）、verdict は journal.yaml から read して非正規化コピー。CR-1〜5 遵守 | Restrictions: append ベースの書き込み禁止、常に whole-file atomic write、status=skipped / error / timeout / incomplete でも manifest を欠落させない | Success: Unit-15 (3) + Unit-16 (5) + Unit-17 (4) + Unit-18 (6) + Unit-23 (3) の計 21 ケースが pass、部分書込クラッシュで既存ファイル破損なし_

- [x] 2.4 crash_recovery を実装（Red: Unit-20, 21, 22）
  - File: `skills/_shared/crash_recovery.py`, `tests/batch_harness/test_crash_recovery.py`
  - Unit-20 (4), Unit-21 (2), Unit-22 (3) を先に書いて Red → 実装で Green
  - `detect_incomplete() -> list[RunRef]` — `.insight/runs/*/run.yaml` で status != "completed"、started_at 降順ソート
  - `unfinished_designs(run_ref) -> list[str]`
  - `finalize_incomplete(run_ref, design_ids, reason)` — manifest_writer 経由で status=incomplete 書き、run.yaml.status=incomplete
  - Purpose: 中断検出と確定処理
  - _Leverage: `skills/_shared/manifest_writer.py`, `skills/_shared/token_manager.py`_
  - _Requirements: AC-6.1, AC-6.3, AC-6.5_
  - _Prompt: Role: ファイルシステム走査と状態管理に慣れた Python 開発者 | Task: Unit-20/21/22 先行。最新選択は started_at 降順、古い中断は `status=incomplete` 固定。CR-1〜5 遵守 | Restrictions: manifest 書き出しは manifest_writer 経由のみ（atomic 保証）、run_id の parse は JST 形式前提 | Success: Unit-20 (4) + Unit-21 (2) + Unit-22 (3) の計 9 ケースが pass_

---

## Group 3: Premortem lib (history_query / risk_evaluator)

- [ ] 3.1 history_query を実装（Red: Unit-19）
  - File: `skills/premortem/lib/__init__.py`, `skills/premortem/lib/history_query.py`, `tests/batch_harness/test_history_query.py`
  - Unit-19 (6 ケース) を先に書いて Red → 実装で Green
  - `query(source_ids, min_samples) -> HistoryStats`
  - `.insight/runs/*/*/manifest.yaml` を glob → `source_ids` **完全一致** でフィルタ → n, median(elapsed_min), median(estimated_rows), success_rate
  - sqlite3 は一切 import しない（Unit-19 で mock 監視）
  - 壊れた YAML は warnings.warn で skip
  - Purpose: 外挿式の入力を YAML グロブのみで取得
  - _Leverage: `ruamel.yaml`, `pathlib`, `statistics.median`, `skills/_shared/models.py`_
  - _Requirements: AC-4.5, AC-2.3, AC-2.3b, AC-2.3c, AC-2.4, AC-2.5_
  - _Prompt: Role: データ集計と pathlib グロブに強い Python 開発者 | Task: Unit-19 (6 ケース) 先行。sqlite3 / sqlalchemy の import 禁止、source_ids 完全一致のみ。CR-1〜5 遵守 | Restrictions: lazy loading なしで 1 関数呼び出しで全 YAML 読む（監視しやすさ優先）、部分一致禁止 | Success: Unit-19 の全 6 ケースが pass、`mock.patch("sqlite3.connect")` で呼び出し 0 回を確認_

- [ ] 3.2 risk_evaluator を実装（Red: Unit-01〜07）
  - File: `skills/premortem/lib/risk_evaluator.py`, `tests/batch_harness/test_risk_evaluator.py`
  - Unit-01 (5), 02 (6), 03 (3), 04 (4), 05 (2), 06 (3), 07 (2) を先に書いて Red → 実装で Green
  - `evaluate(design, history, config, source_checks) -> RiskDecision`
  - 決定ツリー (design.md FR-2.1-2.6):
    1. terminal status → SKIP
    2. HARD_BLOCK: source 未登録 / package allowlist 外 / BQ location 検証成功 + 不一致
    3. API 失敗系 (BQ / allowlist 読み取り) → HIGH + `flag=location_check_failed` or `allowlist_check_failed`（design.md Error #9/#10）
    4. history n >= min_samples: extrapolated > time_high_min OR success_rate < success_rate_high_threshold → HIGH、time_medium_min 超過 → MEDIUM、それ以外 LOW
    5. history 不足: rows > static_rows_high → HIGH + `history_insufficient`、それ以外 MEDIUM + `history_insufficient`
  - 外挿式: `median_elapsed * (new_rows / median_rows) * buffer`
  - Purpose: premortem の中核判定を純粋関数で確立
  - _Leverage: `skills/_shared/models.py`, HistoryStats の型だけ参照（history_query 関数は呼ばない）_
  - _Requirements: AC-2.1, AC-2.2, AC-2.3, AC-2.3b, AC-2.3c, AC-2.4, AC-2.5, Error-Handling-9, Error-Handling-10_
  - _Prompt: Role: 決定木と境界値テストに強い Python 開発者 | Task: Unit-01〜07 先行実装。境界は厳密比較（`<` / `>`）、success_rate=0.6 ちょうどは HIGH でない、static_rows=10000000 ちょうどは MEDIUM。CR-1〜5 遵守 | Restrictions: I/O 禁止（純粋関数）、config は引数で受け取る、flag は list[str] で複数可、reasons は日本語の簡潔な説明 | Success: Unit-01〜07 の計 25 ケース以上が pass_

---

## Group 4: Skill integration (/premortem + /batch-analysis + batch-prompt)

- [ ] 4.1 /premortem skill (SKILL.md + CLI 骨格) を実装
  - File: `skills/premortem/SKILL.md`, `skills/premortem/cli.py`, `skills/premortem/__init__.py`
  - SKILL.md: skill-format.md 準拠のフロントマター（`name: premortem`, `description` にトリガーフレーズ含む, `disable-model-invocation: true`, `argument-hint: "[--queued | --design <id> | --all] [--yes] [--mode manual|review|auto]"`）
  - `cli.py`:
    - argparse で 5 引数をパース
    - list_analysis_designs(MCP) でキュー取得（`next_action.type=batch_execute`）
    - 各 design に対し get_analysis_design + get_table_schema + search_catalog を呼び source_checks を作る
    - history_query.query → risk_evaluator.evaluate → 結果を dict 化
    - stdout rendering（design_id / intent / rows / strategy / risk / 理由、1 行/design）
    - HIGH 時に `[s]kip / [e]dit / [a]bort / [c]ontinue` 表示（HARD_BLOCK では `[c]` 非表示）
    - mode 分岐（manual=対話必須 / review=`--yes` で HIGH → exit 2 / auto=HIGH も approved_designs に入れて exit 0）
    - token_manager.issue で token 発行
    - Launch メッセージを stdout 最終行に出力
  - Purpose: premortem の外部 I/F を固める
  - _Leverage: task 2.1, 2.2, 3.1, 3.2 の成果物, 既存 MCP tools (`list_analysis_designs`, `get_analysis_design`, `get_table_schema`, `search_catalog`)_
  - _Requirements: AC-1.1, 1.2, 1.3, 1.4, 1.5, 2.2, 7.1, 7.2, 7.3, 7.4_
  - _Prompt: Role: CLI UX と Claude Code skill 設計に慣れた開発者 | Task: SKILL.md と cli.py を実装、Exit codes は 0 (成功) / 2 (review + HIGH) / 1 (想定外エラー)。CR-1〜5 遵守、書き込みは `.insight/premortem/` のみに限定 | Restrictions: MCP 呼び出しは read-only tools のみ（`list_analysis_designs`, `get_analysis_design`, `get_table_schema`, `search_catalog`）、config.batch.automation は読まず --mode 引数のみ参照、書き込み禁止契約（AC-1.5）を遵守 | Success: SKILL.md が skill-format.md 準拠、cli.py の引数解析と mode 別 exit code が AC-1.3 / 7.1 / 7.2 / 7.3 / 7.4 を満たす（対応する Integration テストは task 6.1 で検証）_

- [ ] 4.2 /batch-analysis launcher を更新 (stream-json + --approved-by + Phase A/B + crash recovery)
  - File: `skills/batch-analysis/SKILL.md` (既存、該当箇所のみ更新), `skills/batch-analysis/launcher.sh` (新規 wrapper)
  - SKILL.md L215-226 の launch command を `--output-format stream-json --include-hook-events --fallback-model sonnet --max-turns ${BATCH_MAX_TURNS:-200}` に変更、出力先を `events.jsonl` に
  - `launcher.sh` の前処理:
    1. config 読取（config_loader を呼ぶ薄い Python ラッパー経由）
    2. `crash_recovery.detect_incomplete()` 呼出し、最新 1 件に対し token 検証 → resume コマンド組立て（events.jsonl は `>>` append）
    3. `--approved-by` 未指定 + Phase B（`approved_by_required=true`）→ exit 1 + stderr "required; run /premortem first"
    4. `--approved-by` 未指定 + Phase A → stderr WARNING + `run.yaml.automation_mode=legacy / premortem_token=null`
    5. `--approved-by` 指定 + token 期限切れ → exit 1 + stderr "token expired"
    6. mode (manual / review / auto) に従って `/premortem` を dispatch（manual=対話 / review+auto=`--yes`）、review で exit 2 なら batch 停止し stdout に `[s]/[e]/[a]/[c]` 表示
    7. claude 実行後、events.jsonl から jq で最初の system/init の session_id 抽出 → manifest_writer.update_run_session_id、末尾壊れなら 1 行前採用 + stderr WARNING
    8. auto mode で approved_designs に HIGH あれば summary.md に `WARNING: HIGH risk executed without human approval`
  - Purpose: 既存 /batch-analysis を add-only で進化
  - _Leverage: task 1.2, 2.1〜2.4, 3.1, 3.2, 4.1 の成果物, 既存 SKILL.md_
  - _Requirements: AC-3.2, 3.3, 5.1, 5.2, 5.3, 5.3b, 5.4, 5.5, 6.1, 6.2, 7.2, 7.3, 7.4, 7.5_
  - _Prompt: Role: bash と Claude Code 公式ハーネスに詳しいエンジニア | Task: SKILL.md の launch command を stream-json 版に差し替え、launcher.sh で 8 段階の前処理を実装。CR-1〜5 遵守、既存 allowedTools / permission-mode / max-budget-usd は保持 | Restrictions: session.log への書き込み / progress.json 生成ロジックを削除、既存の `next_action.type=batch_execute` キュー仕組みは変えない、bash は macOS / Linux 両対応（readlink -f / GNU date 互換性） | Success: SKILL.md を diff で見ると add-only（削除は progress.json と session.log の 2 つのみ）、launcher.sh が 4 exit code パス (phase A / phase B exit 1 / token expired exit 1 / normal 0) を持つ_

- [ ] 4.3 batch-prompt.md に manifest 書き出し指示を追記
  - File: `skills/batch-analysis/references/batch-prompt.md` (既存、追記のみ)
  - Step 3e (notebook 生成) 直後: methodology_tags を `.insight/rules/methodology_vocab.yaml` から 1-3 個選択し `manifest.yaml.methodology_tags` に設定。vocab 外 → 1 回リトライ → 2 回失敗で default=[descriptive] + `error_category=logic` + `error_detail=methodology_tag_selection_failed` + journal に question event
  - Step 3h (journal 記録) 直後: verdict を journal から読み manifest.yaml.verdict に非正規化コピー
  - Step 3k (summary 更新) 直前: write_design_manifest 呼出しを明示
  - skip / error / timeout 各経路で manifest 書き出しを明示（欠落させない）
  - Purpose: batch agent に manifest 書き出しを教え込む
  - _Leverage: `skills/_shared/manifest_writer.py`, `.insight/rules/methodology_vocab.yaml`, 既存 batch-prompt.md_
  - _Requirements: AC-4.2, 4.3, 4.4, Error-Handling-8_
  - _Prompt: Role: Claude Code prompt engineering と batch 設計に慣れた開発者 | Task: batch-prompt.md の各 Step に manifest 書出しブロックを挿入。既存の 8-cell contract / 3-attempt repair loop / Self-Review は変更しない。CR-1〜5 遵守 | Restrictions: 既存の Step 番号を変えない（他ドキュメントの参照が壊れる）、自前 progress.json / session.log 記述は削除、methodology_tags 自由記述禁止を明文化 | Success: batch-prompt.md の diff が add-only（削除は progress.json / session.log のみ）、Integ-26 (vocab retry + fallback) が pass できる指示が含まれる_

---

## Group 5: E2E ハーネス (stub_claude + fixtures + harness + assertions + runners)

- [ ] 5.1 stub_claude.py と E2E fixtures を整備
  - File: `tests/e2e/__init__.py`, `tests/e2e/stub_claude.py`, `tests/e2e/fixtures/designs/*.yaml`, `tests/e2e/fixtures/runs_history/**/manifest.yaml`, `tests/e2e/fixtures/config/*.yaml`, `tests/e2e/fixtures/expected/**/*.yaml`, `tests/e2e/fixtures/mcp_responses.yaml`
  - `stub_claude.py`:
    - argparse で `--approved-by` / `--output-format stream-json` / `--max-turns` / `--resume` を parse
    - env var `STUB_KILL_AFTER_DESIGNS=N` で N 本完走後に exit 137
    - 決定的に events.jsonl 書出し: `system/init` → 各 design の `tool_use` content_block → `result`
    - fixtures の expected から各 design の manifest / journal snapshot をコピー
  - fixtures:
    - 3 designs (DES-A LOW / DES-B MEDIUM / DES-C HIGH, 異なる source_ids + intent)
    - history 9 件 (DES-A/B 用に各 3 件、DES-C 用に 0 件)
    - config バリアント: review_phase_a / review_phase_b / auto / manual
    - expected snapshots: 各シナリオ後の manifest / journal / summary
    - mock MCP レスポンス辞書
  - Purpose: Light E2E の決定性の源
  - _Leverage: `ruamel.yaml`, `pathlib`, task 1.1〜4.3 の成果物_
  - _Requirements: E2E-01, E2E-02, E2E-03_
  - _Prompt: Role: テストハーネスと決定的モックに慣れた QA エンジニア | Task: stub_claude.py と fixtures 一式を用意、CR-1〜5 遵守、実 `claude -p` を呼ばない | Restrictions: fixtures は YAML or JSON のみ（コード生成は禁止、diff しやすさのため）、stub_claude の出力は完全に決定的（乱数禁止） | Success: `python tests/e2e/stub_claude.py --approved-by TEST_TOKEN --output-format stream-json > /tmp/events.jsonl` が決定的な NDJSON を吐く、fixtures が 20 ファイル以上存在_

- [ ] 5.2 E2E harness (setup / teardown / assert_helpers / claude_wrapper) と assertions を整備
  - File: `tests/e2e/harness/{__init__,setup,teardown,assert_helpers,claude_wrapper}.py`, `tests/e2e/assertions/e2e_0{1,2,3}_assert.py`
  - `setup.py` — temp `.insight/` を構築、fixtures から YAML を展開、PATH に stub_claude を注入、ENV で INSIGHT_ROOT を差し替え
  - `teardown.py` — temp dir 削除、PATH 復元
  - `assert_helpers.py` — YAML load + deep diff + stderr 出力ヘルパー
  - `claude_wrapper.py` — Claude Code 内から呼べる薄いラッパー（shell からは直接 runner を呼ぶので optional）
  - `e2e_0N_assert.py` — test-design の期待値表を 1:1 で assert 文に変換、失敗時に具体的 diff を stderr
  - Purpose: 再現性のある自己検証基盤
  - _Leverage: task 5.1, pytest assertion helper ではなく標準 `assert` で十分_
  - _Requirements: E2E-01〜03 の期待値全項目_
  - _Prompt: Role: テストハーネス設計者 | Task: harness と assertion script を実装。assertion は 1 ファイル 30-100 行、diff 出力は unified format。CR-1〜5 遵守 | Restrictions: pytest に依存しない（runner script が直接呼ぶ）、tempfile.mkdtemp で INSIGHT_ROOT を作成、teardown は必ず shutil.rmtree（途中失敗時も） | Success: 各 `python tests/e2e/assertions/e2e_0N_assert.py` が fixture 期待状態に対し exit 0、不一致なら exit 1 + diff stderr_

- [ ] 5.3 E2E runners (bash スクリプト 3 本) を整備
  - File: `tests/e2e/runners/e2e_0{1,2,3}.sh`
  - 各 runner は `setup.py → /premortem 実行 → token 取得 → /batch-analysis 実行 → assertion → teardown.py` を単一 bash で完結
  - E2E-02 は env `STUB_KILL_AFTER_DESIGNS=1` で 1 回目 session を途中終了、2 回目で resume
  - E2E-03 は config 差し替えで Phase A → Phase B の 2 回起動
  - `set -euo pipefail` で厳格化、失敗時に exit code 非 0
  - Purpose: Claude Code が単一 shell コマンドで自己検証できる入口
  - _Leverage: task 5.1, 5.2, 4.1, 4.2_
  - _Requirements: E2E-01, E2E-02, E2E-03_
  - _Prompt: Role: bash スクリプタ | Task: 3 つの runner bash スクリプトを書き、各々 10-30 行で完結させる。CR-1〜5 遵守、macOS / Linux 両対応 | Restrictions: bash のみ（zsh / fish 非依存）、ブレース展開以外の bash4+ 機能に依存しない、teardown は trap で失敗時も呼ぶ | Success: `bash tests/e2e/runners/e2e_01.sh` / `e2e_02.sh` / `e2e_03.sh` すべて exit 0、実 claude を 1 回も呼ばずに完走_

---

## Group 6: Integration tests

- [ ] 6.1 Integration tests - premortem 系 (CLI / modes / io_contract / performance)
  - File: `tests/integration/test_premortem_cli.py`, `test_premortem_io_contract.py`, `test_premortem_modes.py`, `test_premortem_performance.py`, `tests/integration/conftest.py`
  - Integ-01, 02, 03, 04, 17, 24, 27, 29 を実装
  - conftest.py に mock MCP fixture / temp INSIGHT_ROOT fixture / stub_claude PATH 注入 fixture を置く
  - Integ-24 は pytest-benchmark 不要で `time.perf_counter()` で計測
  - Integ-29 は macOS では `fs_usage` / Linux では `strace` or `ltrace` をラップした helper を使用（fallback は `mock.patch("sqlite3.connect")` でランタイム監視）
  - Purpose: premortem の外部 I/F とパフォーマンス・I/O 契約を検証
  - _Leverage: task 4.1, 5.1, 5.2, pytest, unittest.mock, subprocess_
  - _Requirements: AC-1.1〜1.5, 2.2, 7.1, NFR Performance, Error-Handling-9, AC-4.5, AC-1.5_
  - _Prompt: Role: pytest fixtures と subprocess 統合に精通した QA エンジニア | Task: test-design.md の Integ-01/02/03/04/17/24/27/29 を 1:1 で実装。CR-1〜5 遵守 | Restrictions: 実 Claude Code を呼ばない（stub_claude を使う）、time.sleep 禁止（flaky 防止）、MCP モックは test-design の fixtures を使う | Success: 8 テストが pass、計測時間 < 5 min / ファイル_

- [ ] 6.2 Integration tests - launcher 系 (batch_launcher / session_id / manifest_atomic)
  - File: `tests/integration/test_batch_launcher.py`, `test_session_id_extraction.py`, `test_manifest_atomic.py`
  - Integ-05, 06, 07, 08, 09, 10, 11, 12, 13, 18, 19, 20, 21, 22, 28 を実装
  - subprocess で `launcher.sh` を呼び、stdout / stderr / exit code を検証
  - Integ-22 (events.jsonl 末尾破損) は fixture に壊れた NDJSON を置いて 1 行前採用を検証
  - Purpose: launcher の Phase A/B / token 検証 / mode 分岐 / session_id 抽出・破損復旧 を検証
  - _Leverage: task 4.2, 4.3, 5.1, 5.2, pytest_
  - _Requirements: AC-3.2, 3.3, 4.2, 5.1, 5.2, 5.3, 5.3b, 5.4, 5.5, 7.2, 7.3, 7.4, 7.5, NFR Reliability_
  - _Prompt: Role: bash スクリプトと pytest の統合に慣れたエンジニア | Task: test-design.md の Integ-05〜13, 18〜22, 28 を実装（計 15 テスト）。CR-1〜5 遵守 | Restrictions: 実 Claude Code を呼ばない（stub_claude）、flaky 対策として乱数シード固定、bash 環境変数のクリーンアップを teardown で行う | Success: 15 テストが pass、実行時間 < 5 min_

- [ ] 6.3 Integration tests - recovery + mode × risk matrix
  - File: `tests/integration/test_crash_recovery.py`, `test_mode_risk_matrix.py`
  - Integ-14, 15, 16, 23 を実装
  - Integ-23 は `pytest.mark.parametrize` で mode 3 × risk 5 = 15 組合せを展開（SKIP は mode 共通で 1 ケース × 3 mode = 3、HARD_BLOCK も 3、LOW/MEDIUM/HIGH は 9、計 15）
  - Purpose: 中断復旧と mode×risk 全組合せを table-driven で網羅
  - _Leverage: task 2.4, 4.2, 5.1, 5.2_
  - _Requirements: AC-2.1, 2.2, 3.4, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4_
  - _Prompt: Role: parametrize と状態シナリオに強い pytest エンジニア | Task: Integ-14/15/16 + Integ-23 の 15 組合せを実装。各組合せで expected 配分 (approved / skipped) と exit code を assert。CR-1〜5 遵守 | Restrictions: `@pytest.mark.parametrize` で展開、pytest.ids を明示的に設定して失敗時の追跡性を確保 | Success: 計 19 テスト（Integ-14: 2, 15: 2, 16: 2, 23: 15）が pass_

- [ ] 6.4 Integration tests - security + methodology_tag retry
  - File: `tests/integration/test_token_security.py`, `test_methodology_tag_retry.py`
  - Integ-25, 26 を実装
  - Integ-25 は token YAML をロード → 全 field を再帰スキャン → API key / env var パターンを regex で検出（0 件期待）
  - Integ-26 は batch-prompt の仕様を擬似実行する scenario: vocab 外 → retry → retry 失敗 → descriptive fallback + question event
  - Purpose: NFR Security と Error-Handling-8 を実地確認
  - _Leverage: task 2.2, 2.3, 4.3, 5.1_
  - _Requirements: NFR Security, AC-4.4, Error-Handling-8_
  - _Prompt: Role: security test と fallback flow 検証に慣れた QA | Task: Integ-25 (4 ケース) + Integ-26 (3 ケース) を実装。CR-1〜5 遵守、env var リークは `os.environ` に API key 形式を注入して検出できるか確認 | Restrictions: 実 API key を fixture に置かない（regex だけで検査）、リトライは stub_claude の状態変数で疑似表現 | Success: 計 7 テストが pass_

---

## Group 7: Documentation + follow-up

- [ ] 7.1 ドキュメント更新 (CLAUDE.md + README + structure.md)
  - File: `CLAUDE.md` (既存、追記), `README.md` (既存、追記可), `.spec-workflow/steering/structure.md` (既存、追記可)
  - CLAUDE.md に `/premortem` skill の項を追加（trigger / 引数 / chain フロー）、`/batch-analysis` 項に `--approved-by` と Phase A/B を追記
  - README に overnight 運用セクションを追加（/premortem → /batch-analysis → morning review のフロー、図示）
  - structure.md に `skills/_shared/` と `skills/premortem/lib/` の位置付けを追記（MCP 側依存方向の表は変えず、skill-bundle セクションを新設）
  - Purpose: 新機能を公式ドキュメント化
  - _Leverage: 既存ドキュメント_
  - _Requirements: design.md Project Structure 注記_
  - _Prompt: Role: テクニカルライター兼開発者 | Task: CLAUDE.md / README / structure.md に 3 方向の追記。CR-1〜5 遵守（既存記述を改変しない、add-only） | Restrictions: 既存の目次順序を保持、既存機能の記述を書き換えない、markdown は markdown-lint が通るよう厳格 | Success: 3 ドキュメントの diff が純粋な追加のみ（削除 0）、markdown-lint で warnings 0_

- [ ] 7.2 package_allowlist.yaml への分離 (改善 I-3)
  - File: `.insight/rules/package_allowlist.yaml` (新規, Git 管理対象), `skills/batch-analysis/SKILL.md` (参照リンクに差し替え), `skills/premortem/lib/risk_evaluator.py` (読み込み先変更), `tests/batch_harness/test_risk_evaluator.py` (allowlist_check_failed テストを yaml 失敗シナリオで検証)
  - `package_allowlist.yaml`:
    ```yaml
    allowed_packages:
      pandas: pandas
      matplotlib: matplotlib
      numpy: numpy
      scipy: scipy
      sklearn: scikit-learn
      statsmodels: statsmodels
      seaborn: seaborn
      plotly: plotly
    ```
  - risk_evaluator で primary source を YAML に切替、SKILL.md parse は fallback として保持
  - Purpose: design.md で Tasks 化すると宣言した改善 I-3 を実現
  - _Leverage: task 3.2, `ruamel.yaml`_
  - _Requirements: design.md Code Reuse I-3, Error-Handling-10_
  - _Prompt: Role: YAML 分離 + 後方互換に慣れた開発者 | Task: YAML ファイル新設 + risk_evaluator を YAML 読み込み優先に変更 + SKILL.md の table を YAML への参照リンクで置換（table 自体は残す）。CR-1〜5 遵守 | Restrictions: SKILL.md の既存 table を削除しない（fallback として保持）、package_allowlist.yaml のフォーマットは alias -> pip/uv package name の辞書 | Success: Unit-02 `test_allowlist_read_failure_high_with_flag` が YAML 読み込み失敗シナリオで HIGH + flag=allowlist_check_failed を返す_

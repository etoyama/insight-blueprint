# batch-harness-engineering - テスト設計書

**Spec ID**: `batch-harness-engineering`
**種別**: 新規機能（既存 `/batch-analysis` v1.0 に add-only で拡張）

## 概要

本ドキュメントは `requirements.md` の全 Acceptance Criteria に対して、どのテストレベル（Unit / Integ / E2E）でカバーするかを定義する。`design.md` の AC ↔ Component Coverage Matrix と 1:1 で対応する。

## テストレベル定義

| テストレベル | 略称 | 説明 | ツール |
|-------------|------|------|--------|
| 単体テスト | Unit | 個々の関数 / クラスを純粋関数 or I/O mock で検証。外部依存（MCP / subprocess / YAML）は fixtures + mock | pytest, unittest.mock, pyfakefs（必要に応じ） |
| 統合テスト | Integ | skill を subprocess で起動、実 YAML ファイル + mock MCP で検証。Claude Code 呼び出しは stub した `claude` wrapper で代替 | pytest, subprocess, 実ファイル fixtures |
| E2Eテスト | E2E | overnight 想定シナリオを手動 + スクリプトで再現。実 Claude Code を使った ≤ 3 分の短尺 design で 1 回流す | 手動 + bash scenario runner |

## 要件カバレッジマトリクス

### 機能要件 1: `/premortem` skill 新設

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 1.1 | `/premortem --queued` でキュー取得 + risk 判定 | -- | Integ-01 | E2E-01 | `next_action.type=batch_execute` の design のみ列挙され全件に RiskDecision |
| 1.2 | CLI 1 画面表示 + HIGH 時選択肢 | -- | Integ-01 | E2E-01 | stdout に `design_id/intent/rows/strategy/risk/理由` が 1 行、HIGH あれば `[s]/[e]/[a]/[c]` 表示 |
| 1.3 | `--yes` 非対話 + mode 準拠 | Unit-09 (token issue) | Integ-02 | -- | 対話プロンプト 0 回、token の `approved_by`/`automation_mode` が引数通り |
| 1.4 | "Launch with: /batch-analysis --approved-by `<TOKEN_ID>`" | -- | Integ-01 | E2E-01 | stdout 最終行にコマンドが表示 |
| 1.5 | 書き込み禁止契約（observable I/O） | -- | Integ-03 | -- | `/premortem` 実行中に `.insight/designs/**` `.insight/runs/**` `.insight/catalog/**` への書き込みが 0 回 |

### 機能要件 2: Risk 判定ロジック

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 2.1 | terminal status → SKIP | Unit-01 | -- | -- | status ∈ {supported, rejected, inconclusive} の design は判定対象外 |
| 2.2 | HARD_BLOCK 3 条件 | Unit-02 | Integ-04 | -- | source 未登録 / package 外 / BQ location 失敗で HARD_BLOCK、`[c]` 選択肢なし |
| 2.3 | extrapolated > time_high_min → HIGH | Unit-03 | -- | -- | history n>=3 で外挿式結果 > 閾値で HIGH |
| 2.3b | success_rate &lt; 0.6 → HIGH | Unit-04 | -- | -- | history n>=3 で成功率 0.5 のとき HIGH |
| 2.3c | extrapolated > time_medium_min → MEDIUM | Unit-05 | -- | -- | history n>=3 で 45 &lt; x &lt;= 120 min のとき MEDIUM |
| 2.4 | history 不足 AND rows > 10M → HIGH + flag | Unit-06 | -- | -- | n=0 or 2 AND estimated_rows=20000000 で HIGH + flag=history_insufficient |
| 2.5 | history 不足 AND rows &lt;= 10M → MEDIUM + flag | Unit-07 | -- | -- | n=0 AND rows=5000000 で MEDIUM + flag=history_insufficient |
| 2.6 | config defaults 適用 | Unit-08 | -- | -- | `.insight/config.yaml` に premortem なしで handoff 記載の default が適用 |

### 機能要件 3: 承認トークンのライフサイクル

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 3.1 | トークン YAML が正しく発行される | Unit-09 | Integ-02 | -- | ファイル存在、approved_by 値、approved_designs[] と skipped_designs[] の分配 |
| 3.2 | TTL 検証（期限切れで起動拒否） | Unit-10 | Integ-05 | -- | expires_at &lt; now なら verify が `ok=false, reason=expired` |
| 3.3 | design_hash mismatch skip | Unit-11 | Integ-06 | -- | 承認後 design 書換で当該 design の manifest が `status=skipped / skip_reason=hash_mismatch` |
| 3.4 | auto mode で HIGH も approved_designs | Unit-13 | Integ-07 | -- | auto mode の token に HIGH が `risk_at_approval=HIGH` で含まれる、skipped には入らない |
| 3.5 | `.insight/premortem/` を atomic 作成 | Unit-14 | -- | -- | ディレクトリ未作成状態で issue() → ディレクトリ作成 + ファイル書き込み |

### 機能要件 4: Run / Design Manifest Schema

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 4.1 | run.yaml 5 フィールド作成 | Unit-15 | -- | -- | init_run 後に run_id/session_id/started_at/automation_mode/premortem_token が存在 |
| 4.2 | per-design manifest atomic | Unit-16 | Integ-08 | -- | tempfile + replace で書き、部分書込み禁止、全フィールド揃う |
| 4.3 | verdict が journal と一致 | Unit-17 | Integ-07 | E2E-01 | manifest.verdict.direction == journal の direction |
| 4.4 | methodology_tags vocab 内のみ | Unit-18 | -- | -- | vocab 外 tag で `MethodologyTagError` raise、1 回リトライ後 default fallback |
| 4.5 | history 検索で SQLite 接続 0 回 | Unit-19 | -- | -- | 実行中に `sqlite3.connect` が呼ばれない（mock で監視） |

### 機能要件 5: 公式 Claude Code Harness との結線

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 5.1 | stream-json + include-hook-events 起動 | -- | Integ-09 | E2E-01 | launcher bash の `claude -p` 呼び出しに両オプションが含まれる |
| 5.2 | session_id 抽出 → run.yaml 反映 | -- | Integ-10 | E2E-01 | events.jsonl の最初の `system/init` 行から抽出、run.yaml.session_id に書かれる |
| 5.3 | Phase B 未指定で exit 1 | -- | Integ-11 | -- | `approved_by_required=true` + `--approved-by` 無しで exit code 1 + stderr に required メッセージ |
| 5.3b | Phase A 未指定で warning + legacy 記録 | -- | Integ-12 | E2E-03 | `approved_by_required=false` で起動可、stderr WARNING、run.yaml.automation_mode=legacy / premortem_token=null |
| 5.4 | events.jsonl に NDJSON 書き出し | -- | Integ-09 | E2E-01 | ファイル拡張子 `.jsonl`、各行が parse 可能 |
| 5.5 | --max-budget / --max-turns 到達で session 終了 | -- | Integ-13 | -- | 予算超過時に session 終了、manifest.yaml.status=timeout / error_category=budget_exceeded |

### 機能要件 6: Crash Recovery

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 6.1 | 中断 run の検出 | Unit-20 | Integ-14 | E2E-02 | run.yaml.status != completed の run を検出し stderr に `detected incomplete run` |
| 6.2 | token TTL 内で --resume | -- | Integ-15 | E2E-02 | token 有効時に `claude -p ... --resume {session_id}` が発行、events.jsonl に `>>` append |
| 6.3 | token 期限切れ → incomplete 確定 | Unit-22 | Integ-16 | -- | 未完了 design の manifest を `status=incomplete / skip_reason=token_expired_or_crashed` で書く |
| 6.4 | run 完走時に ended_at + status=completed | Unit-23 | Integ-09 | E2E-01 | run.yaml に 2 フィールド追記、以降の起動で中断検出対象外 |
| 6.5 | 複数中断時は最新 1 件のみ resume | Unit-21 | -- | -- | 2 件中断 fixtures で最新 1 件のみ resume、他は incomplete 固定 |

### 機能要件 7: Automation Mode 3 段階

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 7.1 | manual で対話必須（--yes 禁止） | -- | Integ-17 | -- | manual mode で `/premortem --yes` → exit 1 + error "manual mode requires interactive" |
| 7.2 | review + HIGH で停止 | -- | Integ-18 | -- | `/premortem --yes --mode review` が exit 2、`/batch-analysis` が stdout に HIGH list + 選択肢 |
| 7.3 | review + no HIGH で自動承認 | -- | Integ-19 | E2E-01 | exit 0、token 発行、batch 本体が続行 |
| 7.4 | auto + HIGH で warning + 続行 | -- | Integ-20 | -- | exit 0、batch 本体が実行、summary.md に `WARNING: HIGH risk executed` |
| 7.5 | config default = review | Unit-08 | Integ-21 | -- | `batch.automation` キー無しで review が既定 |

---

## 単体テストシナリオ

### Unit-01: risk_evaluator - terminal status の SKIP 判定

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-01 |
| **テストファイル** | `tests/batch_harness/test_risk_evaluator.py` |
| **テストクラス** | `TestRiskEvaluatorTerminalStatus` |
| **目的** | status が supported/rejected/inconclusive の design は判定対象外 (SKIP) となる |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_supported_returns_skip` | status=supported → RiskLevel.SKIP | 2.1 |
| `test_rejected_returns_skip` | status=rejected → RiskLevel.SKIP | 2.1 |
| `test_inconclusive_returns_skip` | status=inconclusive → RiskLevel.SKIP | 2.1 |
| `test_analyzing_not_skipped` | status=analyzing は通常判定へ | 2.1 |
| `test_in_review_not_skipped` | status=in_review は通常判定へ | 2.1 |

---

### Unit-02: risk_evaluator - HARD_BLOCK 3 条件

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-02 |
| **テストファイル** | `tests/batch_harness/test_risk_evaluator.py` |
| **テストクラス** | `TestRiskEvaluatorHardBlock` |
| **目的** | source 未登録 / package allowlist 外 / BQ location 検証失敗のいずれかで HARD_BLOCK |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_source_not_registered_hard_block` | `source_checks.registered=False` で HARD_BLOCK | 2.2 |
| `test_package_not_in_allowlist_hard_block` | 要求 package が allowlist 外 → HARD_BLOCK | 2.2 |
| `test_bq_location_mismatch_hard_block` | BQ API で location 取得成功 AND 検証結果 NG（cross-location JOIN 等） → HARD_BLOCK | 2.2 |
| `test_bq_location_api_failure_high_with_flag` | BQ API 呼び出し自体が network/auth error で失敗 → HIGH + flag=location_check_failed（HARD_BLOCK では **ない**、design.md Error #9 準拠） | 2.2, Error-Handling-9 |
| `test_allowlist_read_failure_high_with_flag` | SKILL.md / allowlist.yaml の parse 失敗 → HIGH + flag=allowlist_check_failed（design.md Error #10 準拠） | 2.2, Error-Handling-10 |
| `test_multiple_hard_block_reasons_all_listed` | 複数理由が reasons list に全て含まれる | 2.2 |

---

### Unit-03: risk_evaluator - history-based HIGH (extrapolated_time)

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-03 |
| **テストファイル** | `tests/batch_harness/test_risk_evaluator.py` |
| **テストクラス** | `TestRiskEvaluatorHistoryHighTime` |
| **目的** | history n>=3 のとき、外挿式 (median × ratio × 1.3) > time_high_min で HIGH |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_extrapolated_time_exceeds_high_threshold` | n=3, median=60, rows=2x → 60×2×1.3=156 > 120 → HIGH | 2.3 |
| `test_boundary_extrapolated_equals_high` | 外挿値 = 120 ちょうどは MEDIUM（> 厳密比較、境界値） | 2.3, 2.3c |
| `test_extrapolated_below_high_is_medium_or_low` | 外挿値 &lt; time_high_min なら HIGH でない | 2.3 |

---

### Unit-04: risk_evaluator - history-based HIGH (success_rate)

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-04 |
| **テストファイル** | `tests/batch_harness/test_risk_evaluator.py` |
| **テストクラス** | `TestRiskEvaluatorHistorySuccessRate` |
| **目的** | history n>=3 のとき success_rate &lt; threshold で HIGH |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_success_rate_below_threshold_high` | 3 runs 中 1 success (rate=0.33) → HIGH | 2.3b |
| `test_success_rate_at_boundary_not_high` | rate=0.6 ちょうどは HIGH でない（`<` 厳密比較） | 2.3b |
| `test_success_rate_high_and_time_ok` | success_rate 条件のみで HIGH（時間は medium 相当でも） | 2.3b |
| `test_time_and_success_rate_both_trigger_high` | 両条件成立でも HIGH は 1 回のみ判定、reasons に 2 件 | 2.3, 2.3b |

---

### Unit-05: risk_evaluator - history-based MEDIUM

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-05 |
| **テストファイル** | `tests/batch_harness/test_risk_evaluator.py` |
| **テストクラス** | `TestRiskEvaluatorHistoryMedium` |
| **目的** | history n>=3 で HIGH 条件満たさず、extrapolated > time_medium_min で MEDIUM |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_extrapolated_between_medium_and_high_medium` | 外挿値 = 60 (45 &lt; x &lt;= 120) + success_rate ok → MEDIUM | 2.3c |
| `test_extrapolated_below_medium_low` | 外挿値 = 20 + success_rate ok → LOW | 2.3c |

---

### Unit-06: risk_evaluator - static fallback HIGH

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-06 |
| **テストファイル** | `tests/batch_harness/test_risk_evaluator.py` |
| **テストクラス** | `TestRiskEvaluatorStaticHigh` |
| **目的** | history n &lt; 3 で estimated_rows > static_rows_high → HIGH + flag=history_insufficient |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_n_zero_rows_above_threshold_high_with_flag` | n=0, rows=20000000 → HIGH + flag | 2.4 |
| `test_n_two_rows_above_threshold_high_with_flag` | n=2 (不足), rows=15000000 → HIGH + flag | 2.4 |
| `test_flag_history_insufficient_always_present` | static fallback 経由時は flag 必須 | 2.4, 2.5 |

---

### Unit-07: risk_evaluator - static fallback MEDIUM

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-07 |
| **テストファイル** | `tests/batch_harness/test_risk_evaluator.py` |
| **テストクラス** | `TestRiskEvaluatorStaticMedium` |
| **目的** | history n &lt; 3 で rows &lt;= static_rows_high → MEDIUM + flag |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_n_zero_rows_below_threshold_medium_with_flag` | n=0, rows=5000000 → MEDIUM + flag | 2.5 |
| `test_boundary_rows_equals_threshold_medium` | rows=10000000 ちょうどは MEDIUM（>= 厳密比較） | 2.4, 2.5 |

---

### Unit-08: PremortemConfig - config defaults

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-08 |
| **テストファイル** | `tests/batch_harness/test_premortem_config.py` |
| **テストクラス** | `TestPremortemConfigDefaults` |
| **目的** | `.insight/config.yaml` に premortem セクション無しで handoff default 値が使われる |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_defaults_when_config_missing` | 8 項目 (time_high_min=120 等) が default | 2.6, 7.5 |
| `test_partial_override_merges_defaults` | time_high_min のみ上書き → 他は default | 2.6 |
| `test_batch_automation_default_review` | batch.automation 未設定 → review | 7.5 |
| `test_approved_by_required_default_false` | Phase A default 値検証 | 5.3b |

---

### Unit-09: token_manager - issue creates correct YAML

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-09 |
| **テストファイル** | `tests/batch_harness/test_token_manager.py` |
| **テストクラス** | `TestTokenManagerIssue` |
| **目的** | issue() が規定の schema で atomic にトークンを書き出す |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_issue_writes_file_with_required_fields` | token_id/created_at/expires_at/approved_by/automation_mode/risk_summary/approved_designs/skipped_designs | 3.1 |
| `test_issue_approved_by_human` | 対話承認経路 → approved_by=human | 3.1 |
| `test_issue_approved_by_auto` | `--yes` 経路 → approved_by=auto | 3.1, 1.3 |
| `test_issue_expires_at_offset_by_ttl` | expires_at = created_at + ttl_hours | 3.1, 3.2 |
| `test_issue_atomic_no_partial_files` | 書き込み中断で 0 bytes ファイル残らない | 3.1, 3.5 |

---

### Unit-10: token_manager - TTL 検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-10 |
| **テストファイル** | `tests/batch_harness/test_token_manager.py` |
| **テストクラス** | `TestTokenManagerVerify` |
| **目的** | verify() が TTL 内 / 外で正しく判定 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_verify_within_ttl_ok` | expires_at 1h 後、now 現在 → ok=True | 3.2 |
| `test_verify_expired_returns_error` | expires_at 1h 前 → ok=False, reason=expired | 3.2 |
| `test_verify_exact_expiry_boundary` | expires_at == now はどちら? → expired 扱い（`<` 厳密） | 3.2 |
| `test_verify_nonexistent_token_not_found` | 存在しない token_id → ok=False, reason=not_found | 3.2 |

---

### Unit-11: token_manager - design_hash mismatch

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-11 |
| **テストファイル** | `tests/batch_harness/test_token_manager.py` |
| **テストクラス** | `TestTokenManagerHashVerify` |
| **目的** | verify_design_hash() が承認後の design 書換を検知する |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_matching_hash_returns_true` | 承認時 hash == 現在 hash → True | 3.3 |
| `test_mismatched_hash_returns_false` | hash 変更 → False | 3.3 |
| `test_design_not_in_token_returns_false` | token に無い design_id → False | 3.3 |

---

### Unit-12: token_manager - design_hash canonicalization

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-12 |
| **テストファイル** | `tests/batch_harness/test_token_manager.py` |
| **テストクラス** | `TestComputeDesignHash` |
| **目的** | compute_design_hash() が key 順・空白・不要 field に対し冪等 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_hash_stable_across_key_order` | 同内容で key 順違いの 2 つ → 同一 hash | 3.4 |
| `test_hash_excludes_updated_at` | updated_at 違いで同一 hash | 3.4 |
| `test_hash_excludes_created_at` | created_at 違いで同一 hash | 3.4 |
| `test_hash_excludes_id_field` | design.id 違いで同一 hash（ハッシュの入力ではなくキー側に使う field） | 3.4 |
| `test_hash_excludes_status_and_next_action` | status / next_action / review_history 違いで同一 hash | 3.4 |
| `test_hash_changes_on_methodology_change` | methodology 変更で別 hash | 3.4 |
| `test_hash_changes_on_hypothesis_change` | hypothesis 変更で別 hash | 3.4 |
| `test_hash_source_ids_order_insensitive` | source_ids の順序違い → 同一 hash (sorted) | 3.4 |
| `test_hash_format_prefix_sha256` | 返値が `sha256:` プレフィックス + 64 hex | 3.4 |
| `test_hash_whitespace_insensitive` | metrics dict 内の余分な空白や改行入力違い → 同一 hash（canonicalization step 5 の separators=",", ":" 確認） | 3.4 |

---

### Unit-13: token_manager - auto mode approved_designs 分配

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-13 |
| **テストファイル** | `tests/batch_harness/test_token_manager.py` |
| **テストクラス** | `TestTokenManagerAutoMode` |
| **目的** | auto mode で HIGH も approved_designs、skipped_designs に入らない |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_auto_mode_high_in_approved` | automation_mode=auto, HIGH → approved[], risk_at_approval=HIGH | 3.4 |
| `test_auto_mode_hard_block_still_skipped` | HARD_BLOCK は auto mode でも skipped | 3.4, 2.2 |
| `test_review_mode_high_in_skipped` | review mode で HIGH → skipped[] | 3.1 |

---

### Unit-14: token_manager - atomic directory create

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-14 |
| **テストファイル** | `tests/batch_harness/test_token_manager.py` |
| **テストクラス** | `TestTokenManagerAtomicDir` |
| **目的** | `.insight/premortem/` が無い状態で issue() が mkdir + write を成功させる |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_directory_missing_created_before_write` | dir 不存在 + issue → dir 作成 + ファイル書込 | 3.5 |
| `test_directory_exists_reused` | 既存 dir で issue → そのまま書込 | 3.5 |

---

### Unit-15: manifest_writer - init_run

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-15 |
| **テストファイル** | `tests/batch_harness/test_manifest_writer.py` |
| **テストクラス** | `TestManifestWriterInitRun` |
| **目的** | init_run が run.yaml に 5 必須フィールドを書く |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_init_run_has_required_fields` | run_id/session_id(null)/started_at/automation_mode/premortem_token | 4.1 |
| `test_init_run_status_is_running` | 初期 status=running | 4.1, 6.4 |
| `test_update_run_session_id_after_init` | update_run_session_id 後に session_id が null → 値 | 5.2 |

---

### Unit-16: manifest_writer - per-design atomic

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-16 |
| **テストファイル** | `tests/batch_harness/test_manifest_writer.py` |
| **テストクラス** | `TestManifestWriterAtomic` |
| **目的** | write_design_manifest が tempfile + replace で全フィールド atomic |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_write_design_all_required_fields` | design_snapshot/methodology_tags/input_profile/execution/verdict が揃う | 4.2 |
| `test_write_uses_tempfile_replace_pattern` | os.replace が呼ばれ、tempfile は同一ディレクトリに作成 | 4.2 |
| `test_crash_during_write_no_partial_file` | テスト用に os.replace を失敗させる → 既存ファイルは破損しない | 4.2 |
| `test_status_skipped_also_written` | status=skipped でも manifest が存在（欠落しない） | 4.2, 2.2, 3.3 |
| `test_status_error_timeout_also_written` | error/timeout も同様 | 4.2, 5.5 |

---

### Unit-17: manifest_writer - verdict 非正規化

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-17 |
| **テストファイル** | `tests/batch_harness/test_manifest_writer.py` |
| **テストクラス** | `TestManifestWriterVerdict` |
| **目的** | verdict が journal の direction/confidence/events_recorded と一致 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_verdict_direction_matches_journal` | journal.direction=supports → manifest.verdict.direction=supports | 4.3 |
| `test_verdict_confidence_ambiguous_written` | journal.confidence=ambiguous → manifest に反映 | 4.3 |
| `test_events_recorded_count_matches` | journal の events 件数 = manifest.verdict.events_recorded | 4.3 |
| `test_verdict_null_when_status_not_success` | status=error → verdict=null | 4.3 |

---

### Unit-18: manifest_writer - methodology_tags vocab validation

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-18 |
| **テストファイル** | `tests/batch_harness/test_manifest_writer.py` |
| **テストクラス** | `TestManifestWriterVocab` |
| **目的** | vocab 外タグで MethodologyTagError を raise、書き込み中止 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_valid_tags_pass_validation` | vocab 内の tag 1-3 個で成功 | 4.4 |
| `test_invalid_tag_raises_error` | 未定義 tag → MethodologyTagError | 4.4 |
| `test_mixed_valid_invalid_raises` | 1 個でも外 → エラー（空配列書き出しなし） | 4.4 |
| `test_empty_tags_raises` | 空配列 → エラー（最低 1 個必要） | 4.4 |
| `test_four_tags_raises` | 4 個以上 → エラー（1-3 制約） | 4.4 |
| `test_load_vocab_returns_ten_predefined` | vocab.yaml に 10 種 tag が存在 | 4.4 |

---

### Unit-19: history_query - SQLite 接続 0 回

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-19 |
| **テストファイル** | `tests/batch_harness/test_history_query.py` |
| **テストクラス** | `TestHistoryQueryNoSqlite` |
| **目的** | glob + YAML read のみで完結、sqlite3.connect が呼ばれない |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_no_sqlite_connect_called` | mock で sqlite3.connect 監視 → 0 回 | 4.5 |
| `test_empty_history_returns_n_zero` | `.insight/runs/*/` 空 → n=0 | 2.4, 2.5 |
| `test_source_ids_exact_match_filter` | source_ids=[a,b] は [a,b] のみマッチ、[a] は不一致 | 2.4 |
| `test_median_calculation_three_runs` | 3 runs (10, 20, 30 min) → median=20 | 2.5 |
| `test_success_rate_from_status` | 3 runs (2 success, 1 error) → rate=0.67 | 2.3b |
| `test_corrupted_yaml_skipped` | 壊れた manifest.yaml は無視、続行 | -- |

---

### Unit-20: crash_recovery - detect_incomplete

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-20 |
| **テストファイル** | `tests/batch_harness/test_crash_recovery.py` |
| **テストクラス** | `TestCrashRecoveryDetect` |
| **目的** | run.yaml.status != completed の run を列挙 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_no_incomplete_returns_empty` | 全 run が completed → [] | 6.1 |
| `test_one_incomplete_detected` | status=running のまま → 検出 | 6.1 |
| `test_status_incomplete_detected` | status=incomplete も検出対象 | 6.1 |
| `test_missing_status_field_detected` | status 欄が無い → 検出対象（crash で書けなかった） | 6.1 |

---

### Unit-21: crash_recovery - 最新 run 選択

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-21 |
| **テストファイル** | `tests/batch_harness/test_crash_recovery.py` |
| **テストクラス** | `TestCrashRecoveryLatest` |
| **目的** | 複数中断時に最新 1 件のみ resume、他は incomplete 固定 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_multiple_incomplete_latest_selected` | 2 件中 started_at 新しいほうが resume 候補 | 6.5 |
| `test_older_incomplete_marked_as_final` | 古い方は status=incomplete 固定 | 6.5 |

---

### Unit-22: crash_recovery - finalize_incomplete

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-22 |
| **テストファイル** | `tests/batch_harness/test_crash_recovery.py` |
| **テストクラス** | `TestCrashRecoveryFinalize` |
| **目的** | 未完了 design の manifest を status=incomplete で確定 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_finalize_writes_manifest_incomplete` | design ディレクトリに manifest.yaml (status=incomplete) | 6.3 |
| `test_skip_reason_token_expired_or_crashed` | reason フィールドに文字列記録 | 6.3 |
| `test_run_yaml_status_updated_incomplete` | run.yaml.status → incomplete | 6.3 |

---

### Unit-23: manifest_writer - finalize_run

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-23 |
| **テストファイル** | `tests/batch_harness/test_manifest_writer.py` |
| **テストクラス** | `TestManifestWriterFinalize` |
| **目的** | run 完走時に ended_at + status=completed + cost_total |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_finalize_run_completed` | ended_at / status=completed / cost_total_usd が追記 | 6.4 |
| `test_finalize_run_incomplete` | status=incomplete 指定時も書ける | 6.4, 6.3 |
| `test_finalize_preserves_existing_fields` | started_at / session_id 等が保持 | 6.4 |

---

## 統合テストシナリオ

### Integ-01: /premortem --queued happy path

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-01 |
| **テストファイル** | `tests/integration/test_premortem_cli.py` |
| **テストクラス** | `TestPremortemQueuedHappy` |
| **目的** | キュー取得 → 判定 → stdout 1 画面 → token 発行までの end-to-end フロー |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_queued_lists_only_queued_designs` | `next_action.type=batch_execute` のみ対象 | 1.1 |
| `test_stdout_one_line_per_design` | design_id / intent / rows / strategy / risk / 理由 | 1.2 |
| `test_launch_message_last_line` | 最終行に `Launch with: /batch-analysis --approved-by` | 1.4 |

---

### Integ-02: /premortem --yes mode dispatch

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-02 |
| **テストファイル** | `tests/integration/test_premortem_cli.py` |
| **テストクラス** | `TestPremortemYesFlag` |
| **目的** | `--yes --mode <m>` で対話なしでトークンを発行する |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_yes_review_mode_exits_0_no_high` | HIGH 無しの fixtures で exit 0, token issued | 1.3, 7.3 |
| `test_yes_review_mode_exits_2_with_high` | HIGH 有り → exit 2, token 未発行 | 7.2 |
| `test_yes_auto_mode_includes_high` | auto mode で HIGH 含む approved 付き token | 1.3, 3.4, 7.4 |

---

### Integ-03: /premortem 書き込み禁止契約

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-03 |
| **テストファイル** | `tests/integration/test_premortem_io_contract.py` |
| **テストクラス** | `TestPremortemWriteContract` |
| **目的** | `/premortem` 実行中に禁止ディレクトリへの書き込みが 0 回 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_no_writes_to_designs_dir` | `.insight/designs/**` への write open が 0 回（Linux: inotify / macOS: fs_usage または mtime+hash 比較で代替、クロスプラットフォーム fixture helper を使う） | 1.5 |
| `test_no_writes_to_runs_dir` | `.insight/runs/**` への write が 0 回 | 1.5 |
| `test_no_writes_to_catalog_dir` | `.insight/catalog/**` への write が 0 回 | 1.5 |
| `test_writes_only_to_premortem_dir` | 書き込みは `.insight/premortem/*.yaml` に限定 | 1.5 |
| `test_mcp_tools_read_only_called` | 呼ばれる MCP tool は list / get / schema / search のみ | 1.5 |

---

### Integ-04: /batch-analysis HARD_BLOCK を続行不可として扱う

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-04 |
| **テストファイル** | `tests/integration/test_premortem_cli.py` |
| **テストクラス** | `TestPremortemHardBlock` |
| **目的** | HARD_BLOCK 対象 design は `[c]ontinue` で承認できず、skipped_designs に確定記録 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_hard_block_shows_no_continue` | stdout の選択肢に `[c]` が表示されない | 2.2 |
| `test_hard_block_in_skipped_with_reason` | token の skipped_designs[] に理由付きで入る | 2.2, 3.1 |

---

### Integ-05: token TTL 超過で /batch-analysis 起動拒否

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-05 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchTokenTTL` |
| **目的** | 期限切れトークンで `/batch-analysis --approved-by` 起動 → exit 1 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_expired_token_exits_1` | expires_at &lt; now → exit 1 + stderr "token expired" | 3.2 |
| `test_expired_token_message_includes_created_at` | stderr に作成時刻が含まれる | 3.2 |

---

### Integ-06: design_hash mismatch → skip

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-06 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchHashMismatch` |
| **目的** | 承認後 design を書き換えると manifest に skip が記録 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_hash_mismatch_writes_skipped_manifest` | manifest.status=skipped / skip_reason=hash_mismatch | 3.3 |
| `test_hash_match_proceeds_normally` | hash 一致なら通常実行 | 3.3 |

---

### Integ-07: auto mode で summary.md に warning

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-07 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchAutoModeHighWarning` |
| **目的** | auto mode で HIGH design 実行時に summary.md に WARNING 行 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_auto_high_executed_summary_warning` | summary.md に `WARNING: HIGH risk executed without human approval` | 7.4 |
| `test_auto_high_manifest_has_verdict` | 実行されるので manifest.verdict が populate | 3.4, 4.3 |

---

### Integ-08: per-design manifest の atomic 書き出し（マルチプロセス視点）

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-08 |
| **テストファイル** | `tests/integration/test_manifest_atomic.py` |
| **テストクラス** | `TestManifestAtomicWriteIntegration` |
| **目的** | 実 tempfile + os.replace + filelock 経由で部分書き込みが起きない |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_replace_atomic_across_processes` | 2 プロセスが同一 manifest に書いても最後の rename が勝つ（破損なし） | 4.2 |
| `test_partial_tempfile_cleanup` | 書き込み中の tempfile が残らない（on success）| 4.2 |

---

### Integ-09: launcher が stream-json オプションを含む

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-09 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchLauncherOptions` |
| **目的** | 更新された `/batch-analysis` SKILL.md の bash が必須オプションを全て含む |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_command_has_stream_json` | `--output-format stream-json` が含まれる | 5.1 |
| `test_command_has_include_hook_events` | `--include-hook-events` | 5.1 |
| `test_command_writes_to_events_jsonl` | 出力先が `events.jsonl` (末尾 `>`) | 5.4 |
| `test_command_has_max_budget_and_turns` | `--max-budget-usd` `--max-turns` 両方含まれる | 5.5 |
| `test_command_no_session_log_redirect` | `session.log` への書き込みが削除されている（後方互換廃止） | 5.1 |
| `test_run_yaml_status_completed_after_run` | 擬似 batch 完走で run.yaml.status=completed | 6.4 |

---

### Integ-10: session_id 抽出 → run.yaml 反映

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-10 |
| **テストファイル** | `tests/integration/test_session_id_extraction.py` |
| **テストクラス** | `TestSessionIdExtraction` |
| **目的** | events.jsonl の system/init 行から session_id を抽出し run.yaml に書く |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_extracts_first_system_init_session_id` | 正常 fixtures で session_id が run.yaml に反映 | 5.2 |
| `test_extracts_within_500ms` | 1000 行の events.jsonl で抽出時間 &lt; 500ms | NFR Performance |

---

### Integ-11: Phase B で --approved-by 未指定 → exit 1

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-11 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchPhaseBRequired` |
| **目的** | approved_by_required=true で未指定起動 → exit 1 + required メッセージ |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_phase_b_missing_flag_exits_1` | exit 1 | 5.3 |
| `test_phase_b_stderr_contains_required` | stderr に `--approved-by required; run /premortem first` | 5.3 |

---

### Integ-12: Phase A で未指定起動 → warning + legacy

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-12 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchPhaseALegacy` |
| **目的** | approved_by_required=false で未指定起動 → warning + run.yaml legacy 記録 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_phase_a_missing_flag_proceeds` | 実行継続（exit 1 にならない） | 5.3b |
| `test_phase_a_warning_on_stderr` | stderr WARNING テキスト | 5.3b |
| `test_run_yaml_automation_mode_legacy` | run.yaml.automation_mode=legacy, premortem_token=null | 5.3b |

---

### Integ-13: Budget / turns 上限到達時の manifest 記録

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-13 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchBudgetExhaustion` |
| **目的** | Claude Code 側で session が終わった時の manifest.status が timeout + error_category が正しい |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_budget_exceeded_manifest_status_timeout` | status=timeout / error_category=budget_exceeded | 5.5 |
| `test_turn_limit_manifest_status_timeout` | error_category=turn_limit | 5.5 |
| `test_remaining_designs_not_in_same_session` | 残り design は次回起動時 resume 対象（同一 session で進まない） | 5.5, 6.1 |

---

### Integ-14: crash_recovery 検出 - 実 fixtures

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-14 |
| **テストファイル** | `tests/integration/test_crash_recovery.py` |
| **テストクラス** | `TestCrashRecoveryDetectIntegration` |
| **目的** | 実 YAML fixtures で detect_incomplete が正しく中断 run を返す |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_incomplete_run_from_crashed_state` | status 欄欠損 + started_at あり → 検出 | 6.1 |
| `test_stderr_mentions_detected_run_id` | `/batch-analysis` 起動時に `detected incomplete run: {run_id}` | 6.1 |

---

### Integ-15: --resume with valid token

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-15 |
| **テストファイル** | `tests/integration/test_crash_recovery.py` |
| **テストクラス** | `TestCrashRecoveryResume` |
| **目的** | token TTL 内の中断 run で --resume 付き launcher が発行される |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_resume_command_uses_session_id` | claude wrapper に `--resume {session_id}` が渡る | 6.2 |
| `test_events_jsonl_appended_not_overwritten` | `>>` で追記（既存行保持） | 6.2 |

---

### Integ-16: token 失効時 incomplete 確定

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-16 |
| **テストファイル** | `tests/integration/test_crash_recovery.py` |
| **テストクラス** | `TestCrashRecoveryTokenExpired` |
| **目的** | 中断 run の token が期限切れなら未完了 design を incomplete で確定 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_expired_token_finalizes_designs` | 未完了 design の manifest.status=incomplete | 6.3 |
| `test_run_yaml_status_becomes_incomplete` | run.yaml も status=incomplete で固定 | 6.3 |

---

### Integ-17: manual mode で --yes 拒否

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-17 |
| **テストファイル** | `tests/integration/test_premortem_modes.py` |
| **テストクラス** | `TestPremortemManualMode` |
| **目的** | manual mode で `--yes` 指定 → エラー終了 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_manual_yes_exits_non_zero` | exit code != 0 | 7.1 |
| `test_manual_yes_stderr_message` | "manual mode requires interactive" | 7.1 |

---

### Integ-18: review mode + HIGH で batch 停止

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-18 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchReviewHighStop` |
| **目的** | review mode で HIGH 検出 → `/batch-analysis` が停止し選択肢提示 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_premortem_exit_2_stops_batch` | `/premortem --yes --mode review` exit 2 → batch が先へ進まない | 7.2 |
| `test_stdout_prompts_skip_edit_abort_continue` | stdout に選択肢 | 7.2 |

---

### Integ-19: review mode + no HIGH で自動承認

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-19 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchReviewNoHigh` |
| **目的** | HIGH 無しなら review で自動承認して batch 継続 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_review_no_high_token_issued_and_batch_runs` | token 発行 + batch 本体が起動 | 7.3 |

---

### Integ-20: auto mode 全 risk 承認

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-20 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchAutoModeAllApproved` |
| **目的** | auto mode では HARD_BLOCK 以外は全て approved、batch が実行 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_auto_all_non_hard_block_approved` | LOW/MEDIUM/HIGH 全て approved_designs[] | 3.4, 7.4 |
| `test_auto_hard_block_still_skipped` | HARD_BLOCK は auto でも skipped | 2.2 |

---

### Integ-21: default automation = review

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-21 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchDefaultMode` |
| **目的** | config に `batch.automation` が無いと review として動作 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_no_automation_key_uses_review` | config にキー無し → review mode と同等の挙動 | 7.5 |

---

### Integ-22: events.jsonl 最終行破損

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-22 |
| **テストファイル** | `tests/integration/test_session_id_extraction.py` |
| **テストクラス** | `TestEventsJsonlCorruption` |
| **目的** | 末尾 1 行が壊れた events.jsonl から 1 行前を採用し resume |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_corrupted_last_line_falls_back` | 末尾壊れ + 正常な 1 行前 → prior session_id が使われる | NFR Reliability |
| `test_warning_logged_on_fallback` | WARNING メッセージが stderr | NFR Reliability |
| `test_resume_proceeds_after_fallback` | その後 `--resume` で正常継続 | 6.2 |

---

### Integ-23: automation mode × risk level 全組合せ (table-driven)

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-23 |
| **テストファイル** | `tests/integration/test_mode_risk_matrix.py` |
| **テストクラス** | `TestModeRiskMatrix` |
| **目的** | design.md の AC-7 × risk の全組合せ挙動を 1 箇所で table-driven に網羅する（代表パスだけでなく全組合せ） |

**テストケース（pytest.parametrize で展開）:**

各セルで「token 発行可否 / approved_designs に含まれるか / skipped_designs に含まれるか / batch 継続可否 / summary.md WARNING 有無」を assert する。

| # | 関数名 | mode | risk | 期待: /premortem exit | approved_designs[] | skipped_designs[] | batch 挙動 | カバーするAC |
|---|--------|------|------|----------------------|--------------------|---------------------|-----------|-------------|
| 1 | `test_manual_low_interactive_approves` | manual | LOW | 対話必須 (`--yes` 禁止)、人が approve → 0 | ◯ | -- | 実行 | 7.1 |
| 2 | `test_manual_medium_interactive_approves` | manual | MEDIUM | 対話 → approve → 0 | ◯ | -- | 実行 | 7.1 |
| 3 | `test_manual_high_interactive_approves` | manual | HIGH | 対話 → approve → 0 | ◯ | -- | 実行 | 7.1 |
| 4 | `test_manual_hard_block_interactive_skip_only` | manual | HARD_BLOCK | 対話、`[c]` なし、skip のみ → 0 | -- | ◯ | 当該 design のみ skip、他は実行 | 2.2, 7.1 |
| 5 | `test_manual_skip_never_evaluated` | manual | SKIP (terminal status) | 判定対象外、出力に含まれない → 0 | -- | -- | 対象外 | 2.1 |
| 6 | `test_review_yes_low_approved` | review | LOW | `--yes` → 0 | ◯ | -- | 実行 | 7.3 |
| 7 | `test_review_yes_medium_approved` | review | MEDIUM | `--yes` → 0 | ◯ | -- | 実行 | 7.3 |
| 8 | `test_review_yes_high_exits_2` | review | HIGH | `--yes` → exit 2（token 未発行） | -- | -- | batch 停止、`[s]/[e]/[a]/[c]` 提示 | 7.2 |
| 9 | `test_review_yes_hard_block_skipped` | review | HARD_BLOCK | `--yes` → 0 | -- | ◯ | HARD_BLOCK のみ skip、他は実行 | 2.2 |
| 10 | `test_review_skip_never_evaluated` | review | SKIP | 判定対象外 → 0 | -- | -- | 対象外 | 2.1 |
| 11 | `test_auto_yes_low_approved` | auto | LOW | `--yes` → 0 | ◯ | -- | 実行 | 7.4, 3.4 |
| 12 | `test_auto_yes_medium_approved` | auto | MEDIUM | `--yes` → 0 | ◯ | -- | 実行 | 7.4, 3.4 |
| 13 | `test_auto_yes_high_approved_with_warning` | auto | HIGH | `--yes` → 0 | ◯ (risk_at_approval=HIGH) | -- | 実行、summary.md WARNING | 7.4, 3.4 |
| 14 | `test_auto_yes_hard_block_still_skipped` | auto | HARD_BLOCK | `--yes` → 0 | -- | ◯ | HARD_BLOCK のみ skip | 2.2 |
| 15 | `test_auto_skip_never_evaluated` | auto | SKIP | 判定対象外 → 0 | -- | -- | 対象外 | 2.1 |

---

### Integ-24: NFR Performance - /premortem 実行時間

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-24 |
| **テストファイル** | `tests/integration/test_premortem_performance.py` |
| **テストクラス** | `TestPremortemPerformance` |
| **目的** | requirements.md NFR Performance（10 designs × history 30 runs で 30 秒以内）を計測 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_premortem_queued_under_30s_with_10_designs_30_history` | 10 designs + 30 past manifests の fixtures で `/premortem --queued --yes --mode review` の wall-clock &lt; 30 秒 | NFR Performance |
| `test_manifest_atomic_write_under_100ms` | write_design_manifest 1 回あたり median &lt; 100ms | NFR Performance |
| `test_session_id_extraction_under_500ms` | 1000 行 events.jsonl で session_id 抽出 &lt; 500ms | NFR Performance, 5.2 |

---

### Integ-25: NFR Security - トークンに機密情報なし

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-25 |
| **テストファイル** | `tests/integration/test_token_security.py` |
| **テストクラス** | `TestTokenSecurity` |
| **目的** | トークン YAML の全フィールドに機密情報（API key / password パターン / 環境変数値）が含まれないことを確認 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_token_fields_exhaustive_list` | トークン YAML の top-level / nested key が仕様通り（token_id, created_at, expires_at, approved_by, automation_mode, risk_summary, approved_designs, skipped_designs）以外を含まない | NFR Security |
| `test_token_no_api_key_patterns` | 正規表現 `(AKIA|sk-|gh[opsu]_)` 等 API key 形式が 0 件 | NFR Security |
| `test_token_no_env_var_leakage` | `os.environ` の値が token YAML に含まれない（credentials, tokens 等の代表値を fixture で注入して検査） | NFR Security |
| `test_design_hash_is_content_hash_not_secret` | design_hash が規定形式 `sha256:` + 64 hex のみ | NFR Security, 3.4 |

---

### Integ-26: methodology_tags vocab 外でのリトライ → fallback

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-26 |
| **テストファイル** | `tests/integration/test_methodology_tag_retry.py` |
| **テストクラス** | `TestMethodologyTagRetry` |
| **目的** | design.md Error #8 のリトライ失敗時 fallback（error_category=logic + default `descriptive`）を end-to-end で確認 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_single_retry_recovery` | 1 回目 vocab 外 → 2 回目 vocab 内で成功、manifest.status=success | 4.4 |
| `test_double_failure_falls_back_descriptive` | 2 回連続 vocab 外 → manifest.methodology_tags=[descriptive] + error_category=logic + skip_reason/error_detail | 4.4, Error-Handling-8 |
| `test_question_event_appended_on_double_failure` | 2 回失敗時に journal に `question` event が追加される | 4.4 |

---

### Integ-27: BQ API 失敗時の risk_evaluator 挙動（/premortem subprocess）

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-27 |
| **テストファイル** | `tests/integration/test_premortem_cli.py` |
| **テストクラス** | `TestPremortemBQFailure` |
| **目的** | BQ location API 失敗時に `/premortem` が HIGH + flag で表示・トークン記録する |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_bq_api_network_error_shows_high_with_flag` | MCP `get_table_schema` が network error を返す fixture → risk HIGH + reason に `location_check_failed` | Error-Handling-9 |
| `test_bq_api_auth_error_shows_high_with_flag` | auth error 時も同様に HIGH + flag | Error-Handling-9 |
| `test_bq_location_mismatch_still_hard_block` | API 成功 + location 不一致 → HARD_BLOCK のまま（分岐維持確認） | 2.2 |

---

### Integ-28: Phase B + 正常 TOKEN の対照テスト

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-28 |
| **テストファイル** | `tests/integration/test_batch_launcher.py` |
| **テストクラス** | `TestBatchPhaseBWithToken` |
| **目的** | Phase B で正常に TOKEN を指定した起動が成功することを確認（Integ-11 の対照） |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_phase_b_with_valid_token_proceeds` | approved_by_required=true + valid TOKEN → batch が正常起動 | 5.3 |
| `test_phase_b_warns_not_emitted_with_token` | Phase A の WARNING 文言が stderr に出ないこと | 5.3, 5.3b |

---

### Integ-29: Integ-03 拡張 - SQLite 接続も含む書き込み禁止契約

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-29 |
| **テストファイル** | `tests/integration/test_premortem_io_contract.py` |
| **テストクラス** | `TestPremortemNoSqliteRuntime` |
| **目的** | Integ-03 の I/O 契約テストに SQLite 接続監視を追加し、プロセス全体で sqlite3.connect が 0 回であることを確認 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_premortem_subprocess_no_sqlite_connect` | subprocess 実行中 sqlite3 モジュール呼び出しを strace / LD_PRELOAD で監視 → 0 回（macOS は dtrace / fs_usage 代替） | 4.5, 1.5 |

---

## E2E テスト実行方針（Claude Code による自己検証を前提）

E2E はリリース前 smoke test と、spec-implementer / auto-green が実装中の回帰確認の双方で走ることを想定する。**Claude Code 自身が fixtures セットアップ → シナリオ実行 → assertion → 結果レポートを一発で完遂できる**ように、以下の方針とハーネスを整備する。

### 2 層構成（light E2E と full E2E）

| 層 | 目的 | Claude 本体 | 実行時間 | CI 組み込み |
|---|---|---|---|---|
| **light E2E** | Claude Code が毎回自動実行可能な自己検証。実 `claude -p` を呼ばず、決定的な出力を返す **stub claude wrapper** を `PATH` 先頭に挿し替えてシナリオを回す | stub (`tests/e2e/stub_claude.py`) | < 30 秒 / シナリオ | ◯ |
| **full E2E** | 実 Claude Code を使った最終確認。リリース前・設計変更後に人間主導で 1 回実行 | 実 `claude -p` (1-2 min / 短尺 design) | 5-10 分 / 全シナリオ | × (任意) |

light E2E を正（CI 代替）、full E2E を補（リリース前）として扱う。test-design 上は light E2E を自動検証の中心に据える。

### Claude Code 自己検証を成立させる 4 要件

1. **決定的 stub claude** — `stub_claude.py` は引数（`--approved-by` / `--resume` / `events.jsonl` 出力先）を解釈し、fixtures に従って決定的な `events.jsonl`, `manifest.yaml`, `_journal.yaml`, `summary.md` を書き出す。Claude Code 本体の non-determinism を回避
2. **fixtures templates** — `tests/e2e/fixtures/` に「3 designs (LOW/MEDIUM/HIGH) + history + config + mock MCP responses」を YAML で置き、`harness/setup.py` が temp `.insight/` に展開する
3. **assertion script** — 各シナリオごとに `tests/e2e/assertions/e2e_NN_assert.py` を用意。期待値表を 1:1 で assert に変換し、失敗時は明示的な diff を stderr に出す（Claude Code が exit code で pass/fail を判定可能）
4. **runner スクリプト** — `tests/e2e/runners/e2e_NN.sh` が `setup → execute → assert → teardown` を単一コマンドで完結させる（Claude Code が `bash tests/e2e/runners/e2e_01.sh` を呼び exit code 0 を確認するだけで合否判定）

### ハーネスのディレクトリ構成（Claude Code 実行可能性のために新設）

```
tests/e2e/
├── stub_claude.py                 # 実 claude の代替。決定的 NDJSON + manifest/journal を書く
├── fixtures/
│   ├── designs/                   # 3 designs YAML (LOW/MEDIUM/HIGH のテンプレ)
│   ├── runs_history/              # n=3 past runs の manifest.yaml 群
│   ├── config/                    # config.yaml バリアント (review / auto / Phase A / Phase B)
│   └── expected/                  # 期待される manifest / journal / summary のスナップショット
├── harness/
│   ├── setup.py                   # temp .insight/ を構築、stub claude を PATH 先頭に注入
│   ├── teardown.py                # temp ディレクトリ削除
│   ├── assert_helpers.py          # manifest/journal/summary を読み diff するユーティリティ
│   └── claude_wrapper.py          # Claude Code 内部から light E2E を呼ぶ薄いラッパー
├── assertions/
│   ├── e2e_01_assert.py
│   ├── e2e_02_assert.py
│   └── e2e_03_assert.py
└── runners/
    ├── e2e_01.sh                  # bash tests/e2e/runners/e2e_01.sh → exit 0/非 0
    ├── e2e_02.sh
    └── e2e_03.sh
```

### stub claude wrapper の契約

`tests/e2e/stub_claude.py` は以下の挙動を**決定的に**返す:

- 引数 `--approved-by TOKEN` を parse、`.insight/premortem/TOKEN.yaml` を読み承認済み design を取得
- `--output-format stream-json` 指定時、`events.jsonl` に `system/init` + 各 design の `tool_use` + `result` を書き出す
- 各 design について fixtures から期待 manifest / journal スナップショットをコピーする
- `--max-turns` を env var で上書き可能: `STUB_KILL_AFTER_DESIGNS=1` で 1 本目の後に session 終了 (E2E-02 の crash 代替)
- `--resume SESSION_ID` で前回 `events.jsonl` の `session_id` をマッチさせて続きの design から再開
- exit code 0 = 完走、2 = budget 到達、137 = 疑似 kill

これにより、Claude Code が `bash tests/e2e/runners/e2e_02.sh` を呼ぶだけで crash シナリオを再現可能。

### nested Claude Code 実行時の注意（full E2E の場合のみ）

full E2E で実 `claude -p` を Claude Code セッション内部から呼ぶ場合:

- `--permission-mode bypassPermissions` は nested でも許容（設計判断として E2E 専用の短尺 design のみ利用）
- `--max-budget-usd 1` で nested セッションごとの予算上限を縛る
- `--allowedTools` を明示して外部書き込みを制限（既存 `/batch-analysis` と同じ tool set）
- 実行ログは `tests/e2e/full_runs/{TIMESTAMP}/` に隔離保存

---

## E2Eテストシナリオ

### E2E-01: Overnight happy path（3 designs, mixed risk）

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-01 |
| **テスト名** | overnight overall happy path |
| **目的** | /premortem → token → /batch-analysis → manifest / journal / summary.md 整合 |
| **Light E2E 実行方法** | `bash tests/e2e/runners/e2e_01.sh`（Claude Code から呼び出し、exit 0 で pass 判定） |
| **Full E2E 実行方法** | 実 `claude -p` を short-design fixtures で 1 回通す（人間の最終確認） |

**事前条件（setup.py が自動構築）:**

1. temp `.insight/` に 3 designs (DES-A=LOW, DES-B=MEDIUM, DES-C=HIGH) を queue 状態で配置
2. history fixtures (`fixtures/runs_history/`) で DES-A/B の source_ids に n=3 past runs、DES-C は history 無し
3. `fixtures/config/review_phase_a.yaml` を `.insight/config.yaml` にコピー
4. `fixtures/designs/mock_mcp_responses.yaml` を mock MCP server に読み込ませる
5. `PATH=tests/e2e:$PATH` で stub claude を優先させる

**実行ステップ（runners/e2e_01.sh で単一コマンド化）:**

```bash
#!/usr/bin/env bash
set -euo pipefail
python tests/e2e/harness/setup.py --scenario e2e_01
/premortem --queued --yes --mode review      # HIGH 検出 → exit 2 想定
if [[ $? -ne 2 ]]; then echo "FAIL: premortem should exit 2"; exit 1; fi

# スキップ決定を simulate: runner が skip 選択を stdin で注入
/premortem --queued --mode review <<< "s"
TOKEN=$(cat .insight/premortem/*.yaml | grep token_id | head -1 | awk '{print $2}')

/batch-analysis --approved-by "$TOKEN"
python tests/e2e/assertions/e2e_01_assert.py
python tests/e2e/harness/teardown.py
```

**assertion script（assertions/e2e_01_assert.py）が検証する期待値:**

| # | 期待値 | 検証手段 | カバーするAC |
|---|--------|---------|-------------|
| 1 | /premortem stdout 1 画面で HIGH 理由表示 | captured stdout grep | 1.1, 1.2, 2.4 |
| 2 | token に approved=[A,B], skipped=[C] | `.insight/premortem/*.yaml` load + fields assert | 3.1 |
| 3 | DES-A / DES-B の manifest.verdict が journal と一致 | manifest と journal 両方 load し direction/confidence 比較 | 4.3 |
| 4 | DES-C manifest.status=skipped | manifest.yaml load | 2.2, 4.2 |
| 5 | run.yaml status=completed | run.yaml load | 6.4 |
| 6 | events.jsonl が NDJSON で読み取り可能 | jsonl の各行を json.loads | 5.4 |
| 7 | run.yaml.session_id が正しく反映 | events.jsonl の system/init と一致 | 5.2 |
| 8 | Launch message が /premortem 最終行に出る | captured stdout の最終行 regex | 1.4 |
| 9 | HIGH 無し → automatic approval (review) | token.risk_summary と approved_by 値 | 7.3 |

assertion script は期待値 1 つずつ `assert` 文で検証、失敗時に `AssertionError` で exit code 1、Claude Code が stderr の内容から修正箇所を特定可能。

---

### E2E-02: Crash recovery next-day resume

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-02 |
| **テスト名** | mid-run crash + next-day resume |
| **目的** | 中断した run が翌日 `--resume` で継続完了 |
| **Light E2E 実行方法** | `bash tests/e2e/runners/e2e_02.sh`（Claude Code から呼び出し、exit 0 で pass 判定） |
| **Full E2E 実行方法** | full run で `--max-turns 3` を使い強制 session 終了 → 翌朝再起動（人間の最終確認） |

**事前条件:**

1. E2E-01 と同じ fixtures
2. token TTL は `fixtures/config/review_phase_a.yaml` の default 24h を使用
3. stub claude は env var `STUB_KILL_AFTER_DESIGNS=1` で DES-A 完走後に exit 137 を返す

**実行ステップ（runners/e2e_02.sh）:**

```bash
#!/usr/bin/env bash
set -euo pipefail
python tests/e2e/harness/setup.py --scenario e2e_02
/premortem --queued --yes --mode review <<< "s"
TOKEN=$(ls .insight/premortem/*.yaml | head -1 | xargs basename .yaml)

# 1 回目: DES-A 完走後に stub が exit 137 （疑似 crash）
STUB_KILL_AFTER_DESIGNS=1 /batch-analysis --approved-by "$TOKEN" || true

# 中断検出 + resume を claude_wrapper 経由で呼ぶ（2 回目、通常モード）
/batch-analysis --approved-by "$TOKEN"

python tests/e2e/assertions/e2e_02_assert.py
python tests/e2e/harness/teardown.py
```

**assertion script（e2e_02_assert.py）が検証する期待値:**

| # | 期待値 | 検証手段 | カバーするAC |
|---|--------|---------|-------------|
| 1 | 中断検出 stderr メッセージ | 2 回目の stderr に `detected incomplete run: {run_id}` | 6.1 |
| 2 | events.jsonl に 2 起動分のログが append | events.jsonl の system/init が 2 行存在 | 6.2 |
| 3 | DES-B の manifest が最終的に success | manifest.status=success + ended_at あり | 6.2, 4.2 |
| 4 | run.yaml.status=completed で終了 | run.yaml load | 6.4 |
| 5 | 同一 token を 2 回使える（TTL 内） | 1 回目と 2 回目で同じ token_id、拒否なし | 3.2 |

---

### E2E-03: Phase A → Phase B migration

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-03 |
| **テスト名** | approved_by_required 切替 |
| **目的** | Phase A (warning) と Phase B (exit 1) の切替が config 1 行で機能 |
| **Light E2E 実行方法** | `bash tests/e2e/runners/e2e_03.sh`（Claude Code から呼び出し、exit 0 で pass 判定） |
| **Full E2E 実行方法** | 実 claude で 1 design だけの短尺 run を 2 回（Phase A / B）実行（人間の最終確認） |

**事前条件:**

1. Phase A 期間想定: config に `batch.approved_by_required: false`
2. 1 design queue、token なし

**手順:**

#### 1. Phase A 起動

1. `/batch-analysis` を `--approved-by` 無しで実行
2. stderr WARNING → 実行継続
3. run.yaml に `automation_mode=legacy / premortem_token=null`

#### 2. Phase B 切替

1. config を `approved_by_required: true` に変更
2. 再度 `/batch-analysis` を `--approved-by` 無しで実行
3. exit 1、stderr に "required"

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | Phase A で warning + 続行 | 5.3b |
| 2 | run.yaml に legacy 記録 | 5.3b |
| 3 | Phase B で exit 1 | 5.3 |

---

## E2E テストサマリ

| テストID | テスト名 | Light 実行方法 | Full 実行方法 | カバーするAC |
|----------|---------|----------------|---------------|-------------|
| E2E-01 | Overnight happy path | `bash tests/e2e/runners/e2e_01.sh` (Claude Code 自動) | 実 `claude -p` 短尺 design | 1.1-1.4, 2.4, 3.1, 4.3, 4.2, 5.2, 5.4, 6.4, 7.3 |
| E2E-02 | Crash recovery next-day resume | `bash tests/e2e/runners/e2e_02.sh` (stub kill) | 実 `claude -p` + `--max-turns 3` | 3.2, 4.2, 6.1, 6.2, 6.4 |
| E2E-03 | Phase A → B migration | `bash tests/e2e/runners/e2e_03.sh` (config 差替え 2 回実行) | 実 `claude -p` × 2 起動 | 5.3, 5.3b |

Light E2E は全 3 件、Claude Code が shell command 1 つで自己検証可能（exit code 0/非 0 で合否判定）。Full E2E は設計変更後の人間主導 smoke test として残す。

---

## テストファイル構成

```
tests/
├── batch_harness/                         # Unit tests for this spec
│   ├── __init__.py
│   ├── test_risk_evaluator.py             # Unit-01 ～ Unit-07
│   ├── test_premortem_config.py           # Unit-08
│   ├── test_token_manager.py              # Unit-09 ～ Unit-14
│   ├── test_manifest_writer.py            # Unit-15 ～ Unit-18, Unit-23
│   ├── test_history_query.py              # Unit-19
│   └── test_crash_recovery.py             # Unit-20 ～ Unit-22
├── integration/
│   ├── test_premortem_cli.py              # Integ-01, 02, 04, 27
│   ├── test_premortem_io_contract.py      # Integ-03, 29
│   ├── test_premortem_modes.py            # Integ-17
│   ├── test_premortem_performance.py      # Integ-24
│   ├── test_batch_launcher.py             # Integ-05, 06, 07, 09, 11-13, 18-21, 28
│   ├── test_mode_risk_matrix.py           # Integ-23
│   ├── test_token_security.py             # Integ-25
│   ├── test_methodology_tag_retry.py      # Integ-26
│   ├── test_manifest_atomic.py            # Integ-08
│   ├── test_session_id_extraction.py      # Integ-10, 22
│   └── test_crash_recovery.py             # Integ-14, 15, 16
├── e2e/                                   # Light E2E (Claude Code 自己検証)
│   ├── stub_claude.py                     # 決定的 claude 代替
│   ├── fixtures/
│   │   ├── designs/                       # 3 designs YAML
│   │   ├── runs_history/                  # n=3 past manifests
│   │   ├── config/                        # review_phase_a / review_phase_b / auto 等
│   │   └── expected/                      # 期待される manifest/journal/summary snapshot
│   ├── harness/
│   │   ├── setup.py                       # temp .insight/ 構築 + PATH 注入
│   │   ├── teardown.py
│   │   ├── assert_helpers.py
│   │   └── claude_wrapper.py              # Claude Code からの呼び出しラッパー
│   ├── assertions/
│   │   ├── e2e_01_assert.py
│   │   ├── e2e_02_assert.py
│   │   └── e2e_03_assert.py
│   ├── runners/
│   │   ├── e2e_01.sh
│   │   ├── e2e_02.sh
│   │   └── e2e_03.sh
│   └── full_runs/                         # Full E2E のログ隔離（.gitignore 対象）
└── fixtures/batch_harness/                # Unit / Integration 共通 fixtures
    ├── designs/
    ├── runs/
    ├── tokens/
    ├── config/
    └── events_jsonl/
```

---

## 単体テストサマリ

| テストID | 対象モジュール | カバーするAC |
|----------|--------------|-------------|
| Unit-01 | `skills/premortem/lib/risk_evaluator.py` | 2.1 |
| Unit-02 | `skills/premortem/lib/risk_evaluator.py` | 2.2 |
| Unit-03 | `skills/premortem/lib/risk_evaluator.py` | 2.3 |
| Unit-04 | `skills/premortem/lib/risk_evaluator.py` | 2.3b |
| Unit-05 | `skills/premortem/lib/risk_evaluator.py` | 2.3c |
| Unit-06 | `skills/premortem/lib/risk_evaluator.py` | 2.4 |
| Unit-07 | `skills/premortem/lib/risk_evaluator.py` | 2.5 |
| Unit-08 | `skills/premortem/lib/` + `skills/_shared/` config loader | 2.6, 7.5, 5.3b |
| Unit-09 | `skills/_shared/token_manager.py` | 3.1, 1.3 |
| Unit-10 | `skills/_shared/token_manager.py` | 3.2 |
| Unit-11 | `skills/_shared/token_manager.py` | 3.3 |
| Unit-12 | `skills/_shared/token_manager.py` (compute_design_hash) | 3.4 |
| Unit-13 | `skills/_shared/token_manager.py` | 3.4 |
| Unit-14 | `skills/_shared/token_manager.py` | 3.5 |
| Unit-15 | `skills/_shared/manifest_writer.py` | 4.1, 5.2 |
| Unit-16 | `skills/_shared/manifest_writer.py` | 4.2, 3.3, 5.5, 2.2 |
| Unit-17 | `skills/_shared/manifest_writer.py` | 4.3 |
| Unit-18 | `skills/_shared/manifest_writer.py` + vocab load | 4.4 |
| Unit-19 | `skills/premortem/lib/history_query.py` | 4.5, 2.3b, 2.4, 2.5 |
| Unit-20 | `skills/_shared/crash_recovery.py` | 6.1 |
| Unit-21 | `skills/_shared/crash_recovery.py` | 6.5 |
| Unit-22 | `skills/_shared/crash_recovery.py` | 6.3 |
| Unit-23 | `skills/_shared/manifest_writer.py` | 6.4, 6.3 |

---

## 統合テストサマリ

| テストID | 対象コンポーネント | カバーするAC |
|----------|-------------------|-------------|
| Integ-01 | /premortem CLI + MCP mock | 1.1, 1.2, 1.4 |
| Integ-02 | /premortem --yes × mode | 1.3, 7.3, 7.2, 3.4, 7.4 |
| Integ-03 | /premortem I/O 契約 | 1.5 |
| Integ-04 | HARD_BLOCK CLI 挙動 | 2.2, 3.1 |
| Integ-05 | Token TTL 検証 | 3.2 |
| Integ-06 | Hash mismatch skip | 3.3 |
| Integ-07 | auto mode summary.md warning | 7.4, 4.3 |
| Integ-08 | manifest atomic 書込 | 4.2 |
| Integ-09 | launcher options / events.jsonl / run.yaml finalize | 5.1, 5.4, 5.5, 6.4 |
| Integ-10 | session_id 抽出 → run.yaml | 5.2, NFR Performance |
| Integ-11 | Phase B exit 1 | 5.3 |
| Integ-12 | Phase A warning + legacy | 5.3b |
| Integ-13 | Budget/turns 到達時の manifest | 5.5, 6.1 |
| Integ-14 | crash_recovery 検出 | 6.1 |
| Integ-15 | --resume with valid token | 6.2 |
| Integ-16 | token 失効時 incomplete 確定 | 6.3 |
| Integ-17 | manual mode --yes 拒否 | 7.1 |
| Integ-18 | review + HIGH stop | 7.2 |
| Integ-19 | review + no HIGH autoproceed | 7.3 |
| Integ-20 | auto + risk 分配 | 3.4, 7.4, 2.2 |
| Integ-21 | default mode = review | 7.5 |
| Integ-22 | events.jsonl 末尾破損 | NFR Reliability, 6.2 |
| Integ-23 | mode × risk 全組合せ (15 ケース) | 2.1, 2.2, 7.1, 7.2, 7.3, 7.4, 3.4 |
| Integ-24 | NFR Performance (30 秒 / 100ms / 500ms) | NFR Performance, 5.2 |
| Integ-25 | NFR Security (token に機密なし) | NFR Security, 3.4 |
| Integ-26 | methodology_tags リトライ fallback | 4.4, Error-Handling-8 |
| Integ-27 | BQ API 失敗時の HIGH + flag | Error-Handling-9, 2.2 |
| Integ-28 | Phase B + 正常 TOKEN 対照 | 5.3, 5.3b |
| Integ-29 | /premortem subprocess で SQLite 接続 0 回 | 4.5, 1.5 |

---

## カバレッジ目標

| コンポーネント | 目標カバレッジ |
|--------------|--------------|
| `skills/premortem/lib/risk_evaluator.py` | 95% 以上（純粋関数、全分岐を Unit でカバー） |
| `skills/premortem/lib/history_query.py` | 90% 以上 |
| `skills/_shared/token_manager.py` | 95% 以上（hash canonicalization と TTL は Unit でほぼ網羅可能） |
| `skills/_shared/manifest_writer.py` | 90% 以上（atomic write path は Integration でも二重化） |
| `skills/_shared/crash_recovery.py` | 85% 以上（実 I/O が多いため Integration 重視） |
| `skills/_shared/_atomic.py` | 80% 以上（コピーしたパターン、最小限の Unit で足りる） |

---

## 成功基準

- [ ] 全 Acceptance Criteria (7 FR × 34 ACs) が少なくとも 1 つのテストレベルでカバー済み（マトリクスで空白行ゼロ）
- [ ] Unit-01 ～ Unit-23 が pass（Red → Green → Refactor サイクルで実装）
- [ ] Integ-01 ～ Integ-29 が pass（subprocess + mock で再現可能）
- [ ] E2E-01 ～ E2E-03 の **Light E2E** が `bash tests/e2e/runners/e2e_NN.sh` で exit 0（Claude Code が自己検証可能）
- [ ] stub_claude.py が決定的に `events.jsonl` / manifest / journal / summary を生成し、各 assertion script が失敗時に具体的な diff を stderr 出力
- [ ] Full E2E はリリース前に人間主導で 1 回実行（記録は `tests/e2e/full_runs/{TIMESTAMP}/` に保存）
- [ ] カバレッジ目標を全コンポーネントで達成
- [ ] AC-3.4 (design_hash canonicalization) の冪等性テストが全 10 ケース pass (Unit-12)
- [ ] AC-1.5 (書き込み禁止契約) が Integ-03 + Integ-29 で実ファイル観測と SQLite 接続監視で確認済み
- [ ] automation mode × risk の全 15 組合せが Integ-23 (table-driven) で pass
- [ ] NFR Performance: `/premortem` 10 designs × history 30 runs で 30 秒以内、manifest atomic write &lt; 100ms、session_id 抽出 &lt; 500ms (Integ-24 で計測)
- [ ] NFR Security: トークン YAML に API key / env var / 機密パターンなし (Integ-25)
- [ ] NFR Reliability 代表 6 障害シナリオのマッピング:
  - Crash (PC 強制終了) → Integ-14, Integ-15, E2E-02
  - 子プロセス孤児化 / budget 到達 → Integ-13
  - 承認トークン期限切れ → Integ-05, Integ-16
  - design_hash 不一致 → Integ-06
  - events.jsonl 最終行破損 → Integ-22
  - BQ API 失敗 → Integ-27
  - methodology_tags リトライ失敗 → Integ-26

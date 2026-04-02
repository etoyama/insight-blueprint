# Tasks: batch-analysis

## Reference

> **investigation.md**: 実装時は [investigation.md](investigation.md) の Verified Facts と Design Decisions を参照すること。特に V3（セルコントラクト検証）、V5b（haiku/sonnet 比較）、V6a（因果推論検証）の実績値がプロンプト設計の根拠となる。

## 検証方法の実行規則

test-design.md の検証方法列に記載された擬似記法は、Claude Code の対話セッションで以下のツールに変換して実行する:

| 擬似記法 | Claude Code ツール | 例 |
|---------|-------------------|-----|
| `Bash: <command>` | Bash ツール | `Bash: ls .insight/runs/*/notebook.py` → Bash ツールで `ls .insight/runs/*/notebook.py` を実行 |
| `Grep: pattern="<pat>" path="<path>"` | Grep ツール | `Grep: pattern="type: observe" path=".insight/designs/X_journal.yaml"` → Grep ツールで検索 |
| `MCP: <tool_name>(<params>)` | MCP ツール直接呼び出し | `MCP: get_analysis_design(design_id="DEMO-H01")` → mcp__insight-blueprint__get_analysis_design を呼び出し |
| `Read: <path>` | Read ツール | `Read: .insight/runs/*/summary.md` → Read ツールで読む |

**重要**: `echo $?` による終了コード確認は使わない。各コマンドの出力内容で判定する。

## テスト実行モデル

| テストレベル | 実行方法 | 備考 |
|-------------|---------|------|
| Integ-01〜11 | **Claude Code 対話セッション内で直接実行**。MCP tool、Read/Write/Bash/Grep を直接使う。`claude -p` は使わない | V1d で MCP + Bash の組み合わせ動作を確認済み |
| E2E-01〜06 | **Bash ツールで `claude -p` をサブプロセス起動**。`claude -p "$(cat ...)" --model sonnet ... 2>&1` で実行し、完了後に結果ファイルを Read/Grep で検証 | V1d, V3, V6a で claude -p のサブプロセス起動を検証済み。循環依存ではなく入れ子実行 |

**Integ テストで `claude -p` を使わない理由**: Integ テストはパイプラインの各ステップを個別に検証する。MCP tool 呼び出し、ファイル書き込み、marimo 実行は対話セッション内で直接行える。headless 実行の検証は E2E テストの責務。

---

- [ ] 1.1. SKILL.md 作成 — スキル定義・セルコントラクト・設定項目
  - File: `skills/batch-analysis/SKILL.md`
  - Purpose: batch-analysis スキルの公開インターフェースを定義。セルコントラクト（8セル定義）、next_action convention、設定項目（notebook_dir, lib_dir）、headless 起動コマンド例を記載
  - Leverage: `skills/analysis-journal/SKILL.md`（既存スキルの SKILL.md フォーマット参照）、design.md の Cell Contract Detail セクション、design.md の Configuration Resolution セクション
  - Requirements: FR-2.2（セルコントラクト）, FR-2.5（notebook_dir）, FR-2.6（lib_dir）, FR-1.1（next_action convention）
  - Prompt: Role: Skill author for insight-blueprint. Task: Create SKILL.md defining the batch-analysis skill. Include cell contract (8 cells with input/output/responsibility), next_action convention (`{"type": "batch_execute", "priority": N}`), configuration items (notebook_dir, lib_dir with resolution order), headless launch command example, and marimo-specific rules (V3/V5d verified). Follow existing SKILL.md format from analysis-journal. Restrictions: Do not create Python code. This is a documentation-only deliverable. Do not deviate from design.md's DD-6 cell contract or DD-7 verdict schema. Success: `skills/batch-analysis/SKILL.md` が存在し、「## Cell Contract」「## Configuration」「## Launch Command」セクションを含む。

- [ ] 1.2. batch-prompt.md 作成 — オーケストレーション全体の instructions
  - File: `skills/batch-analysis/batch-prompt.md`
  - Purpose: headless 実行時に `claude -p` で渡すプロンプト。キュー取得→パッケージチェック→lib_dir カタログ化→notebook 生成→実行→自己レビュー→エラー修正→journal 記録→summary 生成の全フローを instructions として含む
  - Leverage: design.md のアーキテクチャフロー図、design.md の Self-Review Protocol、design.md の Error Handling、design.md の Session JSON Parsing Specification、design.md の Time Budget Management、investigation.md の V3 プロンプト（`/tmp/v3-cell-contract-prompt.md`）
  - Requirements: FR-1.1〜1.4, FR-2.1〜2.6, FR-3.1〜3.6, FR-4.1〜4.5, FR-5.1〜5.4, FR-6.1〜6.6
  - Dependencies: 1.1（SKILL.md のセルコントラクト定義を参照）
  - Prompt: Role: Prompt engineer for Claude Code headless automation. Task: Create batch-prompt.md containing full orchestration instructions. Structure: (1) Role & Context, (2) Available Tools (MCP + Bash/Read/Write) — Available MCP tools には search_catalog（カタログ検索、source_ids 空の場合のフォールバック用）を含めること, (3) Cell Contract (from SKILL.md), (4) Execution Pipeline (queue → pkg check → lib_dir scan → generate → execute → review → fix → journal → summary), (5) Self-Review Protocol (data processing check, critical analysis review, time budget 30min/design), (6) Error Handling (3-attempt repair loop, context7 for marimo docs, rules update on success), (7) Journal Recording (session JSON parsing, observe/evidence/question extraction, direction determination), (8) Summary Generation (Overview table, Requires Attention, Next Steps), (9) Configuration (notebook_dir, lib_dir, CATALOG.md). Use `[SELF-REVIEW]` marker for reviewable log output. Restrictions: Do not generate conclude journal events. Terminal status transition is human-only. Model is sonnet. Must follow design.md's Time Budget Management (graceful degradation at 25/30 min). FR別チェックリスト（実装完了時に確認）: FR-1.1〜1.4: キュー取得→フィルタ→priority ソート→terminal skip の手順; FR-2.1〜2.6: セルコントラクト定義の参照、exploratory/confirmatory の分岐、notebook_dir/lib_dir 設定; FR-3.1〜3.6: marimo export session 実行、エラー修正ループ（3回）、context7 参照、rules 更新、パッケージチェック; FR-4.1〜4.5: session JSON パース、journal YAML 生成、direction 判定、conclude 禁止; FR-5.1〜5.4: summary.md テンプレート、Overview テーブル、Requires Attention、Next Steps; FR-6.1〜6.6: headless コマンド構成、allowedTools、max-budget-usd、session.log 保存. Success: `skills/batch-analysis/batch-prompt.md` が存在し、上記 FR 別チェックリストの全項目が instructions 内に含まれる。

- [ ] 1.3. テストフィクスチャ作成 — テスト用設計書・データ・lib_dir
  - File: `tests/batch-analysis/fixtures/` (multiple files)
  - Purpose: Integ/E2E テストで使用するテスト用設計書、lib_dir のサンプルユーティリティ、marimo 記法エラーを含む notebook を用意
  - Leverage: `.insight/designs/DEMO-H01_hypothesis.yaml`（既存サンプル）、test-design.md の各テストシナリオの事前条件
  - Requirements: test-design.md の Integ-01〜11, E2E-01〜06 の事前条件
  - Dependencies: 1.1
  - Prompt: Role: Test engineer. Task: Create test fixtures for batch-analysis validation. Include: (1) Exploratory design YAML (DEMO-H01 based), (2) Confirmatory design YAML with PSM methodology (CAUSAL-H01 based), (3) Design with nonexistent data source (for error testing), (4) Design with terminal status (supported) for skip testing, (5) lib_dir with sample utility functions + expected CATALOG.md, (6) Pre-written notebook with `_` prefix violations for Integ-04 marimo syntax error test. Restrictions: Fixtures must work with tutorial/sample_data/sales.csv. Do not modify existing .insight/designs/ files. Success: `tests/batch-analysis/fixtures/` に5種のフィクスチャファイルが存在する。

- [ ] 2.1. 統合テスト実行 — Integ-01〜05（キュー・生成・実行）
  - Purpose: キュー管理、セルコントラクト準拠、データソースフォールバック、エラー修正、パッケージインストールの統合テストを実行
  - Leverage: test-design.md の Integ-01〜05 の検証方法列
  - Requirements: AC-1.1, 1.3, 2.1, 2.2, 2.4, 2.5, 3.1, 3.2, 3.5, 3.6
  - Dependencies: 1.1, 1.2, 1.3
  - Prompt: Role: QA engineer. Task: Execute integration tests Integ-01 through Integ-05 as defined in test-design.md. For each test, follow the exact verification commands in the 検証方法 column. Record pass/fail for each test case. If a test fails, document the failure and the required fix. Restrictions: Execute verification commands exactly as specified. Do not skip any verification step. Success: テスト結果を `.spec-workflow/specs/batch-analysis/test-results/integ-01-05.md` にログとして保存し、全ケースが PASS。

- [ ] 2.2. 統合テスト実行 — Integ-06〜08（journal・MCP）
  - Purpose: journal 自動記録、journal 追記、MCP 接続失敗の統合テストを実行
  - Leverage: test-design.md の Integ-06〜08 の検証方法列
  - Requirements: AC-4.1, 4.2, 4.3, 4.4, 4.5, 6.3
  - Dependencies: 2.1（Integ-02 の実行結果を Integ-06 が使用）
  - Prompt: Role: QA engineer. Task: Execute integration tests Integ-06 through Integ-08 as defined in test-design.md. Integ-06 uses the notebook execution results from Integ-02. Follow exact verification commands. Integ-07（journal 追記）では、実行前に既存 journal のイベント数を `python3 -c "import yaml; ..."` で自動カウントし、実行後のイベント数と比較する。手動での BEFORE_COUNT 埋め込みは行わない。 Restrictions: Execute verification commands exactly as specified. Success: テスト結果を `.spec-workflow/specs/batch-analysis/test-results/integ-06-08.md` にログとして保存し、全ケースが PASS。

- [ ] 2.3. 統合テスト実行 — Integ-09〜11（lib_dir・レビュー・ディレクトリ）
  - Purpose: lib_dir カタログ化、自己レビュー検証、ディレクトリ命名の統合テストを実行
  - Leverage: test-design.md の Integ-09〜11 の検証方法列
  - Requirements: FR-2.5, FR-2.6, NFR Performance
  - Dependencies: 1.2, 1.3
  - Prompt: Role: QA engineer. Task: Execute integration tests Integ-09 through Integ-11 as defined in test-design.md. Follow exact verification commands. Restrictions: Execute verification commands exactly as specified. Success: テスト結果を `.spec-workflow/specs/batch-analysis/test-results/integ-09-11.md` にログとして保存し、全ケースが PASS。

- [ ] 3.1. E2E テスト実行 — E2E-01, E2E-02（正常系）
  - Purpose: exploratory 単件バッチと confirmatory (PSM) 単件バッチの E2E テストを実行
  - Leverage: test-design.md の E2E-01, E2E-02 の手順・検証方法列
  - Requirements: AC-1.1, 1.3, 2.1〜2.4, 3.1, 3.3, 3.5, 4.1, 4.2, 4.4, 4.5, 5.1, 6.1
  - Dependencies: 2.1, 2.2, 2.3（統合テスト通過後）
  - Prompt: Role: QA engineer. Task: Execute E2E-01 (exploratory single batch with DEMO-H01) and E2E-02 (confirmatory PSM batch). Follow exact procedures and verification commands from test-design.md. This is the primary validation of the entire batch-analysis pipeline. Restrictions: Use the actual `claude -p` headless command from SKILL.md. Do not simulate or mock any step. Success: テスト結果を `.spec-workflow/specs/batch-analysis/test-results/e2e-01-02.md` にログとして保存し、全ケースが PASS。

- [ ] 3.2. E2E テスト実行 — E2E-03〜06（エラー・混合・安全終了）
  - Purpose: エラー系、terminal skip、複数件混合バッチ、budget 安全終了の E2E テストを実行
  - Leverage: test-design.md の E2E-03〜06 の手順・検証方法列
  - Requirements: AC-1.2, 1.4, 3.2, 3.4, 5.2〜5.4, 6.2, 6.4
  - Dependencies: 3.1（正常系通過後）
  - Prompt: Role: QA engineer. Task: Execute E2E-03 (unrecoverable error skip), E2E-04 (terminal status skip), E2E-05 (mixed batch with priority ordering and idempotency), E2E-06 (budget safe termination). Follow exact procedures and verification commands. Restrictions: E2E-05 requires 4 design fixtures and a second batch run for idempotency check. E2E-06 uses --max-budget-usd 1.0. Success: テスト結果を `.spec-workflow/specs/batch-analysis/test-results/e2e-03-06.md` にログとして保存し、全ケースが PASS。

- [ ] 4.1. 修正・最終検証
  - Purpose: テスト実行で発見された問題の修正と最終検証
  - Leverage: 2.1〜3.2 のテスト結果
  - Requirements: 全 AC
  - Dependencies: 3.2
  - Prompt: Role: Senior developer. Task: Review all test results from tasks 2.1-3.2. Fix any failures in SKILL.md or batch-prompt.md. Re-run failed tests. Verify all 28 ACs are covered. Update investigation.md changelog. NFR 検証: (1) session.log にバッチ全体のログが記録されている (FR-6.5), (2) [SELF-REVIEW] マーカーが session.log に存在する (NFR Performance), (3) YYYYMMDD_HHmmss ディレクトリ命名が正しい. Restrictions: Do not change requirements or test-design. Only fix implementation (SKILL.md, batch-prompt.md, fixtures). Success: test-results/ の全ログが PASS、investigation.md の changelog が更新済み。

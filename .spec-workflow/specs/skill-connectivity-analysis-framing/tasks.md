# Tasks: skill-connectivity-analysis-framing

## Codex レビュー反映状況

| ID | 重要度 | 指摘 | 対応 |
|----|--------|------|------|
| T-01 | High | E2E テスト実行タスクが未定義 | Task 3.2 を追加。必須 E2E シナリオの実行手順をコピペ可能な粒度で記載 |
| T-02 | Medium | Task 1.1 の作業密度が高い | ヘルパー関数を独立ステップとして明記。パーサー不備が後続ブロックしないよう Prompt に段階的実装を指示 |
| T-03 | Medium | REQ-1 動的 AC の検証責任が不明 | 各実装タスクに対応 E2E ID を明記（E2E 検証列を追加） |
| T-04 | Medium | Markdown 表記揺れに弱い | Task 1.1 Prompt に正規化ルール（空白・全角半角・矢印記法・コードブロック除外）を追加 |
| T-05 | Low | Task 3.1 が重い | 3.1a（新規テスト）と 3.1b（回帰テスト）に分割 |
| T-06 | Low | 実行証跡の出力物が未指定 | Task 3.1a, 3.2 に証跡出力を追加 |

---

## Red Phase: テスト作成（Unit-01 〜 Unit-06）

- [x] 1.1. テストインフラ + Unit-01 + Unit-02: SKILL.md 構造検証とフォワーディンググラフ整合性
  - File: `tests/skills/test_skill_structure.py`（新規）
  - **Step A**: SKILL.md パース用ヘルパー関数を実装する（frontmatter パーサー、セクション分割、Chaining テーブルパーサー）。ヘルパー単体でテスト可能な形にする
  - **Step B**: `TestSkillStructure`（Unit-01）: 全6スキルの必須セクション存在・Chaining テーブルフォーマット・バージョン番号を検証する4テストケース
  - **Step C**: `TestForwardingGraph`（Unit-02）: フォワーディングエッジの双方向整合性を検証する5テストケース
  - Purpose: SKILL.md の構造的ドリフトを自動検出する基盤を構築
  - _Leverage: 既存の `tests/` ディレクトリ構造、pytest fixtures_
  - _Requirements: REQ-2 (AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5)_
  - _Prompt: Role: Python test engineer specializing in structural validation | Task: Create `tests/skills/test_skill_structure.py` in three steps. **Step A — Helpers**: (1) `parse_frontmatter(text)` — extract YAML between `---` delimiters, return dict. (2) `split_sections(text, level=2)` — split Markdown by heading level, return dict[heading_text, content]. (3) `parse_chaining_table(section_text)` — extract `\| From \| To \| When \|` rows, return list[dict]. (4) `normalize_text(text)` — normalize for comparison: strip whitespace, normalize full-width/half-width characters, strip arrow variants (→/->), exclude content inside code blocks (``` fenced blocks). (5) `SKILLS_DIR` constant pointing to `src/insight_blueprint/_skills/`. (6) `ALL_SKILLS` list of 6 skill names. (7) `REQUIRED_SECTIONS` list of 6 section names. **Step B — TestSkillStructure** (Unit-01): 4 tests: `test_all_skills_have_required_sections` (6 skills × 6 sections: frontmatter, When to Use, When NOT to Use, Workflow, Chaining, Language Rules), `test_chaining_table_format` (all Chaining sections have `\| From \| To \| When \|` header), `test_analysis_framing_version` (version == "1.0.0"), `test_existing_skills_version_bump` (5 existing skills version == "1.1.0"). **Step C — TestForwardingGraph** (Unit-02): 5 tests: `test_reflection_to_framing_entry`, `test_design_to_framing_entry`, `test_catalog_register_return_entries`, `test_data_lineage_to_journal_entry`, `test_bidirectional_consistency` (parse all Chaining tables, build edge list, verify From/To both have entries — exclude external skill development-partner). **Normalization rules** (Codex T-04): When matching skill names in Chaining tables, use `normalize_text()` to handle: (a) `/analysis-framing` vs `analysis-framing` (with/without slash), (b) `→` vs `->` (arrow variants), (c) full-width spaces, (d) content inside ``` code blocks should be excluded from Chaining parsing. Skills are at `src/insight_blueprint/_skills/{name}/SKILL.md`. Use `pathlib.Path` for file paths. All tests should fail at this point (Red phase) | Restrictions: Do not create SKILL.md files. Test code only. Use pytest conventions (no unittest.TestCase). Parse Markdown with regex, do not add markdown-parsing library dependencies | Success: All 9 test functions exist and are syntactically valid. Tests fail because SKILL.md files do not yet have required content_

- [x] 1.2. Unit-03 + Unit-04: Framing Brief プロトコル検証テスト
  - File: `tests/skills/test_skill_structure.py`（Task 1.1 に追記）
  - `TestFramingBrief`（Unit-03）: Framing Brief 出力フォーマットの5セクション存在・推奨方向フィールド・検出ルール整合性を検証する3テストケース
  - `TestDesignFramingBriefIntegration`（Unit-04）: analysis-design の Step 1.5 存在・マッピング表・methodology マッピング・必須5フィールド完全性・fallback 記述を検証する5テストケース
  - Purpose: スキル間コンテキスト受け渡しプロトコルの整合性を自動検証
  - _Leverage: Task 1.1 で作成した SKILL.md パースヘルパー_
  - _Requirements: REQ-1 (AC-1.3), REQ-3 (AC-3.1, AC-3.2, AC-3.3)_
  - _Prompt: Role: Python test engineer | Task: Add to `tests/skills/test_skill_structure.py`: (1) `TestFramingBrief` with 3 tests: `test_framing_brief_has_five_sections` (analysis-framing Step 5 contains `## Framing Brief` + 5 subsections: テーマ, 利用可能データ, 既存分析, ギャップ, 推奨方向), `test_framing_brief_recommended_direction_fields` (推奨方向 section contains theme_id, parent_id, analysis_intent, 推奨手法), `test_framing_brief_detection_rules_match_output` (analysis-design Step 1.5 detection conditions — `## Framing Brief` heading + `### テーマ` + `### 推奨方向` + `theme_id:` — are all satisfiable by analysis-framing Step 5 output format. Track Markdown hierarchy: verify `theme_id:` is under `### 推奨方向` which is under `## Framing Brief`), (2) `TestDesignFramingBriefIntegration` with 5 tests: `test_design_has_step_1_5` (section `### Step 1.5` exists), `test_design_step_1_5_has_mapping_table` (mapping table exists in Step 1.5), `test_design_step_1_5_maps_methodology` (table has 推奨手法 → methodology entry), `test_design_step_1_5_mapping_completeness` (table has all 5 mandatory fields: theme_id, parent_id, analysis_intent, title, methodology), `test_design_step_1_5_fallback` (fallback text for missing Brief exists) | Restrictions: Reuse helpers from Task 1.1. Do not modify existing tests | Success: 8 additional test functions, all syntactically valid, all fail (Red)_
  - Dependencies: 1.1

- [x] 1.3. Unit-05 + Unit-06: 外部スキル接続 + デプロイ検証テスト
  - File: `tests/skills/test_skill_structure.py`（Task 1.1 に追記）
  - `TestExternalSkillConnectivity`（Unit-05）: analysis-framing の自立的テーマ絞り込み記述・development-partner オプショナルエントリ・inbound エントリを検証する3テストケース
  - `TestSkillDeployment`（Unit-06）: analysis-framing ソースディレクトリ存在・`_copy_skills_template()` でのデプロイ成功を検証する2テストケース
  - Purpose: 外部依存なしの完全動作とデプロイメカニズムの検証
  - _Leverage: Task 1.1 で作成した SKILL.md パースヘルパー、既存の `_copy_skills_template()` テスト_
  - _Requirements: REQ-4 (AC-4.1, AC-4.2, AC-4.3), REQ-2 (AC-2.1)_
  - _Prompt: Role: Python test engineer | Task: Add to `tests/skills/test_skill_structure.py`: (1) `TestExternalSkillConnectivity` with 3 tests: `test_framing_handles_vague_theme_independently` (analysis-framing SKILL.md Step 1 contains text about presenting candidate directions when theme is vague — no dependency on development-partner), `test_framing_chaining_has_optional_dev_partner` (Chaining table has development-partner entry with "外部スキル" or "存在時のみ" notation), `test_framing_chaining_has_inbound_dev_partner` (Chaining table has development-partner → analysis-framing entry), (2) `TestSkillDeployment` with 2 tests: `test_analysis_framing_source_exists` (path `src/insight_blueprint/_skills/analysis-framing/SKILL.md` exists), `test_skills_deploy_includes_analysis_framing` (call `_copy_skills_template()` to a temp dir and verify `analysis-framing/SKILL.md` is in output). For deployment test, import from `insight_blueprint.storage.project` | Restrictions: Reuse helpers. Do not modify existing tests | Success: 5 additional test functions, all syntactically valid, deployment test may pass once source file exists_
  - Dependencies: 1.1

## Green Phase: SKILL.md 実装

- [x] 2.1. analysis-framing SKILL.md の新規作成
  - File: `src/insight_blueprint/_skills/analysis-framing/SKILL.md`（新規）
  - design.md の Component 1 に定義された全セクションを持つ SKILL.md を作成する
  - frontmatter（name, version: "1.0.0", description, triggers, disable-model-invocation, argument-hint）
  - When to Use / When NOT to Use / Workflow（Step 1-5）/ Chaining（7エントリ）/ Language Rules
  - Step 2 に Agent tool（subagent_type: "Explore"）委譲の指示、探索スコープ制御ガイドライン
  - Step 5 に Framing Brief 出力フォーマット
  - Purpose: ドメインに接地した分析フレーミングスキルの作成
  - E2E 検証: E2E-01（基本探索）, E2E-02（Brief 出力）, E2E-03（漠然テーマ）, E2E-04（空カタログ）, E2E-07（外部スキルなし）, E2E-08（コンテキスト引き継ぎ）, E2E-09（未初期化）, E2E-10（YAML 破損）
  - _Leverage: 既存スキル `analysis-design/SKILL.md` のフォーマット、design.md Component 1 の全仕様_
  - _Requirements: REQ-1 (AC-1.1〜AC-1.5), REQ-3 (AC-3.1), REQ-4 (AC-4.1〜AC-4.3)_
  - _Prompt: Role: Technical writer creating a Claude Code skill definition | Task: Create `src/insight_blueprint/_skills/analysis-framing/SKILL.md` following design.md Component 1 specification exactly. Include: (1) YAML frontmatter with name: analysis-framing, version: "1.0.0", triggers in description, disable-model-invocation: true, argument-hint: "[theme]", (2) When to Use (vague theme, explore data, frame hypothesis), When NOT to Use (hypothesis already clear → analysis-design, record reasoning → analysis-journal), (3) Workflow Step 1-5 as specified in design.md: Step 1 receives theme + handles vague themes independently (AC-1.4), Step 2 uses Agent tool subagent for Agentic Search of 3 directories with scope control guidelines, Step 3 presents Data Map, Step 4 direction dialogue, Step 5 outputs Framing Brief with 5 sections (テーマ, 利用可能データ, 既存分析, ギャップ, 推奨方向 with theme_id/parent_id/analysis_intent/推奨手法), (4) Chaining table with 7 entries including development-partner optional rows with `\* = 外部スキル` footnote, (5) Language Rules section. Reference existing analysis-design SKILL.md for formatting conventions | Restrictions: Do not use MCP tools in workflow. Use only Glob/Read/Grep via Agent tool. Do not create hypothesis_statement (analysis-design's responsibility). Suggest /catalog-register when catalog is empty (AC-1.5). Handle .insight/ missing with init guidance | Success: Unit-01, Unit-03, Unit-05, Unit-06 tests pass for analysis-framing_
  - Dependencies: 1.1, 1.2, 1.3

- [x] 2.2. analysis-design SKILL.md に Step 1.5 と Chaining を追加
  - File: `src/insight_blueprint/_skills/analysis-design/SKILL.md`（修正）
  - Step 1 と Step 2 の間に Step 1.5: Check for Framing Brief を挿入する
  - 検出ルール（3条件）、9行の draft マッピング表、fallback 記述を含む
  - Language Rules の直前に Chaining セクション（5エントリ）を追加する
  - frontmatter version を `1.0.0` → `1.1.0` に更新する
  - Purpose: Framing Brief プロトコルの受信側を実装し、スキル間接続を追加
  - E2E 検証: E2E-05（Brief → design pre-populate）, E2E-06（Brief なし後方互換）
  - _Leverage: design.md Component 2 の全仕様_
  - _Requirements: REQ-2 (AC-2.3), REQ-3 (AC-3.2, AC-3.3)_
  - _Prompt: Role: Technical writer modifying a Claude Code skill definition | Task: Modify `src/insight_blueprint/_skills/analysis-design/SKILL.md`: (1) Update frontmatter version from "1.0.0" to "1.1.0", (2) Insert `### Step 1.5: Check for Framing Brief` between Step 1 and Step 2. Include detection rules (3 conditions: `## Framing Brief` heading + `### テーマ` + `### 推奨方向` subsections + `theme_id:` in 推奨方向), 9-row mapping table (テーマ→title, 利用可能データ→explanatory/metrics, 既存分析→parent_id, ギャップ→hypothesis_background, 推奨方向.仮説の方向性→title/hypothesis_background, 推奨方向.theme_id→theme_id, 推奨方向.parent_id→parent_id, 推奨方向.analysis_intent→analysis_intent, 推奨方向.推奨手法→methodology), user confirmation step, fallback for missing/incomplete Brief, (3) Add `## Chaining` section before Language Rules with 5 entries per design.md Component 2 | Restrictions: Do not modify existing Step 1-4 content. Step 1.5 is additive only. Preserve all existing sections | Success: Unit-04 tests pass, Unit-01 structure tests pass for analysis-design_
  - Dependencies: 1.1, 1.2

- [x] 2.3. analysis-journal + analysis-reflection の Chaining 更新
  - File: `src/insight_blueprint/_skills/analysis-journal/SKILL.md`（修正）、`src/insight_blueprint/_skills/analysis-reflection/SKILL.md`（修正）
  - analysis-journal: 既存 Chaining テーブルに data-lineage → journal エントリを追加、version を `1.1.0` に更新
  - analysis-reflection: 既存 Chaining テーブルを更新し、analysis-framing への outbound（新仮説探索）と analysis-design への outbound（派生仮説が明確）を分岐、version を `1.1.0` に更新
  - Purpose: 既存スキルのフォワーディング表を整備し、双方向接続を完成させる
  - _Leverage: design.md Component 3, 4 の仕様、既存の Chaining セクション_
  - _Requirements: REQ-2 (AC-2.2, AC-2.5)_
  - _Prompt: Role: Technical writer modifying Claude Code skill definitions | Task: (1) In `analysis-journal/SKILL.md`: update version to "1.1.0", add one row to existing Chaining table: `/data-lineage → /analysis-journal \| Lineage diagram generated: "リネージ結果を証拠として記録するなら /analysis-journal {id}"`. (2) In `analysis-reflection/SKILL.md`: update version to "1.1.0", replace existing Chaining table with 5-entry table per design.md Component 4 — key change is splitting "New derived hypothesis" into two entries: `/analysis-reflection → /analysis-framing` (new hypothesis, explore data/direction first) and `/analysis-reflection → /analysis-design` (derived hypothesis already clear) | Restrictions: Only modify Chaining section and version. Do not touch Workflow or other sections | Success: Unit-02 tests for reflection→framing and lineage→journal pass_
  - Dependencies: 1.1

- [x] 2.4. catalog-register + data-lineage の Chaining 追加
  - File: `src/insight_blueprint/_skills/catalog-register/SKILL.md`（修正）、`src/insight_blueprint/_skills/data-lineage/SKILL.md`（修正）
  - catalog-register: Language Rules の直前に Chaining セクション（4エントリ）を新規追加、version を `1.1.0` に更新
  - data-lineage: Language Rules の直前に Chaining セクション（1エントリ）を新規追加、version を `1.1.0` に更新
  - Purpose: Chaining セクションのないスキルにフォワーディング表を追加し、6スキル全体の接続を完成させる
  - _Leverage: design.md Component 5, 6 の仕様_
  - _Requirements: REQ-2 (AC-2.4, AC-2.5)_
  - _Prompt: Role: Technical writer modifying Claude Code skill definitions | Task: (1) In `catalog-register/SKILL.md`: update version to "1.1.0", add `## Chaining` section before Language Rules with 4 entries: framing→catalog-register (data missing), reflection→catalog-register (register knowledge), catalog-register→framing (return to framing), catalog-register→design (continue design). (2) In `data-lineage/SKILL.md`: update version to "1.1.0", add `## Chaining` section before Language Rules with 1 entry: data-lineage→journal (lineage as evidence) | Restrictions: Only add Chaining section and update version. Do not touch other sections | Success: Unit-02 tests for catalog-register return entries and data-lineage→journal pass_
  - Dependencies: 1.1

## Verification Phase: テスト実行と全体検証

- [x] 3.1. Unit テスト実行と回帰テスト（Claude Code 自動実行）
  - File: `tests/skills/test_skill_structure.py`（修正が必要な場合のみ）
  - Claude Code が `uv run pytest tests/skills/test_skill_structure.py -v` を実行し、全 24 テストケースのパスを確認する
  - 続けて `uv run pytest` で既存テストスイート（725 tests）にリグレッションがないことを確認する
  - テスト失敗がある場合: SKILL.md の修正（テストコードは正）
  - Purpose: Green 確認と品質ゲート
  - _Leverage: 全 Unit テスト、既存テストスイート_
  - _Requirements: 全 REQ_
  - _Prompt: Role: QA engineer | Task: Run new unit tests and full regression suite. If any new test fails, fix the corresponding SKILL.md (test is spec, do not modify test expectations). Verify `test_bidirectional_consistency` covers all 15 forwarding edges from design.md Forwarding Table (excluding external skill edges) | Restrictions: Do not modify test expectations. Do not skip or xfail tests | Success: 24/24 new tests pass + 725+ existing tests pass with 0 failures_
  - Dependencies: 2.1, 2.2, 2.3, 2.4

- [x] 3.2. E2E テスト実行（人間が実行・検証）
  - File: なし（手動実行）
  - Claude の動的挙動（スキル呼び出し時の探索・出力・フォワーディング提案）は自動テストできないため、人間が Claude Code 上でスキルを呼び出して出力を目視検証する
  - Purpose: SKILL.md のワークフロー指示が Claude の動的挙動を正しくガイドすることを確認
  - _Requirements: REQ-1 (AC-1.1〜AC-1.5), REQ-3 (AC-3.2, AC-3.3), REQ-4 (AC-4.1, AC-4.3)_

  **なぜ人間が必要か:** E2E テストは Claude Code 上でスキルを呼び出し、Claude の応答（探索方法の選択、Data Map の構造、Framing Brief の内容、フォワーディング提案の適切さ）を人間が判断する。出力の正否は Claude の動的挙動に依存するため、pytest では検証できない。

  ---

  #### 準備: テスト用プロジェクトのセットアップ

  ターミナルで実行:

  ```bash
  mkdir -p /tmp/e2e-framing-test && cd /tmp/e2e-framing-test
  git init
  uv run insight-blueprint init
  ```

  Claude Code 上でテストデータを登録:

  ```
  /catalog-register
  ```
  → 犯罪統計データを登録（source_id: `crime_stats`, カラム: prefecture, year, crime_count, crime_rate_per_100k, 期間: 2010-2023, 粒度: 都道府県×年）

  ```
  /catalog-register
  ```
  → 外国人登録統計を登録（source_id: `foreign_population`, カラム: prefecture, year, foreign_population, foreign_ratio, 期間: 2010-2023, 粒度: 都道府県×年）

  ```
  /analysis-design FP
  ```
  → デザインを作成: title: "外国人比率と犯罪率の相関分析", hypothesis: "外国人比率と犯罪率に正の相関はない"

  ターミナルでドメイン知識を追加:

  ```bash
  cat > .insight/rules/knowledge_foreign_crime_caution.yaml << 'YAML'
  id: foreign_crime_caution
  category: caution
  content: "外国人犯罪統計は在留資格別の内訳を確認すべき"
  source_design_id: null
  created_at: "2026-03-11T00:00:00+09:00"
  YAML
  ```

  ---

  #### E2E-01: 基本探索とデータ地図提示（AC-1.1, AC-1.2）

  Claude Code で入力:

  ```
  /analysis-framing 外国人比率と犯罪率
  ```

  検証（目視）:
  - Agent tool（subagent）が呼び出される
  - subagent 内で Glob, Read, Grep が使用される（MCP ツールは使用されない）
  - `.insight/designs/`, `.insight/catalog/`, `.insight/rules/` の3ディレクトリが探索される
  - 「利用可能データ」にソース名・カラム・期間・粒度が含まれる
  - 「既存分析」にデザイン ID・ステータスが含まれる
  - 「関連知識」に注意事項（在留資格別の内訳）が含まれる
  - 「ギャップ」セクションが存在する

  #### E2E-02: Framing Brief 出力（AC-1.3, AC-3.1）

  E2E-01 の続きで入力:

  ```
  外国人比率と犯罪率の相関を、都道府県別パネルデータで検証する方向で進めよう。探索的分析でいく。
  ```

  検証（目視）:
  - `## Framing Brief` + 5つの `###` サブセクションが出力される
  - `### 推奨方向` に theme_id, parent_id, analysis_intent, 推奨手法がある
  - `/analysis-design` への遷移が提案される

  #### E2E-05: Framing Brief → analysis-design の pre-populate（AC-3.2）

  E2E-02 の直後、同じ会話で入力:

  ```
  /analysis-design
  ```

  検証（目視）:
  - Framing Brief 検出メッセージが出る
  - title, theme_id, analysis_intent の draft 値が提示される
  - ゼロからのインタビューにはならない

  #### E2E-06: Brief なしの後方互換（AC-3.3）

  **新規会話**で入力:

  ```
  /analysis-design
  ```

  検証（目視）:
  - 通常のインタビューフローが開始される（title を聞かれる）
  - 「Framing Brief を検出しました」のメッセージは出ない

  #### E2E-03: 漠然テーマの絞り込み（AC-1.4）

  **新規会話**で入力（事前に異なるジャンルのデータソースを追加しておく）:

  ```
  /analysis-framing データ分析
  ```

  検証（目視）:
  - テーマの絞り込みが求められ、2-3 の候補方向が提示される

  #### E2E-04: カタログ空の場合（AC-1.5）

  ターミナルで空のテスト環境を作成:

  ```bash
  mkdir -p /tmp/e2e-empty-catalog && cd /tmp/e2e-empty-catalog
  git init && uv run insight-blueprint init
  ```

  Claude Code で入力:

  ```
  /analysis-framing 経済成長と教育投資の関係
  ```

  検証（目視）:
  - カタログにデータがないことが報告され、`/catalog-register` が提案される

  #### E2E-07: 外部スキルなしの完全動作（AC-4.1）

  ターミナルで確認:

  ```bash
  ls .claude/skills/ | grep development-partner  # 出力なしであること
  ```

  **新規会話**で入力:

  ```
  /analysis-framing 社会問題
  ```

  検証（目視）:
  - analysis-framing が自立的にテーマ絞り込みを行う
  - `/development-partner` への遷移は提案されない

  #### E2E-08: コンテキスト引き継ぎ（AC-4.3）

  **新規会話**で入力:

  ```
  以下は問題の構造化結果です:

  ## 確定事項
  - 外国人比率と犯罪率の関係を分析したい
  - 都道府県別のパネルデータが利用可能
  - 因果関係ではなく相関分析から始めたい

  ## 未確定事項
  - どの時期のデータが適切か不明
  - 交絡変数の選定が未定

  ## 推奨方向
  - まず探索的分析で全体像を把握してから仮説を立てるべき

  上記を踏まえて、/analysis-framing を実行して
  ```

  検証（目視）:
  - 構造化結果の制約が探索に反映され、Data Map が提示される

  #### E2E-09: .insight/ 未初期化時（AC-1.1 エラーハンドリング）

  ターミナルで未初期化環境を作成:

  ```bash
  mkdir -p /tmp/e2e-no-insight && cd /tmp/e2e-no-insight
  git init
  ```

  Claude Code で入力:

  ```
  /analysis-framing 外国人比率と犯罪率
  ```

  検証（目視）:
  - `.insight/` が存在しないことが検出され、`insight-blueprint init` が案内される

  #### E2E-10: YAML 破損ファイルのスキップ（AC-1.1, AC-1.2 エラーハンドリング）

  ターミナルで壊れた YAML を追加:

  ```bash
  cd /tmp/e2e-framing-test
  cat > .insight/catalog/broken.yaml << 'EOF'
  this is: [not valid yaml
    broken: {unclosed
  EOF
  ```

  Claude Code で入力:

  ```
  /analysis-framing 外国人比率と犯罪率
  ```

  検証（目視）:
  - 壊れたファイルに対する警告が表示される
  - 正常なカタログファイルのデータが Data Map に含まれる

  ---

  **重要度分類:**
  - Critical（必須パス）: E2E-01, E2E-02, E2E-05, E2E-06
  - Important（パス推奨）: E2E-07, E2E-08, E2E-09, E2E-10
  - Nice-to-have: E2E-03, E2E-04

  - Dependencies: 3.1

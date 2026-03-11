# skill-connectivity-analysis-framing - テスト設計書

**Spec ID**: `skill-connectivity-analysis-framing`
**種別**: 新規機能（analysis-framing スキル追加 + 既存スキル Chaining 整備）

## 概要

本ドキュメントは、requirements.md の全 16 AC に対して、どのテストレベルでカバーするかを定義する。

**本 spec の特殊性**: 成果物は SKILL.md ファイル（Markdown）のみであり、Python コード（models / storage / core）の変更を含まない。そのため:
- **Unit**: SKILL.md の構造的バリデーション（Python テストで Markdown をパースし検証）
- **Integ**: 該当なし（コンポーネント間連携がない）
- **E2E**: スキルを実際に呼び出して動作を確認する手動検証シナリオ

## テストレベル定義

| テストレベル | 略称 | 説明 | ツール |
|-------------|------|------|--------|
| 単体テスト | Unit | SKILL.md の構造をパースし、必須セクション・Chaining テーブル・バージョン・フォワーディンググラフの整合性を自動検証 | pytest |
| 統合テスト | Integ | 該当なし — 本 spec は Markdown のみの成果物であり、コンポーネント間連携テストの対象がない | — |
| E2Eテスト | E2E | スキルを Claude Code 上で呼び出し、ワークフローが設計通りに動作するかを手動で確認 | Claude Code 手動実行 |

## 要件カバレッジマトリクス

### REQ-1: analysis-framing スキルの作成

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 1.1 | テーマを渡して invoke → 3ディレクトリを Glob/Read で探索 | - | - | E2E-01 | `.insight/designs/`, `.insight/catalog/`, `.insight/rules/` を探索 |
| 1.2 | 探索完了 → 4セクションのデータ地図を提示 | - | - | E2E-01 | 利用可能データ, 既存分析, 関連知識, ギャップの4セクション |
| 1.3 | 方向性合意 → Framing Brief 出力 + /analysis-design 提案 | Unit-03 | - | E2E-02 | 5セクションの Framing Brief + /analysis-design 提案 |
| 1.4 | テーマが漠然 → 2-3 候補方向を提示 | - | - | E2E-03 | 候補方向が 2-3 個提示される |
| 1.5 | カタログにデータなし → /catalog-register 提案 | - | - | E2E-04 | /catalog-register が提案される |

**備考:**
- AC-1.1, 1.2: Claude の動的挙動に依存するため自動テスト不可。SKILL.md のワークフロー記述が正しいことは Unit-01 で構造検証し、実動作は E2E-01 で手動確認
- AC-1.4, 1.5: エッジケースの動的判断。SKILL.md に条件が記述されていることは目視確認可能だが、Claude の判断品質は E2E でのみ検証可能

### REQ-2: 6スキル全体のフォワーディング表の整備

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 2.1 | 全6スキルに Chaining セクション（`\| From \| To \| When \|` テーブル） | Unit-01 | - | - | 全6スキルに Chaining セクションが存在 |
| 2.2 | reflection → framing（新仮説が必要） | Unit-02 | - | - | reflection の Chaining に framing エントリ |
| 2.3 | design → framing（データ不足） | Unit-02 | - | - | design の Chaining に framing エントリ |
| 2.4 | catalog-register → originating skill | Unit-02 | - | - | catalog-register の Chaining に framing + design エントリ |
| 2.5 | data-lineage → journal（リネージを証拠に） | Unit-02 | - | - | data-lineage の Chaining に journal エントリ |

**備考:**
- REQ-2 の全 AC は SKILL.md の静的構造で完全に検証可能。自動テストのみでカバーする

### REQ-3: フレーミングブリーフプロトコル

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 3.1 | Framing Brief に必須5セクション | Unit-03 | - | E2E-02 | テーマ, 利用可能データ, 既存分析, ギャップ, 推奨方向 |
| 3.2 | Brief あり → design が pre-populate | Unit-04 | - | E2E-05 | Step 1.5 で draft マッピング表に従い値を設定 |
| 3.3 | Brief なし → 現行フロー | Unit-04 | - | E2E-06 | Step 2 のインタビューフローが変更なく実行 |

**備考:**
- AC-3.1: SKILL.md の Step 5 出力フォーマットの構造的整合性を Unit-03 で検証。実出力の品質は E2E-02 で確認
- AC-3.2: Step 1.5 の検出ルールと draft マッピング表の存在を Unit-04 で検証。実際の pre-populate 動作は E2E-05 で確認
- AC-3.3: Step 1.5 の fallback 記述の存在を Unit-04 で検証。実際の fallback 動作は E2E-06 で確認

### REQ-4: 外部スキルとの条件付き接続

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 4.1 | development-partner なし → 完全動作 | Unit-05 | - | E2E-07 | framing が単独で方向絞り込みを実行 |
| 4.2 | development-partner あり + 分析外 → optional note | Unit-05 | - | - | Chaining に optional エントリ |
| 4.3 | development-partner → framing フォワーディング | Unit-05 | - | E2E-08 | Chaining に inbound エントリ + コンテキスト引き継ぎ |

**備考:**
- AC-4.1: SKILL.md の Step 1 にテーマ絞り込み記述があることを Unit-05 で検証。実動作は E2E-07 で確認
- AC-4.2: Chaining テーブルの記述で検証可能（構造テスト）
- AC-4.3: Chaining テーブルの構造は Unit-05 で検証。実際のコンテキスト引き継ぎ動作は E2E-08 で確認（development-partner 本体不要、会話コンテキストにフレーミング結果を事前投入してシミュレート）

---

## 単体テストシナリオ

### Unit-01: 全6スキル SKILL.md 構造検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-01 |
| **テストファイル** | `tests/skills/test_skill_structure.py` |
| **テストクラス** | `TestSkillStructure` |
| **目的** | 全6スキルの SKILL.md が必須セクションを持ち、バージョン番号が正しいことを検証 |

> **設計判断**: SKILL.md はユーザーにデプロイされるワークフローガイドであり、構造の不備はスキル実行時の失敗に直結する。Markdown のセクション構造を正規表現でパースし、自動的にドリフトを検出する。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_all_skills_have_required_sections` | 全6スキルの SKILL.md に frontmatter, When to Use, When NOT to Use, Workflow, Chaining, Language Rules セクションが存在 | 2.1 |
| `test_chaining_table_format` | 全 Chaining セクションが `\| From \| To \| When \|` ヘッダーのテーブルを含む | 2.1 |
| `test_analysis_framing_version` | analysis-framing の version が "1.0.0" | 2.1 |
| `test_existing_skills_version_bump` | 既存5スキルの version が "1.1.0" | 2.1 |

---

### Unit-02: フォワーディンググラフ双方向整合性

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-02 |
| **テストファイル** | `tests/skills/test_skill_structure.py` |
| **テストクラス** | `TestForwardingGraph` |
| **目的** | Chaining テーブルのエントリが From/To 双方の SKILL.md に存在し、フォワーディンググラフが一貫していることを検証 |

> **設計判断**: フォワーディングは双方向で定義される（From のスキルと To のスキルの両方が接続を認知している必要がある）。一方が欠落すると、ユーザーに遷移先が提案されない「片道切符」が発生する。全 Chaining テーブルをパースしてエッジリストを構築し、双方向整合性を自動検証する。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_reflection_to_framing_entry` | analysis-reflection の Chaining に `/analysis-framing` への遷移が存在 | 2.2 |
| `test_design_to_framing_entry` | analysis-design の Chaining に `/analysis-framing` への遷移が存在 | 2.3 |
| `test_catalog_register_return_entries` | catalog-register の Chaining に `/analysis-framing` と `/analysis-design` への帰り道が存在 | 2.4 |
| `test_data_lineage_to_journal_entry` | data-lineage の Chaining に `/analysis-journal` への遷移が存在 | 2.5 |
| `test_bidirectional_consistency` | 全バンドルスキル間のフォワーディングエッジについて、From 側と To 側の双方に対応エントリが存在する（外部スキル development-partner を除く） | 2.2, 2.3, 2.4, 2.5 |

---

### Unit-03: Framing Brief 出力フォーマット整合性

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-03 |
| **テストファイル** | `tests/skills/test_skill_structure.py` |
| **テストクラス** | `TestFramingBrief` |
| **目的** | analysis-framing の Step 5 に定義された Framing Brief 出力フォーマットが、必須5セクションを含み、analysis-design の Step 1.5 検出ルールと整合することを検証 |

> **設計判断**: Framing Brief はスキル間のコンテキスト受け渡しプロトコル。出力フォーマット（analysis-framing）と検出ルール（analysis-design）が乖離すると、Brief が検出されず後方互換 fallback に落ちる。双方の SKILL.md から関連テキストを抽出し、プロトコル整合性を自動検証する。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_framing_brief_has_five_sections` | analysis-framing SKILL.md の Step 5 に `## Framing Brief` + 5つの `### ` サブセクション（テーマ, 利用可能データ, 既存分析, ギャップ, 推奨方向）が定義されている | 3.1 |
| `test_framing_brief_recommended_direction_fields` | `### 推奨方向` セクションに theme_id, parent_id, analysis_intent, 推奨手法 が含まれている | 1.3, 3.1 |
| `test_framing_brief_detection_rules_match_output` | analysis-design Step 1.5 の検出条件（`## Framing Brief` 見出し + `### テーマ` + `### 推奨方向` + `theme_id:`）が、analysis-framing Step 5 の出力フォーマットで全て満たされることを検証 | 3.1 |

> **実装方針**: Markdown のセクション境界を正しく解釈する。`theme_id:` が文書内のどこかに存在するだけでは不十分。`## Framing Brief` → `### 推奨方向` の配下に `theme_id:` が存在することをセクション階層を追跡して検証する。

---

### Unit-04: analysis-design Step 1.5 検出・マッピング検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-04 |
| **テストファイル** | `tests/skills/test_skill_structure.py` |
| **テストクラス** | `TestDesignFramingBriefIntegration` |
| **目的** | analysis-design SKILL.md に Step 1.5 が存在し、draft マッピング表と fallback 記述が設計通りであることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_design_has_step_1_5` | analysis-design SKILL.md に `### Step 1.5: Check for Framing Brief` セクションが存在する | 3.2 |
| `test_design_step_1_5_has_mapping_table` | Step 1.5 に Framing Brief → analysis-design フィールドの draft マッピング表が存在する | 3.2 |
| `test_design_step_1_5_maps_methodology` | draft マッピング表に `推奨手法` → `methodology` のエントリが存在する | 3.2 |
| `test_design_step_1_5_mapping_completeness` | draft マッピング表に必須5エントリ（`theme_id`, `parent_id`, `analysis_intent`, `title`, `methodology`）が全て存在する | 3.2 |
| `test_design_step_1_5_fallback` | Step 1.5 に「Framing Brief がない場合」の fallback 記述（後方互換）が存在する | 3.3 |

---

### Unit-05: 外部スキル条件付き接続検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-05 |
| **テストファイル** | `tests/skills/test_skill_structure.py` |
| **テストクラス** | `TestExternalSkillConnectivity` |
| **目的** | analysis-framing が development-partner なしで完全に動作し、存在時のみオプショナル接続する設計を検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_framing_handles_vague_theme_independently` | analysis-framing SKILL.md の Step 1 に、テーマが漠然としている場合の自立的な絞り込み記述がある（development-partner 不要） | 4.1 |
| `test_framing_chaining_has_optional_dev_partner` | analysis-framing の Chaining テーブルに development-partner への遷移エントリが存在し、「外部スキル」「存在時のみ」の注記がある | 4.2 |
| `test_framing_chaining_has_inbound_dev_partner` | analysis-framing の Chaining テーブルに development-partner からの inbound エントリが存在する | 4.3 |

---

### Unit-06: デプロイ検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-06 |
| **テストファイル** | `tests/skills/test_skill_structure.py` |
| **テストクラス** | `TestSkillDeployment` |
| **目的** | analysis-framing ディレクトリが `src/insight_blueprint/_skills/` に存在し、`_copy_skills_template()` でデプロイ可能であることを検証 |

> **設計判断**: 既存の `_copy_skills_template()` は `_skills/` 配下の全ディレクトリを自動検出してデプロイする。新ディレクトリの存在確認とデプロイ後の `.claude/skills/analysis-framing/SKILL.md` 生成を検証する。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_analysis_framing_source_exists` | `src/insight_blueprint/_skills/analysis-framing/SKILL.md` が存在する | 2.1 |
| `test_skills_deploy_includes_analysis_framing` | `_copy_skills_template()` 実行後、`.claude/skills/analysis-framing/SKILL.md` が生成される | 2.1 |

---

## 統合テストシナリオ

> 本 spec は SKILL.md ファイルのみの成果物であり、Python コンポーネント間の連携テストは不要（Python コード変更なし）。統合テストは該当なし。

---

## E2Eテストシナリオ

> E2E テストは Claude Code 上で手動実行する。自動化は対象外（Claude の動的挙動に依存するため）。

### テストデータのセットアップ

全 E2E シナリオの事前条件として、以下のコマンドでテスト用プロジェクトを準備する。

```bash
# 1. テスト用ディレクトリを作成
mkdir -p /tmp/e2e-framing-test && cd /tmp/e2e-framing-test
git init

# 2. insight-blueprint を初期化
uv run insight-blueprint init

# 3. テスト用データソースを登録（Claude Code 上で実行）
#    → /catalog-register で以下の2つを登録:
#    - 犯罪統計データ（source_id: 0000010111, カラム: prefecture, year, crime_count, crime_rate_per_100k）
#    - 外国人登録統計（source_id: 0000010101, カラム: prefecture, year, foreign_population, foreign_ratio）

# 4. テスト用デザインを作成（Claude Code 上で実行）
#    → /analysis-design FP で以下を作成:
#    - title: "外国人比率と犯罪率の相関分析"
#    - hypothesis_statement: "外国人比率と犯罪率に正の相関はない"
#    - status: in_review

# 5. テスト用ドメイン知識を追加
#    → /analysis-reflection で以下を登録（または手動で .insight/rules/ に YAML 配置）:
#    - category: caution, content: "外国人犯罪統計は在留資格別の内訳を確認すべき"
```

> **注**: 上記はテストデータの最小セット。E2E-03（漠然テーマ）は追加で異なるジャンルのデータソースが必要。E2E-04（空カタログ）とE2E-09（未初期化）は別ディレクトリで実行する。

---

### E2E-01: analysis-framing 基本ワークフロー

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-01 |
| **テスト名** | analysis-framing 基本探索とデータ地図提示 |
| **目的** | `/analysis-framing` をテーマ付きで呼び出し、3ディレクトリ探索とデータ地図提示が行われることを確認 |
| **実行方法** | Claude Code 手動実行 |

**事前条件:**
- テストデータセットアップ済み（design 1件、catalog 2件、rules 1件以上）
- analysis-framing SKILL.md が `.claude/skills/` にデプロイ済み

**手順:**

#### 1. スキル呼び出し

Claude Code で以下を入力:

```
/analysis-framing 外国人比率と犯罪率
```

#### 2. 動作観測

以下の順序で動作を確認する:

1. Claude が **Agent tool**（subagent_type: "Explore"）を呼び出すこと
   - ツール呼び出し履歴に `Agent` が表示される
   - subagent 内で `Glob`, `Read`, `Grep` が使用される
   - `search_catalog`, `list_analysis_designs` 等の **MCP ツールは使用されない**
2. subagent が以下の3ディレクトリを探索すること:
   - `.insight/designs/*_hypothesis.yaml`
   - `.insight/catalog/*.yaml`
   - `.insight/rules/*.yaml`
3. 探索結果が **Data Map** として構造化提示されること

#### 3. 出力検証チェックリスト

Claude の出力に以下が含まれることを確認する:

- [ ] 「利用可能データ」セクションがある
  - [ ] ソース名（例: 犯罪統計データ）が記載されている
  - [ ] 主要カラム（例: crime_rate_per_100k）が記載されている
  - [ ] 期間・粒度の情報がある
- [ ] 「既存分析」セクションがある
  - [ ] デザイン ID（例: FP-H01）が記載されている
  - [ ] ステータス（例: in_review）が記載されている
- [ ] 「関連知識」セクションがある
  - [ ] ドメイン知識（例: 在留資格別の内訳を確認すべき）が記載されている
- [ ] 「ギャップ」セクションがある

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 3ディレクトリ（designs, catalog, rules）が探索される | 1.1 |
| 2 | 探索に Glob / Read / Grep ツールが使用される（MCP ツールは使用されない） | 1.1 |
| 3 | 探索が Agent tool（subagent）経由で実行される | 1.1 |
| 4 | データ地図に「利用可能データ」「既存分析」「関連知識」「ギャップ」の4セクションがある | 1.2 |
| 5 | 利用可能データにソース名・主要カラム・期間・粒度が含まれる | 1.2 |
| 6 | 既存分析にデザイン ID・ステータス・結論が含まれる | 1.2 |

> **観測方法**: Claude Code の実行ログ（ツール呼び出し履歴）で Glob/Read/Grep の使用と MCP ツール不使用を確認する。

---

### E2E-02: Framing Brief 出力

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-02 |
| **テスト名** | Framing Brief の出力と /analysis-design 提案 |
| **目的** | 方向性合意後に Framing Brief が出力され、/analysis-design が提案されることを確認 |
| **実行方法** | Claude Code 手動実行（E2E-01 の続き） |

**事前条件:**
- E2E-01 が完了し、Data Map が提示されている

**手順:**

#### 1. 方向性合意

E2E-01 の続きで、以下を入力:

```
外国人比率と犯罪率の相関を、都道府県別パネルデータで検証する方向で進めよう。探索的分析でいく。
```

#### 2. 出力検証チェックリスト

Claude の出力に以下が含まれることを確認する:

- [ ] `## Framing Brief` 見出しがある
- [ ] `### テーマ` サブセクションがある（1行要約）
- [ ] `### 利用可能データ` サブセクションがある
  - [ ] source_id とカラム情報が含まれる
- [ ] `### 既存分析` サブセクションがある
  - [ ] デザイン ID とステータスが含まれる
- [ ] `### ギャップ` サブセクションがある
- [ ] `### 推奨方向` サブセクションがある
  - [ ] `theme_id:` が含まれる（例: `FP`）
  - [ ] `parent_id:` が含まれる
  - [ ] `analysis_intent:` が含まれる（例: `exploratory`）
  - [ ] `推奨手法:` が含まれる
- [ ] `/analysis-design` への遷移が提案されている

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | `## Framing Brief` + 5サブセクションが出力される | 3.1 |
| 2 | 推奨方向に theme_id, parent_id, analysis_intent, 推奨手法が含まれる | 1.3, 3.1 |
| 3 | `/analysis-design` へのフォワーディングが提案される | 1.3 |

---

### E2E-03: 漠然としたテーマの絞り込み

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-03 |
| **テスト名** | 漠然テーマでの候補方向提示 |
| **目的** | テーマが広すぎる場合に候補方向が提示されることを確認 |
| **実行方法** | Claude Code 手動実行（新規会話） |

**事前条件:**
- `.insight/catalog/` に異なるジャンルのデータソースが3件以上存在する
  - 例: 犯罪統計、外国人統計、経済指標（GDP等）、人口統計

**手順:**

#### 1. 漠然テーマで呼び出し

新規会話で以下を入力:

```
/analysis-framing データ分析
```

#### 2. 出力検証チェックリスト

- [ ] Claude がテーマの絞り込みを求めてくる
- [ ] 2-3 の候補方向が提示される
  - [ ] 各候補が利用可能データに基づいている（空想ではない）
  - [ ] 候補ごとに簡単な説明がある
- [ ] ユーザーの選択を待つ（いきなり Data Map を出さない）

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 2-3 の候補方向が利用可能データに基づいて提示される | 1.4 |

---

### E2E-04: カタログ空の場合の catalog-register 提案

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-04 |
| **テスト名** | データなし時の catalog-register 提案 |
| **目的** | `.insight/catalog/` にデータがない場合に /catalog-register が提案されることを確認 |
| **実行方法** | Claude Code 手動実行 |

**事前条件:**
- カタログが空のプロジェクトで実行する:

```bash
# 空のテスト環境を作成
mkdir -p /tmp/e2e-empty-catalog && cd /tmp/e2e-empty-catalog
git init
uv run insight-blueprint init
# catalog は空のまま。designs/ にデザインを1件作成してもよい
```

**手順:**

#### 1. テーマ指定で呼び出し

```
/analysis-framing 経済成長と教育投資の関係
```

#### 2. 出力検証チェックリスト

- [ ] カタログにデータがないことが報告される
- [ ] `/catalog-register` への遷移が提案される
  - [ ] 具体的な提案文に `/catalog-register` が含まれる

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | `/catalog-register` が提案される | 1.5 |

---

### E2E-05: Framing Brief → analysis-design の pre-populate

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-05 |
| **テスト名** | Framing Brief 付きで analysis-design が pre-populate |
| **目的** | Framing Brief がある状態で `/analysis-design` を呼び出すと、draft 値が pre-populate されることを確認 |
| **実行方法** | Claude Code 手動実行（E2E-02 の続き） |

**事前条件:**
- E2E-02 が完了し、会話コンテキストに `## Framing Brief` が存在する

**手順:**

#### 1. analysis-design 呼び出し

E2E-02 の直後、同じ会話で以下を入力:

```
/analysis-design
```

#### 2. 出力検証チェックリスト

- [ ] Claude が「Framing Brief を検出しました」旨のメッセージを出す
- [ ] 以下の draft 値が提示される:
  - [ ] `title` の候補（Framing Brief のテーマから生成）
  - [ ] `theme_id`（Framing Brief の推奨方向から取得）
  - [ ] `parent_id`（該当する場合）
  - [ ] `analysis_intent`（exploratory / confirmatory / mixed）
  - [ ] `methodology` のデフォルト（推奨手法から取得）
- [ ] 「この内容でよいか、修正したい点があるか」の確認がある
- [ ] ゼロからの Step 2 インタビュー（title は？ hypothesis は？）にはならない

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | Framing Brief が検出され、draft 値が提示される | 3.2 |
| 2 | ユーザーに確認しながら進む（ゼロからインタビューしない） | 3.2 |

---

### E2E-06: Framing Brief なしの後方互換

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-06 |
| **テスト名** | Framing Brief なしで analysis-design の通常フロー |
| **目的** | Framing Brief なしで `/analysis-design` を呼び出した場合、現行のインタビューフローが変更なく動作することを確認 |
| **実行方法** | Claude Code 手動実行（新規会話） |

**事前条件:**
- テストデータセットアップ済みのプロジェクト
- **新規会話**（Framing Brief が存在しない）

**手順:**

#### 1. analysis-design 直接呼び出し

新規会話で以下を入力:

```
/analysis-design
```

#### 2. 出力検証チェックリスト

- [ ] Step 1: `list_analysis_designs()` で既存デザインが確認される
- [ ] Step 2: 通常のインタビューフローが開始される
  - [ ] title を聞かれる
  - [ ] hypothesis_statement を聞かれる
  - [ ] hypothesis_background を聞かれる
- [ ] 「Framing Brief を検出しました」のメッセージは**出ない**
- [ ] Step 1.5 の存在に関する言及はない

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | Step 2 のインタビューフローが変更なく実行される | 3.3 |

---

### E2E-07: development-partner なしでの完全動作

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-07 |
| **テスト名** | 外部スキルなしでの analysis-framing 完全動作 |
| **目的** | development-partner スキルがインストールされていない環境で analysis-framing が完全に動作することを確認 |
| **実行方法** | Claude Code 手動実行 |

**事前条件:**
- development-partner スキルが `.claude/skills/` に**存在しない**ことを確認:

```bash
ls .claude/skills/ | grep development-partner
# 出力なし（存在しない）であること
```

- テストデータセットアップ済み

**手順:**

#### 1. 漠然テーマで呼び出し

```
/analysis-framing 社会問題
```

#### 2. 出力検証チェックリスト

- [ ] analysis-framing が自立的にテーマ絞り込みを行う
  - [ ] 利用可能データに基づいた候補方向が提示される
- [ ] `/development-partner` への遷移は提案**されない**
- [ ] 方向性を選んだ後、Framing Brief が出力される

#### 3. 方向性選択

候補方向の1つを選び:

```
1番目の方向で進めよう
```

#### 4. 最終確認

- [ ] Framing Brief が正常に出力される
- [ ] `/analysis-design` が提案される

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | analysis-framing が単独で完全動作する（絞り込み → Data Map → Brief） | 4.1 |

---

### E2E-08: development-partner からのコンテキスト引き継ぎ

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-08 |
| **テスト名** | 外部スキルからのフレーミングコンテキスト受け取り |
| **目的** | development-partner の構造化結果が会話コンテキストにある状態で analysis-framing を呼び出し、コンテキストを引き継ぐことを確認 |
| **実行方法** | Claude Code 手動実行（新規会話） |

**事前条件:**
- テストデータセットアップ済み

**手順:**

#### 1. コンテキスト投入

新規会話で、development-partner の出力をシミュレートして以下を入力:

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

#### 2. 出力検証チェックリスト

- [ ] analysis-framing が上記の構造化結果を認識する
  - [ ] 「外国人比率と犯罪率」がテーマとして認識される
  - [ ] 「都道府県別パネルデータ」が制約として認識される
- [ ] 探索範囲が絞られている（テーマに沿った探索）
- [ ] 構造化結果の「未確定事項」がギャップとして活用される
- [ ] Data Map が提示される

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 事前コンテキストを活用して探索・フレーミングが行われる | 4.3 |

---

### E2E-09: .insight/ 未初期化時のエラーハンドリング

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-09 |
| **テスト名** | プロジェクト未初期化時の適切なエラー案内 |
| **目的** | `.insight/` ディレクトリが存在しない場合に、適切なエラーメッセージと初期化案内が表示されることを確認 |
| **実行方法** | Claude Code 手動実行 |

**事前条件:**

```bash
# 未初期化のテスト環境を作成
mkdir -p /tmp/e2e-no-insight && cd /tmp/e2e-no-insight
git init
# insight-blueprint init は実行しない（.insight/ が存在しない状態）
```

**手順:**

#### 1. スキル呼び出し

```
/analysis-framing 外国人比率と犯罪率
```

#### 2. 出力検証チェックリスト

- [ ] `.insight/` が存在しないことを検出するメッセージが出る
- [ ] `insight-blueprint init` の実行を案内するメッセージが含まれる
- [ ] 探索は実行されない（Data Map は出ない）

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 初期化案内が表示され、探索は実行されない | 1.1 |

---

### E2E-10: YAML 破損ファイルのスキップ

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-10 |
| **テスト名** | 壊れた YAML ファイルをスキップして探索継続 |
| **目的** | `.insight/` 内に壊れた YAML ファイルが混在している場合、スキップして残りのファイルで探索を継続することを確認 |
| **実行方法** | Claude Code 手動実行 |

**事前条件:**

```bash
# テストデータセットアップ済みのプロジェクトで、壊れた YAML を追加
cd /tmp/e2e-framing-test
cat > .insight/catalog/broken.yaml << 'EOF'
this is: [not valid yaml
  broken: {unclosed
EOF
```

**手順:**

#### 1. スキル呼び出し

```
/analysis-framing 外国人比率と犯罪率
```

#### 2. 出力検証チェックリスト

- [ ] 壊れたファイル（`broken.yaml`）に対する警告が表示される
- [ ] 正常なカタログファイルからのデータが Data Map に含まれる
- [ ] 探索が中断せず最後まで完了する
- [ ] Data Map の「利用可能データ」に正常なソースが表示される

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 壊れたファイルがスキップされ、警告が出る | 1.1 |
| 2 | 残りのファイルで探索が継続され、Data Map が提示される | 1.2 |

---

## E2Eテストサマリ

| テストID | テスト名 | 実行方法 | カバーするAC |
|----------|---------|----------|-------------|
| E2E-01 | 基本探索とデータ地図提示 | Claude Code 手動 | 1.1, 1.2 |
| E2E-02 | Framing Brief 出力 | Claude Code 手動 | 1.3, 3.1 |
| E2E-03 | 漠然テーマの絞り込み | Claude Code 手動 | 1.4 |
| E2E-04 | catalog-register 提案 | Claude Code 手動 | 1.5 |
| E2E-05 | Framing Brief → design pre-populate | Claude Code 手動 | 3.2 |
| E2E-06 | Brief なしの後方互換 | Claude Code 手動 | 3.3 |
| E2E-07 | 外部スキルなしの完全動作 | Claude Code 手動 | 4.1 |
| E2E-08 | 外部スキルからのコンテキスト引き継ぎ | Claude Code 手動 | 4.3 |
| E2E-09 | .insight/ 未初期化時のエラー案内 | Claude Code 手動 | 1.1 |
| E2E-10 | YAML 破損ファイルのスキップ | Claude Code 手動 | 1.1, 1.2 |

## テストファイル構成

```
tests/
└── skills/                          # SKILL.md 構造検証テスト（新規）
    └── test_skill_structure.py
        ├── TestSkillStructure         # Unit-01
        ├── TestForwardingGraph        # Unit-02
        ├── TestFramingBrief           # Unit-03
        ├── TestDesignFramingBriefIntegration  # Unit-04
        ├── TestExternalSkillConnectivity     # Unit-05
        └── TestSkillDeployment              # Unit-06
```

## 単体テストサマリ

| テストID | 対象 | カバーするAC |
|----------|------|-------------|
| Unit-01 | 6スキル SKILL.md 必須セクション・バージョン | 2.1 |
| Unit-02 | フォワーディンググラフ双方向整合性 | 2.2, 2.3, 2.4, 2.5 |
| Unit-03 | Framing Brief 出力フォーマット | 1.3, 3.1 |
| Unit-04 | analysis-design Step 1.5 検出・マッピング | 3.2, 3.3 |
| Unit-05 | 外部スキル条件付き接続 | 4.1, 4.2, 4.3 |
| Unit-06 | デプロイ検証 | 2.1 |

## カバレッジ目標

| コンポーネント | 目標カバレッジ |
|--------------|--------------|
| `tests/skills/test_skill_structure.py` | 全テストケースパス |
| 6 SKILL.md ファイル | 全必須セクション存在 |
| フォワーディンググラフ | バンドルスキル間の全エッジが双方向整合 |

> **注**: コードカバレッジ（行ベース）は本 spec には適用しない。成果物が Markdown であるため、「構造的完全性」と「プロトコル整合性」をカバレッジ指標とする。

## 成功基準

- [ ] Unit-01: 全6スキルの必須セクション存在・バージョン番号がパス
- [ ] Unit-02: フォワーディンググラフ双方向整合性がパス
- [ ] Unit-03: Framing Brief 出力フォーマット整合性がパス
- [ ] Unit-04: Step 1.5 検出・マッピング・fallback がパス
- [ ] Unit-05: 外部スキル条件付き接続がパス
- [ ] Unit-06: デプロイ検証がパス
- [ ] E2E-01: 基本探索とデータ地図が正常動作（MCP 不使用・subagent 使用を確認）
- [ ] E2E-02: Framing Brief が正しく出力される
- [ ] E2E-05: Framing Brief → analysis-design の pre-populate が動作
- [ ] E2E-06: Brief なしの後方互換が維持される
- [ ] E2E-08: 外部スキルからのコンテキスト引き継ぎが動作
- [ ] E2E-09: .insight/ 未初期化時に適切なエラー案内
- [ ] E2E-10: YAML 破損時にスキップして探索継続
- [ ] 既存テストスイート（725 tests）がリグレッションなくパス

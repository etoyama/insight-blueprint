# Plugin Distribution - テスト設計書

**Spec ID**: `plugin-distribution`
**種別**: 機能追加（配布方式移行）

## 概要

本ドキュメントは、plugin-distribution requirements の各 Acceptance Criteria に対して、どのテストレベルでカバーするかを定義する。本 spec は「削除と移動」が中心のため、**存在しないことの検証**（旧コード削除確認）と**構造の検証**（Plugin format 準拠）が主なテスト対象。

## テストレベル定義

| テストレベル | 略称 | 説明 | ツール |
|-------------|------|------|--------|
| 単体テスト | Unit | 個々のファイル構造・関数を独立してテスト | pytest |
| 統合テスト | Integ | init_project() の実行結果を検証 | pytest |
| E2Eテスト | E2E | Plugin インストール→スキル利用の全体フロー | 手動確認 |

## 要件カバレッジマトリクス

### REQ-1: Plugin Manifest の作成

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 1.1 | `claude plugin validate .` がエラー0件 | - | - | E2E-01 | バリデーション通過 |
| 1.2 | plugin.json の name と version | Unit-01 | - | - | name="insight-blueprint", version=pyproject.toml一致 |
| 1.3 | .mcp.json の定義（stdio, --project .） | Unit-02 | - | - | command=uvx, --mode なし |

### REQ-2: Skills の Plugin 自動発見への移行

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 2.1 | 7スキルが全て利用可能 | Unit-03 | - | E2E-02 | 全7スキルの SKILL.md 存在 |
| 2.2 | skills/{name}/SKILL.md 形式 | Unit-03 | - | - | ディレクトリ構造正常 |
| 2.3 | _skills/ が存在しない | Unit-04 | - | - | ディレクトリ不在 |
| 2.4 | 旧関数が削除済み | Unit-05 | - | - | 10関数が project.py に不在 |

### REQ-3: Rules の SKILL.md 統合

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 3.1 | analysis-design に workflow+yaml 統合 | Unit-06 | - | - | 両方のキーワード存在 |
| 3.2 | catalog-register に workflow 統合 | Unit-06 | - | - | キーワード存在 |
| 3.3 | _rules/ が存在しない | Unit-04 | - | - | ディレクトリ不在 |
| 3.4 | 旧関数が削除済み | Unit-05 | - | - | 2関数が project.py に不在 |
| 3.5 | CLAUDE.md に extension-policy | - | Integ-01 | - | managed section に含まれる |

### REQ-4: upgrade-templates サブコマンドの廃止

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 4.1 | コマンドが存在しない | - | Integ-02 | - | "No such command" エラー |
| 4.2 | 旧インポートが cli.py に不在 | Unit-07 | - | - | インポート文不在 |

### REQ-5: init_project の簡素化

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 5.1 | .insight/ 作成 | - | Integ-03 | - | ディレクトリ作成 |
| 5.2 | .mcp.json 登録 | - | Integ-03 | - | サーバー定義あり |
| 5.3 | CLAUDE.md に extension-policy | - | Integ-01 | - | managed section 含む |
| 5.4 | skills/rules コピーなし | - | Integ-04 | - | .claude/skills/ 未作成 |

### REQ-6: テストの更新

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 6.1 | 全テスト pass | - | - | E2E-03 | `uv run pytest` 全 pass |
| 6.2 | 旧テスト削除確認 | Unit-08 | - | - | 旧テストコード不在 |
| 6.3 | Plugin 構造テスト存在 | Unit-08 | - | - | test_plugin_structure.py 存在 |
| 6.4 | CI plugin validate | - | - | E2E-04 | CI ジョブ pass |

### REQ-7: Python パッケージレコメンド

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 7.1 | import 失敗時にレコメンド | Unit-09 | - | - | SKILL.md に Prerequisites Check セクション存在 |
| 7.2 | 承認後インストール | - | - | E2E-05 | 手動確認 |
| 7.3 | 拒否時スキップ | - | - | E2E-05 | インストールされず MCP のみ提供 |
| 7.4 | CLAUDE.md にオプショナル推奨 | - | Integ-01 | - | managed section に記載 |

### REQ-8: README の更新

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 8.1 | Plugin + PyPI 手順 | Unit-10 | - | - | README にキーワード存在 |
| 8.2 | Python パッケージ推奨 | Unit-10 | - | - | README にキーワード存在 |
| 8.3 | 移行ガイド | Unit-10 | - | - | README にキーワード存在 |

---

## 単体テストシナリオ

### Unit-01: plugin.json バリデーション

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-01 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestPluginJson` |
| **目的** | plugin.json が正しいフォーマットで存在することを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_plugin_json_exists` | `.claude-plugin/plugin.json` が存在する | 1.2 |
| `test_plugin_json_name` | name が "insight-blueprint" | 1.2 |
| `test_plugin_json_version_matches_pyproject` | version が pyproject.toml と一致 | 1.2 |
| `test_plugin_json_has_required_metadata` | description, author, repository が存在 | 1.2 |

---

### Unit-02: .mcp.json バリデーション

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-02 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestMcpJson` |
| **目的** | .mcp.json が stdio トランスポート前提で正しく定義されていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_mcp_json_exists` | `.mcp.json` が存在する | 1.3 |
| `test_mcp_json_has_insight_blueprint_server` | mcpServers.insight-blueprint が定義されている | 1.3 |
| `test_mcp_json_command_is_uvx` | command が "uvx" | 1.3 |
| `test_mcp_json_no_mode_flag` | args に "--mode" が含まれない（stdio 保証） | 1.3 |
| `test_mcp_json_has_project_arg` | args に "--project" と "." が含まれる | 1.3 |
| `test_mcp_json_no_secrets` | env に API キー・パスワード等が含まれない | NFR-Security |

---

### Unit-03: Skills ディレクトリ構造

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-03 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestSkillsDirectory` |
| **目的** | skills/ 配下に全7スキルが正しい構造で配置されていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_all_skills_exist` | 7スキル全てに SKILL.md が存在する（parametrize） | 2.1, 2.2 |
| `test_skill_md_has_frontmatter` | 各 SKILL.md に name と description のフロントマターがある | 2.2 |
| `test_skill_md_has_version` | 各 SKILL.md に version がある | 2.2 |

> **設計判断**: `@pytest.mark.parametrize` で7スキル名をパラメータ化し、1テスト関数で全スキルをカバーする。

---

### Unit-04: 旧ディレクトリの不存在確認

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-04 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestLegacyRemoval` |
| **目的** | 旧配布メカニズムのディレクトリが完全に削除されていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_old_skills_dir_removed` | `src/insight_blueprint/_skills/` が存在しない | 2.3 |
| `test_old_rules_dir_removed` | `src/insight_blueprint/_rules/` が存在しない | 3.3 |

---

### Unit-05: 旧関数の削除確認

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-05 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestCodeRemoval` |
| **目的** | storage/project.py から旧配布関連コードが削除されていることを検証 |

> **設計判断**: `ast.parse` でソースコードを解析し、削除対象の関数定義が存在しないことを確認する。grep ではなく AST を使うことで、コメント内の関数名と実際の定義を区別できる。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_skills_copy_functions_removed` | `_copy_skills_template`, `_discover_bundled_skills`, `_hash_skill_directory`, `_hash_skill_directory_from_traversable`, `_collect_traversable_entries`, `_copy_skill_tree`, `_save_skill_state`, `_load_skill_state`, `_write_bundled_update`, `_get_skill_version_from_traversable` が project.py に定義されていない | 2.4 |
| `test_rules_copy_functions_removed` | `_copy_rules_template`, `_discover_bundled_rules` が project.py に定義されていない | 3.4 |

---

### Unit-06: Rules の SKILL.md 統合確認

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-06 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestRulesIntegration` |
| **目的** | Rules の内容が対応する SKILL.md に統合されていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_analysis_design_has_workflow_rules` | analysis-design/SKILL.md に "Workflow Rules" セクションが存在する | 3.1 |
| `test_analysis_design_has_yaml_reference` | analysis-design/SKILL.md に "YAML Format" に関する内容が存在する | 3.1 |
| `test_catalog_register_has_workflow_rules` | catalog-register/SKILL.md に "Workflow Rules" セクションが存在する | 3.2 |

---

### Unit-07: cli.py の旧インポート削除確認

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-07 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestCliCleanup` |
| **目的** | cli.py から旧配布関連のインポートが削除されていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_cli_no_legacy_imports` | cli.py に `_copy_skills_template`, `_copy_rules_template`, `_discover_bundled_skills`, `_discover_bundled_rules` のインポートが存在しない | 4.2 |

---

### Unit-08: テストファイル構成の検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-08 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestTestStructure` |
| **目的** | 旧テストが削除され、新テストが追加されていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_plugin_structure_test_exists` | `tests/test_plugin_structure.py` が存在する | 6.3 |
| `test_old_skill_copy_tests_removed` | テストファイル群に `_copy_skills_template` をテストするコードが存在しない | 6.2 |

> **備考**: テストファイルの存在を検証するテスト自体が `test_plugin_structure.py` 内にあるのは自己参照的だが、CI でテストスイート全体が pass することで AC-6.1 をカバーする。

---

### Unit-09: data-lineage SKILL.md の Prerequisites Check

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-09 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestDataLineagePrerequisites` |
| **目的** | data-lineage SKILL.md に Python パッケージレコメンドロジックが含まれていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_data_lineage_has_prerequisites_check` | data-lineage/SKILL.md に "Prerequisites Check" セクションが存在する | 7.1 |
| `test_data_lineage_mentions_uv_add` | data-lineage/SKILL.md に `uv add insight-blueprint` の記述がある | 7.1 |

---

### Unit-10: README の内容検証

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-10 |
| **テストファイル** | `tests/test_plugin_structure.py` |
| **テストクラス** | `TestReadme` |
| **目的** | README に Plugin インストール手順、PyPI 手順、移行ガイドが含まれていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_readme_has_plugin_install` | README に `claude plugin install` の記述がある | 8.1 |
| `test_readme_has_pypi_install` | README に `uvx insight-blueprint` の記述がある | 8.1 |
| `test_readme_has_optional_python_package` | README に Python パッケージのオプショナル推奨が記載されている | 8.2 |
| `test_readme_has_migration_guide` | README に移行ガイド（`.claude/skills/` クリーンアップ）が記載されている | 8.3 |

---

## 統合テストシナリオ

### Integ-01: init_project() の CLAUDE.md 生成

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-01 |
| **テストファイル** | `tests/test_storage.py` |
| **テストクラス** | `TestInitProject` |
| **目的** | init_project() が CLAUDE.md managed section に extension-policy とオプショナルパッケージ推奨を含むことを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_init_project_claude_md_has_extension_policy` | CLAUDE.md managed section に "Extension Policy" が含まれる | 3.5, 5.3 |
| `test_init_project_claude_md_has_optional_package_note` | CLAUDE.md managed section に Python パッケージのオプショナル推奨が含まれる | 7.4 |

---

### Integ-02: upgrade-templates コマンドの不在確認

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-02 |
| **テストファイル** | `tests/test_storage.py` |
| **テストクラス** | `TestCliCommands` |
| **目的** | upgrade-templates コマンドが削除されていることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_upgrade_templates_command_not_exists` | Click の `main.commands` に `upgrade-templates` が存在しない | 4.1 |
| `test_upgrade_templates_cli_execution_fails` | Click test runner で `upgrade-templates` を実行すると exit code != 0 かつ stderr に "No such command" を含む | 4.1 |

---

### Integ-03: init_project() の基本動作

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-03 |
| **テストファイル** | `tests/test_storage.py` |
| **テストクラス** | `TestInitProject` |
| **目的** | init_project() が .insight/ と .mcp.json を正しく作成することを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_init_project_creates_insight_dirs` | `.insight/designs/`, `.insight/catalog/knowledge/`, `.insight/rules/` が作成される | 5.1 |
| `test_init_project_registers_mcp_server` | `.mcp.json` に insight-blueprint サーバーが登録される | 5.2 |
| `test_init_project_idempotent` | init_project() を2回実行しても .mcp.json の重複エントリや CLAUDE.md の重複セクションが発生しない | 5.1, 5.2, 5.3 |

---

### Integ-04: init_project() が skills/rules コピーをしないことの確認

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-04 |
| **テストファイル** | `tests/test_storage.py` |
| **テストクラス** | `TestInitProject` |
| **目的** | init_project() が skills や rules のコピー処理を行わないことを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_init_project_does_not_copy_skills` | init_project() 実行後に `.claude/skills/` が作成されていない | 5.4 |
| `test_init_project_does_not_copy_rules` | init_project() 実行後に `.claude/rules/` が作成されていない | 5.4 |

---

## E2Eテストシナリオ

### E2E-01: Plugin Validate

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-01 |
| **テスト名** | Plugin バリデーション |
| **目的** | `claude plugin validate .` がエラー0件で通ることを検証 |
| **実行方法** | 手動確認（claude CLI 必要） |

**手順:**
1. `claude plugin validate .` を実行
2. 出力にエラーがないことを確認

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | バリデーションエラー 0 件 | 1.1 |

---

### E2E-02: Plugin インストール後のスキル利用

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-02 |
| **テスト名** | Plugin スキル自動発見 |
| **目的** | Plugin インストール後に全スキルが Claude Code で利用可能であることを検証 |
| **実行方法** | 手動確認 |

**事前条件:**
1. `claude plugin marketplace add etoyama/insight-blueprint`
2. `claude plugin install insight-blueprint`

**手順:**
1. Claude Code を起動
2. `/analysis-design` を実行し、スキルが認識されることを確認
3. `/data-lineage` を実行し、スキルが認識されることを確認

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 全7スキルが利用可能 | 2.1 |

---

### E2E-03: 全テスト pass

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-03 |
| **テスト名** | pytest 全テスト pass |
| **目的** | `uv run pytest` が全テスト pass することを検証 |
| **実行方法** | CI / 手動 |

**手順:**
1. `uv run pytest -v` を実行

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | 全テスト pass、failure 0 | 6.1 |

---

### E2E-04: CI Plugin Validate ジョブ

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-04 |
| **テスト名** | CI plugin-validate ジョブ |
| **目的** | CI の plugin-validate ジョブが正常に動作することを検証 |
| **実行方法** | GitHub Actions |

**手順:**
1. PR を作成し CI を実行
2. plugin-validate ジョブの結果を確認

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | ジョブが pass（またはCLI不在で skip） | 6.4 |

---

### E2E-05: data-lineage Python パッケージレコメンド

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-05 |
| **テスト名** | Python パッケージの初回レコメンド |
| **目的** | Plugin インストール後に /data-lineage を使った際、Python パッケージのインストールが提案されることを検証 |
| **実行方法** | 手動確認 |

**事前条件:**
1. Plugin がインストールされている
2. `insight-blueprint` Python パッケージが**インストールされていない**環境

**手順:**
1. `/data-lineage` を実行
2. Claude が `uv add insight-blueprint` を提案することを確認
3. 承認してインストールを実行
4. `/data-lineage` を再度実行し、tracked_pipe が利用可能であることを確認

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | Claude が `uv add insight-blueprint` を提案する | 7.1 |
| 2 | 承認後にインストールされ tracked_pipe が利用可能 | 7.2 |
| 3 | 拒否した場合、インストールされず MCP ツール経由の操作のみ提供される | 7.3 |

---

## テストファイル構成

```
tests/
├── test_plugin_structure.py    # NEW: Plugin 構造検証 (Unit-01〜Unit-10)
├── test_storage.py             # MODIFY: init_project テスト更新 (Integ-01〜Integ-04)
├── test_skill_update.py        # DELETE: 旧 skills コピーテスト
├── test_skill_integration.py   # DELETE: 旧 skills 統合テスト
└── (既存テストは変更なし)
```

## 単体テストサマリ

| テストID | 対象 | カバーするAC |
|----------|------|-------------|
| Unit-01 | plugin.json | 1.2 |
| Unit-02 | .mcp.json | 1.3, NFR-Security |
| Unit-03 | skills/ ディレクトリ | 2.1, 2.2 |
| Unit-04 | 旧ディレクトリ不在 | 2.3, 3.3 |
| Unit-05 | 旧関数不在 (AST) | 2.4, 3.4 |
| Unit-06 | Rules 統合 | 3.1, 3.2 |
| Unit-07 | cli.py インポート | 4.2 |
| Unit-08 | テストファイル構成 | 6.2, 6.3 |
| Unit-09 | data-lineage Prerequisites | 7.1 |
| Unit-10 | README 内容 | 8.1, 8.2, 8.3 |

## 統合テストサマリ

| テストID | 対象コンポーネント | カバーするAC |
|----------|-------------------|-------------|
| Integ-01 | init_project → CLAUDE.md | 3.5, 5.3, 7.4 |
| Integ-02 | CLI コマンド一覧 | 4.1 |
| Integ-03 | init_project → .insight/ + .mcp.json | 5.1, 5.2 |
| Integ-04 | init_project → skills/rules 非コピー | 5.4 |

## E2Eテストサマリ

| テストID | テスト名 | 実行方法 | カバーするAC |
|----------|---------|----------|-------------|
| E2E-01 | Plugin Validate | 手動 (claude CLI) | 1.1 |
| E2E-02 | Plugin スキル自動発見 | 手動 | 2.1 |
| E2E-03 | pytest 全テスト pass | CI / 手動 | 6.1 |
| E2E-04 | CI plugin-validate | GitHub Actions | 6.4 |
| E2E-05 | Python パッケージレコメンド | 手動 | 7.1, 7.2, 7.3 |

## カバレッジ目標

| コンポーネント | 目標カバレッジ |
|--------------|--------------|
| `tests/test_plugin_structure.py` | 全テストケース pass |
| `tests/test_storage.py`（init_project 部分） | 90%以上 |
| `storage/project.py`（変更後） | 80%以上 |

## 成功基準

- [ ] Unit-01〜Unit-10: 全テストケースが pass
- [ ] Integ-01〜Integ-04: 全テストケースが pass
- [ ] E2E-01: `claude plugin validate .` がエラー0件
- [ ] E2E-02: 全7スキルが Plugin 経由で利用可能
- [ ] E2E-03: `uv run pytest` が全 pass
- [ ] E2E-04: CI plugin-validate ジョブが pass/skip
- [ ] E2E-05: Python パッケージレコメンドが動作

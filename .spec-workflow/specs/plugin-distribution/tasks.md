# Tasks: Plugin Distribution

- [x] 1.1. Plugin manifest ファイルの作成
  - File: `.claude-plugin/plugin.json`, `.mcp.json`
  - Purpose: Claude Code Plugin として認識されるための manifest と MCP 定義を作成する
  - Leverage: 現行 `_register_mcp_server()` の args（同一形式）
  - Requirements: REQ-1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Plugin Developer | Task: `.claude-plugin/plugin.json` を作成（name="insight-blueprint", version=pyproject.toml と一致, description, author, repository, license, keywords）。`.mcp.json` を作成（command=uvx, args=["insight-blueprint", "--project", "."], env=`{"PYTHONUNBUFFERED": "1", "MCP_TIMEOUT": "10000"}`）。--mode フラグは含めない（stdio トランスポート） | Restrictions: plugin.json に MCP/Skills 定義を書かない。.mcp.json に secrets を含めない | Success: 両ファイルが存在し、design.md の Component 1 の仕様に準拠

- [x] 1.2. Plugin 構造検証テストの作成（RED）
  - File: `tests/test_plugin_structure.py`
  - Purpose: Plugin 構造を検証するテストを先に書く（TDD Red フェーズ）
  - Leverage: pytest, `pyproject.toml` からの version 読み取り
  - Requirements: REQ-6 (FR-6.5, FR-6.6, FR-6.7)
  - Dependencies: 1.1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Test Engineer | Task: test-design.md の Unit-01〜Unit-05, Unit-07, Integ-02〜Integ-04 に対応するテストを `tests/test_plugin_structure.py` と `tests/test_storage.py` に実装する。test_plugin_structure.py: TestPluginJson（plugin.json 存在・name・version 一致・metadata）、TestMcpJson（存在・server 定義・uvx・--mode 不在・secrets 不在）、TestSkillsDirectory（7スキル SKILL.md 存在・frontmatter）、TestLegacyRemoval（_skills/ _rules/ 不存在）、TestCodeRemoval（AST 解析で削除対象関数の定義不在）、TestCliCleanup（cli.py に旧インポート不在）。test_storage.py: init_project の簡素化テスト（Integ-02〜04）。version 一致は `tomllib` で pyproject.toml を読み plugin.json と比較。secrets チェックは env キーに token/secret/apikey/password を含まないことを検証 | Restrictions: テストは現時点で大半が fail する（移行前のため）。それが正しい Red 状態 | Success: テストが実行可能で、未移行の項目が適切に fail する

- [x] 2.1. Skills ディレクトリの移動
  - File: `skills/` (リポジトリルート)
  - Purpose: `_skills/` から `skills/` への移動。Plugin 自動発見の対象にする
  - Leverage: 既存の `_skills/` ディレクトリ構造
  - Requirements: REQ-2 (FR-2.1, FR-2.2)
  - Dependencies: 1.2
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Developer | Task: `src/insight_blueprint/_skills/` 配下の全7スキルを `skills/` (リポジトリルート) に移動する。各スキルは `skills/{name}/SKILL.md` の構造を維持。analysis-framing のように references/ や examples/ サブディレクトリを持つスキルはサブディレクトリごと移動。`git mv` を使用 | Restrictions: SKILL.md の内容はまだ変更しない（Rules 統合は次タスク）。`_skills/` ディレクトリはまだ削除しない | Success: `skills/` 配下に7スキル全ての SKILL.md が存在し、Unit-03 テストが pass

- [x] 2.2. Rules の SKILL.md 統合
  - File: `skills/analysis-design/SKILL.md`, `skills/catalog-register/SKILL.md`
  - Purpose: Rules ファイルの内容を対応する SKILL.md に統合する
  - Leverage: `_rules/analysis-workflow.md`, `_rules/catalog-workflow.md`, `_rules/insight-yaml.md`
  - Requirements: REQ-3 (FR-3.1, FR-3.2, FR-3.3)
  - Dependencies: 2.1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Developer | Task: (1) `analysis-workflow.md` の内容を `skills/analysis-design/SKILL.md` に `## Workflow Rules` セクションとして末尾に追加。(2) `insight-yaml.md` の内容を `skills/analysis-design/SKILL.md` に `## YAML Format Reference` セクションとして末尾に追加。(3) `catalog-workflow.md` の内容を `skills/catalog-register/SKILL.md` に `## Workflow Rules` セクションとして末尾に追加。(4) 統合対象スキルの version を patch bump（例: 1.1.0 → 1.2.0） | Restrictions: extension-policy.md はここでは扱わない（タスク 3.2 で対応）。既存の SKILL.md 内容を変更しない、末尾にセクション追加のみ | Success: Unit-06 テストが pass

- [x] 2.3. data-lineage SKILL.md に Prerequisites Check 追加
  - File: `skills/data-lineage/SKILL.md`
  - Purpose: Python パッケージの初回レコメンドロジックを SKILL.md に記述する
  - Leverage: design.md Component 7 の仕様
  - Requirements: REQ-7 (FR-7.1, FR-7.2, FR-7.3)
  - Dependencies: 2.1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Developer | Task: `skills/data-lineage/SKILL.md` の Workflow セクションの冒頭（既存の Step 1 の前）に `### Step 0: Python Package Check` を追加。design.md Component 7 の仕様に従い、import チェック → レコメンド → 承認/拒否フローを記述 | Restrictions: MCP ツール経由の操作（Mermaid 出力等）は Python パッケージなしでも利用可能であることを明記 | Success: Unit-09 テストが pass

- [x] 3.1. storage/project.py から配布コードを削除
  - File: `src/insight_blueprint/storage/project.py`
  - Purpose: Skills/Rules コピー関連の全関数を削除し init_project() を簡素化する
  - Leverage: design.md Component 4 の削除対象一覧
  - Requirements: REQ-2 (FR-2.5〜2.8), REQ-3 (FR-3.6〜3.8), REQ-5
  - Dependencies: 2.1, 2.2
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer | Task: `storage/project.py` から以下を削除: `_copy_skills_template()`, `_get_skill_version_from_traversable()`, `_hash_skill_directory_from_traversable()`, `_collect_traversable_entries()`, `_copy_skill_tree()`, `_save_skill_state()`, `_load_skill_state()`, `_write_bundled_update()`, `_discover_bundled_skills()`, `_hash_skill_directory()`, `_get_skill_version()`, `_parse_version_from_content()`, `_hash_entries()`, `_discover_bundled_rules()`, `_copy_rules_template()` および関連定数。`init_project()` を3行に簡素化（`_create_insight_dirs` + `_register_mcp_server` + `_generate_claude_md` のみ）。不要になったインポート（`packaging.version`, `Traversable` 等）を削除 | Restrictions: `_register_mcp_server()`, `_generate_claude_md()`, `_create_insight_dirs()`, `_load_template()`, `_hash_content()`, CLAUDE.md 関連関数は残す。`shutil` は `_register_mcp_server` 内で使用されている場合残す | Success: Unit-05 テストが pass。`init_project()` が3つの関数呼び出しのみ

- [x] 3.2. CLAUDE.md テンプレートに extension-policy を統合
  - File: `src/insight_blueprint/_templates/CLAUDE.md.template`
  - Purpose: managed section に extension-policy とオプショナルパッケージ推奨を含める
  - Leverage: `_rules/extension-policy.md` の内容
  - Requirements: REQ-3 (FR-3.4, FR-3.9), REQ-7 (FR-7.4)
  - Dependencies: 3.1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Developer | Task: `_templates/CLAUDE.md.template` を更新。(1) extension-policy.md の内容を managed section 内に `## Extension Policy` セクションとして追加。(2) `## Optional: Python Package` セクションを追加し、`uv add insight-blueprint` がオプショナルだが分析パイプライン透明性のために推奨である旨を記載 | Restrictions: 既存の managed section マーカー形式を維持 | Success: Integ-01 テストが pass

- [x] 3.3. 旧 _skills/ と _rules/ ディレクトリの削除 + pyproject.toml 検証
  - File: `src/insight_blueprint/_skills/`, `src/insight_blueprint/_rules/`, `pyproject.toml`
  - Purpose: 旧配布ディレクトリを完全に削除し、wheel ビルドから除外されていることを検証する
  - Leverage: なし
  - Requirements: REQ-2 (FR-2.3, FR-2.4), REQ-3 (FR-3.5)
  - Dependencies: 2.2, 3.1, 3.2
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Developer | Task: (1) `src/insight_blueprint/_skills/` ディレクトリを `git rm -r` で削除。(2) `src/insight_blueprint/_rules/` ディレクトリを `git rm -r` で削除（`__init__.py` 含む）。(3) `pyproject.toml` の `[tool.hatch.build]` を確認し、`skills/`（リポジトリルート）が wheel に含まれないことを検証。現行の `packages = ["src/insight_blueprint"]` 設定では `_skills/` 削除後に自動的に wheel から除外される。`skills/` はリポジトリルートにあるため wheel に含まれないが、念のため確認 | Restrictions: `skills/` (リポジトリルート) に移動済みであることを確認してから削除。pyproject.toml の packages 設定は変更不要（現行設定で正しい） | Success: Unit-04 テストが pass。`uv build` で wheel を作成し、wheel 内に `_skills/` が含まれないことを確認

- [x] 4.1. cli.py の upgrade-templates コマンド削除
  - File: `src/insight_blueprint/cli.py`
  - Purpose: 廃止されたサブコマンドと関連インポートを削除する
  - Leverage: design.md Component 5
  - Requirements: REQ-4
  - Dependencies: 3.1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer | Task: `cli.py` から `upgrade_templates` 関数全体（約115行）を削除。関連インポート文（`_copy_skills_template`, `_copy_rules_template`, `_discover_bundled_skills`, `_discover_bundled_rules`, `_get_skill_version_from_traversable`, `_hash_content`, `_hash_skill_directory`, `_load_claude_md_state`, `_load_skill_state`, `_parse_version_from_content`）を削除 | Restrictions: `main` コマンドグループや他のサブコマンドに影響しない | Success: Unit-07 テストと Integ-02 テストが pass

- [x] 4.2. 旧テストの削除と init_project テストの更新
  - File: `tests/test_skill_update.py`, `tests/test_skill_integration.py`, `tests/test_storage.py`
  - Purpose: 旧配布テストを削除し、init_project テストを新仕様に合わせる
  - Leverage: test-design.md の Integ-01〜Integ-04
  - Requirements: REQ-6 (FR-6.1〜6.4)
  - Dependencies: 3.1, 3.3, 4.1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Test Engineer | Task: (1) `test_skill_update.py` から `_copy_skills_template` 関連テストを削除（ファイルが空になる場合はファイルごと削除）。(2) `test_skill_integration.py` から skills コピー統合テストを削除。(3) `test_storage.py` の `TestInitProject` を更新: init_project が .insight/ と .mcp.json を作成し CLAUDE.md managed section に extension-policy を含むことを検証。.claude/skills/ と .claude/rules/ が作成されないことを検証。冪等性テスト（2回実行で重複なし）を追加。(4) upgrade_templates 関連テストを削除 | Restrictions: 既存の他テストに影響しない | Success: Integ-01〜Integ-04, Unit-08 テストが pass。`uv run pytest` が全 pass

- [x] 5.1. README.md の更新
  - File: `README.md`
  - Purpose: Plugin インストール手順、オプショナル Python パッケージ、移行ガイドを追加する
  - Leverage: design.md Component 8
  - Requirements: REQ-8
  - Dependencies: 1.1, 2.1
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical Writer | Task: README.md に以下のセクションを追加/更新: (1) Plugin Installation（推奨方法: `claude plugin marketplace add etoyama/insight-blueprint` → `claude plugin install insight-blueprint`）。(2) Classic Installation（従来方法: `uvx insight-blueprint --project .`）。(3) Optional: Python Package（data-lineage の tracked_pipe 用。オプショナルだが分析の透明性のために推奨）。(4) Migration Guide（既存ユーザー向け: 旧 `.claude/skills/` のクリーンアップ方法） | Restrictions: 既存の README 内容を破壊しない | Success: Unit-10 テストが pass

- [x] 5.2. CI に plugin-validate ジョブを追加
  - File: `.github/workflows/ci.yml`
  - Purpose: Plugin manifest の CI 検証ゲートを追加する
  - Leverage: design.md の CI Testing セクション
  - Requirements: REQ-6 (FR-6.8)
  - Dependencies: 1.1（1.1 完了後すぐ着手可能。他タスクと並列可）
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CI/CD Engineer | Task: `.github/workflows/ci.yml` に `plugin-validate` ジョブを追加。tag push (v*) 時のみ実行。`claude plugin validate .` を実行し、CLI 不在時は `::warning::` で skip。design.md の CI Testing セクションの YAML 仕様に従う | Restrictions: 既存の python, frontend ジョブに影響しない。plugin-validate は他ジョブの required check にしない | Success: AC-6.4 を満たす CI 設定

- [x] 5.3. GitHub issue 起票（将来対応）
  - File: なし（GitHub API）
  - Purpose: Out of Scope の将来対応項目を issue として起票する
  - Requirements: Out of Scope セクション
  - Dependencies: なし
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Project Manager | Task: 以下の2つの GitHub issue を起票する: (1) `_register_mcp_server()` の将来削除 — Plugin 方式の普及後に init_project() のフォールバック MCP 登録を削除。(2) `_generate_claude_md()` の将来削除 — extension-policy の配布を Plugin hooks に移行後に削除。ラベル: `enhancement`, `future` | Restrictions: 対応は将来。本 spec のスコープ外 | Success: 2つの issue が作成されている

- [x] 6.1. 全テスト実行・最終検証
  - File: なし
  - Purpose: 全テストが pass し、ruff/ty チェックが通ることを確認する
  - Requirements: REQ-6 (AC-6.1)
  - Dependencies: 全タスク
  - Prompt: Implement the task for spec plugin-distribution, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA Engineer | Task: (1) `uv run pytest -v` で全テスト pass を確認。(2) `uv run ruff check .` で lint エラー0件を確認。(3) `uv run ruff format --check .` でフォーマットチェック。(4) 可能なら `claude plugin validate .` を実行し E2E-01 を確認 | Restrictions: テスト失敗があれば該当タスクを修正してから完了とする | Success: 全テスト pass、lint/format pass、Plugin validate pass

# Requirements: Plugin Distribution

## Introduction

insight-blueprint の配布方式を、現行の独自コピー方式から Claude Code Plugin 方式に移行する。現行は `_skills/` → `.claude/skills/` へのファイルコピーとハッシュベースのバージョン管理を自前実装しているが、Claude Code v2.1.80 で Plugin システムが Stable になったため、プラットフォームのライフサイクル管理に乗せて自前コードを削減する。

### Plugin が配布するもの / しないもの

Plugin は以下の2つを配布する:

1. **Skills (SKILL.md)** — Claude Code が使うスキル定義。Plugin の `skills/` ディレクトリから自動発見される
2. **MCP サーバー定義 (.mcp.json)** — `.mcp.json` の `"command": "uvx"` により、MCP サーバーは `uvx` の隔離環境で自動起動される。ユーザーが `pip install` / `uv add` する必要はない

Plugin が直接配布**しない**もの:

3. **Python ライブラリとしての import** — `data-lineage` スキルは `from insight_blueprint.lineage import tracked_pipe` をユーザーのノートブック/スクリプト内で使用する。この import にはユーザーのプロジェクト Python 環境への `uv add insight-blueprint` が別途必要

ただし、ユーザー体験をシンプルにするため、**初回起動時に Python パッケージのインストールを自動レコメンドする**（REQ-7）。Plugin をインストールして最初の分析を始める際に、Claude が `uv add insight-blueprint` を提案し、ユーザーが承認すればそのまま利用可能になる。

つまり、MCP ツール (17個) とスキル (7個) は Plugin だけで完全に動作する。`data-lineage` の `tracked_pipe` はオプショナルだが、分析の透明性を担保するために推奨される。

### Alignment with Product Vision

Product Principle #1「Claude Code First」に直結する。Claude Code のネイティブ Plugin システムを採用することで、Claude Code エコシステムとの統合を深め、ユーザーの導入障壁を下げる。

## Requirements

### REQ-1: Plugin Manifest の作成

**User Story:** As a plugin maintainer, I want insight-blueprint repository to be recognized as a Claude Code plugin, so that users can install it via `claude plugin install`.

#### Functional Requirements

- FR-1.1: リポジトリルートに `.claude-plugin/plugin.json` を配置する
- FR-1.2: plugin.json は Claude Code Plugin format に準拠する（name, version, description, author, repository, license, keywords）
- FR-1.3: リポジトリルートに `.mcp.json` を配置し、insight-blueprint MCP サーバーの起動コマンドを定義する。トランスポートは stdio（デフォルト `full` モード）を使用する。`--mode headless`（SSE）は Plugin の command/args 形式と非互換のため使用しない
- FR-1.4: `claude plugin validate .` でバリデーションが通ること

#### Acceptance Criteria

- AC-1.1: WHEN `claude plugin validate .` を実行 THEN バリデーションエラーが 0 件である
- AC-1.2: WHEN `.claude-plugin/plugin.json` を読み込む THEN name が "insight-blueprint" であり、version が pyproject.toml の version と一致する
- AC-1.3: WHEN `.mcp.json` を読み込む THEN mcpServers.insight-blueprint が定義されており、command が "uvx"、args に "insight-blueprint" と "--project" と "." を含む（`--mode` 指定なし = デフォルト full モード = stdio トランスポート）

### REQ-2: Skills の Plugin 自動発見への移行

**User Story:** As a plugin user, I want skills to be automatically discovered when the plugin is installed, so that I don't need to run any setup commands for skills.

#### Functional Requirements

- FR-2.1: `src/insight_blueprint/_skills/` 配下の全7スキルを `skills/` (リポジトリルート) に移動する
- FR-2.2: 各スキルは `skills/{skill-name}/SKILL.md` の構造を維持する
- FR-2.3: `_skills/` ディレクトリを削除する
- FR-2.4: pyproject.toml の wheel ビルドから `_skills/` 関連の設定を除去する（現行は `packages` に含まれている）
- FR-2.5: `_copy_skills_template()` および関連ヘルパー関数を `storage/project.py` から削除する
- FR-2.6: `_discover_bundled_skills()` を削除する
- FR-2.7: `.skill_state.json` 関連の読み書き関数を削除する
- FR-2.8: `init_project()` から `_copy_skills_template()` の呼び出しを削除する

#### Acceptance Criteria

- AC-2.1: WHEN Plugin をインストールした環境で Claude Code を起動 THEN 7個のスキル（analysis-design, analysis-framing, analysis-journal, analysis-reflection, analysis-revision, catalog-register, data-lineage）が全て利用可能である
- AC-2.2: WHEN `skills/` ディレクトリの構造を確認 THEN 各スキルが `skills/{name}/SKILL.md` の形式で配置されている
- AC-2.3: WHEN `src/insight_blueprint/_skills/` のパスを確認 THEN ディレクトリが存在しない
- AC-2.4: WHEN `storage/project.py` を確認 THEN `_copy_skills_template`, `_discover_bundled_skills`, `_hash_skill_directory`, `_hash_skill_directory_from_traversable`, `_collect_traversable_entries`, `_copy_skill_tree`, `_save_skill_state`, `_load_skill_state`, `_write_bundled_update`, `_get_skill_version_from_traversable` 関数が存在しない

### REQ-3: Rules の SKILL.md 統合

**User Story:** As a plugin user, I want all workflow rules to be included in the relevant skill definitions, so that rules are automatically available when skills are installed.

#### Functional Requirements

- FR-3.1: `analysis-workflow.md` の内容を `skills/analysis-design/SKILL.md` に統合する
- FR-3.2: `catalog-workflow.md` の内容を `skills/catalog-register/SKILL.md` に統合する
- FR-3.3: `insight-yaml.md` の内容を `skills/analysis-design/SKILL.md` に統合する
- FR-3.4: `extension-policy.md` は CLAUDE.md managed section に残す（横断ポリシーのため特定スキルに紐づかない）
- FR-3.5: `_rules/` ディレクトリを削除する
- FR-3.6: `_copy_rules_template()` および関連ヘルパー関数を `storage/project.py` から削除する
- FR-3.7: `_discover_bundled_rules()` を削除する
- FR-3.8: `init_project()` から `_copy_rules_template()` の呼び出しを削除する
- FR-3.9: CLAUDE.md テンプレートを更新し、extension-policy の内容を managed section に含める

#### Acceptance Criteria

- AC-3.1: WHEN `skills/analysis-design/SKILL.md` を読み込む THEN analysis-workflow.md と insight-yaml.md の内容が含まれている
- AC-3.2: WHEN `skills/catalog-register/SKILL.md` を読み込む THEN catalog-workflow.md の内容が含まれている
- AC-3.3: WHEN `src/insight_blueprint/_rules/` のパスを確認 THEN ディレクトリが存在しない
- AC-3.4: WHEN `storage/project.py` を確認 THEN `_copy_rules_template`, `_discover_bundled_rules` 関数が存在しない
- AC-3.5: WHEN `init_project()` 実行後の CLAUDE.md を確認 THEN managed section に extension-policy の内容が含まれている

### REQ-4: upgrade-templates サブコマンドの廃止

**User Story:** As a maintainer, I want to remove the upgrade-templates CLI command, so that the codebase doesn't contain dead code for a deprecated distribution mechanism.

#### Functional Requirements

- FR-4.1: `cli.py` の `upgrade_templates` コマンドを削除する
- FR-4.2: 削除された関数のインポート文を cli.py から除去する
- FR-4.3: upgrade-templates に関連するテストを削除する

#### Acceptance Criteria

- AC-4.1: WHEN `insight-blueprint upgrade-templates` を実行 THEN "No such command" エラーが返る
- AC-4.2: WHEN `cli.py` を確認 THEN `_copy_skills_template`, `_copy_rules_template`, `_discover_bundled_skills`, `_discover_bundled_rules` のインポートが存在しない

### REQ-5: init_project の簡素化

**User Story:** As a user who doesn't use the Plugin system, I want init_project to still create .insight/ directories and register the MCP server, so that the basic functionality works without plugins.

#### Functional Requirements

- FR-5.1: `init_project()` は `_create_insight_dirs()`, `_register_mcp_server()`, `_generate_claude_md()` のみを呼び出す
- FR-5.2: `_register_mcp_server()` は現行の `.mcp.json` upsert ロジックを維持する
- FR-5.3: `_generate_claude_md()` は managed section に extension-policy を含むよう CLAUDE.md テンプレートを更新する

#### Acceptance Criteria

- AC-5.1: WHEN `init_project()` を実行 THEN `.insight/` ディレクトリが作成される
- AC-5.2: WHEN `init_project()` を実行 THEN `.mcp.json` に insight-blueprint サーバーが登録される
- AC-5.3: WHEN `init_project()` を実行 THEN CLAUDE.md の managed section に extension-policy の内容が含まれる
- AC-5.4: WHEN `init_project()` を実行 THEN skills や rules のコピー処理は行われない

### REQ-6: テストの更新

**User Story:** As a developer, I want tests to reflect the new distribution mechanism, so that regressions are caught.

#### Functional Requirements

- FR-6.1: `_copy_skills_template` 関連テストを削除する
- FR-6.2: `_copy_rules_template` 関連テストを削除する
- FR-6.3: `upgrade_templates` コマンドのテストを削除する
- FR-6.4: `init_project()` のテストを更新し、skills/rules コピーが行われないことを検証する
- FR-6.5: Plugin ディレクトリ構造の検証テストを追加する（`skills/` 配下の SKILL.md 存在確認）
- FR-6.6: `plugin.json` のバリデーションテストを追加する
- FR-6.7: `.mcp.json`（Plugin ルート）のバリデーションテストを追加する
- FR-6.8: CI に `claude plugin validate .` を追加し、Plugin manifest の整合性をリリースゲートとする

#### Acceptance Criteria

- AC-6.1: WHEN `uv run pytest` を実行 THEN 全テストが pass する
- AC-6.2: WHEN テストを確認 THEN `_copy_skills_template`, `_copy_rules_template` をテストするコードが存在しない
- AC-6.3: WHEN テストを確認 THEN Plugin 構造（plugin.json, .mcp.json, skills/ 配下の SKILL.md）を検証するテストが存在する
- AC-6.4: WHEN CI を実行 THEN `claude plugin validate .` がパスする（CI 環境に claude CLI がない場合は skip）

### REQ-7: Python パッケージの初回インストールレコメンド

**User Story:** As a plugin user, I want to be prompted to install the insight-blueprint Python package on first use, so that I can use data-lineage tracking without manual setup.

#### Functional Requirements

- FR-7.1: `data-lineage` スキルの SKILL.md に、初回利用時の Python パッケージ検出・レコメンドロジックを記述する
- FR-7.2: スキルは Claude に対し、`import insight_blueprint.lineage` が失敗した場合に `uv add insight-blueprint` をユーザーに提案するよう指示する
- FR-7.3: ユーザーが承認した場合のみインストールを実行する（自動インストールはしない）
- FR-7.4: CLAUDE.md managed section に、Python パッケージのインストールがオプショナルだが推奨である旨を記載する

#### Acceptance Criteria

- AC-7.1: WHEN Plugin インストール後に `/data-lineage` を初めて使用 AND `insight_blueprint.lineage` が import できない THEN Claude がユーザーに `uv add insight-blueprint` の実行を提案する
- AC-7.2: WHEN ユーザーが提案を承認 THEN `uv add insight-blueprint` が実行され、以降 `tracked_pipe` が利用可能になる
- AC-7.3: WHEN ユーザーが提案を拒否 THEN インストールは行われず、`data-lineage` スキルは `tracked_pipe` なしで可能な範囲の機能（MCP ツール経由の操作）のみ提供する
- AC-7.4: WHEN CLAUDE.md を確認 THEN managed section に Python パッケージがオプショナルだが分析の透明性のために推奨である旨が記載されている

### REQ-8: README の更新

**User Story:** As a potential user, I want clear installation instructions in the README, so that I understand the Plugin installation method and the optional Python package.

#### Functional Requirements

- FR-8.1: README.md に Plugin インストール手順を追加する（`claude plugin marketplace add` → `claude plugin install`）
- FR-8.2: README.md に Python パッケージはオプショナルだが、data-lineage（分析パイプラインの透明性追跡）のために推奨である旨を明記する
- FR-8.3: 現行の導入手順（`uvx insight-blueprint --project .`）も引き続き記載する
- FR-8.4: 既存ユーザーの移行ガイドを記載する（旧 `.claude/skills/` にコピー済みのスキルとの共存・クリーンアップ方法）

#### Acceptance Criteria

- AC-8.1: WHEN README.md を読む THEN Plugin インストール手順と PyPI インストール手順の両方が記載されている
- AC-8.2: WHEN README.md を読む THEN Python パッケージがオプショナルだが推奨である理由（分析の透明性）が説明されている
- AC-8.3: WHEN README.md を読む THEN 既存ユーザー向けの移行手順（旧 `.claude/skills/` のクリーンアップ方法）が記載されている

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility Principle**: Plugin manifest（plugin.json）、MCP 定義（.mcp.json）、スキル定義（SKILL.md）は各々独立したファイルとして管理する
- **Code Reduction**: `storage/project.py` から Skills/Rules コピー関連コードを削除し、ファイルの行数を約400行削減する
- **Single Source of Truth**: Skills の定義は `skills/` ディレクトリのみ。PyPI wheel への同梱と Plugin ディレクトリの二重管理を排除する

### Performance

- `init_project()` の実行時間が短縮される（skills/rules コピーが不要になるため）
- Plugin インストールは `claude plugin install` の標準的な速度に依存する

### Security

- `.mcp.json` に secrets を含めない（環境変数で管理）
- Plugin manifest に不要な permissions を宣言しない

### Reliability

- Plugin 未使用ユーザーは `init_project()` 経由で引き続き MCP サーバー登録と CLAUDE.md 生成が可能
- 既存の `.insight/` データディレクトリは一切変更しない

### Usability

- Plugin ユーザーの導入手順: `claude plugin marketplace add etoyama/insight-blueprint` → `claude plugin install insight-blueprint`（2コマンド）。初回の `/data-lineage` 利用時に Claude が Python パッケージのインストールを自動レコメンドする
- Plugin 未使用ユーザーの導入手順は現行と同一（`uvx insight-blueprint --project .`）

## Out of Scope

- Marketplace リポジトリの作成（insight-blueprint 本体リポジトリを直接 marketplace source として使用）
- Hooks の Plugin 配布（hooks/hooks.json の作成は将来対応）
- Agents の Plugin 配布（agents/ ディレクトリの作成は将来対応）
- WebUI の変更（Extension Policy に基づき変更なし）
- `_register_mcp_server()` の削除（Plugin 未使用ユーザーのフォールバックとして維持） → **GitHub issue を起票し将来対応とする**
- `_generate_claude_md()` の削除（extension-policy の配布先として維持） → **GitHub issue を起票し将来対応とする**
- PyPI パッケージの廃止（MCP サーバー本体は引き続き PyPI で配布。Plugin は Skills + MCP 定義の配布のみ）
- `analysis-framing` スキルの references/ や examples/ ディレクトリの移行（SKILL.md のみ移行。サブディレクトリがある場合はそのまま skills/ 配下にコピー）

## Glossary

| Term | Definition |
|------|------------|
| Plugin | Claude Code のプラグイン。`.claude-plugin/plugin.json` を持つディレクトリ |
| plugin.json | Plugin のメタデータファイル。name, version, description 等を定義 |
| .mcp.json | MCP サーバーの起動コマンドを定義する JSON ファイル。Plugin ルートに配置 |
| Marketplace | Claude Code Plugin の配布元。GitHub リポジトリを登録可能 |
| Skills 自動発見 | Claude Code が `skills/` ディレクトリの SKILL.md を自動認識する仕組み |
| Managed Section | CLAUDE.md 内の insight-blueprint が管理するセクション。マーカーで囲まれた領域 |
| init_project | `insight-blueprint --project .` 実行時に呼ばれる初期化関数 |

# SPEC-1: core-foundation — 設計

> **Spec ID**: SPEC-1
> **Status**: pending_approval
> **Created**: 2026-02-18
> **Source**: DESIGN.md v1.1.0

---

## 概要

SPEC-1 は insight-blueprint のコア基盤を確立する。データサイエンティストが
`uvx insight-blueprint --project /path` の1コマンドで起動できるゼロインストール MCP サーバーであり、
CLI エントリポイント・`.insight/` ディレクトリ初期化・Pydantic データモデル・アトミック YAML 永続化・
3つの MCP ツール（`create_analysis_design`、`get_analysis_design`、`list_analysis_designs`）を実装する。
これにより Claude Code は手動のファイルシステム操作なしに、仮説駆動型の分析設計書を管理できるようになる。

## ステアリングドキュメントとの整合

### 技術標準（tech.md）

本設計は以下の技術標準に従う:

- **MCP サーバー**: fastmcp>=2.0、stdio トランスポート（Claude Code ローカル統合の標準）
- **ストレージ**: コメント保持のために ruamel.yaml を使用、アトミック書き込みには `tempfile.mkstemp()` + `os.replace()`
- **品質ツール**: ruff（lint/format、line-length 88）、ty（型チェック、mypy の代替）、pytest（カバレッジ 80%+ 目標）
- **開発方法論**: TDD（Red-Green-Refactor）と YAGNI — SPEC-1 が要求する実装のみ行う。WebUI やデーモンスレッドは対象外
- **プロセスモデル**: `mcp.run()` はメインスレッドをブロックする（MCP プロトコルは stdin/stdout 経由）。uvicorn デーモンスレッドは SPEC-4 のスコープ

### プロジェクト構造（structure.md）

`src/` レイアウト規約と 3 層分離に従う:

- **src/insight_blueprint/** — トップレベルパッケージ（`__init__.py` と `__main__.py`）
- **3 層アーキテクチャ**: `cli.py` → `server.py` → `core/designs.py` → `storage/`
- **単方向依存**: CLI → MCP → Core → Storage。逆方向の依存は禁止
- **SPEC-1 で作成するモジュール**: `cli.py`、`server.py`、`models/design.py`、`models/common.py`、`storage/yaml_store.py`、`storage/project.py`、`core/designs.py`
- **重要な不変条件**: `mcp.run()` は常に `cli.py` の最後の呼び出し。すべての YAML 書き込みはアトミック。`_service` は MCP ツール呼び出し前に `init_project()` で初期化される

## コード再利用分析

### 活用できる既存コンポーネント

SPEC-1 は最初のスペックであるため、活用できる既存のアプリケーションコードは存在しない。
以下の外部ライブラリが基盤的な構成要素を提供する:

- **fastmcp**: `@mcp.tool()` デコレータによる MCP ツール登録と stdio トランスポート
- **Pydantic v2 BaseModel**: `AnalysisDesign` の型安全なデータモデリング、シリアライゼーション、バリデーション
- **ruamel.yaml**: アナリストのコメントを保持した YAML 読み書き（pyyaml はコメントを削除するため不採用）
- **click**: `@click.command()` と `@click.option()` による CLI 引数パース

### 統合ポイント

- **Claude Code `.mcp.json`**: `init_project()` は project root の `.mcp.json` に MCP サーバーエントリを登録し、次回起動時に Claude Code が自動検出できるようにする
- **SPEC-2 以降**: `storage/yaml_store.py` と `storage/project.py` は拡張される。`server.py` は既存ツールを変更せずに `@mcp.tool()` が追加登録される。`core/designs.py` のパターンはカタログ・ルールモジュールに複製される

## アーキテクチャ

### モジュラー設計原則

- **ファイル単一責任**: 各ファイルは1つの関心事のみを担当（`cli.py` = エントリポイント、`server.py` = MCP ツール、`core/designs.py` = ビジネスロジック、`storage/yaml_store.py` = YAML I/O）
- **コンポーネント分離**: 各層は独立してテスト可能。`core/designs.py` は `server.py` や `cli.py` をインポートせずにユニットテストできる
- **サービス層分離**: MCP ツール（`server.py`）は `DesignService`（`core/designs.py`）に委譲し、`DesignService` は `yaml_store.py` に委譲する。層をスキップした呼び出しは禁止
- **ユーティリティのモジュール化**: `models/common.py` は共有ユーティリティ（`now_jst()`）のみを保持する。他のモジュールに混在させない

### コンポーネント図（SPEC-1 スコープ）

```
Claude Code (AI Client)
       |
  stdio (MCP Protocol)
       |
  +---------------------------+
  |  insight-blueprint        |
  |  (Python Process)         |
  |                           |
  |  cli.py (entry point)     |
  |    ├── init_project()     |
  |    └── mcp.run() ← BLOCKS |
  |                           |
  |  server.py (FastMCP)      |
  |    ├── create_analysis_design  |
  |    ├── get_analysis_design     |
  |    └── list_analysis_designs   |
  |           ↓               |
  |  core/designs.py          |
  |           ↓               |
  |  storage/yaml_store.py    |
  |  storage/project.py       |
  +---------------------------+
           ↓
  .insight/
    ├── config.yaml          (schema_version: 1)
    ├── catalog/
    │   ├── sources.yaml
    │   └── knowledge/
    ├── designs/*.yaml
    └── rules/
        ├── review_rules.yaml
        └── analysis_rules.yaml
  .mcp.json  (upserted at project root; machine-specific, gitignore recommended)
  .claude/skills/analysis-design/  (copied from package on first run only)
```

### 設計決定: stdio トランスポート

fastmcp の `mcp.run()` は stdio トランスポートを使用する。これが正しい選択である理由:
- Claude Code の `claude mcp add` はローカル統合においてデフォルトで stdio を想定する
- ネットワーク設定不要・ポート競合なし
- `mcp.run()` がメインスレッドをブロックするのは意図的な設計

SPEC-4 でデーモンスレッド上に uvicorn を追加する。SPEC-1 には HTTP サーバーは存在しない。

### 設計決定: テンプレート配布にシンボリックリンクではなくコピーを使用

`shutil.copytree()` を使用して、バンドルされた `_skills/analysis-design/` テンプレートを
`.claude/skills/analysis-design/` に初回実行時にコピーする。シンボリックリンクを明示的に避ける理由:

- `uvx` はバージョン固有のパス（`~/.cache/uv/.../<version>/`）にパッケージをキャッシュする。シンボリックリンクは新バージョンへのアップグレード時に無通知で破損する
- Windows ではシンボリックリンクの作成に管理者権限が必要なため、クロスプラットフォーム移植性の問題になる
- コピー（上書きしない）により、初回実行後にユーザーが行ったカスタマイズが保護される

テンプレートのアップグレードは **SPEC-1 のスコープ外**。将来の `insight-blueprint upgrade-templates` コマンドで対応する（別の GitHub Issue として追跡）。

### 設計決定: `.mcp.json` への `.gitignore` 推奨

`init_project()` は `.mcp.json` の `mcpServers["insight-blueprint"]` キーのみを upsert し、
他のサーバー登録を保持する。`args` に格納される絶対プロジェクトパスはマシン固有であるため:

- 他の開発者のマシンで動作しないマシン固有パスのコミットを防ぐため、**`.mcp.json` は `.gitignore` に追加すべき**
- 将来の改善（GitHub Issue として追跡）として、`.mcp.json` を git で共有可能にするために相対パス `"."` の使用を検討するが、SPEC-1 では簡潔さと正確性のために絶対パスを使用する

## コンポーネントとインターフェース

### `cli.py`

- **目的:** CLI エントリポイント — `--project` と `--headless` オプションをパースし、project path の存在を検証し、`init_project()` を呼び出し、`mcp.run()` で MCP サーバーを起動する。`--headless` は SPEC-1 では no-op（SPEC-4 のブラウザ起動抑制用に予約）
- **インターフェース:** `main(project: str, headless: bool) -> None`（click コマンド、`insight-blueprint` コンソールスクリプトとして登録）
- **依存関係:** `click`、`storage/project.py:init_project`、`server.py:mcp`
- **再利用:** なし（依存チェーンの最初のモジュール）

### `server.py`

- **目的:** FastMCP サーバー — 3つの非同期 MCP ツールを登録し、`init_project()` が `mcp.run()` 呼び出し前に初期化するモジュールレベルの `_service` 参照を保持する
- **インターフェース:** `create_analysis_design(title, hypothesis_statement, hypothesis_background, parent_id?, theme_id: str = "DEFAULT") -> dict`、`get_analysis_design(design_id) -> dict`、`list_analysis_designs(status?) -> dict`（すべて非同期、`@mcp.tool()` デコレータ付き）
- **依存関係:** `fastmcp.FastMCP`、`core/designs.py:DesignService`
- **再利用:** なし

### `models/common.py`

- **目的:** 共有タイムゾーンユーティリティ — すべての Pydantic モデルで使用される JST タイムゾーン対応の datetime デフォルト値を提供する `now_jst()` を実装
- **インターフェース:** `now_jst() -> datetime`
- **依存関係:** `zoneinfo.ZoneInfo`
- **再利用:** なし

### `models/design.py`

- **目的:** Pydantic データモデル — `DesignStatus` Enum と、すべての必須フィールドおよび JST タイムゾーンデフォルトを持つ `AnalysisDesign` BaseModel を定義
- **インターフェース:** `DesignStatus`（5値の str Enum）、`AnalysisDesign`（10フィールドの BaseModel: `theme_id: str = "DEFAULT"` フィールドを含む）
- **依存関係:** `pydantic.BaseModel`、`pydantic.Field`、`models/common.py:now_jst`
- **再利用:** なし

### `storage/project.py`

- **目的:** プロジェクト初期化 — アーティファクトごとのべき等初期化。`.insight/` ディレクトリツリー（`designs/`、`catalog/`（`sources.yaml` と `knowledge/`）、`rules/`（`review_rules.yaml` と `analysis_rules.yaml`）、`config.yaml`（`schema_version` 付き））を作成する。不在時のみパッケージから `.claude/skills/analysis-design/` テンプレートをコピー（ユーザーカスタマイズ保護のため上書きしない）。バンドルされた `_skills/analysis-design/SKILL.md` は Claude Code スキル仕様の YAML frontmatter（`name`, `description`, `disable-model-invocation: true`, `argument-hint: "[theme_id]"`）を含み、MCP ツールリファレンス・エラーハンドリング・言語ルールを記載すること。既存サーバーを保持しつつ project root の `.mcp.json` にサーバーエントリを upsert する（アトミック書き込み）。`DesignService` を `server._service` に接続する
- **インターフェース:** `init_project(project_path: Path) -> None`
- **依存関係:** `pathlib.Path`、`shutil`、`json`、`core/designs.py:DesignService`、`server._service`
- **再利用:** なし

### `storage/yaml_store.py`

- **目的:** アトミック YAML I/O — `tempfile.mkstemp()` + `os.replace()` を使用してクラッシュセーフな読み書き操作を提供し、部分書き込みを防止する
- **インターフェース:** `read_yaml(path: Path) -> dict`、`write_yaml(path: Path, data: dict) -> None`
- **依存関係:** `ruamel.yaml.YAML`、`tempfile`、`os`
- **再利用:** なし

### `core/designs.py`

- **目的:** 分析設計 CRUD のビジネスロジック — テーマ別独立連番 ID 生成（FP-H01、TX-H01 等）、作成、取得、ステータスフィルタリングによる一覧取得を管理する
- **インターフェース:** `DesignService(project_path: Path)` — メソッド: `create_design(title, hypothesis_statement, hypothesis_background, parent_id?, theme_id: str = "DEFAULT") -> AnalysisDesign`、`get_design(design_id) -> AnalysisDesign | None`、`list_designs(status?) -> list[AnalysisDesign]`
  - `create_design` は theme_id が `[A-Z][A-Z0-9]*` に一致しない場合 `ValueError` を raise する
- **依存関係:** `models/design.py:AnalysisDesign`、`storage/yaml_store.py:read_yaml, write_yaml`
- **再利用:** なし

## データモデル

### ファイル: `.insight/designs/{id}_hypothesis.yaml`

```yaml
id: FP-H01
theme_id: FP
title: Foreign population vs crime rate correlation
hypothesis_statement: No positive correlation exists between...
hypothesis_background: |
  ...
status: draft
parent_id: null
metrics: {}
created_at: "2026-02-18T10:00:00+09:00"
updated_at: "2026-02-18T10:00:00+09:00"
```

- ID 生成: `{THEME_ID}-H{N:02d}`（テーマ内の既存 ID の最大 N + 1。削除後も衝突しない）
- ファイル名: `{THEME_ID}-H{N:02d}_hypothesis.yaml`（例: `FP-H01_hypothesis.yaml`）
- `theme_id` 省略時は `"DEFAULT"` を使用（例: `DEFAULT-H01`）
- `theme_id` 許容パターン: `[A-Z][A-Z0-9]*`（英大文字始まり、英大文字・数字のみ）
- 不正値は `ValueError` を raise する（server.py で error dict に変換）

## エラーハンドリング

### エラーシナリオ

1. **設計が見つからない** — `get_analysis_design("FP-H99")` で FP-H99 が存在しない場合
   - **ハンドリング:** `DesignService.get_design()` が `None` を返す。`server.py` が `{"error": "Design 'FP-H99' not found"}` に変換する
   - **ユーザーへの影響:** Claude はエラー dict を受け取り、設計 ID が存在しないことをアナリストに伝えられる

2. **無効な project path** — CLI に `--project /nonexistent` を渡した場合
   - **ハンドリング:** 初期化より前に、人間が読めるメッセージとともに `click.ClickException` が発生する
   - **ユーザーへの影響:** エラーメッセージが stderr に出力され、exit code 1 で終了する。部分的な状態は作成されない

3. **YAML 書き込み失敗** — `write_yaml()` 実行中に I/O エラーが発生した場合
   - **ハンドリング:** `os.replace()` は呼び出されない。`except` ブロックで tempfile がクリーンアップされる。元の YAML は変更されない
   - **ユーザーへの影響:** `create_analysis_design()` が例外を発生させる。Claude がストレージエラーを報告し、アナリストはリトライできる

4. **サービスが初期化されていない** — `init_project()` より前に MCP ツールが呼び出された場合
   - **ハンドリング:** `get_service()` が `RuntimeError("Service not initialized. Call init_project() first.")` を発生させる
   - **ユーザーへの影響:** MCP プロトコルがエラーレスポンスを返す。`cli.py` は常に `mcp.run()` の前に `init_project()` を呼び出すため、テスト/開発シナリオでのみ発生しうる

5. **破損した `.mcp.json`** — project root の `.mcp.json` が有効な JSON としてパースできない場合
   - **ハンドリング:** `json.JSONDecodeError` を捕捉し、ファイルパスを含む `click.ClickException` として再送出する。ユーザーに JSON を手動修正するか、バックアップを作成してファイルを削除してからリトライするよう案内する
   - **ユーザーへの影響:** project 初期化が exit code 1 で中断される。元の破損ファイルは変更されない。修復または置換の操作可能なガイダンスをユーザーに提供する

6. **無効な theme_id** — `create_analysis_design()` に `"fp"` や `"FP/X"` などを渡した場合
   - **ハンドリング:** `DesignService.create_design()` が `ValueError` を raise する。`server.py` が `{"error": "Invalid theme_id 'fp': must match [A-Z][A-Z0-9]*"}` に変換する
   - **ユーザーへの影響:** Claude がエラー dict を受け取り、theme_id のフォーマットを修正するようアナリストに案内できる

## テスト戦略

### ユニットテスト

テストはモジュール境界ごとに整理される:

| ファイル | カバレッジ対象 |
|---------|--------------|
| `tests/test_designs.py` | `core/designs.py` + `models/design.py` |
| `tests/test_storage.py` | `storage/yaml_store.py` + `storage/project.py` |
| `tests/test_cli.py` | `cli.py`（click CLI 引数パース） |
| `tests/test_server.py` | `server.py`（MCP tool 層の dict 変換） |

**test_designs.py のテストケース:**
- `test_create_design_returns_design_with_generated_id` — ハッピーパス
- `test_create_design_saves_yaml_file` — ファイルシステム副作用
- `test_create_design_sequential_ids` — FP-H01、FP-H02、FP-H03 の順序
- `test_get_design_returns_correct_design` — ラウンドトリップ
- `test_get_design_returns_none_for_missing_id` — 未発見
- `test_list_designs_returns_all` — 複数の設計
- `test_list_designs_filtered_by_status` — ステータスフィルタ
- `test_create_design_with_theme_id_uses_theme_prefix` — theme_id 付き ID 生成（例: `FP-H01`）
- `test_create_design_in_different_themes_number_independently` — 異なるテーマ（FP・TX）で H01 が独立して連番される
- `test_create_design_with_invalid_theme_id_raises_value_error` — "fp"、"FP/X"、"1FP" などが ValueError を raise する

**test_storage.py のテストケース:**
- `test_write_yaml_creates_file` — 基本的な書き込み
- `test_write_yaml_is_atomic` — 失敗時のクリーンアップ
- `test_read_yaml_returns_empty_for_missing_file` — 欠落ファイルの安全な処理
- `test_init_project_creates_directory_structure` — `.insight/` ツリーのべき等作成
- `test_init_project_creates_catalog_sources_yaml` — init 後に `catalog/sources.yaml` スタブが存在する
- `test_init_project_creates_catalog_knowledge_dir` — init 後に `catalog/knowledge/` ディレクトリが存在する
- `test_init_project_creates_rules_yaml_stubs` — `review_rules.yaml` と `analysis_rules.yaml` の両方が存在する
- `test_init_project_creates_config_with_schema_version` — `config.yaml` に `schema_version: 1` が含まれる
- `test_init_project_copies_skills_template_when_absent` — 初回実行時に `.claude/skills/analysis-design/` が作成される
- `test_init_project_does_not_overwrite_existing_skills` — 既存の `.claude/skills/analysis-design/` は変更されない
- `test_init_project_copies_skill_has_valid_frontmatter` — コピーされた SKILL.md に `---` 区切りの YAML frontmatter が存在し、`name` と `description` キーを含む
- `test_init_project_registers_mcp_json_when_absent` — `.mcp.json` が存在しない場合に `mcpServers.insight-blueprint` が作成される
- `test_init_project_merges_existing_mcp_json` — 他のサーバーエントリを持つ既存の `.mcp.json` は保持され、`insight-blueprint` キーのみ追加/更新される
- `test_init_project_does_not_modify_if_already_registered` — `insight-blueprint` が既に登録済みの場合、init の再実行で他のキーが変更されたり不必要な書き込みが発生したりしない
- `test_init_project_partial_recovery` — 部分的な失敗後に init を再実行した場合、既存のものには触れず欠落したアーティファクトのみ作成される

**test_cli.py のテストケース:**
- `test_cli_default_project_uses_cwd` — `--project` 省略時にカレントディレクトリが使用される（AC-1-2 対応）
- `test_cli_nonexistent_project_exits_with_error` — 存在しないパスで exit code 1 で終了する（AC-1-3 対応）

**test_server.py のテストケース:**
- `test_create_analysis_design_returns_dict_with_id_and_status` — `{"id": "FP-H01", "status": "draft", ...}` の dict 形式での返却確認（AC-2-1 対応）
- `test_get_analysis_design_returns_error_dict_for_missing_id` — 存在しない ID に対してエラー dict を返却（例外でない）（AC-2-3 対応）
- `test_list_analysis_designs_returns_count_field` — `count` フィールドが存在し結果数と一致する（AC-2-4 対応）
- `test_get_service_raises_when_not_initialized` — 初期化前の呼び出しで `RuntimeError` が発生する（エラーシナリオ 4 対応）
- `test_create_analysis_design_returns_error_dict_for_invalid_theme_id` — 不正 theme_id に対してエラー dict が返る（例外でない）（AC-2-6 対応）

**テストインフラ** (`tests/conftest.py`):

```python
@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Returns a temporary project directory with .insight/ initialized."""
    from insight_blueprint.storage.project import init_project
    init_project(tmp_path)
    return tmp_path
```

### インテグレーションテスト

- CLI から CRUD までのラウンドトリップ: `init_project()` → `create_analysis_design()` → YAML ファイル作成を確認 → `get_analysis_design()` → データ一致を確認 → `list_analysis_designs()` → 件数とステータスフィルタを確認
- `tests/test_integration.py` に実装（タスク 1.6 で実装）
- 実際の `tmp_path` フィクスチャを使用してテストを実行。ストレージ層はモックしない

### E2E テスト

MCP プロトコルの E2E テスト（実際の MCP クライアントを stdio サーバーに接続する）は **SPEC-1 のスコープ外**。
`test_integration.py` のインテグレーションテストがビジネスロジックスタック全体をエンドツーエンドでカバーする。
fastmcp stdio テストハーネスが利用可能になった将来のスペックで MCP プロトコルの完全な E2E テストに対応する。

### 受け入れ基準 × テストケース 対応表

requirements.md に定義された全 AC と、それをカバーするテストケースの対応を以下に示す:

| AC | 内容（要約） | 対応テストケース | テストファイル |
|----|-------------|----------------|--------------|
| AC-1-1 | `--project /path` → `.insight/` 作成 + stdio 起動 | `test_init_project_creates_directory_structure` | `test_storage.py` |
| AC-1-2 | `--project` 省略 → cwd 使用 | `test_cli_default_project_uses_cwd` | `test_cli.py` |
| AC-1-3 | `--project /nonexistent` → exit 1 | `test_cli_nonexistent_project_exits_with_error` | `test_cli.py` |
| AC-1-4 | 2回実行でデータ破損しない（べき等） | `test_init_project_partial_recovery`、`test_init_project_does_not_modify_if_already_registered` | `test_storage.py` |
| AC-2-1 | `create_analysis_design()` → dict 返却 + YAML 保存 | `test_create_analysis_design_returns_dict_with_id_and_status`、`test_create_design_saves_yaml_file` | `test_server.py`、`test_designs.py` |
| AC-2-2 | `get_analysis_design("FP-H01")` → ラウンドトリップ | `test_get_design_returns_correct_design` | `test_designs.py` |
| AC-2-3 | `get_analysis_design("FP-H99")` → error dict（例外でない） | `test_get_analysis_design_returns_error_dict_for_missing_id` | `test_server.py` |
| AC-2-4 | `list_analysis_designs(status="draft")` → `count` 一致 | `test_list_analysis_designs_returns_count_field`、`test_list_designs_filtered_by_status` | `test_server.py`、`test_designs.py` |
| AC-2-5 | YAML 書き込み中クラッシュ → 元ファイル保全 | `test_write_yaml_is_atomic` | `test_storage.py` |
| AC-2-6 | 不正 theme_id → error dict（例外でない） | `test_create_analysis_design_returns_error_dict_for_invalid_theme_id` | `test_server.py` |

> **注記**: AC-1-1 の stdio 起動部分は MCP プロトコル E2E テストが必要なため SPEC-1 のスコープ外とする。
> ディレクトリ作成のストレージ側はユニットテストでカバーする。

---

## 依存関係（SPEC-1 のみ）

```toml
[project]
dependencies = [
    "fastmcp>=2.0",
    "pydantic>=2.10",
    "ruamel.yaml>=0.18",
    "click>=8.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=6.0",
    "ruff>=0.8",
    "ty>=0.1",
    "poethepoet>=0.31",
]
```

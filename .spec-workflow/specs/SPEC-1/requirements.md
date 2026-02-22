# SPEC-1: core-foundation — Requirements

> **Spec ID**: SPEC-1
> **Feature Name**: core-foundation
> **Status**: pending_approval
> **Created**: 2026-02-18
> **Depends On**: none (first spec)

---

## Introduction

SPEC-1 establishes the core foundation of insight-blueprint — a zero-install MCP server
that data scientists can launch with a single `uvx insight-blueprint --project /path` command.
It covers CLI entry point, `.insight/` directory initialization, Pydantic data models,
atomic YAML persistence, and three MCP tools for managing hypothesis-driven analysis design
documents. After SPEC-1 is complete, Claude Code can call `create_analysis_design()`,
`get_analysis_design()`, and `list_analysis_designs()` to persist and retrieve structured
YAML documents without manual file system access.

## Alignment with Product Vision

This spec directly enables the three core product goals defined in `product.md`:

- **Lightweight analysis design docs**: Provides the `create_analysis_design()` MCP tool
  and YAML storage layer that Claude Code uses to persist structured hypothesis documents
  without the heavy overhead of spec-driven development workflows.
- **Zero-install distribution**: Implements the `uvx insight-blueprint --project /path`
  entry point and `.mcp.json` registration so data scientists can start an MCP-enabled
  EDA session without a manual install step.
- **Spec Roadmap foundation**: All subsequent specs (SPEC-2 through SPEC-5) extend the
  modules and patterns established here; SPEC-1 is a prerequisite for every later spec.

## Requirements

### Requirement 1: CLI起動とプロジェクト初期化

**User Story:** As a data scientist using Claude Code, I want to run
`uvx insight-blueprint --project /path/to/analysis` once and have `.insight/` initialized
and Claude Code ready to call MCP tools immediately, so that I can start my EDA session
without manual setup.

**FR-1: CLI Entry Point**
- `uvx insight-blueprint --project <path>` で MCP server を起動する
- `--project` を省略した場合はカレントディレクトリをデフォルトとする
- `--headless` flag でブラウザ起動を抑制する（自動化・CI 用途）
- project path が存在しない場合、意味のあるエラーメッセージを表示して終了する

**FR-2: Project 初期化**
- 初回実行時に `.insight/` ディレクトリ構造を作成する（idempotent — 複数回実行しても安全）
- ディレクトリ構造:
  ```
  .insight/
  ├── config.yaml
  ├── catalog/
  │   ├── sources.yaml
  │   └── knowledge/
  ├── designs/
  └── rules/
      ├── review_rules.yaml
      └── analysis_rules.yaml
  ```
- 初回実行時に `.claude/skills/` テンプレートをコピーする（`.claude/skills/analysis-design/` が存在しない場合のみ）
  - バンドルされたテンプレートは Claude Code スキル仕様に準拠した YAML frontmatter を含むこと:
    `name`, `description`（Claude の自動検出用トリガーフレーズを含む）、
    `disable-model-invocation: true`, `argument-hint`
- `.mcp.json` を project root に登録する（未登録の場合のみ）

#### Acceptance Criteria

1. WHEN `uvx insight-blueprint --project /path` is executed THEN `.insight/` directory is created and MCP server starts in stdio mode
2. WHEN `--project` is omitted THEN current directory is used as project root
3. WHEN `--project /nonexistent` is specified THEN an error message is printed and the process exits with code 1
4. WHEN `uvx insight-blueprint` is run twice on the same project THEN data is not corrupted (idempotent initialization)
5. WHEN `.claude/skills/analysis-design/SKILL.md` is copied to the project THEN it contains valid YAML frontmatter with `name`, `description`, `disable-model-invocation`, and `argument-hint` fields per Claude Code skill specification

### Requirement 2: 分析設計の管理

**User Story:** As a data scientist, I want Claude to call `create_analysis_design()` with
my hypothesis details and have a structured YAML file saved to `.insight/designs/`, and
then retrieve or list those designs via `get_analysis_design()` and `list_analysis_designs()`
without manually opening the file system, so that I can manage multiple hypotheses efficiently
during an EDA session.

**FR-3: 分析設計データモデル**
- `AnalysisDesign` は以下のフィールドを持つ:
  - `id: str` — 自動生成（例: `FP-H01`, `FP-H02`）
  - `theme_id: str` — テーマ識別子（例: "FP", "TX"、省略時は "DEFAULT"）
    - 許容パターン: `[A-Z][A-Z0-9]*`（英大文字で始まり、英大文字・数字のみ）
    - 最大長: 8文字を推奨（制約は任意）
    - 不正値は `ValueError` を raise する
  - `title: str`
  - `hypothesis_statement: str`
  - `hypothesis_background: str`
  - `status: DesignStatus` — `draft | active | supported | rejected | inconclusive`
  - `parent_id: str | None`
  - `metrics: dict`
  - `created_at: datetime`
  - `updated_at: datetime`
- `DesignStatus` は `draft`, `active`, `supported`, `rejected`, `inconclusive` の5値を取る

**FR-4: YAML ストレージ**
- 分析設計書は `.insight/designs/` ディレクトリに YAML 形式で永続化されること
- YAML ファイルにはアナリストが手動で追記したコメントが保持されること
- プロジェクトパスは実行時パラメータとして受け取り、コードにハードコードしないこと

**FR-5: 分析設計 CRUD**
- 分析設計の作成:
  - `title`, `hypothesis_statement`, `hypothesis_background`, `parent_id?`, `theme_id?` を受け取り `AnalysisDesign` を返す
  - `id` は `{THEME_ID}-H{N:02d}` 形式で採番（テーマ内の既存 ID の最大 N + 1。削除後も衝突しない）
  - `theme_id` 省略時は `"DEFAULT"` を使用
  - `theme_id` は `[A-Z][A-Z0-9]*` パターンに一致すること。一致しない場合は `ValueError` を raise する（MCP layer では error dict に変換）
  - 初期 `status` は `draft`
  - `.insight/designs/{id}_hypothesis.yaml` として保存される（例: `FP-H01_hypothesis.yaml`）
- 分析設計の取得:
  - `design_id` を受け取り対応する `AnalysisDesign` を返す
  - 存在しない場合は `None` を返す
- 分析設計の一覧:
  - オプションの `status` フィルタを受け取り、一致する `AnalysisDesign` のリストを返す
  - `status` が指定されない場合はすべての設計を返す
- CRUD 操作はプロジェクトパスを引数として受け取り、複数プロジェクト間でデータが混在しないこと

**FR-6: MCP Tools（3 tools）**
- Claude が呼び出せる MCP tool として以下の3つを提供すること:
- `create_analysis_design(title, hypothesis_statement, hypothesis_background, parent_id?, theme_id?) → dict`
  - `{id, title, status, message}` を返却
- `get_analysis_design(design_id) → dict`
  - `AnalysisDesign` を dict として返却
  - 見つからない場合は error dict を返却
- `list_analysis_designs(status?) → dict`
  - `{designs: [...], count: int}` を返却
- すべての tool は非同期 I/O に対応すること

#### Acceptance Criteria

1. WHEN `create_analysis_design()` is called with valid inputs THEN `{"id": "FP-H01", "status": "draft", ...}` is returned and a YAML file is saved at `.insight/designs/FP-H01_hypothesis.yaml`
2. WHEN `get_analysis_design("FP-H01")` is called THEN the same data that was saved is returned
3. WHEN `get_analysis_design("FP-H99")` is called for a non-existent design THEN an error dict is returned (not an exception)
4. WHEN `list_analysis_designs(status="draft")` is called THEN only designs with `status == "draft"` are returned and `count` matches the number of results
5. WHEN a YAML write crashes mid-write THEN the original YAML file is preserved (no partial write)
6. WHEN `create_analysis_design()` is called with an invalid theme_id (e.g., "fp", "FP/X", "12") THEN an error dict is returned with a message indicating the invalid theme_id

## Non-Functional Requirements

### Code Architecture and Modularity

- **Single Responsibility Principle**: Each file handles one specific concern (`cli.py` = entry point, `server.py` = MCP tools, `core/designs.py` = business logic, `storage/yaml_store.py` = YAML I/O)
- **Three-Layer Separation**: CLI → Core → Storage; MCP tools delegate to `DesignService`; `DesignService` delegates to `yaml_store.py`; no cross-layer skipping
- **One-Directional Dependencies**: Dependency direction is CLI → MCP → Core → Storage; no reverse dependencies allowed
- **Type Annotations Required**: All functions must have complete type annotations; `ty check` must pass with no errors
- **Code Quality**: `ruff check` passes (line-length 88); `pytest` coverage for `core/` and `storage/` is 80% or higher

### Performance

- CLI startup (`uvx` cold start) completes within 5 seconds (excluding first-time `uvx` package download)
- `create_analysis_design()` completes within 100ms (local YAML write)
- `list_analysis_designs()` completes within 200ms for up to 100 designs

### Security

- No hardcoded secrets, API keys, or credentials in source code
- Project path is validated to exist before any initialization proceeds; paths are resolved to absolute via `Path.resolve()`
- Error messages do not expose internal stack traces or file system structure to MCP clients

### Reliability

- All YAML writes are atomic — `tempfile.mkstemp()` + `os.replace()` ensures no partial write on crash
- Initialization is idempotent — `uvx insight-blueprint` run multiple times does not corrupt data or duplicate files
- `uvx insight-blueprint` works without pre-installation; Python >=3.11 is required; all runtime dependencies are installable via `uv add insight-blueprint`

### Usability

- `--help` output clearly describes all options and expected behavior
- Error messages for invalid inputs (e.g., missing project path) include actionable guidance for the analyst
- MCP tool docstrings are human-readable so Claude can accurately describe tool behavior to users

## Out of Scope

- データカタログ（SPEC-2）
- レビューワークフロー（SPEC-3）
- WebUI ダッシュボード（SPEC-4）
- PyPI 公開（SPEC-5）
- SQLite FTS5 index（SPEC-2）
- FastAPI web server（SPEC-4）
- `update_analysis_design()` MCP tool（SPEC-3、review workflow の一部）

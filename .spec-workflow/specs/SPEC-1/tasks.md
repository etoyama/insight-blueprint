# Tasks: SPEC-1 core-foundation

- [ ] 1.1 Initialize project scaffold and pyproject.toml
  - File: pyproject.toml, src/insight_blueprint/__init__.py, src/insight_blueprint/__main__.py
  - hatchling build backend を src/ layout で設定する
  - runtime dependencies を追加: fastmcp>=2.0, pydantic>=2.10, ruamel.yaml>=0.18, click>=8.1
  - dev dependencies を追加: pytest>=8.0, pytest-cov>=6.0, ruff>=0.8, ty>=0.1, poethepoet>=0.31
  - poe tasks を設定: lint, typecheck, test, all
  - Purpose: import 可能な Python package と動作する toolchain を確立する
  - _Requirements: NFR-3, NFR-4_
  - _Prompt: Role: Python packaging expert specializing in uv and hatchling | Task: Set up pyproject.toml for insight-blueprint with src/ layout, hatchling backend, and poethepoet task runner per requirements NFR-3 and NFR-4 | Restrictions: Do NOT use pip, use uv only; follow src/ layout convention; poe tasks must run without errors | Success: uv sync completes, python -m insight_blueprint --help shows help, poe lint passes_

- [ ] 1.2 Implement Pydantic models for AnalysisDesign
  - File: src/insight_blueprint/models/__init__.py, src/insight_blueprint/models/common.py, src/insight_blueprint/models/design.py
  - `DesignStatus` enum を作成: draft, active, supported, rejected, inconclusive
  - `AnalysisDesign` BaseModel を必要なフィールドと JST timezone default で作成する
  - `AnalysisDesign` と `DesignStatus` を models/__init__.py から re-export する
  - Purpose: storage・core・MCP 層で共有する型を定義する
  - _Leverage: src/insight_blueprint/models/__init__.py_
  - _Requirements: FR-3_
  - _Prompt: Role: Python developer specializing in Pydantic v2 data modeling | Task: Implement AnalysisDesign Pydantic model and DesignStatus enum per FR-3, with JST timezone defaults using zoneinfo | Restrictions: Use Pydantic v2 (BaseModel, Field), all fields must have type annotations, use zoneinfo not pytz | Success: from insight_blueprint.models import AnalysisDesign, DesignStatus works; model instantiates with correct defaults; ty check passes_

- [ ] 1.3 Implement YAML storage layer and project directory management
  - File: src/insight_blueprint/storage/__init__.py, src/insight_blueprint/storage/yaml_store.py, src/insight_blueprint/storage/project.py
  - `read_yaml(path)` を実装する（ファイルが存在しない場合は empty dict を返す）
  - `write_yaml(path, data)` を atomic な `tempfile.mkstemp()` + `os.replace()` で実装する
  - `init_project(project_path)` を idempotent に `.insight/` 構造を作成するよう実装する
  - `tests/test_storage.py` にテストを書く（atomic write safety、idempotent init）
  - Purpose: すべての YAML データに対してクラッシュセーフな persistence layer を提供する
  - _Leverage: src/insight_blueprint/models/design.py_
  - _Requirements: FR-2, FR-4_
  - _Prompt: Role: Python developer specializing in file system operations and atomic writes | Task: Implement atomic YAML storage and .insight/ directory init per FR-2 and FR-4 using ruamel.yaml and tempfile+os.replace pattern | Restrictions: tempfile MUST be in same directory as target for atomic os.replace; read_yaml MUST return {} not raise for missing files; init_project must be idempotent | Success: write then read returns same data; crash simulation leaves original file intact; init_project twice does not raise_

- [ ] 1.4 Implement core DesignService business logic
  - File: src/insight_blueprint/core/__init__.py, src/insight_blueprint/core/designs.py
  - `project_path: Path` を constructor で受け取る `DesignService` class を実装する
  - sequential ID 生成（H01, H02, ...）で `create_design()` を実装する
  - missing ID に対して `None` を返す `get_design()` を実装する
  - optional status filter 付きの `list_designs()` を実装する
  - `tests/test_designs.py` にテストを書く（happy path・not found・filtering を含む 7件以上）
  - Purpose: MCP tools と将来の API で共有する business logic layer
  - _Leverage: src/insight_blueprint/storage/yaml_store.py, src/insight_blueprint/models/design.py_
  - _Requirements: FR-5_
  - _Prompt: Role: Python developer specializing in service layer architecture | Task: Implement DesignService with CRUD operations per FR-5, using yaml_store for persistence and AnalysisDesign model | Restrictions: Sequential IDs H01/H02/... based on file count; get_design returns None not exception for missing; list_designs globs sorted files | Success: create saves YAML at correct path; sequential IDs work; get returns None for missing; list filters by status; 7+ tests pass_

- [ ] 1.5 Implement MCP server with 3 design tools
  - File: src/insight_blueprint/server.py
  - `mcp = FastMCP("insight-blueprint")` で FastMCP instance を作成する
  - `get_service()` guard 付きの global `_service` 変数を実装する
  - 3つの async MCP tools を登録する: create_analysis_design, get_analysis_design, list_analysis_designs
  - `storage/project.py` の `init_project()` を更新して `DesignService` を `server._service` に wire する
  - Purpose: MCP protocol 経由で design 操作を Claude Code に公開する
  - _Leverage: src/insight_blueprint/core/designs.py, src/insight_blueprint/models/design.py_
  - _Requirements: FR-6_
  - _Prompt: Role: Python developer specializing in FastMCP and MCP protocol | Task: Implement 3 MCP tools using fastmcp @mcp.tool() decorator per FR-6; tools must be async; get_analysis_design returns error dict not exception for missing ID | Restrictions: Use fastmcp not mcp.server.fastmcp; all tools async def; return dicts not Pydantic models directly; wire _service in init_project | Success: 3 tools registered; create returns {id, title, status, message}; get returns error dict for missing; list returns {designs, count}_

- [ ] 1.6 Implement CLI entry point and run end-to-end integration test
  - File: src/insight_blueprint/cli.py, src/insight_blueprint/__main__.py, tests/test_integration.py, README.md
  - `--project` と `--headless` option を持つ click CLI を実装する
  - 存在しない project path に対して `ClickException` を追加する
  - `python -m insight_blueprint` サポートのために `__main__.py` を作成する
  - integration test を書く: `.insight/` init → create_design → get_design → list_designs round-trip
  - `poe all` が通ることを確認する（ruff + ty + pytest、`core/` と `storage/` の coverage が 80% 以上）
  - Purpose: 使用可能な CLI entry point を完成させ、end-to-end の動作を検証する
  - _Leverage: src/insight_blueprint/server.py, src/insight_blueprint/storage/project.py_
  - _Requirements: FR-1, AC-1, AC-2, AC-3, AC-5_
  - _Prompt: Role: Python developer specializing in click CLIs and integration testing | Task: Implement CLI entry point per FR-1 with click, add integration test covering full round-trip per AC-1 through AC-5, ensure poe all passes with >=80% coverage | Restrictions: mcp.run() must be LAST call in main(); ClickException for missing project path; --headless suppresses browser (no-op in SPEC-1); README must have install and quick-start | Success: uvx insight-blueprint --project /path creates .insight/; --project /nonexistent exits with error; poe all passes; coverage >=80%_

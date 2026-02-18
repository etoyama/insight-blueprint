# Tasks: SPEC-1 core-foundation

- [ ] 1.1 Initialize project scaffold and pyproject.toml
  - File: pyproject.toml, src/insight_blueprint/__init__.py, src/insight_blueprint/__main__.py
  - Configure hatchling build backend with correct src/ layout
  - Add runtime dependencies: fastmcp>=2.0, pydantic>=2.10, ruamel.yaml>=0.18, click>=8.1
  - Add dev dependencies: pytest>=8.0, pytest-cov>=6.0, ruff>=0.8, ty>=0.1, poethepoet>=0.31
  - Configure poe tasks: lint, typecheck, test, all
  - Purpose: Establish importable Python package and working toolchain
  - _Requirements: NFR-3, NFR-4_
  - _Prompt: Role: Python packaging expert specializing in uv and hatchling | Task: Set up pyproject.toml for insight-blueprint with src/ layout, hatchling backend, and poethepoet task runner per requirements NFR-3 and NFR-4 | Restrictions: Do NOT use pip, use uv only; follow src/ layout convention; poe tasks must run without errors | Success: uv sync completes, python -m insight_blueprint --help shows help, poe lint passes_

- [ ] 1.2 Implement Pydantic models for AnalysisDesign
  - File: src/insight_blueprint/models/__init__.py, src/insight_blueprint/models/common.py, src/insight_blueprint/models/design.py
  - Create DesignStatus enum: draft, active, supported, rejected, inconclusive
  - Create AnalysisDesign BaseModel with all required fields and JST timezone defaults
  - Re-export AnalysisDesign and DesignStatus from models/__init__.py
  - Purpose: Define shared data types used by storage, core, and MCP layers
  - _Leverage: src/insight_blueprint/models/__init__.py_
  - _Requirements: FR-3_
  - _Prompt: Role: Python developer specializing in Pydantic v2 data modeling | Task: Implement AnalysisDesign Pydantic model and DesignStatus enum per FR-3, with JST timezone defaults using zoneinfo | Restrictions: Use Pydantic v2 (BaseModel, Field), all fields must have type annotations, use zoneinfo not pytz | Success: from insight_blueprint.models import AnalysisDesign, DesignStatus works; model instantiates with correct defaults; ty check passes_

- [ ] 1.3 Implement YAML storage layer and project directory management
  - File: src/insight_blueprint/storage/__init__.py, src/insight_blueprint/storage/yaml_store.py, src/insight_blueprint/storage/project.py
  - Implement read_yaml(path) returning empty dict for missing files
  - Implement write_yaml(path, data) using atomic tempfile.mkstemp() + os.replace()
  - Implement init_project(project_path) creating .insight/ structure idempotently
  - Write tests in tests/test_storage.py (atomic write safety, idempotent init)
  - Purpose: Provide crash-safe persistence layer for all YAML data
  - _Leverage: src/insight_blueprint/models/design.py_
  - _Requirements: FR-2, FR-4_
  - _Prompt: Role: Python developer specializing in file system operations and atomic writes | Task: Implement atomic YAML storage and .insight/ directory init per FR-2 and FR-4 using ruamel.yaml and tempfile+os.replace pattern | Restrictions: tempfile MUST be in same directory as target for atomic os.replace; read_yaml MUST return {} not raise for missing files; init_project must be idempotent | Success: write then read returns same data; crash simulation leaves original file intact; init_project twice does not raise_

- [ ] 1.4 Implement core DesignService business logic
  - File: src/insight_blueprint/core/__init__.py, src/insight_blueprint/core/designs.py
  - Implement DesignService class with project_path: Path constructor
  - Implement create_design() with sequential ID generation (H01, H02, ...)
  - Implement get_design() returning None for missing IDs
  - Implement list_designs() with optional status filter
  - Write tests in tests/test_designs.py (7+ test cases covering happy path, not-found, filtering)
  - Purpose: Business logic layer shared by MCP tools and future API
  - _Leverage: src/insight_blueprint/storage/yaml_store.py, src/insight_blueprint/models/design.py_
  - _Requirements: FR-5_
  - _Prompt: Role: Python developer specializing in service layer architecture | Task: Implement DesignService with CRUD operations per FR-5, using yaml_store for persistence and AnalysisDesign model | Restrictions: Sequential IDs H01/H02/... based on file count; get_design returns None not exception for missing; list_designs globs sorted files | Success: create saves YAML at correct path; sequential IDs work; get returns None for missing; list filters by status; 7+ tests pass_

- [ ] 1.5 Implement MCP server with 3 design tools
  - File: src/insight_blueprint/server.py
  - Create FastMCP instance: mcp = FastMCP("insight-blueprint")
  - Implement global _service variable with get_service() guard
  - Register 3 async MCP tools: create_analysis_design, get_analysis_design, list_analysis_designs
  - Update storage/project.py init_project() to wire DesignService into server._service
  - Purpose: Expose design operations to Claude Code via MCP protocol
  - _Leverage: src/insight_blueprint/core/designs.py, src/insight_blueprint/models/design.py_
  - _Requirements: FR-6_
  - _Prompt: Role: Python developer specializing in FastMCP and MCP protocol | Task: Implement 3 MCP tools using fastmcp @mcp.tool() decorator per FR-6; tools must be async; get_analysis_design returns error dict not exception for missing ID | Restrictions: Use fastmcp not mcp.server.fastmcp; all tools async def; return dicts not Pydantic models directly; wire _service in init_project | Success: 3 tools registered; create returns {id, title, status, message}; get returns error dict for missing; list returns {designs, count}_

- [ ] 1.6 Implement CLI entry point and run end-to-end integration test
  - File: src/insight_blueprint/cli.py, src/insight_blueprint/__main__.py, tests/test_integration.py, README.md
  - Implement click CLI with --project and --headless options
  - Add ClickException for non-existent project path
  - Create __main__.py for python -m insight_blueprint support
  - Write integration test: init .insight/ → create_design → get_design → list_designs round-trip
  - Ensure poe all passes (ruff + ty + pytest with >=80% coverage on core/ and storage/)
  - Purpose: Complete the usable CLI entry point and verify end-to-end functionality
  - _Leverage: src/insight_blueprint/server.py, src/insight_blueprint/storage/project.py_
  - _Requirements: FR-1, AC-1, AC-2, AC-3, AC-5_
  - _Prompt: Role: Python developer specializing in click CLIs and integration testing | Task: Implement CLI entry point per FR-1 with click, add integration test covering full round-trip per AC-1 through AC-5, ensure poe all passes with >=80% coverage | Restrictions: mcp.run() must be LAST call in main(); ClickException for missing project path; --headless suppresses browser (no-op in SPEC-1); README must have install and quick-start | Success: uvx insight-blueprint --project /path creates .insight/; --project /nonexistent exits with error; poe all passes; coverage >=80%_

# Insight Blueprint MCP - Research Findings

> **Author**: Researcher (Gemini CLI - 5 parallel queries)
> **Date**: 2026-02-18
> **Status**: Complete (Updated with Gemini research)

---

## Task 1: Python MCP SDK Options

### Recommendation: FastMCP (`fastmcp`) for development, consider official `mcp` for stability

Two viable options exist:

| Feature | FastMCP (`jlowin/fastmcp`) | Official SDK (`mcp`) |
|---------|---------------------------|----------------------|
| Best For | Rapid Local Dev, Production Apps | Core Implementation, Library Authors |
| Package | `fastmcp` | `mcp` |
| API Style | High-level Decorators (FastAPI-style) | Low-level Protocol + Basic Decorators |
| Pydantic | **Native & Automatic** schema inference | Supported but manual schema binding |
| Transport | `stdio`, `sse` (1-line switch) | Manual setup of StdioServerTransport |
| Dev Tools | Built-in Inspector / Debugger UI | None |
| Status | Active, Feature-rich (v3+) | Stable, Spec-compliant Reference |

**Important Note**: The official `mcp` package includes a basic FastMCP (v1) at `mcp.server.fastmcp.FastMCP`, but `jlowin/fastmcp` (v2/v3) has significantly better DX. They are **different packages**.

**Installation:**
```bash
# Option A: FastMCP (recommended for DX)
uv add fastmcp

# Option B: Official SDK
uv add "mcp>=1.8"
```

**FastMCP Example (Recommended):**
```python
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

mcp = FastMCP("InsightBlueprint")

class AnalysisDesignInput(BaseModel):
    name: str = Field(description="Name of the analysis design")
    description: str = Field(description="Description of the analysis")

@mcp.tool()
async def create_analysis_design(params: AnalysisDesignInput, ctx: Context) -> str:
    """Create a new analysis design document."""
    ctx.info(f"Creating design: {params.name}")
    return f"Created analysis design: {params.name}"

if __name__ == "__main__":
    mcp.run()  # Auto-detects stdio vs SSE
```

**Official SDK Example:**
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("insight-blueprint")

@mcp.tool()
async def create_analysis_design(
    design_id: str,
    hypothesis_statement: str,
    hypothesis_background: str,
    parent_id: str | None = None,
) -> dict:
    """Create a new analysis design document."""
    ...

if __name__ == "__main__":
    mcp.run()  # defaults to stdio transport
```

**Key Differences:**
1. FastMCP: Full Pydantic model as parameter -> auto JSON Schema
2. FastMCP: `ctx.info()` for logging back to client
3. FastMCP: Built-in Inspector/Debugger UI
4. Official: Manual `.model_json_schema()` for complex models
5. Official: No dev tools

**Decision Factor**: Both work. FastMCP is better DX. Official SDK is lower risk. If using official `mcp` package, its built-in `FastMCP` provides a similar decorator API (just less feature-rich).

**Constraint**: Python >=3.10 for `mcp>=1.8`. We target >=3.11, so no conflict.

---

## Task 2: React+Vite Frontend Bundling in Python Package

### Recommended Project Structure

```text
insight-blueprint/
├── pyproject.toml
├── frontend/                    # React+Vite source
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
└── src/
    └── insight_blueprint/
        ├── __init__.py
        ├── server.py            # FastAPI app serving UI + MCP
        └── static/              # DESTINATION for frontend build
            ├── index.html
            └── assets/
```

### pyproject.toml Configuration (Hatchling)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/insight_blueprint"]

# KEY: Include git-ignored build artifacts in the wheel
artifacts = [
  "src/insight_blueprint/static/**/*",
]
```

The `artifacts` key is critical - it tells Hatchling to include files that would normally be git-ignored (build output).

Without `artifacts`, if `static/` is in `.gitignore`, Hatchling would skip it.

### Vite Config (Build directly into Python package)

```typescript
// frontend/vite.config.ts
export default defineConfig({
  build: {
    outDir: '../src/insight_blueprint/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",  // Dev: proxy to FastAPI
    },
  },
})
```

### Serving with FastAPI

```python
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()

# API routes first (before static mount)
app.include_router(api_router, prefix="/api")

if STATIC_DIR.is_dir():
    # Mount assets subfolder
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # SPA catch-all: serve index.html for React Router
    @app.get("/{full_path:path}")
    async def serve_app(full_path: str):
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def index():
        return {"message": "Frontend not found. Run 'npm run build' in frontend/"}
```

**Alternative (simpler):** Use `html=True` on StaticFiles mount:
```python
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

### Build Pipeline

```bash
#!/bin/bash
set -e
# 1. Build Frontend
cd frontend && npm install && npm run build && cd ..
# 2. Build Python Package
uvx hatch build
```

Or in pyproject.toml:
```toml
[tool.poe.tasks]
build-frontend = "bash -c 'cd frontend && npm run build'"
build = ["build-frontend"]
```

### Path Resolution (for installed packages)

```python
# Modern way (Python 3.9+)
from importlib.resources import files

def get_static_path():
    return files("insight_blueprint").joinpath("static")

# Traditional way (simpler, works everywhere)
from pathlib import Path

def get_static_path():
    return Path(__file__).parent / "static"
```

### Real-World References
- **Marimo**: Uses `hatchling` with `artifacts` config (see their pyproject.toml)
- **Gradio**: Builds Svelte frontend into `gradio/templates/frontend`
- **Prefect**: Bundles UI into server package
- **MLflow**: React SPA in `mlflow/server/js/build/`

---

## Task 3: Similar Reference Projects - Key Patterns

### Port Management (Dynamic)

```python
import socket
from contextlib import closing

def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))  # OS selects a free port
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
```

### Auto Browser Opening

```python
import threading
import webbrowser
import uvicorn

def open_browser(url: str):
    import time
    time.sleep(1.5)  # Wait for server to start
    webbrowser.open(url)

def start_app():
    port = find_free_port()
    url = f"http://localhost:{port}"
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    print(f"Dashboard running at: {url}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
```

### Graceful Shutdown

```python
import signal, sys

def handle_exit(signum, frame):
    # Cleanup: close DB connections, stop background threads
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
```

### Lessons from Ecosystem

| Tool | Key Pattern | Lesson for Us |
|------|-------------|---------------|
| **Gradio** | Bundled Svelte + internal FastAPI | Abstract UI; Python defines API, bundled frontend renders |
| **Streamlit** | WebSocket state sync | React app connects via WS to Python |
| **Marimo** | WASM export, hatchling artifacts | Standard pattern for static asset bundling |
| **spec-workflow-mcp** | Files as database, MD as source of truth | Use filesystem as state; human-editable files preferred |

### Key Takeaways
1. **Static files inside package directory** is the simplest approach
2. **`html=True` on StaticFiles** handles SPA routing automatically
3. **Port conflict detection**: bind to port 0, let OS choose
4. **Auto-open browser**: `webbrowser.open()` with threaded delay
5. **Lifecycle**: Most servers (Uvicorn) handle SIGINT natively

---

## Task 4: Project-Level Storage Patterns

### Recommendation: Structured Text Files (YAML + Markdown with Frontmatter)

For <10,000 entries, the filesystem IS an efficient enough database.

| Use Case | Format | Why |
|----------|--------|-----|
| Analysis/Design Docs | **Markdown + YAML Frontmatter** | Rich text + structured metadata |
| Domain Knowledge Notes | **Markdown + YAML Frontmatter** | Natural for free-form notes |
| Data Catalog | **YAML** | Structured schema fits nested key-value |
| Review Rules / Config | **YAML** | Rules map directly to YAML lists |

### Directory Structure

```text
.insight/
├── config.yaml              # Project config
├── catalog/
│   ├── users_table.yaml     # Data catalog entries
│   └── orders_table.yaml
├── designs/
│   ├── feature_x_v1.md      # Analysis design docs
│   └── migration_plan.md
├── knowledge/
│   ├── domain_glossary.md   # Domain knowledge
│   └── business_rules.md
└── rules/
    └── review_checklist.yaml # Review rules
```

### Key Libraries

| Library | Use Case | Install |
|---------|----------|---------|
| `ruamel.yaml` | YAML with comment preservation (round-trip editing) | `uv add ruamel.yaml` |
| `python-frontmatter` | Markdown with YAML frontmatter parsing | `uv add python-frontmatter` |
| `pydantic` v2+ | Schema validation for YAML/frontmatter content | `uv add pydantic` |

**Why `ruamel.yaml` over `PyYAML`**: preserves comments when programmatically editing files. Critical for files that data scientists also edit manually.

### Code Pattern

```python
from pydantic import BaseModel, Field
import frontmatter
from pathlib import Path

class DesignDocMetadata(BaseModel):
    title: str
    status: str = "draft"
    tags: list[str] = []
    hypothesis: str = ""

def load_design_doc(path: Path) -> tuple[DesignDocMetadata, str]:
    post = frontmatter.load(path)
    metadata = DesignDocMetadata(**post.metadata)
    return metadata, post.content
```

### Optional: SQLite FTS Index (auto-generated)

For search-heavy use cases (e.g., `search_catalog(keyword)` across hundreds of entries):
- Use `sqlite3` (stdlib) with FTS5 extension
- Rebuild index from YAML/MD files on startup
- YAML/MD files remain source of truth
- Index is a cache, not primary storage

### Why NOT SQLite as Primary Storage
1. **Binary format** - unreadable Git diffs
2. **Merge conflicts** on entire `.db` file (unusable for collaboration)
3. **Overkill** for <10,000 entries
4. **LLMs** understand Markdown/YAML better than SQL dumps

### Why NOT JSON
1. **No comments** (standard JSON)
2. **Multi-line strings** are painful
3. **Less human-editable** than YAML

---

## Task 5: Claude Code Skill Auto-Setup & MCP Registration

### `.claude/settings.json` MCP Server Format

```json
{
  "mcpServers": {
    "insight-blueprint": {
      "command": "uvx",
      "args": [
        "insight-blueprint",
        "--",
        "--project",
        "/absolute/path/to/project"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

Note: `--` separates `uvx` arguments from tool arguments.

### CLI Registration Command

```bash
claude mcp add insight-blueprint -- uvx insight-blueprint --project $(pwd)
```

This is the **preferred** approach as `claude mcp add` handles merging correctly.

### Programmatic Settings Merge

```python
import json
import os
from pathlib import Path

def register_mcp_server(project_dir: Path) -> None:
    settings_path = project_dir / ".claude" / "settings.json"

    # Load existing or start fresh
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}

    # Merge (don't overwrite other settings)
    data.setdefault("mcpServers", {})["insight-blueprint"] = {
        "command": "uvx",
        "args": ["insight-blueprint", "--", "--project", str(project_dir.resolve())],
        "env": {"PYTHONUNBUFFERED": "1"},
    }

    # Atomic write
    temp_path = settings_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(temp_path, settings_path)
```

### Bundled Skill Extraction

```python
import importlib.resources
from pathlib import Path

def install_bundled_skills(package_name: str, dest_dir: Path) -> None:
    """Copy bundled skill files from installed package to .claude/skills/"""
    skills_resource = importlib.resources.files(package_name).joinpath("_skills")
    dest_dir.mkdir(parents=True, exist_ok=True)

    for resource in skills_resource.iterdir():
        if resource.name.endswith(".md"):
            content = resource.read_text(encoding="utf-8")
            dest_file = dest_dir / resource.name
            if not dest_file.exists():  # Don't overwrite user edits
                dest_file.write_text(content, encoding="utf-8")
```

Skills stored inside package at `src/insight_blueprint/_skills/` (auto-included in wheel via Hatch).

### Skill File Format

```markdown
---
name: insight-blueprint
description: Manage analysis designs and data catalog for data science projects.
---

# Insight Blueprint Skill

## Usage
When the user asks for analysis design management, use insight-blueprint MCP tools.

## Available MCP Tools
- `create_analysis_design` - Create a new analysis design
- `list_data_catalog` - List data catalog entries
- `add_domain_knowledge` - Add domain knowledge notes
```

### First-Run Setup Sequence

```
uvx insight-blueprint --project /path
  -> Initialize .insight/ directory (if first run)
  -> Copy skills to .claude/skills/ (if not present)
  -> Register MCP server in .claude/settings.json (if not present)
  -> Start FastAPI + uvicorn in background thread
  -> Open browser (webbrowser.open)
  -> Start MCP server via mcp.run() (stdio, blocks main thread)
```

---

## Summary: Top 5 Key Findings

1. **FastMCP vs Official SDK**: FastMCP (`jlowin/fastmcp`) provides superior DX with automatic Pydantic support, built-in inspector, and 1-line transport switching. Official `mcp` package has its own `FastMCP` (simpler). Both work for our use case. Choose based on stability vs DX preference.

2. **Frontend Bundling**: Hatchling `artifacts` config is the standard way to include React+Vite build output. Build directly to `src/insight_blueprint/static/` via Vite `outDir`. Reference: Marimo project does exactly this.

3. **Storage Pattern**: YAML + Markdown with Frontmatter is the clear winner for `.insight/` - git-friendly, human-editable, LLM-readable. Use `ruamel.yaml` (preserves comments) + `python-frontmatter` + `pydantic` for validation. SQLite only as optional FTS index.

4. **Server Lifecycle**: Dynamic port via `socket.bind(('', 0))`, threaded browser auto-open with delay, FastAPI `StaticFiles(html=True)` for SPA serving. Follow Marimo/Gradio patterns. Uvicorn handles SIGINT natively.

5. **Claude Code Integration**: `claude mcp add` is preferred for MCP registration. Skills are Markdown with YAML frontmatter in `.claude/skills/`. Programmatic setup via JSON merge for `.claude/settings.json` is straightforward. Bundle skills inside package at `_skills/`.

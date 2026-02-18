# SPEC-1: core-foundation — Design

> **Spec ID**: SPEC-1
> **Status**: pending_approval
> **Created**: 2026-02-18
> **Source**: DESIGN.md v1.1.0

---

## Architecture

### Component Diagram (SPEC-1 scope)

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
  .insight/designs/*.yaml
```

### Key Design Decision: stdio Transport

fastmcp's `mcp.run()` uses stdio transport. This is the correct choice because:
- Claude Code's `claude mcp add` expects stdio by default
- No network configuration, no port conflicts
- `mcp.run()` blocks main thread — this is intentional

SPEC-4 adds uvicorn on a daemon thread. In SPEC-1, there is no HTTP server.

---

## Module Design

### `cli.py`

```python
import click
from insight_blueprint.storage.project import init_project
from insight_blueprint.server import mcp

@click.command()
@click.option("--project", default=".", help="Project directory path")
@click.option("--headless", is_flag=True, help="Do not open browser")
def main(project: str, headless: bool) -> None:
    """insight-blueprint MCP server + WebUI."""
    project_path = Path(project).resolve()
    if not project_path.exists():
        raise click.ClickException(f"Project directory not found: {project_path}")

    init_project(project_path)          # Step 1: .insight/ setup
    mcp.run()                           # Step 2: BLOCKS (stdio MCP)
```

### `server.py`

```python
from fastmcp import FastMCP
from insight_blueprint.core.designs import DesignService

mcp = FastMCP("insight-blueprint")
_service: DesignService | None = None

def get_service() -> DesignService:
    global _service
    if _service is None:
        raise RuntimeError("Service not initialized. Call init_project() first.")
    return _service

@mcp.tool()
async def create_analysis_design(
    title: str,
    hypothesis_statement: str,
    hypothesis_background: str,
    parent_id: str | None = None,
) -> dict:
    """Create a new analysis design document."""
    design = get_service().create_design(
        title=title,
        hypothesis_statement=hypothesis_statement,
        hypothesis_background=hypothesis_background,
        parent_id=parent_id,
    )
    return {"id": design.id, "title": design.title, "status": design.status, "message": "Created"}

@mcp.tool()
async def get_analysis_design(design_id: str) -> dict:
    """Retrieve an analysis design by ID."""
    design = get_service().get_design(design_id)
    if design is None:
        return {"error": f"Design '{design_id}' not found"}
    return design.model_dump()

@mcp.tool()
async def list_analysis_designs(status: str | None = None) -> dict:
    """List analysis designs, optionally filtered by status."""
    designs = get_service().list_designs(status=status)
    return {"designs": [d.model_dump() for d in designs], "count": len(designs)}
```

### `models/common.py`

```python
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

def now_jst() -> datetime:
    return datetime.now(JST)
```

### `models/design.py`

```python
from enum import Enum
from pydantic import BaseModel, Field
from insight_blueprint.models.common import now_jst

class DesignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"

class AnalysisDesign(BaseModel):
    id: str
    title: str
    hypothesis_statement: str
    hypothesis_background: str
    status: DesignStatus = DesignStatus.DRAFT
    parent_id: str | None = None
    metrics: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_jst)
    updated_at: datetime = Field(default_factory=now_jst)
```

### `storage/project.py`

```python
from pathlib import Path
from insight_blueprint.core.designs import DesignService
import insight_blueprint.server as server_module

INSIGHT_DIR = ".insight"

def init_project(project_path: Path) -> None:
    """Initialize .insight/ directory structure (idempotent)."""
    insight = project_path / INSIGHT_DIR

    # Create directory structure
    for subdir in ["catalog/knowledge", "designs", "rules"]:
        (insight / subdir).mkdir(parents=True, exist_ok=True)

    # Initialize config.yaml if not present
    config_file = insight / "config.yaml"
    if not config_file.exists():
        config_file.write_text("version: 1\n")

    # Initialize rules templates
    for rules_file in ["review_rules.yaml", "analysis_rules.yaml"]:
        rules_path = insight / "rules" / rules_file
        if not rules_path.exists():
            rules_path.write_text(f"# {rules_file}\nrules: []\n")

    # Wire up service
    service = DesignService(project_path=project_path)
    server_module._service = service
```

### `storage/yaml_store.py`

```python
import os
import tempfile
from pathlib import Path
from ruamel.yaml import YAML

_yaml = YAML()
_yaml.preserve_quotes = True

def read_yaml(path: Path) -> dict:
    """Read a YAML file. Returns empty dict if file does not exist."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return _yaml.load(f) or {}

def write_yaml(path: Path, data: dict) -> None:
    """Write data to YAML atomically (tempfile + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".yaml.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            _yaml.dump(data, f)
        os.replace(tmp_path, path)  # atomic on POSIX
    except Exception:
        os.unlink(tmp_path)
        raise
```

### `core/designs.py`

```python
from pathlib import Path
from insight_blueprint.models.design import AnalysisDesign, DesignStatus
from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

class DesignService:
    def __init__(self, project_path: Path) -> None:
        self._designs_dir = project_path / ".insight" / "designs"

    def _next_id(self) -> str:
        existing = list(self._designs_dir.glob("H*.yaml"))
        n = len(existing) + 1
        return f"H{n:02d}"

    def create_design(
        self, title: str, hypothesis_statement: str, hypothesis_background: str,
        parent_id: str | None = None
    ) -> AnalysisDesign:
        design = AnalysisDesign(
            id=self._next_id(),
            title=title,
            hypothesis_statement=hypothesis_statement,
            hypothesis_background=hypothesis_background,
            parent_id=parent_id,
        )
        path = self._designs_dir / f"{design.id}_hypothesis.yaml"
        write_yaml(path, design.model_dump(mode="json"))
        return design

    def get_design(self, design_id: str) -> AnalysisDesign | None:
        path = self._designs_dir / f"{design_id}_hypothesis.yaml"
        data = read_yaml(path)
        return AnalysisDesign(**data) if data else None

    def list_designs(self, status: str | None = None) -> list[AnalysisDesign]:
        designs = []
        for path in sorted(self._designs_dir.glob("H*_hypothesis.yaml")):
            data = read_yaml(path)
            if data:
                designs.append(AnalysisDesign(**data))
        if status:
            designs = [d for d in designs if d.status == status]
        return designs
```

---

## Data Model

### File: `.insight/designs/{id}_hypothesis.yaml`

```yaml
id: H01
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

ID Generation: `H{N:02d}` where N is count of existing design files + 1.
Range: H01–H99 (sufficient for typical EDA sessions).

---

## Error Handling

| Scenario | Behavior |
|----------|---------|
| `get_analysis_design("H99")` — not found | Returns `{"error": "Design 'H99' not found"}` |
| `--project /nonexistent` | `click.ClickException` with human-readable message |
| YAML write fails mid-way | `os.replace()` not called; temp file is cleaned up; original YAML unchanged |
| MCP called before `init_project()` | `RuntimeError("Service not initialized")` |

---

## Testing Strategy

### Unit Tests

| File | Coverage Target |
|------|----------------|
| `tests/test_designs.py` | `core/designs.py` + `models/design.py` |
| `tests/test_storage.py` | `storage/yaml_store.py` + `storage/project.py` |

### Test Cases

**test_designs.py:**
- `test_create_design_returns_design_with_generated_id` — happy path
- `test_create_design_saves_yaml_file` — file system side effect
- `test_create_design_sequential_ids` — H01, H02, H03 order
- `test_get_design_returns_correct_design` — round-trip
- `test_get_design_returns_none_for_missing_id` — not found
- `test_list_designs_returns_all` — multiple designs
- `test_list_designs_filtered_by_status` — status filter

**test_storage.py:**
- `test_write_yaml_creates_file` — basic write
- `test_write_yaml_is_atomic` — temp file cleanup on failure
- `test_read_yaml_returns_empty_for_missing_file` — graceful missing
- `test_init_project_creates_directory_structure` — idempotent

### Test Infrastructure

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Returns a temporary project directory with .insight/ initialized."""
    from insight_blueprint.storage.project import init_project
    init_project(tmp_path)
    return tmp_path
```

---

## Dependencies (SPEC-1 only)

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

Here are the best practices and concise examples for a Python CLI tool in 2025 using a `.insight/` directory architecture where YAML is the "Source of Truth" and SQLite is the "Read/Search Model."

### 1. YAML Handling: `ruamel.yaml` is Essential
For a CLI where users might edit configuration files, preserving comments and formatting is critical. `PyYAML` discards comments on load. `ruamel.yaml` is the industry standard for round-trip preservation.

**Recommendation:** Use `ruamel.yaml` with the `YAML()` instance pattern.

```python
from pathlib import Path
from ruamel.yaml import YAML

# Configure for maximum compatibility and preservation
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

file_path = Path(".insight/config.yaml")

# 1. Read (preserves comments/structure)
if file_path.exists():
    with open(file_path, "r") as f:
        data = yaml.load(f) or {}

    # 2. Modify
    data["updated_at"] = "2025-02-18" # Comments on other lines stay intact

    # 3. Write (see Atomic Write below)
    with open(file_path, "w") as f:
        yaml.dump(data, f)
```

### 2. SQLite FTS5 for Search Indexing
Parsing YAML files for every search query is too slow. Use SQLite's FTS5 (Full-Text Search 5) module as a derived index. Rebuild or update this index when YAML files change.

**Schema:**
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS project_search
USING fts5(filepath UNINDEXED, content, type);
```

**Python Sync Logic (YAML -> SQLite):**
```python
import sqlite3

def sync_yaml_to_index(db_path: Path, yaml_files: list[Path]):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable FTS5
    cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS project_search USING fts5(filepath UNINDEXED, content, type)")

    # Transaction for speed
    with conn:
        # Optional: Clear old index or use upsert logic based on file modification times
        cursor.execute("DELETE FROM project_search")

        for p in yaml_files:
            # Flatten YAML content for searchability
            text_content = p.read_text()
            cursor.execute(
                "INSERT INTO project_search (filepath, content, type) VALUES (?, ?, ?)",
                (str(p), text_content, "config")
            )
    conn.close()

def search_index(db_path: Path, query: str):
    conn = sqlite3.connect(db_path)
    # Fast full-text search
    results = conn.execute(
        "SELECT filepath, snippet(project_search, 1, '<b>', '</b>', '...', 10) FROM project_search WHERE project_search MATCH ? ORDER BY rank",
        (query,)
    ).fetchall()
    conn.close()
    return results
```

### 3. Atomic Write Pattern
Never write directly to the target file. If the program crashes or disk fills up mid-write, the user loses their data (and their comments). Use the "Write-Temp-Move" pattern.

```python
import os
import tempfile
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def atomic_write(file_path: Path, mode="w"):
    """
    Yields a temporary file object.
    On success, atomically renames temp file to target file_path.
    """
    file_path = Path(file_path)
    parent = file_path.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in the same directory to ensure atomic rename (same filesystem)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=parent, text="b" not in mode)

    try:
        with os.fdopen(tmp_fd, mode) as f:
            yield f
            f.flush()
            os.fsync(f.fileno()) # Force write to disk

        # Atomic replacement (POSIX compliant, works on modern Windows too)
        os.replace(tmp_name, file_path)
    except Exception:
        # Cleanup if write fails
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise

# Usage
from ruamel.yaml import YAML
yaml = YAML()

target = Path(".insight/data.yaml")
data = {"status": "active", "id": 123}

with atomic_write(target) as f:
    yaml.dump(data, f)
# If this block finishes, .insight/data.yaml is guaranteed valid.
```

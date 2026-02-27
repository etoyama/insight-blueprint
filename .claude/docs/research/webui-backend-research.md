# SPEC-4a WebUI Backend Research

Research for two key technical topics needed by the webui-backend implementation.

## Topic 1: Hatch Artifacts — Including Pre-built Static Files in a Wheel

### Problem

React build output (e.g., `frontend/dist/`) is typically `.gitignore`d.
Hatchling's default inclusion rules follow VCS, so these files are excluded
from the wheel unless explicitly configured.

### Solution A: `force-include` (Recommended)

Maps a source directory on the filesystem to a destination path inside the wheel.
Best for mapping a single well-known build output directory.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/insight_blueprint"]

# Map React build output into the Python package
[tool.hatch.build.targets.wheel.force-include]
"frontend/dist" = "insight_blueprint/static"
```

**Behavior:**
- Contents of `frontend/dist/` are recursively copied.
- `frontend/dist/index.html` becomes `insight_blueprint/static/index.html`
  in the installed package.
- Files must be mapped to exact paths, not to directories (for individual
  files). Directory sources have their contents recursively included.
- To map contents directly to root, use `/` as the destination.

### Solution B: `artifacts` (Alternative)

Declares glob patterns for VCS-ignored files to include. Semantically
equivalent to `include` but not affected by `exclude`.

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/insight_blueprint"]
artifacts = [
    "src/insight_blueprint/static/**",
]
```

**When to use:** When the React build step copies output *into* the Python
package tree before `hatch build`. Less control over path mapping than
`force-include`.

### Recommendation for This Project

Use **`force-include`** because:
1. React build output lives outside the Python `src/` tree (`frontend/dist/`).
2. Explicit source-to-destination mapping is clearer and more maintainable.
3. No need to copy files into the source tree before building.

### References

- [Hatch Build Configuration](https://hatch.pypa.io/1.13/config/build/) — official docs for `force-include` and `artifacts`
- [hatch issue #1130](https://github.com/pypa/hatch/issues/1130) — edge cases with `force-include` in hatchling v1.19+

---

## Topic 2: Uvicorn in a Python Daemon Thread (alongside MCP stdio server)

### Problem

The MCP server blocks the main thread on `stdin`/`stdout` (stdio transport).
The web UI backend (uvicorn + FastAPI/Starlette) must run concurrently in the
same process so it can share in-memory state with the MCP server.

### Signal Handler Constraint

Python only allows signal handlers to be set from the main thread.
Uvicorn's `Server.install_signal_handlers()` will raise `NotImplementedError`
if called from a non-main thread.

**Good news:** Since uvicorn **0.13.0** (PR #871, merged 2021), uvicorn
automatically detects when it is running in a non-main thread and skips
signal handler installation. For modern uvicorn (>=0.20), no override is
needed. However, the override pattern is still widely used for explicitness
and backward compatibility.

### Recommended Pattern

```python
import contextlib
import threading
import time

import uvicorn


class ThreadedUvicorn(uvicorn.Server):
    """Uvicorn server that can run in a non-main thread.

    Explicitly disables signal handlers (safe even on modern uvicorn
    where this is automatic, ensures no surprises).
    """

    def install_signal_handlers(self) -> None:
        pass  # Signals handled by the main thread (MCP server)

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


def start_webui(app, host: str = "127.0.0.1", port: int = 8765) -> ThreadedUvicorn:
    """Start uvicorn in a daemon thread. Returns the server instance."""
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        # CRITICAL: do not let uvicorn touch stdout — MCP owns it
        access_log=False,
    )
    server = ThreadedUvicorn(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server readiness
    while not server.started:
        time.sleep(1e-3)

    return server
```

### Integration with MCP Server

```python
import sys

from insight_blueprint.webui.app import create_app
from insight_blueprint.webui.server import start_webui


def main():
    app = create_app()

    # 1. Start web UI in background daemon thread
    server = start_webui(app, host="127.0.0.1", port=8765)
    print(f"WebUI available at http://127.0.0.1:8765", file=sys.stderr)

    # 2. Run MCP server on main thread (blocks on stdio)
    try:
        run_mcp_server()  # Blocks until stdin closes or Ctrl+C
    except KeyboardInterrupt:
        print("Shutting down...", file=sys.stderr)
    finally:
        server.should_exit = True
        # Daemon thread auto-terminates when main thread exits
```

### Key Design Decisions

1. **Subclass `uvicorn.Server`** — Override `install_signal_handlers` with
   `pass`. Explicit and safe across all uvicorn versions.

2. **`daemon=True`** — Ensures the web server thread dies automatically when
   the main MCP process exits (clean or crash). No orphan threads.

3. **Stdio isolation** — MCP owns `stdout`; uvicorn must never write to it.
   Set `log_level="warning"` and `access_log=False`. Direct uvicorn logs to
   `stderr` or a file handler.

4. **Graceful shutdown** — Set `server.should_exit = True` in a `finally`
   block. Uvicorn will finish in-flight requests and stop.

5. **Context manager alternative** — The `run_in_thread()` context manager
   is useful for tests; direct thread start is simpler for production.

### References

- [uvicorn PR #871](https://github.com/Kludex/uvicorn/pull/871) — auto-skip signal handlers in non-main threads (v0.13.0+)
- [FastAPI issue #650](https://github.com/fastapi/fastapi/issues/650) — running uvicorn in a thread
- [uvicorn discussion #1708](https://github.com/encode/uvicorn/discussions/1708) — signal handler override patterns

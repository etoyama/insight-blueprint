# Task 1: Python MCP SDK Research

Source: Gemini CLI query (2026-02-18)

## Comparison: Official SDK vs. Standalone FastMCP

As of 2026, the ecosystem has bifurcated into two distinct paths for Python developers.

| Feature | **Official SDK (`mcp`)** | **Standalone (`fastmcp`)** |
| :--- | :--- | :--- |
| **Package** | `pip install mcp` | `pip install fastmcp` |
| **Import** | `from mcp.server.fastmcp import FastMCP` | `from fastmcp import FastMCP` |
| **Status** | **Stable & Core.** Integrated directly into the official SDK. Focuses on strict spec adherence and stability. | **Advanced & Feature-Rich.** Maintained by `jlowin` (creator of Prefect). Evolved independently (v2/v3+) to include high-level features not in the core SDK. |
| **Features** | Core MCP features (Tools, Resources, Prompts). Good for simple, standard servers. | **Superset.** Includes everything in the official SDK plus **Authentication** (Auth0, GitHub), **Deployment** helpers, and advanced routing patterns. |
| **Best For** | Library authors, strict spec compliance, or those wanting zero extra dependencies. | **Application developers.** Building production-ready servers with less boilerplate and more "batteries included." |

## Recommendation for 2025-2026

**Use the standalone `fastmcp` package.**

While the official SDK is excellent for low-level control, the standalone `fastmcp` library has become the "FastAPI of MCP" -- offering the best developer experience, better debug tools, and built-in solutions for real-world problems like authentication and image handling.

## Minimal Tool Definition & Stdio Server

Here is a minimal example using the recommended **standalone `fastmcp`** package. It defines a simple calculator tool and runs as a standard input/output (stdio) server, which is the standard mode for connecting to clients like Claude Desktop or Cursor.

### 1. Install the package
```bash
pip install fastmcp
```

### 2. Create `server.py`
```python
from fastmcp import FastMCP

# Initialize the server
mcp = FastMCP("Math Helper")

# Define a tool using the decorator
# Type hints and docstrings are automatically used for the tool definition
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

# Define a dynamic resource (optional but common)
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    # Runs as a stdio server by default
    mcp.run()
```

### 3. Run the server
Since the server uses `stdio` for communication, it is designed to be spawned by an MCP client (e.g., Claude Desktop, Cursor). Configure the client to run `python server.py`.

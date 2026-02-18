# Task 2 Research: Bundling React+Vite Frontend in Python Package

Source: Gemini CLI query (2026-02-18)

---

Here is the concise setup to bundle a React/Vite frontend into a Python package using `hatchling` and `uv`.

### 1. Directory Structure
Locate your static build folder **inside** your Python package source directory so `hatchling` can package it.

```text
my-project/
├── frontend/             # React/Vite source code
│   ├── vite.config.ts
│   └── ...
├── src/
│   └── my_package/       # Python package
│       ├── static/       # <--- DESTINATION for Vite build
│       │   ├── assets/
│       │   └── index.html
│       ├── __init__.py
│       └── main.py
├── pyproject.toml
└── .gitignore            # Should include 'src/my_package/static'
```

### 2. Vite Configuration (`vite.config.ts`)
Configure Vite to output directly to your Python package's static directory.

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    // Output to the python package directory
    outDir: path.resolve(__dirname, '../src/my_package/static'),
    emptyOutDir: true, // Clears old build files
  }
})
```

### 3. Pyproject Configuration (`pyproject.toml`)
Configure `hatchling` to include the git-ignored `static` directory in the wheel.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my_package"
version = "0.1.0"
# ... dependencies ...

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]
# "artifacts" forces inclusion of files even if they are in .gitignore
artifacts = ["src/my_package/static"]
```

### 4. FastAPI Serving (`src/my_package/main.py`)
Serve static assets and handle the SPA catch-all (for client-side routing).

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# 1. Define path to static folder relative to this file
pkg_dir = os.path.dirname(__file__)
static_dir = os.path.join(pkg_dir, "static")

# 2. Check if built files exist (dev mode safety)
if os.path.exists(static_dir):
    # Mount assets (JS/CSS) at the root or /assets depending on your Vite config
    # Default Vite puts css/js in 'assets/' folder inside outDir
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    # 3. SPA Catch-all: Return index.html for any non-API route
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Optional: Check if file exists to return 404 for missing resources
        # that aren't the main index.html
        return FileResponse(os.path.join(static_dir, "index.html"))
```

### Build & Run
1.  **Build Frontend:** `cd frontend && npm run build`
2.  **Run with UV:** `uv run fastapi dev src/my_package/main.py`
3.  **Build Package:** `uv build` (This creates the `.whl` containing the UI)

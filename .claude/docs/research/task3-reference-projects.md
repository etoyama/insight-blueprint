# Task 3: Reference Projects — How Python Packages Bundle and Serve Web UIs

Source: Gemini CLI research (2026-02-18)

## 1. Where they store pre-built frontend files

Python packages typically include compiled frontend assets (HTML/CSS/JS) as "package data" (defined in `MANIFEST.in`). At runtime, the Python server locates these files relative to the installed package path.

| Package | Frontend Tech | Storage Location (Inside Package) | Mechanism |
| :--- | :--- | :--- | :--- |
| **Gradio** | Svelte | `gradio/templates/frontend` | Uses `importlib.resources` or `__file__` traversal to locate the `frontend` folder. The server (FastAPI) mounts this directory as a static file route (e.g., `/`). |
| **Marimo** | React/TS | `marimo/_static` | The build process places assets in `_static`. The server (Starlette/Uvicorn) identifies the package location and serves these files. |
| **MLflow** | React | `mlflow/server/js/build` | The huge React application is compiled into static files within the `server/js` subdirectory. The Flask server serves `index.html` from this path. |

**Concrete Example (Gradio Pattern):**
```python
# Simplified logic from Gradio's networking code
import os

# Find the path relative to the current file
frontend_path = os.path.join(os.path.dirname(__file__), "templates", "frontend")

# Mount in FastAPI
app.mount("/", StaticFiles(directory=frontend_path, html=True))
```

## 2. How they detect port conflicts

Tools meant for quick iteration (Gradio, Marimo) usually implement "auto-incrementing" port scanners. Ops platforms (MLflow) often fail fast or require manual intervention to ensure stability (predictable URLs).

*   **Gradio**:
    *   **Strategy**: **Auto-increment**.
    *   **Default**: Port `7860`.
    *   **Logic**: It tries to bind a socket to 7860. If it catches an `OSError` (Address in use), it increments to 7861, 7862, etc., usually up to a certain limit or until it finds a free one.
    *   **Code Concept**:
        ```python
        s = socket.socket()
        s.bind(("localhost", 7860)) # If fails, try 7861...
        ```

*   **Marimo**:
    *   **Strategy**: **Auto-increment (Aggressive)**.
    *   **Default**: Port `2718`.
    *   **Logic**: Similar to Gradio, it will try up to ~100 ports starting from the default to find an empty slot.
    *   **User Control**: Can be overridden with `-p 8000`.

*   **MLflow**:
    *   **Strategy**: **Fail / Manual**.
    *   **Default**: Port `5000`.
    *   **Logic**: MLflow generally assumes it is a persistent service. If port 5000 is taken, it will crash with an "Address already in use" error (or similar stack trace from the underlying Gunicorn/Flask server). You must manually run `mlflow ui -p 5001`.

## 3. How they auto-open the browser

This is almost exclusively done using Python's standard library `webbrowser` module, but the defaults vary by use case.

*   **Gradio**:
    *   **Default**: **False** (usually prints URL).
    *   **Activation**: You must pass `inbrowser=True` to the `launch()` method.
    *   **Implementation**:
        ```python
        import webbrowser
        if inbrowser:
            webbrowser.open(url)
        ```

*   **Marimo**:
    *   **Default**: **True** (Auto-opens).
    *   **Activation**: Commands like `marimo edit` or `marimo run` open the browser immediately to reduce friction.
    *   **Deactivation**: Users must pass `--headless` to stop this behavior (useful for remote servers/Docker).

*   **MLflow**:
    *   **Default**: **False** (Never opens).
    *   **Logic**: As a developer tool/server often running in the background or on a remote cluster, it simply prints the URL to `stdout`:
        ```text
        [INFO] Starting gunicorn 20.1.0
        [INFO] Listening at: http://127.0.0.1:5000
        ```

## Summary

| Feature | Gradio | Marimo | MLflow |
|---------|--------|--------|--------|
| Static files location | `gradio/templates/frontend` | `marimo/_static` | `mlflow/server/js/build` |
| Port conflict strategy | Auto-increment from 7860 | Auto-increment from 2718 | Fail fast on 5000 |
| Browser auto-open | Opt-in (`inbrowser=True`) | On by default | Never |
| Web framework | FastAPI | Starlette/Uvicorn | Flask/Gunicorn |

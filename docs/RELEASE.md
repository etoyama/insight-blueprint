# Release Procedure

Step-by-step guide for publishing insight-blueprint to PyPI.

## Prerequisites

Install the upload tool:

```bash
uv tool install twine
```

Ensure you have a PyPI account and API token. Create a token at https://pypi.org/manage/account/token/ and save it in `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE
```

## Step 1: Version Bump

Edit the version in `pyproject.toml`:

```bash
# Open pyproject.toml and update the version field
# e.g., version = "0.1.0" -> version = "0.2.0"
```

Follow [Semantic Versioning](https://semver.org/):
- **Patch** (0.1.0 -> 0.1.1): Bug fixes, documentation updates
- **Minor** (0.1.0 -> 0.2.0): New features, backward-compatible changes
- **Major** (0.1.0 -> 1.0.0): Breaking changes

## Step 2: Build Frontend

Build the frontend assets that will be included in the wheel:

```bash
poe build-frontend
```

Verify the static files exist:

```bash
ls src/insight_blueprint/static/
# Should show index.html, assets/, etc.
```

## Step 3: Build the Package

Clean previous builds and create the wheel:

```bash
rm -rf dist/
uv build --wheel
```

This creates a wheel (.whl) in `dist/`.

> **Important**: Use `--wheel` to build the wheel directly. Do NOT use bare
> `uv build` — it builds an sdist first then creates the wheel from that sdist.
> Since `src/insight_blueprint/static/` is in `.gitignore` (build artifacts
> should not be committed), hatchling's sdist excludes it, and the resulting
> wheel will be missing frontend assets. Building the wheel directly honors the
> `artifacts` setting in `[tool.hatch.build.targets.wheel]` and includes
> static files correctly.

## Step 4: Verify the Wheel

### 4a: Check wheel contents

Verify that all required files are included:

```bash
# Check skills are included
unzip -l dist/*.whl | grep _skills/
# Should list all SKILL.md files

# Check frontend assets are included
unzip -l dist/*.whl | grep static/
# Should list index.html, JS, CSS files

# Check LICENSE is included
unzip -l dist/*.whl | grep LICENSE
```

### 4b: Check metadata

```bash
unzip -p dist/*.whl '*/METADATA' | head -30
```

Verify these fields are present:
- `License: MIT`
- `Classifier:` entries (Development Status, License, Python versions)
- `Project-URL:` entries (Homepage, Repository, Bug Tracker)

### 4c: Check SKILL.md structure

```bash
# Verify all skills have version field
for f in $(unzip -l dist/*.whl | grep SKILL.md | awk '{print $4}'); do
    echo "=== $f ==="
    unzip -p dist/*.whl "$f" | head -5
done
```

## Step 5: Local Install Test

Test the wheel in an isolated environment before uploading:

```bash
# Create a temporary test environment
cd /tmp
mkdir insight-blueprint-test && cd insight-blueprint-test
python -m venv .venv
source .venv/bin/activate

# Install from the local wheel
pip install /path/to/insight-blueprint/dist/insight_blueprint-*.whl

# Test: Initialize a project and verify skills are copied
insight-blueprint --project /tmp/insight-blueprint-test --headless &
SERVER_PID=$!
sleep 3

# Verify skills were copied
ls .claude/skills/
# Should show: analysis-design/ catalog-register/

# Verify skill files
cat .claude/skills/analysis-design/SKILL.md | head -5
# Should show frontmatter with name and version

# Verify WebUI is running
curl -s http://127.0.0.1:3000 | head -5
# Should return HTML

# Clean up
kill $SERVER_PID
deactivate
cd /tmp && rm -rf insight-blueprint-test
```

## Step 6: Upload to PyPI

Once local testing passes, upload to PyPI:

```bash
twine upload dist/*
```

Twine will prompt for credentials if `~/.pypirc` is not configured.

After upload, verify the package page at:
https://pypi.org/project/insight-blueprint/

### Verify Remote Install

```bash
# Test installation from PyPI
uvx insight-blueprint --help
```

## Troubleshooting

### "File already exists" error on upload

PyPI does not allow overwriting existing versions. Bump the version number and rebuild.

### Missing files in wheel

Check `pyproject.toml` build configuration:
- `packages = ["src/insight_blueprint"]` includes Python files
- `artifacts = ["src/insight_blueprint/static/**"]` includes frontend assets
- Skills in `src/insight_blueprint/_skills/` are included automatically via the packages path

### Frontend assets not included

1. Run `poe build-frontend` before building. The static files must exist at build time.
2. Use `uv build --wheel` (not bare `uv build`). The sdist path excludes `.gitignore`
   entries, which includes `src/insight_blueprint/static/`.

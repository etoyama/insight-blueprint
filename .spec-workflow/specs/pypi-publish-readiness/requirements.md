# Requirements: PyPI Publish Readiness

## Introduction

insight-blueprint を PyPI に公開可能な状態にするための整備。MCP サーバー + React WebUI という構成で、`pip install insight-blueprint` / `uvx insight-blueprint` で即座に動作する wheel を確実にビルド・配布する仕組みを構築する。

現状、コードとテスト（707 tests passing）は公開可能な品質に達しているが、パッケージメタデータの不備（py.typed 欠落、version 二重管理）、リリース自動化の欠如（publish workflow なし）、フロントエンドアセット同梱の保証がない（wheel 検証なし）という3つのギャップがある。

## Alignment with Product Vision

product.md の Distribution 方針「PyPI パッケージ（`pip install insight-blueprint`）」を実現するための基盤整備。tech.md の Build System（hatchling + Vite）構成を前提に、ビルド→検証→配布のパイプラインを確立する。

## Requirements

### REQ-1: Package Metadata Completeness

**User Story:** As a package consumer, I want insight-blueprint to have complete and standard PyPI metadata, so that I can discover the package, verify its type annotations, and track changes across versions.

#### Functional Requirements

- FR-1.1: `src/insight_blueprint/py.typed` marker file SHALL exist (PEP 561 compliance)
- FR-1.2: `py.typed` SHALL be included in the built wheel
- FR-1.3: Package version SHALL have a single source of truth in `pyproject.toml`
- FR-1.4: `__init__.py` SHALL derive `__version__` from `importlib.metadata.version()` instead of hardcoding
- FR-1.5: CHANGELOG.md SHALL exist in the project root, following Keep a Changelog format
- FR-1.6: CHANGELOG.md SHALL contain a `[0.1.0]` section documenting the initial release
- FR-1.7: PyPI classifiers SHALL include `Topic :: Scientific/Engineering :: Information Analysis` and `Intended Audience :: Science/Research`

#### Acceptance Criteria

- AC-1.1: WHEN a user installs insight-blueprint THEN `py.typed` SHALL be present in the installed package directory
- AC-1.2: WHEN `uv build` is executed THEN the resulting wheel SHALL contain `insight_blueprint/py.typed`
- AC-1.3: WHEN `__version__` is accessed at runtime THEN it SHALL return the same value as `pyproject.toml` `[project].version`
- AC-1.4: WHEN a developer updates the version THEN only `pyproject.toml` needs to be changed (no other file references a hardcoded version string)
- AC-1.5: WHEN the wheel is inspected THEN METADATA SHALL contain the scientific classifiers

### REQ-2: Publish Workflow Automation

**User Story:** As a maintainer, I want an automated publish pipeline triggered by git tags, so that releasing to PyPI is a single `git push --tags` operation with no manual steps.

#### Functional Requirements

- FR-2.1: A GitHub Actions workflow (`.github/workflows/publish.yml`) SHALL be triggered on tag push matching `v*`
- FR-2.2: The workflow SHALL build frontend assets (`npm ci && npm run build` in `frontend/`) before building the Python wheel
- FR-2.3: The workflow SHALL build both sdist and wheel using `uv build`
- FR-2.4: The workflow SHALL upload to PyPI using Trusted Publisher (OIDC), requiring no API token in secrets
- FR-2.5: The workflow SHALL use a GitHub Environment named `pypi` with deployment protection rules

#### Acceptance Criteria

- AC-2.1: WHEN a tag matching `v*` is pushed THEN the publish workflow SHALL trigger automatically
- AC-2.2: WHEN the workflow executes THEN frontend build SHALL complete before `uv build`
- AC-2.3: WHEN PyPI upload is attempted THEN authentication SHALL use OIDC (no `PYPI_TOKEN` secret required)
- AC-2.4: WHEN a non-tag push occurs THEN the publish workflow SHALL NOT trigger

### REQ-3: Wheel Integrity Verification

**User Story:** As a maintainer, I want the CI pipeline to verify that built wheels contain frontend assets, so that broken releases (missing WebUI) are caught before publishing.

#### Functional Requirements

- FR-3.1: The publish workflow SHALL verify that the wheel contains `insight_blueprint/static/index.html`
- FR-3.2: The publish workflow SHALL verify that the wheel contains at least one `.js` file under `insight_blueprint/static/assets/`
- FR-3.3: IF verification fails THEN the workflow SHALL abort before PyPI upload
- FR-3.4: The CI workflow (`ci.yml`) SHALL include a `build-check` job that builds the wheel (with frontend) and verifies static asset inclusion on every PR
- FR-3.5: The `build-check` job SHALL depend on existing `python` and `frontend` jobs (runs after both pass)

#### Acceptance Criteria

- AC-3.1: WHEN `uv build` produces a wheel without `static/index.html` THEN the publish workflow SHALL fail with a descriptive error message
- AC-3.2: WHEN `uv build` produces a wheel without JS assets in `static/assets/` THEN the publish workflow SHALL fail with a descriptive error message
- AC-3.3: WHEN a PR is opened THEN the `build-check` CI job SHALL verify wheel integrity
- AC-3.4: WHEN the `build-check` job fails THEN the PR SHALL be blocked from merging (via branch protection)

## Non-Functional Requirements

### Code Architecture and Modularity

- The publish workflow SHALL be a separate file from the existing CI workflow (`ci.yml`), following single-responsibility principle
- The wheel verification logic SHALL be inline in the workflow (no external script), keeping the solution self-contained

### Reliability

- The publish workflow SHALL separate the `build` job from the `publish` job, so that build artifacts are verified before upload
- The build job SHALL upload artifacts using `actions/upload-artifact`, and the publish job SHALL download them (no re-build)

### Security

- PyPI authentication SHALL use Trusted Publisher (OIDC) — no long-lived API tokens
- The `pypi` GitHub Environment SHALL require manual approval or be restricted to the `main` branch (configurable by maintainer)

### Maintainability

- Version management SHALL be single-source (pyproject.toml only) to prevent version drift
- CHANGELOG.md SHALL be manually maintained (no auto-generation) to ensure meaningful release notes

## Out of Scope

- **TestPyPI staging**: Publishing to TestPyPI before production PyPI (can be added later)
- **Automated version bumping**: Tools like `bump2version` or `python-semantic-release` (manual version management is sufficient for now)
- **Multi-platform wheel builds**: Only `py3-none-any` wheel is needed (pure Python + bundled static assets)
- **GitHub Release creation**: Auto-creating GitHub Releases from tags (can be added as a follow-up)
- **README rendering validation**: Verifying README renders correctly on PyPI (low risk with Markdown)

## Glossary

| Term | Definition |
|------|-----------|
| Trusted Publisher | PyPI's OIDC-based authentication for GitHub Actions, eliminating the need for API tokens |
| py.typed | PEP 561 marker file indicating a package ships inline type annotations |
| wheel | Python binary distribution format (`.whl`), the standard for `pip install` |
| sdist | Source distribution format (`.tar.gz`), built alongside wheel for completeness |
| hatch artifacts | Hatchling build configuration that includes gitignored files in the wheel |

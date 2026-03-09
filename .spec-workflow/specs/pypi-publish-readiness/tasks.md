# Tasks: PyPI Publish Readiness

- [ ] 1.1. GitHub Actions SHA pin 調査
  - File: `.claude/docs/research/sha-pins.md`
  - Purpose: publish.yml で使用する GitHub Actions の SHA commit hash を確定する
  - Leverage: GitHub 公式リポジトリの release tags
  - Requirements: REQ-2 (FR-2.4, FR-2.5)
  - Dependencies: なし
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DevOps Engineer specializing in GitHub Actions security | Task: Research and document the exact SHA commit hashes for the following GitHub Actions at their current latest stable versions: actions/checkout, actions/setup-node, astral-sh/setup-uv, actions/upload-artifact, actions/download-artifact, pypa/gh-action-pypi-publish. Save results to .claude/docs/research/sha-pins.md with format "action: sha # vX.Y.Z". Also check if the project's existing dependabot.yml covers GitHub Actions version updates. | Restrictions: Use only official releases, not pre-releases. Verify SHA matches the tagged release. | _Leverage: .github/dependabot.yml for existing automation config | _Requirements: FR-2.4, FR-2.5 | Success: sha-pins.md contains verified SHA for all 6 actions, with version comments. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 1.2. Version テスト作成 + `__init__.py` version 一元化 (TDD)
  - File: `tests/test_version.py`, `src/insight_blueprint/__init__.py`
  - Purpose: version の single source of truth を実現する。テストを先に書き、実装で Green にする
  - Leverage: `pyproject.toml` version フィールド、`importlib.metadata`
  - Requirements: REQ-1 (FR-1.3, FR-1.4, AC-1.3, AC-1.4)
  - Dependencies: なし
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer specializing in packaging and TDD | Task: (1) RED: Create tests/test_version.py with TestVersion (test_version_matches_pyproject, test_version_is_pep440) and TestVersionFallback (test_version_fallback_on_package_not_found, test_version_fallback_is_pep440). For the fallback test, mock importlib.metadata.version to raise PackageNotFoundError, then importlib.reload(insight_blueprint). (2) GREEN: Modify src/insight_blueprint/__init__.py to use importlib.metadata.version("insight-blueprint") with try/except PackageNotFoundError fallback to "0.0.0+unknown". Remove the hardcoded __version__ = "0.1.0". | Restrictions: Do not change pyproject.toml version. Fallback value must be PEP 440 compliant. Ensure reload-based test has proper cleanup. | _Leverage: pyproject.toml [project].version as single source | _Requirements: FR-1.3, FR-1.4, AC-1.3, AC-1.4 | Success: test_version.py passes (4 tests). __init__.py has no hardcoded version string. `uv run python -c "import insight_blueprint; print(insight_blueprint.__version__)"` returns pyproject.toml version. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 1.3. py.typed マーカー + classifiers 更新
  - File: `src/insight_blueprint/py.typed`, `pyproject.toml`
  - Purpose: PEP 561 準拠の型情報マーカーと PyPI 検索性向上の classifiers 追加
  - Leverage: 既存 pyproject.toml classifiers
  - Requirements: REQ-1 (FR-1.1, FR-1.2, FR-1.7, AC-1.5)
  - Dependencies: なし
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Packaging Engineer | Task: (1) Create empty file src/insight_blueprint/py.typed (PEP 561 marker). (2) Add classifiers to pyproject.toml: "Intended Audience :: Science/Research" and "Topic :: Scientific/Engineering :: Information Analysis". (3) Verify py.typed is included in wheel by running `uv build` and checking with `uv run python -c "import zipfile; z=zipfile.ZipFile(next(__import__('pathlib').Path('dist').glob('*.whl'))); print([n for n in z.namelist() if 'py.typed' in n])"`. | Restrictions: py.typed must be an empty file (no content). Do not modify other classifiers. | _Leverage: existing pyproject.toml structure, hatch artifacts config | _Requirements: FR-1.1, FR-1.2, FR-1.7, AC-1.5 | Success: py.typed exists, wheel contains insight_blueprint/py.typed, classifiers added. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 1.4. CHANGELOG.md 作成
  - File: `CHANGELOG.md`
  - Purpose: Keep a Changelog 形式で初期リリースノートを作成
  - Leverage: README.md の Features セクション
  - Requirements: REQ-1 (FR-1.5, FR-1.6)
  - Dependencies: なし
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical Writer | Task: Create CHANGELOG.md in project root following Keep a Changelog format (https://keepachangelog.com/). Include header with format description, [Unreleased] section (empty), and [0.1.0] section with date. For 0.1.0, document initial features from README.md: Analysis Design management, Data Catalog, Review Workflow, Domain Knowledge, Data Lineage, WebUI Dashboard, Bundled Skills (5 skills). Group under "Added" subsection. Include link references at bottom. | Restrictions: Use English for content. Do not add entries for unreleased changes. Date for 0.1.0 should be the actual initial release date or today if not yet released. | _Leverage: README.md Features section for content | _Requirements: FR-1.5, FR-1.6 | Success: CHANGELOG.md exists, has valid Keep a Changelog structure, [0.1.0] section documents all key features. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 2.1. verify_wheel.py テスト作成 + スクリプト実装 (TDD)
  - File: `tests/test_verify_wheel.py`, `scripts/verify_wheel.py`
  - Purpose: wheel 検証ロジックを standalone スクリプトとして実装する。CI とローカルで共用
  - Leverage: `zipfile` 標準ライブラリ
  - Requirements: REQ-3 (FR-3.1, FR-3.2, FR-3.3, AC-3.1, AC-3.2)
  - Dependencies: 1.3 (py.typed が存在すること)
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer specializing in packaging tooling and TDD | Task: (1) RED: Create tests/test_verify_wheel.py with TestVerifyWheel class. Tests create minimal .whl files (ZIP archives) in tmp_path with controlled contents. Test cases: test_verify_valid_wheel (has index.html + JS + py.typed → returns success), test_verify_missing_index_html (→ fails with descriptive error), test_verify_missing_js_assets (→ fails), test_verify_missing_py_typed (→ fails). (2) GREEN: Create scripts/verify_wheel.py with a verify_wheel(whl_path) function that returns (success: bool, messages: list[str]). Also a main() that accepts --dist-dir argument (default "dist/"), finds the .whl file, runs verify, prints results, exits with code 0 or 1. (3) The script must check: insight_blueprint/static/index.html exists, at least one .js file under insight_blueprint/static/assets/, insight_blueprint/py.typed exists. | Restrictions: Use only stdlib (zipfile, pathlib, argparse, sys). No external dependencies. The verify function must be importable for testing. | _Leverage: zipfile stdlib | _Requirements: FR-3.1, FR-3.2, FR-3.3, AC-3.1, AC-3.2 | Success: test_verify_wheel.py passes (4 tests). scripts/verify_wheel.py is executable and importable. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 2.2. check_tag_version.py テスト作成 + スクリプト実装 (TDD)
  - File: `tests/test_check_tag_version.py`, `scripts/check_tag_version.py`
  - Purpose: git tag と pyproject.toml version の一致チェックを standalone スクリプトとして実装
  - Leverage: `tomllib` (Python 3.11+)、`subprocess` (git describe)
  - Requirements: REQ-2 (FR-2.1, AC-2.1)
  - Dependencies: なし
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python Developer specializing in release tooling and TDD | Task: (1) RED: Create tests/test_check_tag_version.py. Test cases: test_matching_tag_and_version (tag "v0.1.0" with pyproject version "0.1.0" → success), test_mismatched_tag_and_version (tag "v0.2.0" with pyproject version "0.1.0" → failure with descriptive error), test_tag_without_v_prefix (tag "0.1.0" → failure), test_no_tag_provided_and_no_git_tag (→ failure with guidance). Use tmp_path with a minimal pyproject.toml for isolation. (2) GREEN: Create scripts/check_tag_version.py with check_tag_version(tag: str, pyproject_path: Path) function returning (success: bool, message: str). Main accepts --tag (optional, falls back to git describe --tags --exact-match) and --pyproject (default "pyproject.toml"). Uses tomllib to read version. | Restrictions: Use only stdlib (tomllib, subprocess, argparse, pathlib, sys). tag must start with "v" prefix. | _Leverage: tomllib (Python 3.11+ stdlib) | _Requirements: FR-2.1, AC-2.1 | Success: test_check_tag_version.py passes (4 tests). scripts/check_tag_version.py is executable and importable. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 2.3. poe タスク追加 (verify-wheel, check-tag-version, release-dry-run)
  - File: `pyproject.toml`
  - Purpose: ローカル開発者がリリース前検証を手元で実行できるようにする
  - Leverage: 既存 poe タスク構成 (build-frontend 等)
  - Requirements: REQ-3 (FR-3.4, AC-3.3) + テスト設計 Local-01, Local-02
  - Dependencies: 2.1, 2.2 (スクリプトが存在すること)
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python DevOps Engineer | Task: Add three poe tasks to pyproject.toml: (1) verify-wheel: cmd = "uv run python scripts/verify_wheel.py", help = "Verify wheel contains frontend assets and py.typed". (2) check-tag-version: cmd = "uv run python scripts/check_tag_version.py", help = "Check git tag matches pyproject.toml version". (3) release-dry-run: sequence = ["build-frontend", {shell = "rm -rf dist/ && uv build"}, "verify-wheel", {shell = "uvx --from twine twine check dist/*"}], help = "Full release dry-run: build frontend, build wheel, verify, twine check". Verify by running `poe release-dry-run` locally. | Restrictions: Do not add twine to dev dependencies (use uvx). release-dry-run must clean dist/ before building to avoid stale files. Do not modify existing poe tasks. | _Leverage: existing poe task patterns in pyproject.toml | _Requirements: FR-3.4, AC-3.3 | Success: `poe verify-wheel`, `poe check-tag-version`, and `poe release-dry-run` all execute successfully. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 2.4. Wheel ビルド統合テスト作成
  - File: `tests/test_packaging.py`
  - Purpose: 実際にビルドした wheel のメタデータと同梱物を検証する統合テスト
  - Leverage: `subprocess` (uv build)、`zipfile`、`tmp_path`
  - Requirements: REQ-1 (AC-1.1, AC-1.2, AC-1.3, AC-1.5), REQ-3 (AC-3.1, AC-3.2, AC-3.3)
  - Dependencies: 1.2, 1.3 (version + py.typed が実装済み)
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python QA Engineer specializing in packaging tests | Task: Create tests/test_packaging.py with two test classes. (1) TestWheelContents: test_wheel_contains_py_typed (Integ-01), test_wheel_metadata_version_matches_pyproject (Integ-02), test_wheel_metadata_contains_scientific_classifiers (Integ-03). These tests run `subprocess.run(["uv", "build", "--wheel", "--out-dir", str(tmp_dir)], check=True)` and inspect the resulting wheel with zipfile. Read METADATA from the wheel to check version and classifiers. Read pyproject.toml with tomllib for comparison. (2) TestWheelStaticAssets: test_wheel_contains_index_html (Integ-04), test_wheel_contains_js_bundle (Integ-04). These tests check for frontend assets. If src/insight_blueprint/static/index.html does not exist, use pytest.skip("Frontend not built"). Use tmp_path for build output to avoid polluting dist/. | Restrictions: Do not run poe build-frontend in tests (too slow, CI handles this). Use pytest.skip for frontend-dependent tests when static/ is missing. Each test must clean up its tmp build dir. | _Leverage: zipfile, subprocess, tomllib, tmp_path fixture | _Requirements: AC-1.1, AC-1.2, AC-1.3, AC-1.5, AC-3.1, AC-3.2, AC-3.3 | Success: test_packaging.py passes. Integ-01/02/03 always run. Integ-04 runs when frontend is built, skips otherwise. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 3.1. publish.yml 作成
  - File: `.github/workflows/publish.yml`
  - Purpose: tag push → build → verify → PyPI upload の自動 publish ワークフロー
  - Leverage: SHA pins (タスク 1.1)、scripts/verify_wheel.py、scripts/check_tag_version.py
  - Requirements: REQ-2 (FR-2.1〜FR-2.5, AC-2.1〜AC-2.4), REQ-3 (FR-3.1〜FR-3.3, AC-3.1, AC-3.2)
  - Dependencies: 1.1, 2.1, 2.2 (SHA pins + スクリプト完成)
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DevOps Engineer specializing in GitHub Actions and PyPI publishing | Task: Create .github/workflows/publish.yml. Structure: (1) on.push.tags ["v*"]. (2) build job: checkout (SHA pinned) → check_tag_version.py (extract tag from GITHUB_REF, compare with pyproject.toml) → setup-node (SHA pinned, node 22, cache npm) → npm ci + npm run build in frontend/ → setup-uv (SHA pinned) → uv build → verify_wheel.py → twine check (uvx --from twine twine check dist/*) → upload-artifact dist/. (3) publish job: needs build, runs-on ubuntu-latest, environment pypi, permissions id-token write. Steps: download-artifact → pypa/gh-action-pypi-publish (SHA pinned). Use SHA pins from .claude/docs/research/sha-pins.md with version comments. | Restrictions: All actions must be SHA pinned (from task 1.1 research). No PYPI_TOKEN secret — Trusted Publisher only. Scripts must be called via `python scripts/xxx.py`, not inline duplication. Tag version check must use --tag flag with extracted tag. | _Leverage: .claude/docs/research/sha-pins.md for SHA pins, scripts/verify_wheel.py, scripts/check_tag_version.py | _Requirements: FR-2.1〜FR-2.5, AC-2.1〜AC-2.4, FR-3.1〜FR-3.3, AC-3.1, AC-3.2 | Success: publish.yml is valid YAML, uses SHA-pinned actions, has correct trigger/permissions/environment, calls shared scripts. Validate with actionlint if available. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 3.2. ci.yml build-check ジョブ追加
  - File: `.github/workflows/ci.yml`
  - Purpose: PR ごとに wheel ビルド + フロントエンド同梱を検証するジョブを追加
  - Leverage: 既存 ci.yml の python / frontend ジョブ、scripts/verify_wheel.py
  - Requirements: REQ-3 (FR-3.4, FR-3.5, AC-3.3, AC-3.4)
  - Dependencies: 2.1 (verify_wheel.py 完成)
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CI/CD Engineer | Task: Add a build-check job to .github/workflows/ci.yml. Structure: needs [python, frontend], runs-on ubuntu-latest. Steps: checkout → setup-node (node 22, cache npm) → npm ci + npm run build in frontend/ → setup-uv → uv build → python scripts/verify_wheel.py → uvx --from twine twine check dist/*. This job uses the same major-tag action versions as existing ci.yml jobs (not SHA pinned — consistency with existing ci.yml). | Restrictions: Do not modify existing python or frontend jobs. Do not SHA pin actions in ci.yml (only publish.yml uses SHA pins). build-check must depend on [python, frontend] via needs. | _Leverage: existing ci.yml structure, scripts/verify_wheel.py | _Requirements: FR-3.4, FR-3.5, AC-3.3, AC-3.4 | Success: ci.yml has build-check job, depends on python and frontend, runs verify_wheel.py and twine check. Existing jobs unchanged. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

- [ ] 3.3. 最終検証: poe release-dry-run 実行 + 全テスト通過
  - File: なし（検証のみ）
  - Purpose: 全タスクの成果物が統合的に動作することを確認する
  - Leverage: poe release-dry-run, poe all
  - Requirements: 全 REQ
  - Dependencies: 1.1〜3.2 全タスク
  - _Prompt: Implement the task for spec pypi-publish-readiness, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Release Engineer | Task: Final verification of all deliverables. (1) Run `poe all` — lint, typecheck, test must all pass. (2) Run `poe release-dry-run` — build-frontend, uv build, verify-wheel, twine check must all pass. (3) Verify test count: new tests (test_version.py, test_verify_wheel.py, test_check_tag_version.py, test_packaging.py) should add ~15 tests to the existing 707. (4) Verify CHANGELOG.md exists and has [0.1.0] section. (5) Spot-check publish.yml: trigger is v* tags, SHA pinned actions, environment pypi, id-token write. (6) Spot-check ci.yml: build-check job exists, needs [python, frontend]. Report any issues found. | Restrictions: Do not fix issues in this task — report only. If issues exist, reopen the relevant prior task. | _Leverage: poe all, poe release-dry-run | _Requirements: All | Success: All checks pass. No issues found. Report "All clear" with test count and verification results. Mark task as [-] in tasks.md before starting, log with log-implementation after, mark [x] when done._

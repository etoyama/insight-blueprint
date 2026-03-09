# PyPI Publish Readiness - テスト設計書

**Spec ID**: `pypi-publish-readiness`
**種別**: 新規機能（CI/CD パイプライン + パッケージング整備）

## 概要

本ドキュメントは、requirements.md の各 Acceptance Criteria に対して、どのテストレベルでカバーするかを定義する。

この spec の特性上、テスト対象は通常のアプリケーションロジックではなく**ビルドパイプラインとパッケージメタデータ**である。GitHub Actions ワークフローのロジックをローカルでもテスト可能にするため、検証ロジックを standalone Python スクリプトとして切り出し、pytest / poe タスク / CI の3箇所から共通実行する設計とする（Codex レビュー反映）。

## テストレベル定義

| テストレベル | 略称 | 説明 | ツール |
|-------------|------|------|--------|
| 単体テスト | Unit | 個々の関数・モジュールを独立してテスト。外部依存はモック化 | pytest, unittest.mock |
| 統合テスト | Integ | 実際のビルド成果物（wheel）を生成・検査するテスト。ファイルシステム操作を含む | pytest, subprocess (uv build) |
| ローカル実行テスト | Local | poe タスクによるローカル実行。CI と同一の検証ロジックを開発者が手元で実行 | poe, scripts/ |
| CI テスト | CI | GitHub Actions 上で実行。publish.yml / ci.yml のジョブとして実行 | GitHub Actions |

## 要件カバレッジマトリクス

### REQ-1: Package Metadata Completeness

| AC# | Acceptance Criteria | Unit | Integ | Local | CI |
|-----|---------------------|:----:|:-----:|:-----:|:--:|
| 1.1 | py.typed が installed package に存在 | - | Integ-01 | Local-01 | CI-01 |
| 1.2 | wheel に py.typed が含まれる | - | Integ-01 | Local-01 | CI-01 |
| 1.3 | `__version__` が pyproject.toml と一致 | Unit-01 | Integ-02 | - | CI-01 |
| 1.4 | version 変更は pyproject.toml のみ | Unit-01, Unit-02 | - | - | - |
| 1.5 | wheel METADATA に scientific classifiers | - | Integ-03 | Local-01 | CI-01 |

> 備考: AC-1.1 / AC-1.2 はビルド成果物の検査のため Integ レベル。AC-1.3 / AC-1.4 は `__init__.py` のコードロジックのため Unit レベルでもカバー。

### REQ-2: Publish Workflow Automation

| AC# | Acceptance Criteria | Unit | Integ | Local | CI |
|-----|---------------------|:----:|:-----:|:-----:|:--:|
| 2.1 | tag push で publish workflow がトリガー | - | - | - | CI-02 |
| 2.2 | frontend build が uv build の前に実行 | - | - | Local-02 | CI-02 |
| 2.3 | OIDC 認証（トークン不要） | - | - | - | CI-02 |
| 2.4 | non-tag push で workflow が発火しない | - | - | - | CI-02 |

> 備考: AC-2.1 / AC-2.3 / AC-2.4 は GitHub Actions のトリガー制御であり、ローカルでの完全再現は不可。publish.yml の YAML 構造の静的確認で補完する。AC-2.2 は `poe release-dry-run` でローカル検証可能。

### REQ-3: Wheel Integrity Verification

| AC# | Acceptance Criteria | Unit | Integ | Local | CI |
|-----|---------------------|:----:|:-----:|:-----:|:--:|
| 3.1 | static/index.html 欠落で publish 失敗 | Unit-03 | Integ-04 | Local-01 | CI-01 |
| 3.2 | JS assets 欠落で publish 失敗 | Unit-03 | Integ-04 | Local-01 | CI-01 |
| 3.3 | PR の build-check ジョブで wheel 検証 | - | - | Local-01 | CI-01 |
| 3.4 | build-check 失敗で PR マージ不可 | - | - | - | CI-01 |

> 備考: AC-3.4 は GitHub branch protection の設定であり、テストではなく設定確認で検証。

---

## 開発環境整備（Codex レビュー反映）

本 spec のテストを実行するために、以下の開発環境整備が**実装タスクに含まれる**。

### standalone スクリプト

CI のインライン検証ロジックを Python スクリプトに切り出し、CI とローカルで共通実行する。

| スクリプト | 用途 | 引数 |
|-----------|------|------|
| `scripts/verify_wheel.py` | wheel 内の static assets 存在確認 + py.typed 確認 | `--dist-dir dist/`（省略時カレント `dist/`） |
| `scripts/check_tag_version.py` | git tag と pyproject.toml version の一致確認 | `--tag vX.Y.Z`（省略時 `git describe --tags` で自動取得） |

### poe タスク追加

```toml
[tool.poe.tasks.verify-wheel]
cmd = "uv run python scripts/verify_wheel.py"
help = "Verify wheel contains frontend assets and py.typed"

[tool.poe.tasks.check-tag-version]
cmd = "uv run python scripts/check_tag_version.py"
help = "Check git tag matches pyproject.toml version"

[tool.poe.tasks.release-dry-run]
sequence = ["build-frontend", {shell = "uv build"}, "verify-wheel", {shell = "uvx --from twine twine check dist/*"}]
help = "Full release dry-run: build frontend, build wheel, verify, twine check"
```

### twine の扱い

dev deps には追加しない。`uvx --from twine twine check dist/*` で一時実行する（Codex 推奨の軽量パターン）。

---

## 単体テストシナリオ

### Unit-01: `__init__.py` - version 正常取得

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-01 |
| **テストファイル** | `tests/test_version.py` |
| **テストクラス** | `TestVersion` |
| **目的** | `__version__` が pyproject.toml の version と一致することを検証 |

> **設計判断**: editable install 環境（`uv sync`）では `importlib.metadata.version()` が正常動作するため、mock なしでの実行も有効。

**テストケース:**

| 関数名 | 検証内容 | カバーする AC |
|--------|----------|-------------|
| `test_version_matches_pyproject` | `__version__` が pyproject.toml の `[project].version` と一致 | 1.3 |
| `test_version_is_pep440` | `__version__` が PEP 440 準拠のバージョン文字列 | 1.3 |

---

### Unit-02: `__init__.py` - version fallback

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-02 |
| **テストファイル** | `tests/test_version.py` |
| **テストクラス** | `TestVersionFallback` |
| **目的** | `PackageNotFoundError` 発生時に fallback 値が返ることを検証 |

> **設計判断（Codex レビュー反映）**: `importlib.metadata.version` を mock して `PackageNotFoundError` を raise させた後、`importlib.reload(insight_blueprint)` でモジュールを再評価する。テスト後に `reload` で元に戻す cleanup が必要。

**テストケース:**

| 関数名 | 検証内容 | カバーする AC |
|--------|----------|-------------|
| `test_version_fallback_on_package_not_found` | `PackageNotFoundError` 時に `"0.0.0+unknown"` が返る | 1.4 |
| `test_version_fallback_is_pep440` | fallback 値が PEP 440 準拠 | 1.4 |

---

### Unit-03: `scripts/verify_wheel.py` - 検証ロジック

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-03 |
| **テストファイル** | `tests/test_verify_wheel.py` |
| **テストクラス** | `TestVerifyWheel` |
| **目的** | wheel 検証スクリプトの判定ロジックを、テスト用の wheel ファイルを使って検証 |

> **設計判断**: 実際の `uv build` は Integ テストに任せる。Unit では `zipfile` で最小限の `.whl` を生成し、検証関数に渡す。

**テストケース:**

| 関数名 | 検証内容 | カバーする AC |
|--------|----------|-------------|
| `test_verify_valid_wheel` | index.html + JS + py.typed を含む wheel → 成功 | 3.1, 3.2 |
| `test_verify_missing_index_html` | index.html 欠落 → 失敗 + エラーメッセージに "index.html" | 3.1 |
| `test_verify_missing_js_assets` | JS ファイル欠落 → 失敗 + エラーメッセージに "assets" | 3.2 |
| `test_verify_missing_py_typed` | py.typed 欠落 → 失敗 + エラーメッセージに "py.typed" | 1.2 |

---

## 統合テストシナリオ

### Integ-01: Wheel ビルド - py.typed 同梱

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-01 |
| **テストファイル** | `tests/test_packaging.py` |
| **テストクラス** | `TestWheelContents` |
| **目的** | 実際にビルドした wheel に py.typed が含まれることを検証 |

> **設計判断**: `uv build` を subprocess で実行し、生成された wheel を zipfile で検査する。テスト実行に数秒かかるが、ビルドパイプラインの実テストとして価値がある。`tmp_path` で隔離した output dir を使い、既存の `dist/` を汚さない。

**テストケース:**

| 関数名 | 検証内容 | カバーする AC |
|--------|----------|-------------|
| `test_wheel_contains_py_typed` | wheel 内に `insight_blueprint/py.typed` が存在 | 1.1, 1.2 |

---

### Integ-02: Wheel ビルド - METADATA version 一致

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-02 |
| **テストファイル** | `tests/test_packaging.py` |
| **テストクラス** | `TestWheelContents` |
| **目的** | wheel の METADATA に記載された version が pyproject.toml と一致することを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーする AC |
|--------|----------|-------------|
| `test_wheel_metadata_version_matches_pyproject` | METADATA の `Version:` が pyproject.toml と一致 | 1.3 |

---

### Integ-03: Wheel ビルド - classifiers 検証

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-03 |
| **テストファイル** | `tests/test_packaging.py` |
| **テストクラス** | `TestWheelContents` |
| **目的** | wheel の METADATA に scientific classifiers が含まれることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーする AC |
|--------|----------|-------------|
| `test_wheel_metadata_contains_scientific_classifiers` | METADATA に `Topic :: Scientific/Engineering` が含まれる | 1.5 |

---

### Integ-04: Wheel ビルド - static assets 検証（フロントエンド同梱）

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-04 |
| **テストファイル** | `tests/test_packaging.py` |
| **テストクラス** | `TestWheelStaticAssets` |
| **目的** | `poe build-frontend` + `uv build` で生成した wheel にフロントエンドアセットが含まれることを検証 |

> **設計判断**: このテストは `poe build-frontend` が実行済みであることを前提とする（CI では先行ジョブで実行済み）。ローカルでは `poe release-dry-run` 経由で実行するか、明示的に `poe build-frontend` を事前実行する。テスト自体は `uv build` + zipfile 検査のみ行う。フロントエンド未ビルド時は `pytest.skip()` で明示的にスキップする。

**テストケース:**

| 関数名 | 検証内容 | カバーする AC |
|--------|----------|-------------|
| `test_wheel_contains_index_html` | wheel 内に `insight_blueprint/static/index.html` が存在 | 3.1, 3.3 |
| `test_wheel_contains_js_bundle` | wheel 内に `insight_blueprint/static/assets/*.js` が最低1つ存在 | 3.2, 3.3 |

---

## ローカル実行テストシナリオ

### Local-01: poe verify-wheel

| 項目 | 内容 |
|------|------|
| **テストID** | Local-01 |
| **テスト名** | Wheel 検証 poe タスク |
| **目的** | `scripts/verify_wheel.py` がローカルで正しく実行でき、CI と同一の検証が行えることを確認 |
| **実行方法** | `poe verify-wheel` |

**事前条件:**
1. `poe build-frontend` が実行済み
2. `uv build` が実行済み（`dist/` に wheel が存在）

**手順:**
1. `poe release-dry-run` を実行（build-frontend → uv build → verify-wheel → twine check を一括実行）
2. 全ステップが成功で完了することを確認

**期待値:**

| # | 期待値 | カバーする AC |
|---|--------|-------------|
| 1 | `scripts/verify_wheel.py` が exit 0 で完了し、`OK: N static files verified` を出力 | 1.1, 1.2, 3.1, 3.2, 3.3 |
| 2 | `twine check dist/*` が `PASSED` を出力 | 1.5 |

---

### Local-02: poe release-dry-run（フルパイプライン）

| 項目 | 内容 |
|------|------|
| **テストID** | Local-02 |
| **テスト名** | リリース dry-run |
| **目的** | publish.yml の build ジョブと同等のパイプラインをローカルで一気通貫実行できることを確認 |
| **実行方法** | `poe release-dry-run` |

**事前条件:**
1. Node.js がインストール済み
2. `uv sync --all-extras` 済み

**手順:**
1. `poe release-dry-run` を実行
2. 以下の順序で各ステップが成功することを確認:
   - `poe build-frontend`（npm ci + npm run build）
   - `uv build`（sdist + wheel 生成）
   - `poe verify-wheel`（static assets + py.typed 検証）
   - `uvx --from twine twine check dist/*`（メタデータ検証）

**期待値:**

| # | 期待値 | カバーする AC |
|---|--------|-------------|
| 1 | 全4ステップが exit 0 で完了 | 2.2 |
| 2 | `dist/` に `.whl` と `.tar.gz` が生成される | 2.2 |

---

## CI テストシナリオ

### CI-01: ci.yml build-check ジョブ

| 項目 | 内容 |
|------|------|
| **テストID** | CI-01 |
| **テスト名** | PR ビルドチェック |
| **目的** | PR ごとに wheel が正しくビルドでき、フロントエンドアセットが含まれることを検証 |
| **実行方法** | GitHub Actions（ci.yml の build-check ジョブ、PR で自動実行） |

**検証内容:**

| # | 検証内容 | カバーする AC |
|---|----------|-------------|
| 1 | `scripts/verify_wheel.py` が成功 | 1.1, 1.2, 3.1, 3.2, 3.3 |
| 2 | `twine check dist/*` が成功 | 1.5 |
| 3 | build-check 失敗時に PR マージ不可（branch protection で制御） | 3.4 |

---

### CI-02: publish.yml（構造確認）

| 項目 | 内容 |
|------|------|
| **テストID** | CI-02 |
| **テスト名** | Publish ワークフロー構造確認 |
| **目的** | publish.yml のトリガー条件、ジョブ構成、パーミッション設定が正しいことを確認 |
| **実行方法** | 手動レビュー + 初回タグ push での実証 |

> **設計判断**: publish.yml のトリガー条件（`on: push: tags: ["v*"]`）やOIDC パーミッション（`id-token: write`）は、ローカルで自動テストすることが困難。YAML の構造的正しさは手動レビューで担保し、初回リリース時に実証テストとする。

**検証内容:**

| # | 検証内容 | カバーする AC |
|---|----------|-------------|
| 1 | `on.push.tags` が `["v*"]` に設定されている | 2.1, 2.4 |
| 2 | build ジョブで frontend build → uv build の順序 | 2.2 |
| 3 | publish ジョブに `permissions.id-token: write` + `environment: pypi` | 2.3 |
| 4 | tag-version 一致チェックが build ジョブの早期ステップに存在 | 2.1 |

---

## テストファイル構成

```
tests/
├── test_version.py              # Unit-01, Unit-02: __version__ テスト
├── test_verify_wheel.py         # Unit-03: verify_wheel.py ロジックテスト
├── test_packaging.py            # Integ-01~04: wheel ビルド + 検査テスト
├── ...                          # (既存テストファイルは変更なし)
scripts/
├── verify_wheel.py              # Wheel 検証スクリプト（CI + ローカル共用）
├── check_tag_version.py         # Tag-version 一致チェック（CI + ローカル共用）
```

## 単体テストサマリ

| テストID | 対象 | カバーする AC |
|----------|------|-------------|
| Unit-01 | `__init__.py` version 正常取得 | 1.3 |
| Unit-02 | `__init__.py` version fallback | 1.4 |
| Unit-03 | `scripts/verify_wheel.py` 検証ロジック | 1.2, 3.1, 3.2 |

## 統合テストサマリ

| テストID | 対象 | カバーする AC |
|----------|------|-------------|
| Integ-01 | wheel 内 py.typed | 1.1, 1.2 |
| Integ-02 | wheel METADATA version | 1.3 |
| Integ-03 | wheel METADATA classifiers | 1.5 |
| Integ-04 | wheel 内 static assets | 3.1, 3.2, 3.3 |

## ローカル実行テストサマリ

| テストID | テスト名 | 実行方法 | カバーする AC |
|----------|---------|----------|-------------|
| Local-01 | Wheel 検証 | `poe verify-wheel` | 1.1, 1.2, 3.1, 3.2, 3.3 |
| Local-02 | リリース dry-run | `poe release-dry-run` | 2.2 |

## CI テストサマリ

| テストID | テスト名 | 実行方法 | カバーする AC |
|----------|---------|----------|-------------|
| CI-01 | PR ビルドチェック | ci.yml build-check | 1.1, 1.2, 1.5, 3.1, 3.2, 3.3, 3.4 |
| CI-02 | Publish ワークフロー | publish.yml + 手動確認 | 2.1, 2.2, 2.3, 2.4 |

## カバレッジ目標

| コンポーネント | 目標カバレッジ |
|--------------|--------------|
| `src/insight_blueprint/__init__.py`（変更部分） | 100% |
| `scripts/verify_wheel.py` | 90% 以上 |
| `scripts/check_tag_version.py` | 90% 以上 |

## 成功基準

- [ ] Unit-01: `__version__` が pyproject.toml と一致
- [ ] Unit-02: `PackageNotFoundError` 時に fallback 値が返る
- [ ] Unit-03: verify_wheel.py が正常 wheel を pass、欠損 wheel を fail
- [ ] Integ-01: 実ビルド wheel に py.typed が存在
- [ ] Integ-02: 実ビルド wheel の METADATA version が pyproject.toml と一致
- [ ] Integ-03: 実ビルド wheel の METADATA に scientific classifiers が存在
- [ ] Integ-04: 実ビルド wheel にフロントエンド static assets が存在（build-frontend 実行時）
- [ ] Local-01: `poe verify-wheel` がローカルで正常実行
- [ ] Local-02: `poe release-dry-run` がローカルで全ステップ成功
- [ ] CI-01: ci.yml build-check ジョブが PR で正常実行
- [ ] CI-02: publish.yml の構造が要件を満たす（手動レビュー確認）

# Design — SPEC-5: skills-distribution

## Overview

SPEC-5 は insight-blueprint を PyPI 配布可能な状態にする最終スペック。既存の `_copy_skills_template()` を version-aware な更新機構に拡張し、bundled skills をバイリンガル化し、パッケージメタデータ・README を整備する。主な変更は `storage/project.py` のスキルコピーロジックと、`_skills/` 内の SKILL.md ファイル、`pyproject.toml`、`README.md`。

## Steering Document Alignment

### Technical Standards (tech.md)

- **Build backend**: hatchling（変更なし）。`_skills/` は `packages` パス内なので wheel に自動含有
- **Skills path resolution**: `importlib.resources.files("insight_blueprint")` を継続使用
- **Skill frontmatter**: `version` フィールドを追加（tech.md に反映済み）
- **Update mechanism**: tech.md に記載済み — version 比較 + カスタマイズ検出 + `.bundled-update`
- **Language**: body は英語、`description` はバイリンガル、応答言語は CLAUDE.md 委譲（tech.md に反映済み）

### Project Structure (structure.md)

- SPEC-5 対象モジュール: `_skills/`, `README.md`, `pyproject.toml`, `LICENSE`
- `storage/project.py` の `_copy_skills_template()` を拡張（新ファイル作成なし）
- リリース手順書: `docs/RELEASE.md`（新規）

## Code Reuse Analysis

### Existing Components to Leverage

- **`storage/project.py`**: `_copy_skills_template()` — 拡張対象。`importlib.resources.files()` パターンはそのまま再利用
- **`storage/project.py`**: `_register_mcp_server()` — atomic write パターン（`tempfile.mkstemp` + `os.replace`）を `.bundled-update` 書き出しでも再利用
- **`storage/yaml_store.py`**: YAML frontmatter パース — SKILL.md の `version` 読み取りに活用可能だが、SKILL.md は ruamel.yaml ではなく YAML frontmatter（`---` 区切り）なので標準的な文字列パースで十分

### Integration Points

- **`cli.py`**: `init_project()` 呼び出し経路は変更なし。ログ出力のみ追加
- **`_skills/`**: SKILL.md ファイルのみ変更。Python コードへの影響なし
- **`pyproject.toml`**: メタデータ追加のみ。build 設定は変更なし

## Architecture

SPEC-5 は新しいアーキテクチャパターンを導入しない。既存の `init_project()` → `_copy_skills_template()` フローを拡張する。

```
init_project(project_path)
  ├── _create_insight_dirs()      # 変更なし
  ├── _copy_skills_template()     # ★ 拡張: version-aware update
  │     ├── _discover_bundled_skills()     # 新規: _skills/ 自動検出
  │     ├── _get_skill_version()           # 新規: frontmatter version 読み取り
  │     ├── _hash_skill_directory()        # 新規: ディレクトリ全体の SHA-256
  │     ├── _load_skill_state()            # 新規: state.json 読み取り
  │     ├── _save_skill_state()            # 新規: state.json 書き込み
  │     ├── _copy_skill_tree()             # 新規: Traversable API 再帰コピー
  │     └── _write_bundled_update()        # 新規: .bundled-update.json 書き出し
  └── _register_mcp_server()      # 変更なし
```

### Update Decision Logic

Codex レビュー（`.claude/docs/research/SPEC-5-codex-design-review.md`）の指摘を反映し、version + hash の2軸で判定する。

```python
# Pseudocode: _copy_skills_template() per-skill logic
for skill_name in _discover_bundled_skills():
    dest = project_path / ".claude" / "skills" / skill_name
    bundled_version = _get_skill_version(bundled_path / "SKILL.md")
    bundled_hash = _hash_skill_directory(bundled_path)

    if not dest.exists():
        # Case 1: 初回コピー
        _copy_skill_tree(bundled_path, dest)
        _save_skill_state(dest, bundled_version, bundled_hash)
        continue

    state = _load_skill_state(dest)
    installed_version = state.get("installed_version")

    if bundled_version and installed_version:
        if Version(bundled_version) <= Version(installed_version):
            # Case 2: 同 version or downgrade → 何もしない
            continue

    # bundled が新しい → ユーザーカスタマイズ判定
    installed_hash = _hash_skill_directory(dest, exclude_managed=True)
    prev_bundled_hash = state.get("installed_bundled_hash")

    if prev_bundled_hash and installed_hash == prev_bundled_hash:
        # Case 3: 未編集 → 自動更新
        _copy_skill_tree(bundled_path, dest)
        _save_skill_state(dest, bundled_version, bundled_hash)
    else:
        # Case 4: ユーザー編集済み → スキップ + 通知
        logger.warning("Skill '%s' v%s available (customized, skipped)", ...)
        _write_bundled_update(bundled_path, dest, bundled_version, installed_version)
```

### Modular Design Principles

- **Single File Responsibility**: スキル更新ロジックは全て `storage/project.py` に閉じる。ヘルパー関数を追加するが新ファイルは作らない（YAGNI）。ファイル長が 800行を超える場合のみ `storage/skill_updater.py` への分離を検討
- **Component Isolation**: SKILL.md のバイリンガル化は Python コードに影響しない。パッケージメタデータは `pyproject.toml` に閉じる
- **Service Layer Separation**: スキルコピーは storage layer の責務。core/ には触れない
- **Utility Modularity**: frontmatter パースは `_get_skill_version()` として分離。将来他の frontmatter フィールドが必要になっても拡張可能

## Components and Interfaces

### Component 1: Skill Update Engine (`storage/project.py`)

- **Purpose:** bundled skills の自動検出・version-aware コピー・カスタマイズ検出・通知
- **Interfaces:**
  - `_copy_skills_template(project_path: Path) -> None` — 既存 signature 維持
  - `_discover_bundled_skills() -> list[str]` — `_skills/` 配下で `SKILL.md` を含むディレクトリ名一覧を返す
  - `_get_skill_version(skill_md_path: Path) -> str | None` — SKILL.md frontmatter から `version` を読み取り。パースエラー時は `None`
  - `_hash_skill_directory(skill_dir: Path, exclude_managed: bool = False) -> str` — ディレクトリ全体の SHA-256。`exclude_managed=True` で `.insight-blueprint-state.json` と `.bundled-update.json` を除外。行末正規化（LF 統一）してから hash
  - `_load_skill_state(skill_dir: Path) -> dict` — `.insight-blueprint-state.json` を読み取り。欠損時は空 dict
  - `_save_skill_state(skill_dir: Path, version: str | None, bundled_hash: str) -> None` — state を JSON で保存
  - `_copy_skill_tree(src: Traversable, dest: Path) -> None` — `importlib.resources.files` の `Traversable` API で再帰コピー。`shutil.copytree(str(src))` は使わない（importer 依存を避ける）
  - `_write_bundled_update(bundled_path: Traversable, dest_dir: Path, new_version: str | None, old_version: str | None) -> None` — `.bundled-update.json` に新バージョン情報を書き出し
- **Dependencies:** `importlib.resources`, `hashlib`, `json`, `logging`, `packaging.version`（version 比較用。`packaging` は pip/setuptools 経由で常にインストール済み）
- **Reuses:** 既存の `importlib.resources.files()` パターン、atomic write パターン

### Component 2: Bundled Skills (`_skills/`)

- **Purpose:** Claude Code ユーザー向けのバイリンガルスキルテンプレート
- **Interfaces:** YAML frontmatter（`name`, `description`, `version`, `disable-model-invocation`）
- **Dependencies:** なし（テキストファイル）
- **Reuses:** 既存の SKILL.md 構造

### Component 3: Package Metadata (`pyproject.toml`, `LICENSE`, `README.md`)

- **Purpose:** PyPI 配布に必要なメタデータとドキュメント
- **Interfaces:** なし（静的ファイル）
- **Dependencies:** なし
- **Reuses:** 既存の `pyproject.toml` 構造

## Data Models

### SKILL.md Frontmatter（拡張）

```yaml
---
name: analysis-design          # 既存
version: "1.0.0"               # ★ 新規: semver
description: |                 # 既存（内容をバイリンガル化）
  English description here.
  Triggers: "create analysis design", "分析設計を作りたい", ...
disable-model-invocation: true # 既存
argument-hint: "[theme_id]"    # 既存
---
```

### Skill State File

コピー時の状態を記録し、次回の更新判定に使用する。

```
.claude/skills/<name>/.insight-blueprint-state.json
```

```json
{
  "installed_version": "1.0.0",
  "installed_bundled_hash": "sha256:abc123...",
  "updated_at": "2026-02-28T12:00:00Z"
}
```

- `installed_version`: コピー元 bundled skill の version（frontmatter から取得）
- `installed_bundled_hash`: コピー時のスキルディレクトリ全体の SHA-256 hash
- `updated_at`: 最終コピー/更新の ISO 8601 タイムスタンプ

**判定ロジック**: `installed_bundled_hash` と現在の installed ディレクトリの hash を比較。一致すれば未編集（自動更新可）、不一致ならユーザー編集済み（スキップ + 通知）。

### Bundled Update Notification

ユーザー編集済みスキルのスキップ時に書き出す通知ファイル。

```
.claude/skills/<name>/.bundled-update.json
```

```json
{
  "from_version": "1.0.0",
  "to_version": "1.1.0",
  "created_at": "2026-02-28T12:00:00Z",
  "message": "Run: diff .claude/skills/analysis-design/SKILL.md .claude/skills/analysis-design/.bundled-update/SKILL.md"
}
```

さらに `.bundled-update/` ディレクトリに新バージョンのスキルファイル一式をコピーし、ユーザーが diff で差分確認・手動マージできるようにする。

**Hash 計算からの除外**: `.insight-blueprint-state.json`, `.bundled-update.json`, `.bundled-update/` は hash 計算時に除外する（managed files）。

## Error Handling

### Error Scenarios

1. **`_skills/` ディレクトリが空（skill が0個）**
   - **Handling:** `_discover_bundled_skills()` が空リストを返す。ループが回らず正常終了
   - **User Impact:** なし。スキルなしで起動

2. **SKILL.md に `version` フィールドがない（古い形式）**
   - **Handling:** `_get_skill_version()` が `None` を返す。version が `None` の場合は従来動作（dest.exists() なら skip）にフォールバック
   - **User Impact:** なし。既存動作と同一

3. **`.bundled-hash` ファイルが欠損（手動削除等）**
   - **Handling:** hash ファイルがなければ「カスタマイズ済み」と判定（安全側に倒す）。更新スキップ + `.bundled-update` 書き出し
   - **User Impact:** warning ログで通知。ユーザーは `.bundled-update` で diff 確認可能

4. **SKILL.md の frontmatter パースエラー**
   - **Handling:** パースエラー時は version `None` として扱い、従来動作にフォールバック
   - **User Impact:** warning ログのみ。起動は継続

5. **`.bundled-update.json` の書き込み失敗（permission 等）**
   - **Handling:** 例外をキャッチし warning ログ。スキル更新処理全体は継続
   - **User Impact:** 通知ファイルが作成されないが、warning ログで状況は伝わる

6. **不正な version 文字列（`v1`, `latest` 等）**
   - **Handling:** `packaging.version.Version` でパース。`InvalidVersion` 例外時は version `None` として扱い、従来動作にフォールバック
   - **User Impact:** warning ログのみ

7. **Downgrade（bundled version < installed version）**
   - **Handling:** `Version(bundled) <= Version(installed)` の場合は何もしない。Downgrade は明示的に行わない
   - **User Impact:** なし

8. **部分更新失敗（コピー途中でエラー）**
   - **Handling:** `_copy_skill_tree()` は既存ディレクトリを一旦 `.backup` にリネーム → 新規コピー → 成功したら `.backup` を削除。失敗したら `.backup` をリストアする
   - **User Impact:** 中途半端な状態にならない。エラー時は元の状態を維持

## Testing Strategy

### Unit Testing

- `_discover_bundled_skills()`: `_skills/` 配下に0個・1個・複数のディレクトリがある場合。`SKILL.md` なしディレクトリは除外
- `_get_skill_version()`: version あり・version なし・frontmatter 不正・不正 version 文字列
- `_hash_skill_directory()`: 正常 hash・managed files 除外・行末正規化（LF/CRLF 混在）
- `_load_skill_state()` / `_save_skill_state()`: 正常読み書き・state.json 欠損・不正 JSON
- `_copy_skill_tree()`: Traversable からの再帰コピー・部分失敗時のリストア
- `_write_bundled_update()`: 正常書き出し・書き込み先 permission エラー
- `_copy_skills_template()` 統合: 新規コピー・version アップ（未編集）・version アップ（編集済み）・同 version・downgrade・version なし旧 skill

### Integration Testing

- `init_project()` の E2E: 空ディレクトリから `init_project()` → skills がコピーされる → 再度 `init_project()`（version 同じ）→ 変更なし → SKILL.md 編集 → bundled version 上げ → 再度 `init_project()` → `.bundled-update` が書き出される
- wheel build: `uv build` → wheel 内に `_skills/` と `static/` が含まれることを検証

### End-to-End Testing

- ローカル wheel インストール: `uv build` → `pip install dist/*.whl` → `insight-blueprint --project /tmp/test` → `.claude/skills/` にスキルがコピーされ WebUI が起動する

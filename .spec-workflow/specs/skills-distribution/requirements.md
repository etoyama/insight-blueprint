# Requirements — SPEC-5: skills-distribution

## はじめに

SPEC-5 はロードマップ最終スペック。PyPI 公開に向けて以下を整備する:
1. bundled skills のバイリンガル化（英語本体 + 日本語トリガー）
2. PyPI メタデータ・LICENSE・README 整備
3. wheel に全 artifact（skills, static frontend）が含まれることの検証

## Product Vision との対応

1. **Zero-install** — `uvx insight-blueprint --project /path` で動く。wheel に全部入っていることが前提
2. **OSS (MIT) on PyPI** — LICENSE、classifiers、メタデータを整備して PyPI に正しく表示
3. **Bundled Skills** — `_skills/` から `.claude/skills/` へコピー。日英どちらのトリガーでも発見可能にする

## 要件

### 1. Skill バイリンガル化

**User Story:** Claude Code ユーザー（日英問わず）として、自分の言語でスキルを呼び出したい。

- FR-1: SKILL.md 本体（workflow, rules 等）は英語で記述
- FR-2: `description` YAML フィールドに英語説明 + 日本語トリガーフレーズを併記
- FR-3: `## Language Rules` セクションで「プロジェクトの CLAUDE.md の言語設定に従う。設定がなければ日本語をデフォルトとする。code/ID は常に英語」と明記
- FR-4: `.claude/rules/skill-format.md` の YAML frontmatter スキーマに準拠

#### Acceptance Criteria

1. WHEN "create analysis design" 入力 THEN `analysis-design` skill が発見できる
2. WHEN "分析設計を作りたい" 入力 THEN `analysis-design` skill が発見できる
3. WHEN "catalog register" 入力 THEN `catalog-register` skill が発見できる
4. WHEN "データカタログ登録" 入力 THEN `catalog-register` skill が発見できる
5. WHEN skill 起動 AND CLAUDE.md に言語設定なし THEN ユーザーへの応答はデフォルト日本語
6. WHEN skill 起動 AND CLAUDE.md に `Language: English` 設定あり THEN ユーザーへの応答は英語

### 2. PyPI パッケージメタデータ

**User Story:** PyPI を閲覧する開発者として、license・author・classifiers が表示されていてほしい。

- FR-5: `pyproject.toml` に `license`, `authors`, `classifiers`, `urls` を追加
- FR-6: リポジトリ root に MIT `LICENSE` ファイルを配置
- FR-7: classifiers に Development Status, License, Python 3.11+, Topic, Framework を含める
- FR-8: urls に Homepage, Repository, Bug Tracker を含める

#### Acceptance Criteria

1. WHEN `uv build` THEN wheel metadata に license, author, classifiers が含まれる
2. WHEN PyPI ページ表示 THEN sidebar に MIT, Python >=3.11, project URLs が表示される

### 3. README 整備

**User Story:** PyPI / GitHub 訪問者として、insight-blueprint が何か・どう使うかをすぐ理解したい。

- FR-9: README.md に概要、インストール（`uvx` / `uv tool install`）、Quick Start、機能一覧（MCP tools, WebUI, Skills）、開発セットアップを記載
- FR-10: `pyproject.toml` の `readme = "README.md"` で long_description として使用（設定済み）
- FR-11: claude-code-orchestra 固有コンテンツ（Codex CLI, Gemini CLI, spec-workflow-mcp 等）を削除または別ファイルに移動

#### Acceptance Criteria

1. WHEN README を読む THEN 最初の3セクションで「何か・インストール・使い方」が分かる
2. WHEN `uv build` THEN wheel の long_description が README.md から生成される
3. WHEN GitHub で表示 THEN claude-code-orchestra 固有の内容が含まれない

### 4. Skill アップデート機構

**User Story:** パッケージ更新後も、bundled skill の改善がユーザーに届いてほしい。ただしユーザーがカスタマイズした skill は上書きしたくない。

- FR-12: SKILL.md frontmatter に `version` フィールド（semver 形式）を追加
- FR-13: `_copy_skills_template()` は bundled skill の `version` とコピー済み skill の `version` を比較し、bundled が新しければ更新する
- FR-14: ユーザーがスキルを手動編集している場合（ファイルハッシュが bundled 元と異なる場合）は自動更新をスキップし、warning ログを出力する
- FR-15: スキップ時、bundled の新バージョンを `.claude/skills/<name>/.bundled-update` に書き出し、ユーザーが diff で差分確認・手動マージできるようにする
- FR-16: 初回コピー時（dest が存在しない場合）の動作は従来通り

#### Acceptance Criteria

1. WHEN bundled skill の version が "1.1.0" でコピー済みが "1.0.0"（未編集）THEN skill が更新される
2. WHEN bundled skill の version が "1.1.0" でコピー済みが "1.0.0"（ユーザー編集済み）THEN 自動更新はスキップされ、warning ログが出力され、`.bundled-update` に新バージョンが書き出される
3. WHEN コピー済み skill が存在しない THEN 従来通り新規コピーされる
4. WHEN bundled skill と コピー済み skill が同じ version THEN 何もしない

### 5. 配布検証

**User Story:** パッケージメンテナとして、wheel に必要な artifact が全て入っていることを確認したい。

- FR-17: `uv build` の wheel に `insight_blueprint/_skills/` が含まれる
- FR-18: `uv build` の wheel に `insight_blueprint/static/` が含まれる
- FR-19: `_copy_skills_template()` を `_skills/` ディレクトリの自動検出に変更（hardcoded list 廃止）
- FR-20: 手動リリース手順書を作成（version bump → build → verify → ローカルテスト → upload）
- FR-21: ローカル wheel からのインストール + E2E 動作確認手順を含める（`pip install dist/*.whl` でスキルコピー・WebUI 起動を検証）

#### Acceptance Criteria

1. WHEN `uv build` THEN `unzip -l dist/*.whl | grep _skills` で全 SKILL.md が表示される
2. WHEN `uv build` THEN `unzip -l dist/*.whl | grep static` で frontend assets が表示される
3. WHEN 新 skill を `_skills/` に追加 THEN コード変更なしで `_copy_skills_template()` がコピーする
4. WHEN ローカル wheel をインストール THEN `insight-blueprint --project /tmp/test` でスキルコピー・WebUI 起動が動作する

> **Note:** 実際の PyPI publish はチームによる使用感確認後に手動実行する。SPEC-5 の検証基準はローカル wheel での動作確認まで。

## 非機能要件

### Code Architecture and Modularity
- skill 変更は `_skills/` 内に閉じる。メタデータ変更は `pyproject.toml` + `LICENSE` に閉じる
- `_copy_skills_template()` は `importlib.resources` のディレクトリ走査で自動検出。hardcoded list 不要
- SPEC-5 で新しい runtime 依存は追加しない
- skill コピーの contract: 初回は新規コピー、以降は version 比較で更新。ユーザーカスタマイズ済みは自動更新スキップ + 通知 + `.bundled-update` 書き出し

### Performance
- NFR-1: `_copy_skills_template()` は 10 skills まで 500ms 以内
- NFR-2: skill 自動検出が `init_project()` に体感できる遅延を加えない

### Security
- NFR-3: README, SKILL.md, `pyproject.toml` に secret・API key を含めない
- NFR-4: LICENSE は標準 MIT テキスト（正しい copyright holder と年）

### Reliability
- NFR-5: `_skills/` に subdirectory が0個でもエラーにならない
- NFR-6: `static/` が空でも wheel build が成功する

### Usability
- NFR-7: README は Claude Code や MCP の事前知識なしでも理解できる
- NFR-8: リリース手順書は PyPI 初心者でも追える

## Out of Scope

- 新スキル作成（review-workflow, data-explorer）
- CI/CD（GitHub Actions での自動 PyPI publish）
- バージョン自動バンプ・changelog 生成
- TestPyPI ステージング
- 実際の PyPI publish（チーム使用感確認後に手動実行。手順書は SPEC-5 で提供）

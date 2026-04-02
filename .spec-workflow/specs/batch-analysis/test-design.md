# batch-analysis - テスト設計書

**Spec ID**: `batch-analysis`
**種別**: 新規機能

## Reference

> **investigation.md**: テスト設計の前提となる検証済み事実は [investigation.md](investigation.md) を参照。特に V1-V6a の実機検証結果がテストの期待値の根拠となる。

## 概要

本ドキュメントは、batch-analysis requirements.md の全 AC（28件）に対して、どのテストレベルでカバーするかを定義する。

本スキルは Python コード変更を含まない（Skill レイヤーのみ）ため、従来の単体テストは不要。テストは以下の2レベルで構成する:

| テストレベル | 略称 | 説明 | ツール |
|-------------|------|------|--------|
| 統合テスト | Integ | パイプラインの各ステップを個別に検証。MCP ツール + marimo + ファイル I/O の連携 | Claude Code 対話セッション（MCP tool 直接呼び出し）, marimo CLI, ファイル検証 |
| E2Eテスト | E2E | headless バッチ全体を実行し、入力（設計書キュー）から出力（notebook + journal + summary）までを検証 | claude -p (headless), ファイル検証コマンド |

## 要件カバレッジマトリクス

### REQ-1: バッチキュー管理

| AC# | Acceptance Criteria | Integ | E2E | 期待値 |
|-----|---------------------|:-----:|:---:|--------|
| 1.1 | next_action で batch_execute 設定 | Integ-01 | E2E-01 | next_action が正しく更新される |
| 1.2 | priority 昇順で処理 | - | E2E-05 | priority=1 が priority=2 より先に処理される |
| 1.3 | 処理完了後 next_action が null | - | E2E-01 | 処理後の設計書の next_action が null |
| 1.4 | terminal status はスキップ | - | E2E-04 | summary にスキップ理由が記録される |

### REQ-2: marimo notebook 自動生成

| AC# | Acceptance Criteria | Integ | E2E | 期待値 |
|-----|---------------------|:-----:|:---:|--------|
| 2.1 | 設計書から8セル notebook 生成 | Integ-02 | E2E-01 | 8セル構成の .py ファイルが生成される |
| 2.2 | marimo export session で実行成功 | Integ-02 | E2E-01 | exit code 0、session JSON に8セル分の output |
| 2.3 | exploratory → パターン列挙 + open questions | - | E2E-01 | verdict に conclusion + open_questions |
| 2.4 | confirmatory → AC 合否判定 | - | E2E-02 | verdict に AC pass/fail + 総合判定 |
| 2.5 | source_ids 空 → catalog フォールバック | Integ-03 | - | catalog 検索でソースが推定される |

### REQ-3: バッチ実行

| AC# | Acceptance Criteria | Integ | E2E | 期待値 |
|-----|---------------------|:-----:|:---:|--------|
| 3.1 | marimo export session で全セル実行 | Integ-02 | E2E-01 | session JSON の全セルに output あり |
| 3.2 | エラー時に修正試行 → 3回失敗でスキップ | Integ-04 | E2E-03 | summary に修正試行の詳細とスキップ理由 |
| 3.3 | 実行完了後 status → analyzing | - | E2E-01 | get_design で status == analyzing |
| 3.4 | status が in_review 以外 → 遷移スキップ | - | E2E-05 | analyzing の設計書を再処理しても status 変わらず |
| 3.5 | methodology.package 未インストール → uv add | Integ-05 | E2E-02 | パッケージがインストールされてから実行成功 |
| 3.6 | marimo 記法エラー修正 → rules 更新 | Integ-04 | - | marimo-notebooks.md に知見が追記される |

### REQ-4: journal 自動記録

| AC# | Acceptance Criteria | Integ | E2E | 期待値 |
|-----|---------------------|:-----:|:---:|--------|
| 4.1 | 成功時に observe + evidence 記録 | Integ-06 | E2E-01 | journal YAML に observe ≥ 1 + evidence ≥ 1 |
| 4.2 | open questions → question イベント | Integ-06 | E2E-01 | verdict の open_questions 数 == question イベント数 |
| 4.3 | 既存 journal に追記（上書きしない） | Integ-07 | - | 既存イベントが保持され、新イベントが末尾に追加 |
| 4.4 | evidence に direction 付与 | Integ-06 | E2E-02 | metadata.direction が supports or contradicts |
| 4.5 | conclude が生成されない | Integ-06 | E2E-01 | journal 内に type: conclude のイベントが0件 |

### REQ-5: 朝レビュー用サマリー

| AC# | Acceptance Criteria | Integ | E2E | 期待値 |
|-----|---------------------|:-----:|:---:|--------|
| 5.1 | summary.md 生成 | - | E2E-01 | .insight/runs/YYYYMMDD_HHmmss/summary.md が存在 |
| 5.2 | Overview テーブルに全件表示 | - | E2E-05 | テーブル行数 == 処理対象設計書数 |
| 5.3 | エラー時に Requires Attention | - | E2E-03 | "Requires Attention" セクションにエラー詳細 |
| 5.4 | 30秒以内にトリアージ可能な構造 | - | E2E-05 | summary.md に Overview テーブル（ID/title/intent/verdict/issues の5列）+ Requires Attention + Next Steps の3セクション |

### REQ-6: headless オーケストレーション

| AC# | Acceptance Criteria | Integ | E2E | 期待値 |
|-----|---------------------|:-----:|:---:|--------|
| 6.1 | 人間介入なしで完了 | - | E2E-01 | claude -p が exit code 0 で完了 |
| 6.2 | max-budget-usd 到達で安全終了 | - | E2E-06 | 処理済み結果が保持、summary に中断理由 |
| 6.3 | MCP 接続失敗 → session.log 記録 | Integ-08 | - | session.log にエラーメッセージ |
| 6.4 | 全処理完了後に summary 生成してから終了 | - | E2E-05 | summary.md のタイムスタンプ > 最後の journal タイムスタンプ |

---

## 統合テストシナリオ

### Integ-01: キュー管理 — next_action convention

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-01 |
| **目的** | MCP ツール経由で next_action の設定・読み取り・リセットが正しく動作するか |
| **実行方法** | Claude Code の対話セッションで MCP tool を直接呼び出す |

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_queue_set` | 1. `MCP: update_analysis_design(design_id="DEMO-H01", next_action={"type": "batch_execute", "priority": 1})` を実行 | next_action が設定され、list で読み取れる | `MCP: list_analysis_designs()` → 結果から DEMO-H01 の `next_action.type` == `"batch_execute"` を目視確認 | 1.1 |
| `test_queue_reset` | 1. `MCP: update_analysis_design(design_id="DEMO-H01", next_action=null)` を実行 | next_action が null にリセットされる | `MCP: get_analysis_design(design_id="DEMO-H01")` → `next_action` == `null` を確認 | 1.3 |

---

### Integ-02: セルコントラクト準拠 — notebook 生成 + 実行

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-02 |
| **目的** | 生成された notebook が8セル構造を持ち、marimo export session で全セル実行可能か |
| **実行方法** | Claude Code の対話セッションで MCP tool でデータ取得 → notebook 生成 → marimo export session → session JSON 解析 |

> **設計判断**: V3（exploratory）および V6a（confirmatory/PSM）で既に検証済み。ここでは回帰テストとして位置づける。

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_exploratory_notebook` | 1. `MCP: get_analysis_design(design_id="DEMO-H01")` で設計書取得 2. `MCP: get_table_schema(source_id=...)` でスキーマ取得 3. セルコントラクトに従い notebook.py を生成 4. `Bash: uv run marimo export session --force-overwrite notebook.py` | DEMO-H01 で8セル生成 + 全セル実行成功 | `Bash: echo $?` → exit code == 0; `Bash: python3 -c "import json; cells=json.load(open('__marimo__/session/notebook.py.json'))['cells']; assert len(cells)==8, f'Expected 8 cells, got {len(cells)}'; assert all(c.get('outputs') for c in cells), 'Some cells have no output'"` | 2.1, 2.2, 3.1 |
| `test_confirmatory_notebook` | 1. CAUSAL-H01 相当の confirmatory 設計書で同様に notebook 生成・実行 | AC 判定が含まれる verdict 生成 | `Bash: python3 -c "import json; cells=json.load(open('__marimo__/session/notebook.py.json'))['cells']; verdict_text=str(cells[6]); assert 'pass' in verdict_text.lower() or 'fail' in verdict_text.lower(), 'No AC pass/fail in verdict'"` | 2.1, 2.2, 2.4, 3.1 |

---

### Integ-03: データソースフォールバック

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-03 |
| **目的** | source_ids が空の設計書でエージェントがデータソースを推定し、`get_table_schema` でスキーマを取得できるか |
| **実行方法** | Claude Code の対話セッションで source_ids=[] の設計書に対し、MCP tool を使ってフォールバック手順を実行 |

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_empty_source_ids_fallback` | 1. `MCP: get_analysis_design(design_id="DEMO-H01")` で設計書取得（source_ids が空であることを確認） 2. hypothesis/methodology のキーワードを抽出 3. `MCP: catalog_search(query="{extracted_keywords}")` でソース候補を検索 4. 候補が返ったら `MCP: get_table_schema(source_id="{candidate_id}")` でスキーマ取得 | source_ids 未指定時にエージェントが hypothesis/methodology のキーワードから catalog_search でソースを推定し、推定したソースの get_table_schema でスキーマを取得して notebook を生成する | `MCP: catalog_search(query=...)` の結果が 1件以上返ること; `MCP: get_table_schema(source_id=...)` がスキーマ（columns 情報）を返すこと; 生成された notebook の Cell 2 に推定ソースの読み込みコードが含まれること → `Grep: pattern="read_csv\|read_sql\|pd.read" path="notebook.py"` → 1件以上 | 2.5 |

---

### Integ-04: エラー修正ループ

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-04 |
| **目的** | marimo 実行エラー時にエージェントが修正を試み、rules に知見を蓄積するか |
| **実行方法** | 2種類のエラーを注入して修正ループを観察 |

**テストケース:**

| ケース | 手順 | 検証内容 | エラー注入方法 | 検証方法 | カバーするAC |
|--------|------|----------|--------------|----------|-------------|
| `test_error_repair_package` | 1. methodology.package に未インストールパッケージを指定した設計書を用意 2. notebook 生成 → `Bash: uv run marimo export session notebook.py` 実行 → ModuleNotFoundError 3. エージェントが `Bash: uv add --dev {package}` 実行 4. 再実行で成功確認 | 修復可能なエラー（パッケージ不足）で uv add --dev → 再実行成功 | methodology.package に未インストールパッケージを指定 | `Bash: uv run marimo export session --force-overwrite notebook.py && echo "EXIT:$?"` → EXIT:0 を確認; `Bash: uv pip list \| grep {package}` → パッケージが存在 | 3.2 |
| `test_error_repair_marimo_syntax` | 1. `_` prefix なしの変数名を使った notebook を手書きで用意（例: `fig, ax = plt.subplots()` を複数セルに配置し multiple-defs を誘発） 2. `Bash: uv run marimo export session --force-overwrite bad_notebook.py` → multiple-defs エラー確認 3. エージェントに修正を依頼（context7 で marimo docs 参照 → `_` prefix 追加 → 再実行） 4. 修正成功後、`.claude/rules/marimo-notebooks.md` への知見追記を確認 | **marimo 記法エラー**（multiple-defs）の修正 + rules 更新 | 事前に `_` prefix なしの notebook を手書きで用意し `marimo export session` にかけてエラー発生 → Claude Code がこれを修正 → rules 更新を検証 | `Bash: uv run marimo export session --force-overwrite bad_notebook.py && echo "EXIT:$?"` → 修正後 EXIT:0; `Bash: git diff .claude/rules/marimo-notebooks.md` → 差分が存在（知見追記あり）; `Grep: pattern="_fig\|_ax" path="bad_notebook.py"` → `_` prefix 付き変数に修正されていること | **3.6** |
| `test_error_repair_failure` | 1. 存在しない DB 接続文字列をデータソースに指定した設計書で notebook 生成 2. 3回修正試行 → 全て失敗 3. スキップされ summary に記録 | 修復不能なエラー（3回失敗）でスキップ + summary 記録 | 存在しない DB 接続文字列をデータソースに指定 | `Grep: pattern="Requires Attention\|skip\|error" path="summary.md" -i` → 当該設計書のエラー詳細が記載; `Grep: pattern="3.*attempt\|修正.*3\|retry" path="summary.md" -i` → 修正試行回数の記録あり | 3.2 |

> **設計判断（AC-3.6）**: marimo 記法エラーの再現は、意図的に `_` prefix なしの notebook を手書きで事前に用意し、`marimo export session` でエラーを発生させる。batch-prompt の改変は行わない。修正成功後に `.claude/rules/marimo-notebooks.md` に追記されたことを `git diff` で確認する。

---

### Integ-05: パッケージ事前インストール

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-05 |
| **目的** | methodology.package で指定されたパッケージが未インストール時に uv add --dev が実行されるか |
| **実行方法** | Claude Code の対話セッションで methodology.package に statsmodels を指定し、notebook 実行前にインストールされることを確認 |

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_package_preinstall` | 1. `MCP: get_analysis_design(design_id=...)` で methodology.package を確認 2. `Bash: python3 -c "import statsmodels"` でインストール状況確認 3. バッチ処理のパッケージチェック手順に従い `Bash: uv add --dev statsmodels` 実行 4. notebook 生成・実行 | 未インストールパッケージが uv add --dev で追加される | `Bash: python3 -c "import statsmodels; print(statsmodels.__version__)"` → バージョンが出力される（ImportError なし）; `Bash: uv run marimo export session --force-overwrite notebook.py && echo "EXIT:$?"` → EXIT:0 | 3.5 |

---

### Integ-06: journal 自動記録

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-06 |
| **目的** | session JSON から journal イベントが正しく生成されるか |
| **実行方法** | Integ-02 の実行後に journal YAML を解析 |

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_journal_observe_evidence` | Integ-02 完了後、journal YAML を確認 | observe ≥ 1 件 + evidence ≥ 1 件が記録される | `Grep: pattern="type: observe" path=".insight/designs/DEMO-H01_journal.yaml"` → 1件以上; `Grep: pattern="type: evidence" path=".insight/designs/DEMO-H01_journal.yaml"` → 1件以上 | 4.1 |
| `test_journal_questions` | Integ-02 完了後、verdict の open_questions と journal の question イベントを比較 | verdict の open_questions が question イベントとして記録される | `Bash: python3 -c "import yaml; j=yaml.safe_load(open('.insight/designs/DEMO-H01_journal.yaml')); q_count=len([e for e in j['events'] if e['type']=='question']); print(f'question events: {q_count}'); assert q_count >= 1, 'No question events'"` | 4.2 |
| `test_journal_direction` | Integ-02 完了後、evidence イベントの metadata.direction を確認 | evidence の metadata.direction が設定され、仮説の方向と一致する判定が正しいか検証（exploratory: 相関の符号と仮説の方向を比較、confirmatory: AC pass/fail から判定） | `Bash: python3 -c "import yaml; j=yaml.safe_load(open('.insight/designs/DEMO-H01_journal.yaml')); evs=[e for e in j['events'] if e['type']=='evidence']; assert all(e.get('metadata',{}).get('direction') in ('supports','contradicts') for e in evs), f'Invalid direction: {[e.get(\"metadata\") for e in evs]}'"` | 4.4 |
| `test_journal_no_conclude` | Integ-02 完了後、journal に conclude が含まれないことを確認 | type: conclude のイベントが 0 件 | `Grep: pattern="type: conclude" path=".insight/designs/DEMO-H01_journal.yaml"` → 0件（マッチなし） | 4.5 |

---

### Integ-07: journal 追記（既存 journal の保護）

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-07 |
| **目的** | 既存 journal がある設計書に対して追記が正しく行われ、既存イベントが上書きされないか |
| **実行方法** | 事前に journal を持つ設計書（DEMO-H01）でバッチ実行し、追記前後を比較 |

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_journal_append` | 1. `Bash: python3 -c "import yaml; j=yaml.safe_load(open('.insight/designs/DEMO-H01_journal.yaml')); print(f'Before: {len(j[\"events\"])} events')"` で既存イベント数を記録 2. バッチ実行（DEMO-H01 を再処理） 3. 追記後の journal を確認 | 既存イベントが保持され、新イベントが末尾に追加される | `Bash: python3 -c "import yaml; j=yaml.safe_load(open('.insight/designs/DEMO-H01_journal.yaml')); events=j['events']; print(f'After: {len(events)} events'); assert len(events) > BEFORE_COUNT, 'No new events appended'"` （BEFORE_COUNT は手順1で取得した値に置換）; `Bash: python3 -c "import yaml; j=yaml.safe_load(open('.insight/designs/DEMO-H01_journal.yaml')); ids=[e['id'] for e in j['events']]; assert len(ids)==len(set(ids)), f'Duplicate IDs found: {ids}'"` → ID の重複なし | 4.3 |

---

### Integ-08: MCP 接続失敗時のエラー検知

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-08 |
| **目的** | MCP サーバーに接続できない場合にエラーが検知可能か |
| **実行方法** | `--strict-mcp-config` + 無効な MCP config JSON を指定して headless 実行 |

> **設計判断**: MCP 起動前に失敗すると `session.log` 自体が作成されない可能性がある。そのため「session.log にエラーが記録される」ではなく「`claude -p` の exit code ≠ 0 または stderr 出力でエラーが検知できる」を期待値とする。バッチ起動スクリプト側でこの exit code/stderr をキャプチャし、アラートする設計を前提とする。

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_mcp_connection_failure` | 1. 無効な MCP config を作成: `Bash: echo '{"mcpServers":{"invalid":{"command":"nonexistent-binary"}}}' > /tmp/bad-mcp.json` 2. `Bash: claude -p "test" --mcp-config /tmp/bad-mcp.json --strict-mcp-config 2>&1; echo "EXIT:$?"` | `claude -p` が非ゼロ exit code で終了し、stderr に MCP 接続エラーが出力される | `Bash: claude -p "test" --mcp-config /tmp/bad-mcp.json --strict-mcp-config 2>&1 \| tee /tmp/mcp-error.log; echo "EXIT:$?"` → EXIT:0 以外; `Grep: pattern="error\|fail\|connect" path="/tmp/mcp-error.log" -i` → エラーメッセージが存在 | 6.3 |

---

### Integ-09: lib_dir カタログ化とユーティリティ管理

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-09 |
| **目的** | lib_dir の事前スキャン → CATALOG.md 生成、notebook での import、実行中のユーティリティ追加が動作するか |
| **実行方法** | Claude Code の対話セッションで lib_dir にサンプルユーティリティを配置してバッチ実行。CATALOG.md の生成と notebook からの import を検証 |

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_catalog_generation` | 1. `Bash: mkdir -p /tmp/test_lib && echo 'def clean_data(df): """Remove nulls."""; return df.dropna()' > /tmp/test_lib/utils.py` 2. lib_dir=/tmp/test_lib でバッチ実行 | lib_dir 内の .py ファイルから CATALOG.md が自動生成される | `Bash: ls /tmp/test_lib/CATALOG.md && echo "EXISTS"` → EXISTS; `Grep: pattern="clean_data" path="/tmp/test_lib/CATALOG.md"` → 関数名が記載; `Grep: pattern="Remove nulls" path="/tmp/test_lib/CATALOG.md"` → docstring が記載 | FR-2.6 |
| `test_notebook_import_from_lib` | 1. test_catalog_generation 完了後、生成された notebook を確認 | 生成 notebook の Cell 0 に `sys.path.insert` が含まれ、lib_dir の関数を import して使用できる | `Grep: pattern="sys.path.insert" path=".insight/runs/*/DEMO-H01/notebook.py"` → 1件以上; `Grep: pattern="from utils import\|import utils" path=".insight/runs/*/DEMO-H01/notebook.py"` → 1件以上 | FR-2.6 |
| `test_lib_dir_not_found` | 1. lib_dir に存在しないパス（`/tmp/nonexistent_lib_dir`）を指定してバッチ実行 | lib_dir に存在しないパスを指定した場合にエラーとなる（自動作成しない） | `Bash: ls /tmp/nonexistent_lib_dir 2>&1` → "No such file or directory"; バッチ実行のログ/summary にエラー記録があること | FR-2.6 |
| `test_utility_addition` | 1. バッチ実行中にエージェントが新ユーティリティを lib_dir に追加する状況を再現 2. CATALOG.md が更新されることを確認 | notebook 生成中に新しいユーティリティが lib_dir に追加され、CATALOG.md が更新される | `Bash: python3 -c "content=open('/tmp/test_lib/CATALOG.md').read(); print(f'Functions listed: {content.count(\"def \")}')"` → 追加後に関数数が増加; 後続 notebook が新ユーティリティを import 可能であること | FR-2.6 |

---

### Integ-10: 自己レビュー・時間予算管理

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-10 |
| **目的** | 30分/件の時間予算管理と自己レビューの段階的簡略化が動作するか |
| **実行方法** | 自己レビューが実行されていることを session.log の内容から検証。batch-prompt.md が自己レビュー時に `[SELF-REVIEW]` マーカーを出力する設計を前提とする |

> **設計判断**: 時間予算の厳密なテストは困難（実行時間は環境依存）。代替として (1) `[SELF-REVIEW]` マーカーで自己レビュー実行の証跡を確認、(2) batch-prompt が時間を記録していることを session.log から確認する。

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_self_review_executed` | E2E-01 or E2E-05 の完了後、session.log を確認 | session.log に自己レビュー実行の証跡がある | `Grep: pattern="\[SELF-REVIEW\]" path=".insight/runs/*/session.log"` → 1件以上（設計書1件につき1回以上の `[SELF-REVIEW]` マーカー出力） | NFR Performance |
| `test_time_tracking` | E2E-01 or E2E-05 の完了後、session.log を確認 | session.log に設計書ごとの処理開始・終了時刻が記録されている | `Grep: pattern="処理開始\|処理完了\|start.*processing\|finish.*processing" path=".insight/runs/*/session.log" -i` → 設計書1件につき開始・完了各1件以上 | NFR Performance |

---

### Integ-11: ディレクトリ命名・設定解決

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-11 |
| **目的** | YYYYMMDD_HHmmss の同日再実行衝突回避と、notebook_dir/lib_dir の設定解決順序が正しく動作するか |
| **実行方法** | 同一日に2回バッチ実行し、別ディレクトリに結果が保存されることを確認 |

**テストケース:**

| ケース | 手順 | 検証内容 | 検証方法 | カバーするAC |
|--------|------|----------|----------|-------------|
| `test_same_day_rerun` | 1. バッチ実行1回目 2. 数分待って2回目実行 | 同日2回実行で `.insight/runs/` に異なるタイムスタンプのディレクトリが2つ作成される | `Bash: ls -d .insight/runs/$(date +%Y%m%d)_* \| wc -l` → 2以上; `Bash: ls -d .insight/runs/$(date +%Y%m%d)_*` → タイムスタンプ部分が異なる2ディレクトリ | FR-2.5 |
| `test_config_resolution_default` | 1. `.insight/config.yaml` に `batch.notebook_dir` 設定なしでバッチ実行 | notebook_dir 未設定時にデフォルト（`.insight/runs/YYYYMMDD_HHmmss/{design_id}/`）が使われる | `Bash: ls .insight/runs/*/DEMO-H01/notebook.py && echo "EXISTS"` → EXISTS; パス形式が `YYYYMMDD_HHmmss/DEMO-H01/` であること | FR-2.5 |
| `test_config_resolution_custom` | 1. `.insight/config.yaml` に `batch: {notebook_dir: "/tmp/custom_notebooks"}` を設定 2. バッチ実行 | `.insight/config.yaml` に `batch.notebook_dir` を設定した場合にそのパスが使われる | `Bash: ls /tmp/custom_notebooks/*/DEMO-H01/notebook.py && echo "EXISTS"` → EXISTS（カスタムパスに出力）; `Bash: ls .insight/runs/*/DEMO-H01/notebook.py 2>&1` → 存在しない（デフォルトパスには出力されない） | FR-2.5 |

---

## E2Eテストシナリオ

### E2E-01: 正常系 — exploratory 単件バッチ

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-01 |
| **テスト名** | Exploratory 単件バッチ実行 |
| **目的** | 設計書1件（exploratory）でバッチ全体が正常に完了するか |
| **実行方法** | claude -p batch-prompt.md |

**事前条件:**
1. DEMO-H01 に `next_action: {"type": "batch_execute"}` が設定されている
2. tutorial/sample_data/sales.csv が存在する

**手順:**

1. `update_analysis_design(DEMO-H01, next_action={"type": "batch_execute"})` でキューに投入
2. `claude -p "$(cat skills/batch-analysis/batch-prompt.md)" --model sonnet --allowedTools "..." --permission-mode bypassPermissions`
3. 実行完了を待つ

**期待値:**

| # | 期待値 | 検証方法 | カバーするAC |
|---|--------|----------|-------------|
| 1 | .insight/runs/YYYYMMDD_HHmmss/DEMO-H01/notebook.py が存在 | `Bash: ls .insight/runs/*/DEMO-H01/notebook.py && echo "EXISTS"` → EXISTS | 2.1 |
| 2 | session JSON に8セルの output | `Bash: python3 -c "import json, glob; p=glob.glob('.insight/runs/*/DEMO-H01/__marimo__/session/notebook.py.json')[0]; cells=json.load(open(p))['cells']; assert len(cells)==8, f'Got {len(cells)}'; assert all(c.get('outputs') for c in cells), 'Missing output'"` | 2.2, 3.1 |
| 3 | verdict に conclusion + **evidence_summary（発見パターンの列挙）** + open_questions | `Bash: python3 -c "import json, glob; p=glob.glob('.insight/runs/*/DEMO-H01/__marimo__/session/notebook.py.json')[0]; v=str(json.load(open(p))['cells'][6]); assert 'conclusion' in v.lower() or 'open_questions' in v.lower(), 'verdict missing key fields'"` | 2.3 |
| 4 | journal に observe + evidence + question（conclude なし） | `Grep: pattern="type: observe" path=".insight/designs/DEMO-H01_journal.yaml"` → 1件以上; `Grep: pattern="type: evidence" path=".insight/designs/DEMO-H01_journal.yaml"` → 1件以上; `Grep: pattern="type: conclude" path=".insight/designs/DEMO-H01_journal.yaml"` → 0件 | 4.1, 4.2, 4.5 |
| 5 | DEMO-H01 の status == analyzing | `MCP: get_analysis_design(design_id="DEMO-H01")` → status == "analyzing" | 3.3 |
| 6 | DEMO-H01 の next_action == null | `MCP: get_analysis_design(design_id="DEMO-H01")` → next_action == null | 1.3 |
| 7 | summary.md が存在し、DEMO-H01 の結果が記載 | `Bash: ls .insight/runs/*/summary.md && echo "EXISTS"` → EXISTS; `Grep: pattern="DEMO-H01" path=".insight/runs/*/summary.md"` → 1件以上 | 5.1 |
| 8 | claude -p が正常終了 | `Bash: echo $?` → 0（claude -p 実行直後に確認） | 6.1 |

---

### E2E-02: 正常系 — confirmatory（因果推論）

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-02 |
| **テスト名** | Confirmatory 単件バッチ実行（PSM） |
| **目的** | 因果推論（傾向スコアマッチング）を含む confirmatory 設計書が正常に処理されるか |
| **実行方法** | claude -p batch-prompt.md |

**事前条件:**
1. CAUSAL-H01 相当の設計書に `next_action: {"type": "batch_execute"}` を設定
2. sklearn, statsmodels が dev 依存にインストール済み（FR-3.5 で自動追加もテスト可）

**期待値:**

| # | 期待値 | 検証方法 | カバーするAC |
|---|--------|----------|-------------|
| 1 | verdict に AC pass/fail + 総合判定 | `Bash: python3 -c "import json, glob; p=glob.glob('.insight/runs/*/CAUSAL-H01/__marimo__/session/notebook.py.json')[0]; v=str(json.load(open(p))['cells'][6]).lower(); assert 'pass' in v or 'fail' in v, 'No AC judgment in verdict'"` | 2.4 |
| 2 | evidence に direction: supports or contradicts | `Bash: python3 -c "import yaml; j=yaml.safe_load(open('.insight/designs/CAUSAL-H01_journal.yaml')); evs=[e for e in j['events'] if e['type']=='evidence']; dirs=[e.get('metadata',{}).get('direction') for e in evs]; assert all(d in ('supports','contradicts') for d in dirs), f'Invalid directions: {dirs}'"` | 4.4 |
| 3 | methodology.package のパッケージが利用可能 | `Bash: python3 -c "import statsmodels; print('OK')"` → OK; `Bash: python3 -c "import sklearn; print('OK')"` → OK | 3.5 |

---

### E2E-03: エラー系 — 修復不能エラー

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-03 |
| **テスト名** | 修復不能エラーでのスキップ |
| **目的** | 修復不能なエラー（存在しないデータソース等）で当該設計書がスキップされ、バッチ全体は継続するか |
| **実行方法** | 存在しないデータソースを参照する設計書をキューに入れて実行 |

**期待値:**

| # | 期待値 | 検証方法 | カバーするAC |
|---|--------|----------|-------------|
| 1 | 当該設計書がスキップされる | `MCP: get_analysis_design(design_id="{error_design_id}")` → status が analyzing に遷移していない（in_review のまま） | 3.2 |
| 2 | summary の "Requires Attention" にエラー詳細 | `Grep: pattern="Requires Attention" path=".insight/runs/*/summary.md"` → 1件以上; `Grep: pattern="{error_design_id}" path=".insight/runs/*/summary.md"` → Requires Attention セクション内に該当 ID が記載 | 5.3 |
| 3 | 他の設計書の処理は正常継続 | `Bash: ls .insight/runs/*/DEMO-H01/notebook.py && echo "EXISTS"` → EXISTS（正常設計書の notebook が生成されている）; `MCP: get_analysis_design(design_id="DEMO-H01")` → status == "analyzing" | 3.2 |

---

### E2E-04: エラー系 — terminal status スキップ

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-04 |
| **テスト名** | Terminal status 設計書のスキップ |
| **目的** | supported/rejected/inconclusive の設計書がバッチ処理でスキップされるか |
| **実行方法** | status=supported の設計書に next_action を設定して実行 |

**期待値:**

| # | 期待値 | 検証方法 | カバーするAC |
|---|--------|----------|-------------|
| 1 | 設計書がスキップされる | `Bash: ls .insight/runs/*/{supported_design_id}/notebook.py 2>&1` → "No such file" (notebook が生成されていない) | 1.4 |
| 2 | summary にスキップ理由が記録される | `Grep: pattern="{supported_design_id}" path=".insight/runs/*/summary.md"` → 1件以上; `Grep: pattern="skip\|terminal\|supported" path=".insight/runs/*/summary.md" -i` → スキップ理由の記載あり | 1.4 |

---

### E2E-05: 複数件バッチ（混合シナリオ）

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-05 |
| **テスト名** | 複数件混合バッチ |
| **目的** | 複数設計書（正常 + エラー + terminal）が混在するバッチが正しく処理されるか |
| **実行方法** | 3件の設計書をキューに入れて実行 |

**事前条件:**
1. 設計書A: exploratory, priority=1（正常）
2. 設計書B: confirmatory, priority=2（正常）
3. 設計書C: supported, priority=3（terminal → スキップ）
4. 設計書D: exploratory, priority なし（正常、最後に処理されるべき）

**手順:**
1. A, B, C, D を全てキューに投入
2. バッチ実行
3. 処理完了後、**設計書A（status=analyzing）に再度 next_action を設定して再実行**し、AC-3.4 の冪等性を検証

**期待値:**

| # | 期待値 | 検証方法 | カバーするAC |
|---|--------|----------|-------------|
| 1 | A → B → D の順で処理される（priority 昇順、なしは最後） | `Bash: python3 -c "import yaml, glob, os; journals={}; [journals.update({os.path.basename(f).replace('_journal.yaml',''):yaml.safe_load(open(f))}) for f in glob.glob('.insight/designs/*_journal.yaml')]; times={k:v['events'][-1]['created_at'] for k,v in journals.items() if v.get('events')}; print(times)"` → A の最終イベント時刻 < B < D の順序を確認 | 1.2 |
| 2 | A, B, D は正常処理（notebook + journal + analyzing） | `Bash: for id in A_ID B_ID D_ID; do ls .insight/runs/*/$id/notebook.py && echo "$id: OK"; done` → 3件全て OK; `MCP: get_analysis_design(design_id="A_ID")` 等 → 全て status == "analyzing" | 2.1, 3.3 |
| 3 | C はスキップ | `Bash: ls .insight/runs/*/C_ID/notebook.py 2>&1` → "No such file" | 1.4 |
| 4 | summary の Overview に4件全て表示 | `Grep: pattern="A_ID\|B_ID\|C_ID\|D_ID" path=".insight/runs/*/summary.md"` → 4件全ての ID が記載 | 5.2 |
| 5 | summary のタイムスタンプ > 最後の journal | `Bash: python3 -c "import os, glob, yaml; summary=glob.glob('.insight/runs/*/summary.md')[0]; s_mtime=os.path.getmtime(summary); j_files=glob.glob('.insight/designs/*_journal.yaml'); j_mtime=max(os.path.getmtime(f) for f in j_files); assert s_mtime > j_mtime, f'summary({s_mtime}) <= journal({j_mtime})'; print('OK')"` → OK | 6.4 |
| 6 | summary に Overview テーブル（ID/title/intent/verdict/issues の5列）+ Requires Attention + Next Steps の3セクション | `Grep: pattern="## Overview\|## Requires Attention\|## Next Steps" path=".insight/runs/*/summary.md"` → 3件; `Grep: pattern="ID.*title.*intent.*verdict.*issues\|ID.*\|.*title.*\|.*intent.*\|.*verdict.*\|.*issues" path=".insight/runs/*/summary.md" -i` → Overview テーブルヘッダに5列が存在 | 5.4 |
| 7 | 手順3の再実行で設計書A の status が analyzing のまま変わらない（遷移スキップ） | `MCP: get_analysis_design(design_id="A_ID")` → 再実行後も status == "analyzing"（変化なし） | 3.4 |

---

### E2E-06: 安全終了 — max-budget-usd 到達

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-06 |
| **テスト名** | Budget 上限での安全終了 |
| **目的** | --max-budget-usd に到達した場合、セッションが安全に終了するか |
| **実行方法** | 5件以上の設計書をキューに入れ、--max-budget-usd を小さめの値（例: 1.0）で実行。途中で budget 到達による中断を発生させる |

> **設計判断**: Max プランでは budget は課金制御ではなくセッション制御の安全弁。極小値（0.01）だと1件も処理されずフレークするため、少なくとも1〜2件は処理完了する程度の値を設定する。

**期待値:**

| # | 期待値 | 検証方法 | カバーするAC |
|---|--------|----------|-------------|
| 1 | セッションがエラーではなく正常終了する（exit code で確認） | `Bash: echo $?` → 0（claude -p 実行直後に確認）; exit code が 0 でない場合も、stderr に "budget" 関連メッセージがあれば正常中断と判断: `Grep: pattern="budget\|limit\|max-budget" path="/tmp/e2e06-stderr.log" -i` | 6.2 |
| 2 | budget 到達前に処理された設計書の notebook/journal が残っている | `Bash: ls .insight/runs/*/*/notebook.py 2>/dev/null \| wc -l` → 1以上（少なくとも1件は処理済み）; `Bash: ls .insight/designs/*_journal.yaml 2>/dev/null \| wc -l` → 1以上 | 6.2 |
| 3 | summary.md が生成されている（中断時点の結果を含む） | `Bash: ls .insight/runs/*/summary.md && echo "EXISTS"` → EXISTS; `Grep: pattern="budget\|中断\|interrupted" path=".insight/runs/*/summary.md" -i` → 中断理由の記載あり | 6.2 |

---

## E2Eテストサマリ

| テストID | テスト名 | 実行方法 | カバーするAC |
|----------|---------|----------|-------------|
| E2E-01 | Exploratory 単件バッチ | claude -p | 1.1, 1.3, 2.1, 2.2, 2.3, 3.1, 3.3, 4.1, 4.2, 4.5, 5.1, 6.1 |
| E2E-02 | Confirmatory (PSM) | claude -p | 2.4, 3.5, 4.4 |
| E2E-03 | 修復不能エラー | claude -p | 3.2, 5.3 |
| E2E-04 | Terminal status スキップ | claude -p | 1.4 |
| E2E-05 | 複数件混合バッチ | claude -p | 1.2, 3.4, 5.2, 5.4, 6.4 |
| E2E-06 | Budget 安全終了 | claude -p | 6.2 |

## 統合テストサマリ

| テストID | 対象 | カバーするAC |
|----------|------|-------------|
| Integ-01 | キュー管理（next_action） | 1.1, 1.3 |
| Integ-02 | セルコントラクト準拠 | 2.1, 2.2, 2.4, 3.1 |
| Integ-03 | データソースフォールバック | 2.5 |
| Integ-04 | エラー修正ループ | 3.2, 3.6 |
| Integ-05 | パッケージ事前インストール | 3.5 |
| Integ-06 | journal 自動記録 | 4.1, 4.2, 4.4, 4.5 |
| Integ-07 | journal 追記 | 4.3 |
| Integ-08 | MCP 接続失敗 | 6.3 |
| Integ-09 | lib_dir カタログ化 | FR-2.6 |
| Integ-10 | 自己レビュー・時間予算 | NFR Performance |
| Integ-11 | ディレクトリ命名・設定解決 | FR-2.5 |

## カバレッジ検証

### 全 AC のカバレッジ

| AC | Integ | E2E | カバー済み |
|----|:-----:|:---:|:---------:|
| 1.1 | Integ-01 | E2E-01 | ✓ |
| 1.2 | - | E2E-05 | ✓ |
| 1.3 | Integ-01 | E2E-01 | ✓ |
| 1.4 | - | E2E-04 | ✓ |
| 2.1 | Integ-02 | E2E-01 | ✓ |
| 2.2 | Integ-02 | E2E-01 | ✓ |
| 2.3 | - | E2E-01 | ✓ |
| 2.4 | Integ-02 | E2E-02 | ✓ |
| 2.5 | Integ-03 | - | ✓ |
| 3.1 | Integ-02 | E2E-01 | ✓ |
| 3.2 | Integ-04 | E2E-03 | ✓ |
| 3.3 | - | E2E-01 | ✓ |
| 3.4 | - | E2E-05 | ✓ |
| 3.5 | Integ-05 | E2E-02 | ✓ |
| 3.6 | Integ-04 | - | ✓ |
| 4.1 | Integ-06 | E2E-01 | ✓ |
| 4.2 | Integ-06 | E2E-01 | ✓ |
| 4.3 | Integ-07 | - | ✓ |
| 4.4 | Integ-06 | E2E-02 | ✓ |
| 4.5 | Integ-06 | E2E-01 | ✓ |
| 5.1 | - | E2E-01 | ✓ |
| 5.2 | - | E2E-05 | ✓ |
| 5.3 | - | E2E-03 | ✓ |
| 5.4 | - | E2E-05 | ✓ |
| 6.1 | - | E2E-01 | ✓ |
| 6.2 | - | E2E-06 | ✓ |
| 6.3 | Integ-08 | - | ✓ |
| 6.4 | - | E2E-05 | ✓ |

**全28 AC がカバー済み。** 未カバー: 0件。

## 成功基準

- [ ] Integ-01〜11: 全テストケースがパス
- [ ] E2E-01: Exploratory 単件が正常完了（notebook + journal + summary）
- [ ] E2E-02: Confirmatory (PSM) が AC 判定を含めて正常完了
- [ ] E2E-03: 修復不能エラーでスキップ + summary 記録
- [ ] E2E-04: Terminal status 設計書がスキップされる
- [ ] E2E-05: 3件混合バッチが priority 順で正常処理
- [ ] E2E-06: Budget 上限で安全終了

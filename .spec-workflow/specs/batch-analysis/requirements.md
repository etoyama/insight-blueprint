# Requirements: batch-analysis

## Reference

> **investigation.md**: 本 spec の設計判断は全て実機検証に基づく。requirements/design/tasks の修正時は [investigation.md](investigation.md) の Verified Facts (V1-V4) および Design Decisions (DD-1〜DD-8) に矛盾しないことを確認すること。矛盾する修正が必要な場合は、investigation.md 側を先に更新する。

## Introduction

batch-analysis は、分析設計書（AnalysisDesign）を複数キューに入れておくと、夜間に Claude Code headless モードで marimo notebook を自動生成・実行し、分析結果を journal に記録するスキルである。データアナリストは朝イチで summary.md を確認し、レビュー・最終判定を行う。

現状の分析ワークフローでは、分析設計書の作成からnotebook 実装・実行・journal 記録・振り返りまで全て人間の対話的操作が必要である。本スキルにより、notebook 生成→実行→journal 記録を自動化し、アナリストの時間をレビュー・意思決定に集中させる。

### Key Concepts

- **分析設計書（AnalysisDesign）**: 仮説・検証指標・分析手法・データソースを構造化した YAML ドキュメント。ステートマシン（in_review → analyzing → supported / rejected / inconclusive）でライフサイクルを管理する
- **Insight Journal**: 分析の推論過程を時系列で記録する YAML ファイル（`.insight/designs/{design_id}_journal.yaml`）。8種類のイベントタイプ（observe, hypothesize, evidence, question, decide, reflect, conclude, branch）で構成され、「何を観察し、何を証拠とし、何が未解決か」を追跡する。本スキルでは observe（データの観察）, evidence（仮説を支持/反証する証拠）, question（未解決の問い）の3種を自動生成する。conclude（結論）は人間の判断として自動生成しない
- **セルコントラクト**: marimo notebook の8セル固定構造。各セルの入出力を契約として定義し、notebook の構造一貫性と lineage 記録の完全性を保証する

## Alignment with Product Vision

- **Claude Code First**: Claude Code の headless モード（`-p`）を活用し、MCP ツール経由で設計書の読み取り・ステータス遷移を行う。人間の介入なしで夜間に自動実行
- **知見の自動蓄積**: notebook 実行結果を自動的に journal イベント（observe, evidence, question）として記録。手動記録を最小化
- **分析の再現性向上**: セルコントラクト方式により notebook 構造が一貫し、生成された notebook は再実行可能
- **Extension Policy 準拠**: MCP ツール・モデル変更なし。全て Skill レイヤーで実現

## Requirements

### REQ-1: バッチキュー管理

**User Story:** As a データアナリスト, I want to 分析設計書をバッチ実行キューに入れたい, so that 夜間に自動で分析が実行される

**Functional Requirements:**

- FR-1.1: AnalysisDesign の `next_action` フィールドに `{"type": "batch_execute"}` を設定することでキューに投入できる
- FR-1.2: `next_action` に `priority` フィールド（integer）を任意で設定でき、値が小さい順に処理される
- FR-1.3: バッチ実行完了後、`next_action` は `null` にリセットされる
- FR-1.4: `status` が terminal（supported / rejected / inconclusive）の設計書はキューに入れても処理をスキップする

#### Acceptance Criteria

- AC-1.1: WHEN `update_analysis_design(design_id, next_action={"type": "batch_execute"})` を実行 THEN 設計書の `next_action` が更新される
- AC-1.2: WHEN バッチ実行時に複数設計書がキューにある THEN `priority` の昇順で処理される（`priority` なしは最後）
- AC-1.3: WHEN 設計書の処理が完了 THEN `next_action` が `null` にリセットされる
- AC-1.4: WHEN terminal ステータスの設計書がキューにある THEN スキップされ、summary にスキップ理由が記録される

### REQ-2: marimo notebook 自動生成

**User Story:** As a データアナリスト, I want to 分析設計書から自動的に marimo notebook が生成されてほしい, so that 手動で notebook を書く必要がない

**Functional Requirements:**

- FR-2.1: 設計書の全フィールド（hypothesis, metrics, explanatory, chart, methodology, source_ids）を読み取り、対応する marimo notebook を生成する
- FR-2.2: 生成される notebook は8セル固定のセルコントラクトに従う（imports → meta → data_load → data_prep → analysis → viz → verdict → lineage）。各セルの責務境界は以下の通り:
  - **Cell 3 (data_prep)**: methodology に依存しないデータ前処理のみ。欠損処理、異常値除外、型変換、対象データのフィルタ、特徴量エンジニアリング（one-hot, binning 等）。全操作を `tracked_pipe` 経由で lineage に記録する
  - **Cell 4 (analysis)**: methodology に依存するデータ操作（treatment/control 分割、train/test split、マッチング、リサンプリング等）と統計量の算出・モデルフィッティング。Cell 4 は `session` / `tracked_pipe` を入力に持たないため、Cell 4 内のデータ操作は lineage に記録されない（分析手法の内部操作であり、前処理ではないため許容する）
  - **Cell 5 (viz)**: `df_clean` と `results` の可視化のみ。データ変換は行わない
- FR-2.3: データソースの接続情報は catalog（`get_table_schema`）から取得する
- FR-2.4: `analysis_intent`（exploratory / confirmatory）に応じて analysis セルと verdict セルのロジックが変わる:
  - **exploratory**: Cell 4 はパターン探索（相関、分布、サブグループ比較等）を行い、事前に定めた合否基準は持たない。Cell 6 は発見したパターンの列挙、効果量の解釈、open questions（次に検証すべき仮説の候補）を出力する
  - **confirmatory**: Cell 4 は設計書の metrics に定義された指標を計算し、acceptance criteria（AC）に照らして合否を判定する。Cell 6 は各 AC の pass/fail、総合判定（supported / rejected / inconclusive）、残る不確実性を出力する
- FR-2.5: 生成された notebook は `.insight/runs/YYYYMMDD_HHmmss/{design_id}/notebook.py` に保存される（デフォルト）。初回起動時またはバッチ設定で、notebook 出力ディレクトリを変更可能とする
- FR-2.6: notebook 間で再利用するユーティリティ関数（共通の前処理、カスタム可視化等）を配置するライブラリディレクトリを設定可能とする。生成される notebook はこのディレクトリからインポートできる

#### Acceptance Criteria

- AC-2.1: WHEN 設計書に hypothesis, metrics, explanatory, chart が定義されている THEN 8セル構成の有効な marimo notebook が生成される
- AC-2.2: WHEN 生成された notebook を `uv run marimo export session` で実行 THEN エラーなく全セルが実行される
- AC-2.3: WHEN `analysis_intent` が `exploratory` THEN verdict セルがパターン列挙と open questions を出力する
- AC-2.4: WHEN `analysis_intent` が `confirmatory` THEN verdict セルが metrics の AC 合否判定を出力する
- AC-2.5: WHEN 設計書の `source_ids` が空 THEN catalog 検索にフォールバックし、利用可能なソースを推定する

### REQ-3: バッチ実行

**User Story:** As a データアナリスト, I want to 生成された notebook が自動で実行されてほしい, so that 朝に結果を確認するだけでよい

**Functional Requirements:**

- FR-3.1: `uv run marimo export session` で notebook を実行し、session JSON を取得する
- FR-3.2: 実行結果（session JSON）は `__marimo__/session/` に自動保存される
- FR-3.3: 実行エラーが発生した場合、エージェントは修正を試みる。修正不能なエラーの場合のみ当該設計書をスキップし、他の設計書の処理を継続する（エラー分離）。具体的には:
  - エージェントが修正可能なエラー（構文エラー、marimo 固有の記法ミス、import エラー等）は marimo 公式ドキュメント（context7 経由）を参照して修正を試み、再実行する
  - 修正が成功した場合、再発防止のために `.claude/rules/marimo-notebooks.md` に得られた知見を追記する
  - 修正を3回試みても解消しないエラーは「修正不能」としてスキップし、summary に詳細を記録する
- FR-3.4: 実行後、設計書のステータスを `analyzing` に遷移する
- FR-3.5: notebook 実行前に、設計書の `methodology.package` で指定されたパッケージがインストール済みか確認し、不足している場合は `uv add --dev` で追加する

#### Acceptance Criteria

- AC-3.1: WHEN notebook が正常に生成されている THEN `marimo export session` で全セルが実行される
- AC-3.2: WHEN 1つの notebook でエラーが発生 THEN エージェントが修正を試みる。修正成功なら再実行し、修正不能（3回失敗）なら当該設計書をスキップして次の設計書の処理が続行される
- AC-3.6: WHEN marimo 固有の記法エラーを修正した THEN `.claude/rules/marimo-notebooks.md` に再発防止の知見が追記される
- AC-3.3: WHEN notebook 実行が完了 THEN 設計書のステータスが `analyzing` に遷移する
- AC-3.4: WHEN 設計書のステータスが `in_review` 以外（例: `analyzing`）THEN ステータス遷移はスキップされる（冪等性）
- AC-3.5: WHEN `methodology.package` に `statsmodels` が指定され未インストール THEN `uv add --dev statsmodels` が実行されてから notebook 実行に進む

### REQ-4: journal 自動記録

**User Story:** As a データアナリスト, I want to 分析結果が自動的に journal に記録されてほしい, so that 手動で観察を記録する必要がない

**Functional Requirements:**

- FR-4.1: session JSON の text/markdown セルから分析結果を抽出する
- FR-4.2: 抽出結果を analysis-journal 形式の YAML に記録する（`.insight/designs/{design_id}_journal.yaml`）
- FR-4.3: 生成する journal イベントの種類は `observe`, `evidence`, `question` のみ。`conclude` は生成しない（人間が判定）
- FR-4.4: `evidence` イベントには `metadata.direction`（supports / contradicts）を付与する
- FR-4.5: 既存の journal がある場合は追記する（上書きしない）

#### Acceptance Criteria

- AC-4.1: WHEN notebook 実行が成功 THEN journal YAML に最低1つの `observe` と1つの `evidence` イベントが記録される
- AC-4.2: WHEN verdict セルに open questions がある THEN 各 question が `question` イベントとして記録される
- AC-4.3: WHEN 既存 journal がある THEN 新しいイベントが既存イベントの後に追記される（既存を上書きしない）
- AC-4.4: WHEN evidence の相関値が仮説の方向と一致 THEN `direction: supports` が設定される
- AC-4.5: WHEN `conclude` イベントが生成される THEN これはバグである（conclude は人間の判定であり、自動生成してはならない）

### REQ-5: 朝レビュー用サマリー

**User Story:** As a データアナリスト, I want to 夜間バッチの結果を一覧で確認したい, so that 朝イチで優先順位をつけてレビューできる

**Functional Requirements:**

- FR-5.1: バッチ完了後、`.insight/runs/YYYYMMDD_HHmmss/summary.md` に結果一覧を生成する
- FR-5.2: サマリーには全処理対象の設計書一覧（ID, タイトル, intent, verdict, issues）を含む
- FR-5.3: 注意が必要な設計書（エラー、予想外の結果）を "Requires Attention" セクションで強調する
- FR-5.4: 各設計書の次のアクション候補を提示する（`/analysis-reflection`, `/analysis-journal` 等）

#### Acceptance Criteria

- AC-5.1: WHEN バッチ実行が完了 THEN `summary.md` が生成される
- AC-5.2: WHEN 全設計書が正常に処理された THEN サマリーの Overview テーブルに全件が表示される
- AC-5.3: WHEN エラーが発生した設計書がある THEN "Requires Attention" セクションにエラー内容と対処法が記載される
- AC-5.4: WHEN サマリーを読む THEN 30秒以内に全体像が把握できる構造である

### REQ-6: headless オーケストレーション

**User Story:** As a データアナリスト, I want to 夜間に Claude Code が無人で実行されてほしい, so that 手動操作なしで分析が完了する

**Functional Requirements:**

- FR-6.1: Claude Code の `-p` フラグと `--permission-mode bypassPermissions` で非対話実行する
- FR-6.2: `--allowedTools` で必要最小限のツールのみ許可する（MCP tools + Read/Write/Bash/Glob/Grep）
- FR-6.3: `--max-budget-usd` でセッション上限を設定する（Max プランでは追加コストなし。レート制限・暴走時の安全弁として機能）
- FR-6.4: `--model sonnet` で品質優先とする（V5b で haiku の品質同等を確認済みだが、30分/件の自己レビューを含む丁寧な分析には sonnet の推論力を優先する）
- FR-6.5: バッチ実行の全ログを `.insight/runs/YYYYMMDD_HHmmss/session.log` に保存する
- FR-6.6: batch-prompt.md にオーケストレーション全体の instructions を含める

#### Acceptance Criteria

- AC-6.1: WHEN headless コマンドを実行 THEN 人間の介入なしでバッチ全体が完了する
- AC-6.2: WHEN `--max-budget-usd` に達した THEN セッションが安全に終了し、処理済みの結果は保持される
- AC-6.3: WHEN MCP サーバーが起動できない THEN session.log にエラーが記録される
- AC-6.4: WHEN 全設計書の処理が完了 THEN summary.md が生成されてからセッションが終了する

## Non-Functional Requirements

### Code Architecture and Modularity

- Skill レイヤーでの実装に限定（Extension Policy 準拠）
- MCP ツール・Pydantic モデルへの変更なし
- `next_action` フィールドの convention は SKILL.md に文書化
- セルコントラクト定義は SKILL.md に含める

### Performance

- 設計書1件あたりの処理時間: 30分以内（notebook 生成 + 実行 + 自己レビュー・修正 + journal 記録）。速度より丁寧さを優先する:
  - データ処理の不備がないか確認・修正する
  - 批判的な観点で分析結果をレビューし、問題があれば notebook を修正して再実行する
  - 結果の解釈が妥当か、open questions に漏れがないか点検する
- バッチ全体の制御: `--max-budget-usd` でセッション上限を設定（Max プラン前提、追加コストなし。安全弁として機能）
- marimo export session の実行: 60秒以内/notebook

### Security

- `--dangerouslySkipPermissions` は使用しない
- `--allowedTools` で明示的にツールをホワイトリスト
- notebook はデータソースへのネットワークアクセスを許可する（BigQuery 等のクラウドデータウェアハウスへの接続を含む）。ただし外部からの notebook へのインバウンドアクセスは不可（marimo サーバーを公開しない）
- 生成される notebook にハードコードされたシークレットが含まれない

### Reliability

- エラー発生時はエージェントが修正を試みる（最大3回）。修正不能な場合のみスキップし、他の設計書の処理をブロックしない（修正優先のエラー分離）
- 修正で得られた知見は `.claude/rules/marimo-notebooks.md` に蓄積し、同じエラーの再発を防ぐ（自己改善ループ）
- バッチ途中でセッションが中断しても、処理済みの結果（notebook, journal, summary の途中結果）は保持される
- session.log に全操作の記録が残る

### Usability

- summary.md を読むだけで朝のトリアージが30秒以内に完了する
- 各設計書の結果から `/analysis-reflection` へのチェーン方法が明示される
- notebook は `uv run marimo edit` で対話的に再確認可能

## Out of Scope

- **スケジューリング（L1）**: launchd / cron の設定は本スキルのスコープ外。起動コマンドのみ提供
- **terminal ステータス遷移**: `supported` / `rejected` / `inconclusive` への遷移は人間が `/analysis-reflection` で行う
- **WebUI 変更**: Extension Policy により WebUI は Fix。バッチ結果の表示は summary.md で代替
- **MCP ツール追加**: 既存ツールの convention 活用のみ。新規ツール追加なし
- **AnalysisDesign モデル変更**: `next_action` フィールドの convention 活用のみ。enum/フィールド追加なし
- **`conclude` journal イベントの自動生成**: 最終判定は常に人間が行う
- **マルチマシン実行**: ローカルマシンでの単一セッション実行のみ
- **分析設計書の自動生成**: 本スキルは「既存の設計書を実行する」スコープ。設計書の作成は人間が行う前提
- **独立した品質ゲート**: hooks/subagent による段階的な品質チェック機構（FV-2）は含まない。本スキルではエージェント自身が自己レビュー・修正を行うが、独立したレビュアーとしての品質ゲートは Future Vision のスコープ

## Future Vision

本スキル（batch-analysis）は以下の構想の基盤となる。これらは本スキルのスコープ外だが、batch-analysis の設計判断がこれらの拡張を阻害しないよう留意する。

### FV-1: 自律的分析設計生成

**動機**: batch-analysis により分析実行が自動化されると、律速は「人間による分析設計書の作成」に移る。設計書の量産がボトルネックになる。

**構想**: 分析結果を入力に、Claude Code が次の分析設計書を自動生成する。生成パイプラインは1つで、出力先を信頼度で振り分ける。

```
batch-analysis 実行結果
  │
  ├─ verdict.open_questions     → "季節性を統制すべきか？"
  ├─ journal の question イベント → "店舗間で相関に差があるか？"
  └─ evidence (contradicts)    → 反証からの新仮説
  │
  ▼
設計書自動生成パイプライン
  │
  ├─ 派生設計書を生成（parent_id 付き）
  ├─ 自己評価（仮説の新規性、データ可用性、手法妥当性）
  │
  ▼
信頼度に応じてキュー振り分け
  │
  ├─ 高: next_action: {"type": "batch_execute"}  → そのまま夜間実行へ
  └─ 低: next_action: {"type": "human_review"}   → 人間の承認待ち
```

信頼度の判定基準（例）:
- **高**: 既存設計の `open_questions` から機械的に導出。親設計のコンテキストが豊富
- **中**: evidence (contradicts) から反仮説。反証の解釈に幅がある
- **低**: 新テーマの探索、データソースの妥当性が不明

**閾値は人間が設定する。** 最初は全て `human_review` に流し、運用で信頼を積みながら `batch_execute` への自動投入を段階的に解放する。FV-2 の品質ゲートが信頼度の裏付けになる。

**batch-analysis との接続**: verdict dict の `open_questions`、journal の `question` / `evidence` イベント、`parent_id` フィールド、`next_action` convention — 全て現在の設計がそのままサポートする。`next_action.type` に `human_review` を追加するだけ。

### FV-2: 品質ゲート（hooks + subagent による段階的レビュー）

**動機**: 夜間の自動分析の品質を担保するために、notebook 生成→実行→journal 記録の各段階にレビューポイントを設ける。

**構想**: Claude Code の hooks 機構を利用して、以下の段階で品質チェック用の skill/subagent を起動する。ゲートを通過しなければ次段階に進まない。

| ゲート | タイミング | チェック内容 |
|--------|----------|-------------|
| G1: 分析手法レビュー | notebook 生成後、実行前 | methodology が hypothesis に対して適切か、前提条件（サンプルサイズ、分布の仮定）を満たすか |
| G2: データ加工レビュー | Cell 3 (data_prep) 実行後 | 欠損処理の妥当性、フィルタによるバイアスの有無、データリークの検出 |
| G3: 結果解釈レビュー | Cell 6 (verdict) 実行後 | p-hacking の兆候、効果量の実質的意義、交絡因子の見落とし |
| G4: 結論妥当性レビュー | journal 記録前 | evidence と conclusion の整合性、open questions の網羅性 |

**batch-analysis との接続**: セルコントラクトの8セル固定構造が各ゲートの挿入点を自然に提供する。Cell 3 の後、Cell 6 の後、journal 記録前にフックが入る。session JSON のセル別出力がゲートの入力データになる。

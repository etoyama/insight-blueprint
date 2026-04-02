# batch-analysis: Investigation Log & Design Decisions

> **目的**: spec のレビュー・修正サイクルを通じて「検証済み事実」と「確定した設計判断」が失われることを防ぐ。
> requirements.md / design.md / tasks.md の修正時は、本文書の Verified Facts に矛盾しないことを確認すること。

---

## 1. Verified Facts（検証済み事実）

実機で検証し、再現可能な結果のみ記載する。推測は含まない。

### V1: Claude Code headless 実行（2026-03-27 検証）

| 項目 | 結果 | 検証コマンド |
|------|:----:|-------------|
| **V1a: MCP 接続** | pass | `claude -p "list_analysis_designs を呼べ" --allowedTools "mcp__insight-blueprint__list_analysis_designs" --permission-mode bypassPermissions --output-format json` |
| **V1b: Bash 実行** | pass | V1d で統合検証 |
| **V1c: Write/Read** | pass | V1d で統合検証 |
| **V1d: 統合テスト** | pass | MCP×2 + Write×1 + Bash×1 を1セッションで実行 |
| **V1e: 最小権限** | pass | `--allowedTools` + `--permission-mode bypassPermissions` の組み合わせで動作。`--dangerouslySkipPermissions` 不要 |
| **V1f: MCP 自動起動** | pass | `.mcp.json` の stdio サーバーが headless 起動時に自動起動 |

**V1d 統合テスト実績値:**
- ターン数: 6
- 所要時間: 25.2秒
- コスト: $0.34（Opus、cold cache）
- 実行内容: `list_analysis_designs` → `get_analysis_design(DEMO-H01)` → Write `/tmp/batch-v1d-test.md` → Bash `uv --version`

### V1g: ターン上限とコスト制御

- **`--max-turns` フラグは存在しない**（claude --help で確認済み、2026-03-27時点）
- 代替手段: `--max-budget-usd` ��コスト上限制御
- `--model` でモデル選択可能（sonnet でコスト最適化）
- `--output-format json` でセッションメタデータ（turns, cost, duration）取得可

### V2: marimo バッチ実行方法（2026-03-27 検証）

| 方法 | 判定 | 根拠 |
|------|:----:|------|
| `marimo export html` | △ | 全セル実行される。HTML 321KB / **218K tokens** — Claude が読むには重すぎる |
| **`marimo export session`** | **○** | JSON 出力。セルごとに `{mimetype: data}` で構造化。text/markdown セルだけ抽出すれば軽量 |
| `marimo run` | × | Web サーバー起動。バッチ向きでない |

**marimo export session の特性:**
- 出力先: `__marimo__/session/{notebook_name}.json`（notebook と同ディレクトリ配下）
- キャッシュ: 変更のない notebook はスキップ（`--force-overwrite` で上書き可）
- ディレクトリ指定: 複数 notebook を一括実行可
- `--continue-on-error`: エラー時も次の notebook に進む（デフォルト有効）

**session JSON の構造:**
```json
{
  "version": "1",
  "metadata": {"marimo_version": "...", "script_metadata_hash": "..."},
  "cells": [
    {
      "id": "...",
      "code_hash": "...",
      "outputs": [{"data": {"text/markdown": "<html content>"}}],
      "console": []
    }
  ]
}
```

- text/markdown セル: 数百〜数千文字（Claude が読める）
- image セル: 100K〜200K文字（Base64 エンコード画像、スキップすべき）
- **重要**: `text/markdown` の値は HTML タグで囲まれている（`<span class="markdown prose ...">...</span>`）

### V3: セルコントラクト付き notebook 生成（2026-03-27 検証）

**テスト条件:**
- モデル: claude-sonnet-4-6
- 入力: DEMO-H01 設計書 + tutorial-sales スキーマ + セルコントラクト定義プロンプト
- 出力: `/tmp/v3-generated-notebook.py`（250行、8セル）

**実績値:**
- ターン数: 2
- 所要時間: 293.8秒
- コスト: **$0.62**（sonnet）
- 結果: marimo export session でエラーなく全セル実行

**生成品質:**
- _prefix ルール: 全セルで遵守（_fig, _ax, _palette, _subset, _slot, _corr 等）
- plt.gcf(): viz セルの最後に正しく配置
- mo.mermaid(): lineage セルで正しく使用
- import marimo as mo: Cell 2 で正しくインポート
- LineageSession + tracked_pipe: 正しく連携

**判明した不具合（改善済み）:**
- Cell 6 (verdict) の `mo.md()` で multiline f-string 展開を使うと、indentation の混在でコードブロック化する
  - **原因**: `{_evidence_md}` が indent なしで展開され、周囲の8スペース indent と混在
  - **修正**: 事前に string を組み立ててから `mo.md()` に渡す
- Cell 4 (analysis) の `results` dict が session JSON に text 出力として現れない
  - **原因**: `mo.md()` で結果を表示していなかった（dict を return するのみ）
  - **修正**: results の主要値を `mo.md()` でも表示する

### V4: journal 自動抽出（V3 から自明）

V3 の session JSON 出力から以下が構造的に取得可能であることを確認:

| Cell | session JSON の出力 | journal イベント種別 |
|------|-------------------|-------------------|
| Cell 2 (data_load) | "408行、10列、期間 2025-04-02〜09-22" | `observe` |
| Cell 3 (data_prep) | "408→207行（iced_coffee + frappuccino に絞り込み）" | `observe` |
| Cell 6 (verdict) | "r=0.4659（中程度の正の相関）" | `evidence` |
| Cell 6 (verdict) | "afternoon=0.6931, morning=0.1262" | `evidence` |
| Cell 6 (verdict) | 4つのオープンクエスチョン | `question` |

### コスト実績値

| 項目 | モデル | 実測コスト |
|------|--------|-----------|
| MCP 読み取り（list + get） | Opus (cold cache) | $0.34 |
| 統合テスト 6ターン | Opus (cold cache) | $0.34 |
| notebook 生成 2ターン | **Sonnet** | **$0.62** |
| 設計書1件 full pipeline（推定） | Sonnet | ~$0.80-1.00 |
| **夜間バッチ5件（推定）** | **Sonnet** | **~$4-5** |

---

## 2. Design Decisions（確定した設計判断）

### DD-1: notebook 生成戦略 → セルコ��トラクト方式（C案）

3案を比較し C 案を選択。

| 案 | 概要 | 採否 | 理由 |
|----|------|:----:|------|
| A: フルスクラッチ | 毎回ゼロから生成 | × | marimo 違反リスク高、朝レビューの一貫性なし |
| B: テンプレート穴埋め | 固定テンプレに AI が穴埋�� | × | 仮説ごとに分析ロジックが変わるため穴が大きすぎる |
| **C: セルコントラクト** | **セル構造固定、中身は AI が自由に生成** | **○** | **V3 で実証済み。構造一貫、中身柔軟、marimo 違反を構造的に防止** |

**参照**: Papermill（Netflix）のテンプレート notebook の「構造は固定」思想を借りつつ、「中身は AI が書く」にずらした。

### DD-2: バッチ実行方法 → `marimo export session`

V2 で `marimo export html`（218K tokens で重すぎ）と `marimo run`（サーバー起動）を除外。`marimo export session` が JSON 出力でセル別に構造化データを返す点が決め手。

### DD-3: キュー管理 → `next_action` フィールド convention

3案を比較し B 案を選択。

| 案 | 概要 | 採否 | 理由 |
|----|------|:----:|------|
| A: `queued` status 追加 | DesignStatus enum に値追加 | × | モデル変更の影響範囲大（enum, VALID_TRANSITIONS, tests, REST, WebUI） |
| **B: next_action field** | **既存 dict フィールドに convention 追加** | **○** | **モデル変更なし、Extension Policy 準拠、update_design で操作可** |
| C: 別ファイル | `.insight/batch-queue.yaml` | × | MCP から見えない、管理が二重系統 |

**convention**: `next_action: {"type": "batch_execute", "priority": N}`

### DD-4: 裁量レベル → Mid（journal 記録まで、terminal 遷移は人間）

| レベル | 範囲 | 採否 | 理由 |
|--------|------|:----:|------|
| Low | notebook 生成のみ | × | 夜間完結しない |
| **Mid** | **生成 + 実行 + journal 記録** | **○** | **結果は記録するが結論は人間が出す。レビューの意味が保たれる** |
| High | 結論（terminal 遷移）まで | × | 誤判定リスク。朝のレビューが形骸化 |

### DD-5: headless 起動構成（V5b → haiku → **レビューで sonnet に戻し**）

> **例外**: V5b で haiku の品質が sonnet と同等であることを確認したが、レビューにより品質優先で sonnet を採用。理由: 30分/件の自己レビューを含む丁寧な分析には sonnet の推論力が望ましい。

```bash
claude -p "$(cat skills/batch-analysis/batch-prompt.md)" \
  --model sonnet \
  --allowedTools "mcp__insight-blueprint__list_analysis_designs,mcp__insight-blueprint__get_analysis_design,mcp__insight-blueprint__get_table_schema,mcp__insight-blueprint__update_analysis_design,mcp__insight-blueprint__transition_design_status,Read,Write,Bash,Glob,Grep" \
  --permission-mode bypassPermissions \
  --max-budget-usd 10 \
  > .insight/runs/$(date +%Y%m%d_%H%M%S)/session.log 2>&1
```

各フラグの選択理由:
- `--model sonnet`: V5b で haiku の品質同等を確認済みだが、レビューで品質優先により sonnet を採用。30分/件の自己レビューには sonnet の推論力が望ましい
- `--permission-mode bypassPermissions`: V1e で `dangerouslySkipPermissions` 不要を確認
- `--allowedTools`: V1d で MCP + Read/Write/Bash の組み合わせ動作を確認
- `--max-budget-usd 10`: 5件で ~$4-5 の実績値に対し余裕を持たせた値

### DD-6: セルコントラクト（8セル固定、V3/V5d で更新）

```
Cell 0: imports    → exports: (pd, plt, np, LineageSession, export_lineage_as_mermaid, tracked_pipe)
Cell 1: meta       → input: (mo,)          → display only
Cell 2: data_load  → input: (pd, LineageSession) → exports: (raw_df, session, mo)  ← mo はここで import
Cell 3: data_prep  → input: (raw_df, session, tracked_pipe, mo) → exports: (df_clean,)
Cell 4: analysis   → input: (df_clean, pd, mo)  → exports: (results,)
Cell 5: viz        → input: (df_clean, results, plt) → no export
Cell 6: verdict    → input: (results, mo)  → exports: (verdict,)
Cell 7: lineage    → input: (session, export_lineage_as_mermaid, mo) → no export
```

**marimo 固有のルール（V3 + V5d で検証済み）:**
- 全 cell-local 変数は `_` prefix 必須（`_fig`, `_ax`, `_subset` 等）
- `plt.gcf()` を viz セルの最後の式にする
- `mo.mermaid()` で Mermaid 描画（`mo.md()` + ` ```mermaid ` は不可）
- `mo.md()` 内で multiline f-string 展開を避ける（事前に string 組み立て）
- `import marimo as mo` は **Cell 2** で行い、他セルは引数で受け取る（V5d で Cell 0 に mo を置くと循環依存になることを確認）

### DD-7: verdict dict スキーマ（固定）

```python
verdict = {
    "conclusion": str,             # 一行の結論
    "evidence_summary": list[str], # エビデンス箇条書き
    "open_questions": list[str],   # 未解決の問い
}
```

journal 自動生成のパーサーがこのスキーマに依存するため、変更する場合は journal 記録ロジックも同時に修正する必要がある。

### DD-8: 結果の保存先

```
.insight/runs/
  YYYYMMDD_HHmmss/                 # 日時別（同日追加実行対応、レビューで変更）
    session.log                    # Claude Code セッション全体のログ
    summary.md                     # 朝レビュー用サマリー
    {design_id}/
      notebook.py                  # 生成された marimo notebook
```

journal は既存の場所（`.insight/designs/{design_id}_journal.yaml`）に追記。
session JSON は marimo の convention に従い `__marimo__/session/` に自動保存。

### V5: コスト構造と Ollama ハイブリッド検証（2026-03-27 検証）

#### V5a: 課金形態

```json
{
  "authMethod": "claude.ai",
  "subscriptionType": "max"
}
```

**Max プラン確認済み。`claude -p` のコストはサブスクリプションに含まれる。** investigation 初版で算出した $0.62/件、$4-5/バッチは追加課金ではない。

→ コスト削減の緊急度は低い。Ollama ハイブリッドは「レート制限対策」「サブスク変更時の保険」としての位置づけに変わる。

#### V5c: Ollama ハイブリッド構成テスト

**環境**: Ollama 0.17.7, qwen2.5-coder:32b-instruct-q2_K (12GB)

**テスト方法**: V3 と同等のセルコントラクトプロンプトを `ollama run` に渡し、生成された notebook を `marimo export session` で実行。

**結果**: 8セル構造は正しく生成されたが、**実行は部分成功（Cell 3 以降の出力が空）。**

| 観点 | Sonnet (V3) | Ollama (V5c) |
|------|:-:|:-:|
| 8セル構造 | ○ | ○ |
| `_` prefix ルール | ○ | △（一部欠落） |
| `tracked_pipe` API | ○（正しい） | **×（デコレータとして誤用）** |
| return tuple 構文 | ○ `(df_clean,)` | **×** `df_clean`（tuple なし） |
| verdict 計算 | ○（実数値を計算） | **×（placeholder テキスト `[positive/negative/weak]`）** |
| `mo.md()` 引数 | ○（文字列） | **△（dict/DataFrame を直接渡す箇所あり）** |
| marimo 実行 | 全セル成功 | **部分成功（Cell 3 以降空出力）** |
| 所要時間 | 294秒 | 未計測（体感30秒程度） |
| コスト | $0.62（Max なら $0） | $0 |

**判定: 現状の Ollama (qwen2.5-coder:32b q2_K) は notebook 生成品質が不足。**

不足の主因:
1. **insight-blueprint 固有 API（tracked_pipe）の知識がない** — 学習データに含まれていない
2. **q2_K 量子化が激しすぎる** — 32B モデルでも 12GB に圧縮しており精度低下
3. **プロンプト内のスケルトンコードをそのまま返す傾向** — placeholder を実計算に置換できていない

**改善可能性（未検証）:**
- より大きいモデル（70B+）や軽い量子化（q4_K, q8_0）で品質向上の可能性
- プロンプトに tracked_pipe の API ドキュメントを含めれば API 誤用は防げる可能性
- Claude → Ollama → Claude のパイプラインで、Ollama 出力を Claude が検証・修正する二段構成

#### V5d: Ollama + API ドキュメント注入テスト（2026-03-27 検証）

V5c の主要失敗原因（tracked_pipe API 誤用）に対し、API ドキュメント（関数シグネチャ + 正しい使用例 + よくある間違い）をプロンプトに注入して再テスト。

**注入した情報:**
- `tracked_pipe` の関数シグネチャと `df.pipe()` での正しい使い方
- 「デコレータとして使うのは間違い」という明示的な警告
- `LineageSession` のコンストラクタ
- `export_lineage_as_mermaid` の呼び出し方
- marimo のセルルール（`_` prefix、return tuple、`plt.gcf()`、`mo.mermaid()`）

**結果:**

| 観点 | V5c（注入なし） | V5d（API 注入あり） |
|------|:-:|:-:|
| `tracked_pipe` API | **×（デコレータ誤用）** | **○（df.pipe で正しく使用）** |
| return tuple | × | **○** |
| `_` prefix | △ | **○** |
| `plt.gcf()` | ○ | ○ |
| `mo.mermaid()` | ○ | ○ |
| `mo.md()` 引数 | △（dict 直渡し） | **○（文字列のみ）** |
| lineage 出力 | 失敗（tracked_pipe 不動） | **○（3ステップの lineage 正常出力）** |
| **marimo 実行** | **部分成功** | **全セル成功（手動パッチ2箇所後）** |

**手動パッチが必要だった2箇所（marimo 構造知識の不足）:**
1. Cell 0 の `def imports(mo):` → `def _():` — `mo` は Cell 2 で import するため Cell 0 に渡せない。循環依存
2. 全セルの関数名 `def imports`, `def meta` → `def _` — marimo の convention

**分析:**
- API ドキュメント注入は **insight-blueprint 固有 API の誤用を完全に解消** した
- 残る問題は **marimo 固有の構造知識**（`mo` の import パターン、`def _` convention）
- これらも marimo のセル構造ルールをプロンプトに追加すれば解消可能（要検証）
- **パッチ2箇所は機械的に検出・修正可能**（`mo` を引数に取る Cell 0 を修正、関数名を `_` に統一）

#### V5 の結論

**Max プランである限り、Ollama ハイブリッドの優先度は低い。** ただし API ドキュメント注入により品質ギャップは大幅に縮小した。

| シナリオ | 推奨 |
|---------|------|
| Max プラン継続 | Claude (sonnet) を使う。レビューで品質優先により haiku から変更。DD-5 参照 |
| サブスク変更・レート制限 | Ollama + API 注入 + 自動パッチ（Cell 0 の mo 除去 + 関数名統一）で実用可能 |
| オフライン環境 | Ollama が唯一の選択肢。API 注入 + パッチで対応可能 |

将来的に Ollama ルートを本格化する場合の追加投資:
1. marimo セル構造ルールのプロンプト追加（~10行）
2. 自動パッチスクリプト（Cell 0 の mo 除去 + def 名統一、~20行の Python）
3. より軽い量子化のモデル（q4_K 以上）でのテスト

### V5b: haiku notebook 生成テスト（2026-03-27 検証）

**テスト条件**: V3 と同じセルコントラクトプロンプト、`--model haiku`

| 項目 | Sonnet (V3) | Haiku (V5b) |
|------|:-:|:-:|
| ターン数 | 2 | 4 |
| 所要時間 | 294秒 | **59秒** |
| コスト | $0.62 | **$0.17** |
| 行数 | 250行 | 250行 |
| 8セル構造 | ○ | ○ |
| コード品質 | ほぼ完璧 | **sonnet と同等**（コード構造・ロジックがほぼ同一） |
| marimo 実行 | 全セル成功 | 全セル成功（exit code 1 だが出力は正常） |

**判定: haiku は sonnet と同等の品質で notebook を生成できる。** 5倍速く、コストも 1/4。セルコントラクトが十分詳細なプロンプトであれば、モデルの推論力差はほぼ影響しない。

→ **DD-5 の `--model` 推奨を haiku に変更可能。** Max プラン内なので金額差はないが、速度面で haiku が有利（59秒 vs 294秒）。5件バッチで 5分 vs 25分。

### V6a: 因果推論（傾向スコアマッチング）セルコントラクト検証（2026-03-27 検証）

**テスト条件**: CAUSAL-H01 設計書（PSM: Logit → NN matching → ATT → SMD）、sonnet

**実績値:**
- ターン数: 3
- 所要時間: 388.9秒
- コスト: $0.76
- 行数: **317行**（V3 の 250行より 67行増）
- 結果: **全セル実行成功**（sklearn/statsmodels を dev 依存に追加後）

**8セルコントラクトへのフィット:**

| Cell | 内容 | 行数概算 | フィット |
|------|------|:---:|:---:|
| Cell 3 (data_prep) | iced_coffee フィルタ + 気温二値化 + one-hot encoding | ~40行 | ○ |
| **Cell 4 (analysis)** | **Logit 推定 → NN matching → ATT 算出 → SMD 計算** | **~80行** | **○（収まった）** |
| Cell 5 (viz) | 傾向スコア分布 + バランスチェック（subplot 2枚） | ~40行 | ○ |
| Cell 6 (verdict) | AC-1(ATT>0, p<0.05) + AC-2(SMD<0.1) 判定 | ~30行 | ○ |

**実行結果（分析内容）:**
- iced_coffee 104件、気温中央値 24.6°C で二値化（treated/control 各52件）
- ATT = +1676.9 JPY（p = 0.0000）→ AC-1 PASS
- 全共変量 SMD < 0.1 → AC-2 PASS
- Verdict: **SUPPORTED**
- Mermaid lineage 図も正常出力

**判定: 傾向スコアマッチングは8セル固定構造で問題なく収まる。**

Cell 4 が ~80行になったが、marimo のセルとしては許容範囲（1セル100行以下が目安）。ロジスティック回帰→マッチング→効果推定→バランスチェックの4ステップを1セルに収める形で、リアクティブの粒度としても「分析の一単位」として意味がある。

**A-7（因果推論が8セルに収まるか）は解消。** ただし以下は未検証:
- XGBoost + cross-validation（特徴量エンジニアリング込みで Cell 3+4 が 150行超になる可能性）
- 複数モデル比較（Cell 4 が 1モデルなら OK だが、3モデル比較は overflow しうる）

**依存パッケージの教訓:**
sklearn, statsmodels は dev 依存に追加が必要だった（初回は `ModuleNotFoundError` で全セル失敗）。
→ **batch-prompt.md に「必要なパッケージが不足している場合は `uv add --dev` で追加する」ステップを含める必要がある。** あるいは、notebook 生成前に methodology.package をチェックして事前インストールするロジック。

---

## 3. Assumptions（前提・仮定）

検証はしていないが、設計の前提としているもの。

| ID | 前提 | リスク | 検証方法 |
|----|------|--------|---------|
| A-1 | データソースがローカルファイル（CSV）である | DB 接続が必要な場合は notebook 生成ロジックの変更が必要 | 実際のユースケースで確認 |
| A-2 | 1晩のバッチ対象は5件程度 | 20件以上になると所要時間の再検討が必要 | 運用で確認 |
| ~~A-3~~ | ~~sonnet で十分な品質の notebook が生成できる~~ | ~~複雑な統計手法では Opus が必要かも~~ | **V3 で散布図+相関は確認済み。因果推論は V6a で検証予定** |
| A-4 | `marimo export session` の出力 JSON 形式は安定している | marimo のバージョンアップで変わる可能性 | marimo changelog を監視 |
| A-5 | headless セッションで MCP サーバーのタイムアウトが発生しない | 長時間バッチで MCP 接続が切れる可能性 | 5件バッチの実走で確認 |
| A-6 | Max プランのレート制限が夜間バッチに十分 | 5件連続でレート制限に抵触する可能性 | 5件バッチの実走で確認 |
| ~~A-7~~ | ~~因果推論・ML が8セルコントラクトに収まる~~ | | **V6a で PSM は確認済み。XGBoost + CV は未検証** |
| A-8 | 分析に必要なパッケージ (sklearn, statsmodels 等) がインストール済み | methodology.package で指定されたパッケージが未インストールの場合、全セル失敗 | batch-prompt に事前チェックロジックを含める |

---

## 4. Changelog

| 日付 | 変更内容 |
|------|---------|
| 2026-03-27 | 初版作成。V1-V4 検証結果、DD-1〜DD-8 設計判断を記録 |
| 2026-03-27 | V5 追加。Max プラン確認（コスト問題解消）、Ollama ハイブリッドテスト（品質不足で現時点非推奨）、A-2 更新（コスト→所要時間）、A-6/A-7 追加 |
| 2026-03-27 | V5b 追加。haiku が sonnet 同等品質で 5倍速（59秒 vs 294秒）。V6a 追加。PSM（傾向スコアマッチング）が8セルに収まることを確認。A-7 解消、A-8 追加（パッケージ依存） |
| 2026-03-27 | V5d 追加。Ollama + API ドキュメント注入で tracked_pipe 誤用が完全解消。手動パッチ2箇所（mo 循環依存 + 関数名）で全セル実行成功。Ollama ルートの実用可能性を確認 |

# insight-blueprint チュートリアル

仮説駆動型データ分析の全ワークフローを体験するハンズオンガイドです。
架空のコーヒーチェーン売上データを使い、仮説の設計から検証、新たな仮説の導出までを一連の流れで体験します。

## 体験するスキルと機能

| # | スキル / 機能 | 役割 |
|---|-------------|------|
| 1 | `/catalog-register` | データソースをカタログに登録 |
| 2 | `/analysis-framing` | データの探索と仮説方向の決定 |
| 3 | `/analysis-design` | 仮説設計ドキュメントの作成 |
| 4 | **WebUI** | 仮説・手法のレビューコメント投稿 |
| 5 | `/analysis-revision` | レビュー指摘への対応 |
| 6 | **marimo notebook** | 実データの分析と可視化 |
| 7 | `/data-lineage` | データ変換パイプラインの追跡 |
| 8 | `/analysis-journal` | 推論過程の記録 |
| 9 | `/analysis-reflection` | 構造化された振り返りと結論 |
| 10 | `/catalog-register` | 知見のナレッジ登録 |

## 前提条件

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) がインストール済み
- Python 3.11+
- 以下のパッケージがインストール済み:

```bash
# insight-blueprint (MCP サーバー + data-lineage API)
uv add insight-blueprint

# 分析用パッケージ
uv add pandas matplotlib

# notebook 環境
uv add marimo
```

## セットアップ

### 1. insight-blueprint プラグインのインストール

**方法 A: Claude Code Plugin（推奨）**

```bash
claude plugin add etoyama/insight-blueprint
```

**方法 B: 手動設定**

プロジェクトの `.mcp.json` に以下を追加:

```json
{
  "mcpServers": {
    "insight-blueprint": {
      "command": "uvx",
      "args": ["insight-blueprint", "--project", "."],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_TIMEOUT": "10000"
      }
    }
  }
}
```

### 2. プロジェクトの初期化

Claude Code を起動すると、`.insight/` ディレクトリが自動作成されます。

### 3. チュートリアルファイルの準備

このチュートリアルのファイルをプロジェクトにコピーします:

```bash
cp -r tutorial/sample_data .
cp -r tutorial/notebooks .
```

---

## 1回転目: 探索的分析（DEMO-H01）

### Step 1: データソースの登録

Claude Code で以下のように話しかけます:

```
sample_data/sales.csv をカタログに登録して
```

> `/catalog-register` スキルが起動します。
> CSV のヘッダーを読み取り、カラム情報とともにカタログに登録します。
> source_id (例: `coffee_sales`) を控えておいてください。

### Step 2: データの探索とフレーミング

```
コーヒーチェーンの売上データで何か面白い分析ができないか探して
```

> `/analysis-framing` スキルが起動します。
> `.insight/` 内のカタログ情報を探索し、利用可能なデータと
> 分析の方向性を提案します。
>
> **Framing Brief** が出力されます。これが次の仮説設計の入力になります。

### Step 3: 仮説の設計

```
「気温が高い日はアイスコーヒーの売上が増える」という仮説で分析設計を作りたい
```

> `/analysis-design` スキルが起動します。
> Framing Brief を自動検出し、以下のフィールドを対話で埋めていきます:

| フィールド | 入力例 |
|-----------|--------|
| title | 気温とアイスコーヒー売上の関係 |
| hypothesis_statement | 気温が高い日はアイスコーヒーの売上が増加する |
| theme_id | DEMO |
| analysis_intent | exploratory |
| treatment (ExplanatoryVariable) | temperature (role: treatment) |
| primary metric | revenue (tier: primary) |
| chart | scatter (intent: correlation), line (intent: trend) |
| methodology | method: 散布図 + Pearson 相関係数, package: pandas + matplotlib |

> **design_id** (例: `DEMO-H01`) が発行されます。
> ステータスは `in_review` で作成されます。

### Step 4: WebUI で仮説・手法をレビュー

ブラウザで `http://127.0.0.1:3000` を開きます。

1. **Designs タブ** で DEMO-H01 をクリック
2. **Overview** で仮説と手法の妥当性を確認し、レビューコメントを書く
   - 例: methodology に「相関係数だけでなく散布図の目視確認も必要では？」
   - 例: hypothesis_statement に「対象商品をアイスコーヒーだけでなくフラペチーノも含めるべきでは？」
3. **Review Batch** を送信（verdict: `revision_requested`）

> ステータスが `revision_requested` に変わります。

### Step 5: 指摘への対応

```
レビューの指摘を確認して対応したい
```

> `/analysis-revision` スキルが起動します。
> 各コメントに対して fix / skip / discuss を選択し、
> 対応完了後にステータスを `in_review` に戻します。

### Step 6: 分析開始への遷移

> WebUI で DEMO-H01 のステータスを `analyzing` に遷移させます。
> これで分析を実施する準備が整いました。

### Step 7: marimo notebook で探索的分析

```bash
marimo edit notebooks/01_explore.py
```

> notebook が開きます。以下のセルを順に実行します:
>
> 1. **データ読み込み**: `sales.csv` をロード
> 2. **クレンジング**: `tracked_pipe` で変換を記録しながら前処理
> 3. **全体散布図**: 気温 vs アイスコーヒー売上 → 相関 r を確認
> 4. **時間帯別散布図**: **午前帯で逆転パターンを発見**
> 5. **リネージ出力**: `.insight/lineage/DEMO-H01.mmd` に Mermaid 図を出力
>
> **発見**: 午後は正の相関があるが、午前は通勤需要でホットコーヒーが優勢。
> 気温効果が時間帯によって変わる。

### Step 8: リネージの確認

```
DEMO-H01 のデータリネージを見せて
```

> `/data-lineage` スキルが `.insight/lineage/DEMO-H01.mmd` の Mermaid 図を表示します。
> 各変換ステップの行数変化が可視化されます。

### Step 9: 推論過程の記録

```
分析の結果を記録して。全体では相関があるが、午前帯だけ逆転していた
```

> `/analysis-journal` スキルが起動します。以下のイベントを記録します:
>
> - `observe`: 全体散布図で中程度の正の相関を確認
> - `evidence`: 午後帯は r > 0.3 の明確な正の相関
> - `question`: 午前帯で相関がほぼゼロ。通勤需要が原因か？
>
> ジャーナルは `.insight/designs/DEMO-H01_journal.yaml` に保存されます。

### Step 10: 振り返りと結論

```
DEMO-H01 を振り返って結論を出したい
```

> `/analysis-reflection` スキルが起動します。
> ジャーナルの証拠を整理し、3つの質問で構造化された振り返りを行います:
>
> 1. 証拠を総合すると？ → 仮説は条件付きで支持される
> 2. 残っている疑問は？ → 時間帯の媒介効果を検証したい
> 3. 結論は？ → **supported（条件付き）**
>
> ステータスが `analyzing → supported` に遷移します。

---

## 2回転目: 検証的分析（DEMO-H02）

### Step 11: 派生仮説の設計

```
DEMO-H01 の結果から派生仮説を作りたい。
「時間帯が気温効果を媒介する——午前は逆転、午後は正の相関」
```

> `/analysis-design` が起動し、以下のように設定します:

| フィールド | 入力例 |
|-----------|--------|
| title | 時間帯による気温効果の媒介 |
| parent_id | DEMO-H01 |
| analysis_intent | confirmatory |
| treatment | temperature |
| confounder | time_slot (role: confounder) |
| primary metric | revenue |
| secondary metric | quantity |
| guardrail metric | 客単価 revenue/quantity |
| chart | scatter × 3 (intent: comparison) |
| methodology | method: 層別分析, package: pandas |

> **design_id**: `DEMO-H02` が発行されます。

### Step 12: marimo notebook で検証的分析

```bash
marimo edit notebooks/02_verify.py
```

> 1. **データ読み込み + フィルタ**: アイスコーヒーに絞り、`tracked_pipe` で記録
> 2. **層別散布図**: 朝・午後・夜の3パネルで相関係数を比較
> 3. **判定**: 午後 r > 0.3（PASS）、朝 r < 0.15（PASS）
> 4. **ガードレール**: 客単価が時間帯で安定していることを確認
> 5. **リネージ出力**: `.insight/lineage/DEMO-H02.mmd`

### Step 13: 証拠の記録と結論

```
DEMO-H02 の層別分析の結果を記録して。午後は r > 0.3、朝は r < 0.15 で仮説が支持された
```

> `/analysis-journal` で `evidence` + `conclude` イベントを記録。

```
DEMO-H02 を振り返って結論を出したい
```

> `/analysis-reflection` で **supported** に遷移。

### Step 14: 知見のナレッジ登録

```
「時間帯が気温効果を媒介する」という知見をカタログに登録して
```

> `/catalog-register` でドメインナレッジとして登録します。
> `.insight/catalog/knowledge/` に YAML ファイルが作成されます。
>
> 今後の分析で `/analysis-design` を使うと、この知見が
> `suggest_knowledge_for_design` で自動的に提案されます。

---

## ワークフロー全体図

```
/catalog-register (CSV 登録)
    │
    ▼
/analysis-framing (データ探索)
    │
    ▼
/analysis-design (DEMO-H01: exploratory, status: in_review)
    │
    ▼
WebUI レビュー (仮説・手法の妥当性確認)
    │
    ▼
/analysis-revision (指摘対応 → in_review に戻す)
    │
    ▼
analyzing に遷移
    │
    ▼
marimo 01_explore.py ─── tracked_pipe ──→ /data-lineage
    │
    ▼
/analysis-journal (observe, evidence, question)
    │
    ▼
/analysis-reflection (supported, 条件付き)
    │
    └──→ /analysis-design (DEMO-H02: confirmatory, parent_id)
             │
             ▼
         marimo 02_verify.py ─── tracked_pipe ──→ /data-lineage
             │
             ▼
         /analysis-journal (evidence, conclude)
             │
             ▼
         /analysis-reflection (supported)
             │
             ▼
         /catalog-register (ナレッジ登録)
```

## データについて

`sample_data/sales.csv` は架空のコーヒーチェーン（3店舗、6ヶ月間）の売上データです。
`tutorial/scripts/generate_data.py` で再生成できます（seed=42 で再現可能）。

| カラム | 説明 |
|--------|------|
| date | 日付 (2025-04-01 ~ 2025-09-30) |
| store_id | 店舗 ID (STORE-A: 都心, STORE-B: 郊外, STORE-C: 海沿い) |
| region | 地域 (downtown, suburban, coastal) |
| product | 商品 (hot_coffee, iced_coffee, latte, frappuccino) |
| price | 単価 (JPY) |
| quantity | 販売数 |
| revenue | 売上 (price x quantity) |
| weather | 天気 (sunny, cloudy, rainy) |
| temperature | 気温 (℃) |
| time_slot | 時間帯 (morning, afternoon, evening) |

# Team Server Separation - テスト設計書

**Spec ID**: `team-server-separation`
**種別**: 新規機能

## 概要

本ドキュメントは、requirements.md の各 Acceptance Criteria に対して、どのテストレベル（Unit / Integ / E2E）でカバーするかを定義する。

## テストレベル定義

| テストレベル | 略称 | 説明 | ツール |
|-------------|------|------|--------|
| 単体テスト | Unit | CLI 引数パース、Lock 動作、関数単位の検証。外部依存はモック化 | pytest, unittest.mock, click.testing.CliRunner |
| 統合テスト | Integ | FastAPI + MCP SSE マウント、サーバー起動、複数クライアントの連携 | pytest, httpx, TestClient |
| E2Eテスト | E2E | 実プロセス起動 → Claude Code 接続 → MCP ツール呼び出しの全フロー | 手動確認 |

## 要件カバレッジマトリクス

### REQ-1: Server Mode Selection

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 1.1 | full mode = stdio + WebUI + browser | Unit-01 | Integ-06 | - | 現行動作と同一 |
| 1.2 | server mode = SSE + WebUI on single port | Unit-01 | Integ-01 | E2E-01 | port 4000 で両方起動 |
| 1.3 | headless mode = SSE only | Unit-01 | Integ-02 | - | WebUI なし、SSE のみ |
| 1.4 | --mode 未指定 = full | Unit-01 | - | - | full と同一動作 |
| 1.5 | --headless deprecation warning | Unit-02 | - | - | stderr に警告 |
| 1.6 | --mode full --no-browser | Unit-02 | - | - | browser 抑制、他は通常 |
| 1.7 | --mode full --host → 警告 | Unit-01 | - | - | stderr に警告、--host 無視 |

### REQ-2: SSE Transport for MCP

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 2.1 | SSE 接続で全ツール利用可能 | - | Integ-03 | E2E-01 | /mcp/sse で接続可 |
| 2.2 | SSE ツール = stdio 同一結果 | - | Integ-03 | - | create_analysis_design 同一 |
| 2.3 | 複数 SSE クライアント同時接続 | - | Integ-04 | - | 全クライアント独立動作 |

### REQ-3: Single Port Architecture

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 3.1 | WebUI + SSE 同一ポート | - | Integ-01 | E2E-01 | / と /mcp/sse 両方応答 |
| 3.2 | REST API 正常動作 | - | Integ-05 | - | 既存エンドポイント維持 |
| 3.3 | headless は WebUI なし | - | Integ-02 | - | / は 404、SSE は動作 |

### REQ-4: Concurrent Write Safety

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 4.1 | 同時書き込みでファイル破損なし | Unit-03 | - | - | 両方完了、破損なし |
| 4.2 | 中間状態の読み取りなし | Unit-03 | - | - | atomic write 維持 |
| 4.3 | Lock オーバーヘッド無視可能 | - | Integ-01 | - | MCP ツール呼び出し 500ms 以内 |

### REQ-5: Backward Compatibility

| AC# | Acceptance Criteria | Unit | Integ | E2E | 期待値 |
|-----|---------------------|:----:|:-----:|:---:|--------|
| 5.1 | 既存ユーザー変更なし | Unit-01 | Integ-06 | - | v0.3.0 互換 |
| 5.2 | --headless 後方互換 | Unit-02 | - | - | 動作同一 + 警告 |
| 5.3 | .mcp.json stdio 登録 | Unit-05 | - | - | stdio 形式のまま |

---

## 単体テストシナリオ

### Unit-01: CLI Mode Dispatch - モード引数パース

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-01 |
| **テストファイル** | `tests/test_cli.py` |
| **テストクラス** | `TestCliModeDispatch` |
| **目的** | --mode, --host, --port, --no-browser の各組み合わせが正しくパースされることを検証 |

> **設計判断**: Click の CliRunner でサーバー起動をモックし、引数パースと分岐ロジックのみをテスト。実際のサーバー起動は Integ で検証。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_default_mode_is_full` | --mode 未指定時に full モードで起動 | 1.1, 1.4, 5.1 |
| `test_mode_full_explicit` | --mode full で stdio MCP + WebUI 起動 | 1.1 |
| `test_mode_server` | --mode server で SSE + WebUI 起動 | 1.2 |
| `test_mode_headless` | --mode headless で SSE のみ起動 | 1.3 |
| `test_mode_invalid_value` | --mode invalid で Click エラー | - |
| `test_host_default` | --host 未指定時のデフォルト 0.0.0.0 | 1.2, 1.3 |
| `test_port_default` | --port 未指定時のデフォルト 4000 | 1.2, 1.3 |
| `test_host_port_ignored_in_full_mode` | --mode full --host → 警告出力、値無視 | 1.7 |

---

### Unit-02: CLI Flags - --no-browser と --headless

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-02 |
| **テストファイル** | `tests/test_cli.py` |
| **テストクラス** | `TestCliFlags` |
| **目的** | --no-browser と --headless（非推奨）フラグの動作を検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_no_browser_suppresses_browser` | --no-browser でブラウザ起動抑制 | 1.6 |
| `test_no_browser_keeps_webui_and_mcp` | --no-browser で WebUI と MCP は通常起動 | 1.6 |
| `test_headless_flag_deprecation_warning` | --headless で stderr に deprecation warning | 1.5, 5.2 |
| `test_headless_flag_suppresses_browser` | --headless でブラウザ起動抑制 | 1.5, 5.2 |

---

### Unit-03: Write Lock - 並行書き込み安全性

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-03 |
| **テストファイル** | `tests/test_storage.py` |
| **テストクラス** | `TestWriteLock` |
| **目的** | threading.Lock による並行書き込み保護を検証 |

> **設計判断**: 2スレッドから同時に write_yaml を呼び出し、ファイル破損がないことを確認。lost update は許容（AC-4.1）。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_concurrent_writes_no_corruption` | 2スレッドで 100回ずつ書き込み、最終ファイルが valid YAML | 4.1 |
| `test_concurrent_writes_no_intermediate_state` | 並行読み取りで不完全な YAML が返らない | 4.2 |
| `test_write_lock_is_module_level` | _write_lock が module-level で共有されていること | 4.1 |

---

### Unit-04: Write Lock - パフォーマンス（削除 → Integ-01 に統合）

> **設計判断（Codex レビュー反映）**: Lock の micro-benchmark は CI ジッターで flaky になるため削除。AC-4.3 は「MCP ツールのレスポンスタイム 500ms 以内に影響しない」を要求しているため、Integ-01 の MCP ツール呼び出しテスト内でレスポンスタイムを assert する形で検証する。

---

### Unit-05: init_project - .mcp.json 登録

| 項目 | 内容 |
|------|------|
| **テストID** | Unit-05 |
| **テストファイル** | `tests/test_storage.py` |
| **テストクラス** | `TestInitProjectMcpRegistration` |
| **目的** | init_project が .mcp.json に stdio 形式で登録することを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_mcp_json_registers_stdio_transport` | .mcp.json に command + args が登録される（SSE ではない） | 5.3 |

---

## 統合テストシナリオ

### Integ-01: Server Mode - 単一ポート WebUI + SSE

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-01 |
| **テストファイル** | `tests/test_web.py` |
| **テストクラス** | `TestServerMode` |
| **目的** | server モードで FastAPI + MCP SSE が同一ポートで共存することを検証 |

> **設計判断**: httpx.AsyncClient + TestClient で FastAPI app にリクエスト。実ポート起動は不要。mount_mcp_sse() 後にルーティングを検証。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_mcp_sse_endpoint_responds` | /mcp/sse が SSE ストリームを返す | 1.2, 3.1 |
| `test_webui_static_after_sse_mount` | /mcp マウント後も / (static) が正常応答 | 3.1 |
| `test_api_designs_after_sse_mount` | /mcp マウント後も /api/designs が正常応答 | 3.2 |

---

### Integ-02: Headless Mode - SSE のみ

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-02 |
| **テストファイル** | `tests/test_server.py` |
| **テストクラス** | `TestHeadlessMode` |
| **目的** | headless モードで MCP SSE のみ動作し、WebUI がないことを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_headless_mcp_sse_available` | mcp.run(transport="sse") で SSE エンドポイントが応答 | 1.3 |
| `test_headless_no_webui` | headless モードで WebUI エンドポイントが存在しない | 3.3 |

---

### Integ-03: SSE Transport - MCP ツール動作

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-03 |
| **テストファイル** | `tests/test_server.py` |
| **テストクラス** | `TestSseTransport` |
| **目的** | SSE 経由で MCP ツールが stdio と同一の結果を返すことを検証 |

> **設計判断**: FastMCP の http_app() + httpx で SSE セッションを確立し、tool call を送信。stdio モードのテスト結果と照合。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_create_design_via_sse` | SSE 経由で create_analysis_design が正常動作 | 2.1, 2.2 |
| `test_list_designs_via_sse` | SSE 経由で list_analysis_designs が正常動作 | 2.1 |
| `test_tools_list_via_sse_returns_all_tools` | SSE 経由で tools/list を呼び出し、全17ツールの名前が返ること | 2.1 |

---

### Integ-04: SSE - 複数クライアント同時接続

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-04 |
| **テストファイル** | `tests/test_server.py` |
| **テストクラス** | `TestSseMultiClient` |
| **目的** | 複数 SSE クライアントが同時に接続・操作できることを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_two_clients_independent_operations` | 2クライアントが同時に異なる操作を実行 | 2.3 |

---

### Integ-05: Server Mode - 既存 REST API 互換

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-05 |
| **テストファイル** | `tests/test_web.py` |
| **テストクラス** | `TestServerModeRestApi` |
| **目的** | server モードで既存 REST API エンドポイントが全て正常動作することを検証 |

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_existing_api_endpoints_with_sse_mount` | SSE マウント後の /api/designs, /api/catalog 等が 200 を返す | 3.2 |

---

### Integ-06: Full Mode - 後方互換回帰

| 項目 | 内容 |
|------|------|
| **テストID** | Integ-06 |
| **テストファイル** | `tests/test_cli.py` |
| **テストクラス** | `TestFullModeBackwardCompat` |
| **目的** | full モード（デフォルト）が v0.3.0 と同一の動作をすることを回帰テストで検証 |

> **設計判断（Codex レビュー反映）**: Unit テストでは dispatch ロジックのみ検証（モック）。「既存動作と完全同一」を保証するには、実際のサービス配線と WebUI 起動を含む統合テストが必要。CliRunner + モック（start_server, mcp.run）で呼び出し順序・引数を検証する。

**テストケース:**

| 関数名 | 検証内容 | カバーするAC |
|--------|----------|-------------|
| `test_full_mode_calls_start_server_then_mcp_run` | full モードで start_server(daemon) → mcp.run(stdio) の順に呼ばれる | 1.1, 5.1 |
| `test_full_mode_webui_port_3000` | full モードで WebUI が :3000 で起動する | 1.1, 5.1 |
| `test_full_mode_mcp_run_no_transport_arg` | full モードで mcp.run() に transport 引数が渡されない（stdio） | 5.1 |

---

## 実装リスクと対策

> **Codex レビューで特定されたテスト実装上のリスク。実装時に参照すること。**

| テスト | リスク | 対策 |
|--------|--------|------|
| Integ-02 (headless) | `mcp.run(transport="sse")` がブロッキング。pytest 内でインプロセス実行は困難 | `mcp.http_app(transport="sse")` で ASGI アプリを取得し、httpx.AsyncClient でテスト。ブロッキング `mcp.run()` 自体は呼ばない |
| Integ-03 (SSE tool) | SSE MCP は `/mcp/sse` + `/mcp/messages/` のハンドシェイクが必要。素の httpx では protocol-fragile | FastMCP の `Client` / テストユーティリティを使用。なければ httpx-sse でストリーム接続 |
| Integ-04 (multi-client) | 2つの同時 SSE セッションの決定的同期が難しい。flaky リスク | asyncio.Barrier + timeout で同期。テストは `pytest.mark.flaky` でマーク可 |

---

## E2Eテストシナリオ

### E2E-01: Server Mode フルフロー

| 項目 | 内容 |
|------|------|
| **テストID** | E2E-01 |
| **テスト名** | Server Mode 起動 → SSE 接続 → MCP ツール → WebUI 確認 |
| **目的** | 実プロセスでの server モード全フローを検証 |
| **実行方法** | 手動確認 |

**事前条件:**
1. insight-blueprint がインストール済み
2. テスト用プロジェクトディレクトリが存在

**手順:**

#### 1. サーバー起動

```bash
insight-blueprint --project /tmp/test-project --mode server --port 4000
```

#### 2. Claude Code 設定

```json
{
  "mcpServers": {
    "insight-blueprint": {
      "type": "sse",
      "url": "http://localhost:4000/mcp/sse"
    }
  }
}
```

#### 3. MCP ツール呼び出し

Claude Code から `create_analysis_design` を実行

#### 4. WebUI 確認

`http://localhost:4000/` にブラウザでアクセスし、作成した design が表示されることを確認

**期待値:**

| # | 期待値 | カバーするAC |
|---|--------|-------------|
| 1 | server mode が port 4000 で起動 | 1.2 |
| 2 | Claude Code が SSE 経由で接続・ツール実行可能 | 2.1 |
| 3 | WebUI で design が表示される | 3.1 |

---

## テストファイル構成

```
tests/
├── test_cli.py                  # Unit-01, Unit-02, Integ-06 (既存ファイルに追加)
│   ├── TestCliModeDispatch      # Unit-01
│   ├── TestCliFlags             # Unit-02
│   └── TestFullModeBackwardCompat  # Integ-06
├── test_storage.py              # Unit-03, Unit-05 (既存ファイルに追加)
│   ├── TestWriteLock            # Unit-03
│   └── TestInitProjectMcpRegistration  # Unit-05
├── test_server.py               # Integ-02, Integ-03, Integ-04 (既存ファイルに追加)
│   ├── TestHeadlessMode         # Integ-02
│   ├── TestSseTransport         # Integ-03
│   └── TestSseMultiClient       # Integ-04
└── test_web.py                  # Integ-01, Integ-05 (既存ファイルに追加)
    ├── TestServerMode           # Integ-01
    └── TestServerModeRestApi    # Integ-05
```

## 単体テストサマリ

| テストID | 対象 | カバーするAC |
|----------|------|-------------|
| Unit-01 | CLI mode dispatch | 1.1, 1.2, 1.3, 1.4, 1.7, 5.1 |
| Unit-02 | CLI flags (--no-browser, --headless) | 1.5, 1.6, 5.2 |
| Unit-03 | write_yaml Lock 並行安全性 | 4.1, 4.2 |
| ~~Unit-04~~ | ~~write_yaml Lock パフォーマンス~~ | ~~4.3~~ → Integ-01 に統合 |
| Unit-05 | init_project .mcp.json 登録 | 5.3 |

## 統合テストサマリ

| テストID | 対象コンポーネント | カバーするAC |
|----------|-------------------|-------------|
| Integ-01 | FastAPI + MCP SSE 共存 + レスポンスタイム | 1.2, 3.1, 3.2, 4.3 |
| Integ-02 | headless SSE のみ | 1.3, 3.3 |
| Integ-03 | SSE MCP ツール動作 + tools/list 全件 | 2.1, 2.2 |
| Integ-04 | 複数 SSE クライアント | 2.3 |
| Integ-05 | REST API 互換 | 3.2 |
| Integ-06 | full mode 後方互換回帰 | 1.1, 5.1 |

## E2Eテストサマリ

| テストID | テスト名 | 実行方法 | カバーするAC |
|----------|---------|----------|-------------|
| E2E-01 | Server Mode フルフロー | 手動確認 | 1.2, 2.1, 3.1 |

## カバレッジ目標

| コンポーネント | 目標カバレッジ |
|--------------|--------------|
| `src/insight_blueprint/cli.py`（変更部分） | 90%以上 |
| `src/insight_blueprint/storage/yaml_store.py`（変更部分） | 95%以上 |
| `src/insight_blueprint/web.py`（変更部分） | 80%以上 |
| `src/insight_blueprint/server.py`（変更部分） | 80%以上 |

## 成功基準

- [ ] Unit-01: CLI mode dispatch テストがパス
- [ ] Unit-02: CLI flags テストがパス
- [ ] Unit-03: 並行書き込みテストがパス（100回×2スレッド、破損なし）
- [ ] Unit-05: .mcp.json stdio 登録テストがパス
- [ ] Integ-01: server mode WebUI + SSE 共存テストがパス
- [ ] Integ-02: headless mode SSE のみテストがパス
- [ ] Integ-03: SSE 経由 MCP ツールテストがパス
- [ ] Integ-04: 複数クライアント同時接続テストがパス
- [ ] Integ-05: REST API 互換テストがパス
- [ ] Integ-06: full mode 後方互換回帰テストがパス
- [ ] E2E-01: server mode フルフローが手動確認で正常完了

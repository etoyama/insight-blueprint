# Requirements: Team Server Separation

## Introduction

insight-blueprint をチーム利用に拡張するための Phase 1 仕様。現在の single-user stdio モードに加え、`--mode` フラグでチームサーバーモード（SSE）とヘッドレスモード（SSE、バッチ/CI 用）を提供する。チームメンバーは共有サーバーに接続し、カタログ・設計書を一元管理できるようになる。

Phase 2（Plugin 化: `.claude-plugin/` ディレクトリ生成）は別 spec で扱う。

## Alignment with Product Vision

- **Collaboration** (product.md Future Vision): 「複数アナリストによる同時レビュー」の実現基盤を構築する
- **Claude Code First**: MCP ツールが SSE トランスポート経由でも完全に動作することを保証する
- **YAML as Source of Truth**: ストレージ層は変更しない。排他制御を追加して整合性を保証する
- **後方互換の優先**: `--mode full`（デフォルト）は現行動作と完全に同一

## Terms

| 用語 | 定義 |
|------|------|
| full モード | 現行の動作。stdio MCP + daemon WebUI + ブラウザ自動起動 |
| server モード | SSE MCP + WebUI を単一ポートで提供。チームサーバー用 |
| headless モード | SSE MCP のみ提供。WebUI なし。バッチ・CI 用 |
| SSE | Server-Sent Events。MCP プロトコルの HTTP ベーストランスポート |
| Single Writer Lock | YAML 書き込みを直列化する threading.Lock |

## Requirements

### REQ-1: Server Mode Selection

**User Story:** As a team lead, I want to start insight-blueprint in different modes, so that I can run a shared server for my team or a headless instance for CI.

#### Functional Requirements

- FR-1.1: CLI は `--mode` オプションを受け付ける。値は `full`、`server`、`headless` の3つ
- FR-1.2: `--mode` のデフォルト値は `full`
- FR-1.3: `--host` オプションを受け付ける。デフォルト値は `0.0.0.0`。`server` および `headless` モードでのみ有効
- FR-1.4: `--port` オプションを受け付ける。デフォルト値は `4000`。`server` および `headless` モードでのみ有効
- FR-1.5: `--no-browser` フラグを受け付ける。`full` モードでブラウザ自動起動を抑制する
- FR-1.6: 既存の `--headless` フラグは非推奨とし、`--no-browser` と同義で動作する。使用時に deprecation warning を stderr に出力する
- FR-1.7: `--mode full` 時に `--host` または `--port` が指定された場合、警告を出力して無視する

#### Acceptance Criteria

- AC-1.1: WHEN `insight-blueprint --project . --mode full` を実行する THEN システムは stdio MCP サーバー + daemon WebUI(:3000) + ブラウザ自動起動で起動する SHALL（現行動作と同一）
- AC-1.2: WHEN `insight-blueprint --project . --mode server --port 4000` を実行する THEN システムは SSE MCP + WebUI を port 4000 で起動する SHALL
- AC-1.3: WHEN `insight-blueprint --project . --mode headless --port 4000` を実行する THEN システムは SSE MCP のみを port 4000 で起動する SHALL（WebUI なし）
- AC-1.4: WHEN `insight-blueprint --project .` を実行する（--mode 指定なし）THEN システムは `--mode full` と同一の動作をする SHALL
- AC-1.5: WHEN `--headless` フラグを使用する THEN deprecation warning が stderr に出力される SHALL AND ブラウザ自動起動が抑制される SHALL
- AC-1.6: WHEN `--mode full --no-browser` を指定する THEN ブラウザ自動起動のみが抑制される SHALL AND WebUI と stdio MCP は通常通り起動する SHALL
- AC-1.7: WHEN `--mode full --host 0.0.0.0` を指定する THEN 警告メッセージが stderr に出力される SHALL AND `--host` は無視される SHALL

### REQ-2: SSE Transport for MCP

**User Story:** As a team member, I want to connect to a shared insight-blueprint server from my Claude Code, so that our team shares a single catalog and set of analysis designs.

#### Functional Requirements

- FR-2.1: `server` モードでは FastMCP の SSE トランスポートを使用して MCP プロトコルを提供する
- FR-2.2: `headless` モードでも同様に SSE トランスポートを使用する
- FR-2.3: 全 MCP ツール（17個）が SSE トランスポート経由で stdio と同一の動作をする
- FR-2.4: SSE エンドポイントは `/mcp` パスに配置する（例: `http://host:4000/mcp/sse`）

#### Acceptance Criteria

- AC-2.1: WHEN Claude Code が `{"type": "sse", "url": "http://host:4000/mcp/sse"}` で接続する THEN 全 MCP ツールが利用可能になる SHALL
- AC-2.2: WHEN `server` モードで `create_analysis_design` ツールを SSE 経由で呼び出す THEN stdio モードと同一の結果が返る SHALL
- AC-2.3: WHEN 複数の Claude Code クライアントが同時に SSE 接続する THEN 全クライアントが独立してツールを使用できる SHALL

### REQ-3: Single Port Architecture

**User Story:** As a team lead, I want WebUI and MCP SSE to be served from a single port, so that server configuration is simple.

#### Functional Requirements

- FR-3.1: `server` モードでは FastAPI アプリに MCP SSE エンドポイントをマウントし、単一ポートで WebUI と MCP SSE の両方を提供する
- FR-3.2: WebUI の既存エンドポイント（`/api/*`, `/` static files）は変更しない
- FR-3.3: MCP SSE エンドポイントは `/mcp` パス配下にマウントする
- FR-3.4: `headless` モードでは FastMCP の standalone SSE サーバーを使用する（WebUI なし）

#### Acceptance Criteria

- AC-3.1: WHEN `--mode server --port 4000` で起動する THEN `http://host:4000/` で WebUI が表示される SHALL AND `http://host:4000/mcp/sse` で MCP SSE に接続できる SHALL
- AC-3.2: WHEN `--mode server` で起動する THEN WebUI の全 REST API エンドポイントが正常動作する SHALL
- AC-3.3: WHEN `--mode headless --port 4000` で起動する THEN `http://host:4000/` は応答しない SHALL AND MCP SSE は動作する SHALL

### REQ-4: Concurrent Write Safety

**User Story:** As a team member, I want my design updates to not be lost when another team member is simultaneously editing, so that our shared data remains consistent.

#### Functional Requirements

- FR-4.1: YAML ファイルの書き込み操作を `threading.Lock` で直列化する（Single Writer Lock）
- FR-4.2: Lock は `yaml_store.py` の `write_yaml()` 関数に適用する
- FR-4.3: Lock は全モード（full, server, headless）で有効とする
- FR-4.4: 読み取り操作（`read_yaml()`）は Lock を取得しない

#### Acceptance Criteria

- AC-4.1: WHEN 2つのクライアントが同時に `update_analysis_design` を同一の design に対して呼び出す THEN 両方の操作が完了し、後の書き込みが先の書き込みを上書きする SHALL（lost update は許容するが、ファイル破損は禁止）
- AC-4.2: WHEN `write_yaml()` が同時に呼び出される THEN ファイルが中間状態で読み取られることがない SHALL
- AC-4.3: WHEN `full` モードで動作する THEN Lock のオーバーヘッドが MCP ツールのレスポンスタイム（500ms 以内）に影響しない SHALL

### REQ-5: Backward Compatibility

**User Story:** As an existing user, I want my current workflow to continue working without changes, so that I don't have to modify my setup.

#### Functional Requirements

- FR-5.1: `--mode full`（デフォルト）の動作は現行リリース (v0.3.0) と完全に同一
- FR-5.2: `init_project()` の動作（スキルコピー、`.mcp.json` 登録、CLAUDE.md 生成）は全モードで同一
- FR-5.3: 既存の `--headless` フラグは `--no-browser` として引き続き動作する
- FR-5.4: `.mcp.json` に登録される MCP サーバー設定は stdio 形式のまま変更しない

#### Acceptance Criteria

- AC-5.1: WHEN 既存ユーザーが `insight-blueprint --project .` を実行する THEN v0.3.0 と同一の動作をする SHALL
- AC-5.2: WHEN `insight-blueprint --project . --headless` を実行する THEN v0.3.0 の `--headless` と同一の動作をする SHALL AND deprecation warning が出力される SHALL
- AC-5.3: WHEN `init_project()` が実行される THEN `.mcp.json` に `{"command": "uvx", "args": ["insight-blueprint", "--project", "."]}` が登録される SHALL（SSE 設定は登録しない）

## Non-Functional Requirements

### Code Architecture and Modularity

- `main()` からサービス配線ロジックを `_wire_registry()` 関数に抽出する
- モード分岐は `cli.py` の `main()` 内に集約し、`server.py` / `web.py` にモード判定ロジックを漏洩させない
- 依存方向 `server.py / web.py → core/ → storage/ → models/` を維持する

### Performance

- `full` モードのパフォーマンスは v0.3.0 と同等（Lock のオーバーヘッドは無視可能）
- `server` / `headless` モードの MCP ツールレスポンスは 500ms 以内（tech.md 準拠）

### Security

- `server` / `headless` モードはデフォルトで `0.0.0.0` にバインドする。認証は Phase 1 のスコープ外だが、ドキュメントに注意事項を記載する
- `full` モードの WebUI は `127.0.0.1` バインドを維持する（現行通り）

### Reliability

- ポート競合時は OS 割り当てポートにフォールバックする（`server` / `headless` モード）
- サーバー起動失敗時は明確なエラーメッセージを出力して終了する

### Usability

- `--mode` の不正な値に対しては Click の標準エラーメッセージを表示する
- `server` モード起動時に stderr に `MCP SSE: http://host:port/mcp/sse` と `WebUI: http://host:port/` を出力する
- `headless` モード起動時に stderr に `MCP SSE: http://host:port/mcp/sse` を出力する

## Out of Scope

- Plugin 化（`.claude-plugin/` ディレクトリ生成）— Phase 2 別 spec
- `--init-plugin` コマンド — Phase 2
- 認証・認可機構 — チームアクセス制御は将来検討
- 分散ロック / MVCC / Optimistic Concurrency — YAGNI
- WebUI の変更（新規画面・コンポーネントの追加） — なし
- WebSocket によるリアルタイム更新 — 現行通りポーリング
- Streamable HTTP トランスポート — SSE で十分

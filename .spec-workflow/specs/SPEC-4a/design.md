# SPEC-4a: webui-backend — Design

> **Spec ID**: SPEC-4a
> **Created**: 2026-02-27

---

## Overview

既存の 3 層アーキテクチャ（CLI → MCP/Core → Storage）に HTTP レイヤーを追加し、
`server.py`（MCP）と対等な `web.py`（FastAPI）を配置する。サービス配線を
`_registry.py` に集約し、両モジュールが同一サービスインスタンスを共有する。

## Steering Document Alignment

### Technical Standards (tech.md)

- FastAPI >= 0.115 + uvicorn（daemon thread、tech.md §WebUI 準拠）
- 単一プロセスモデル: MCP (stdio) が main thread、HTTP が daemon thread
- ポート戦略: `socket.bind(('', 0))` → OS 割り当て、デフォルト 3000
- `static/` は hatch `artifacts` で wheel に同梱（tech.md §Distribution 準拠）

### Project Structure (structure.md)

- `web.py` は `server.py` と同階層（structure.md の Layer Architecture 準拠）
- `_registry.py` は新規だが、既存の module-level getter パターンを集約するだけ
- `frontend/` と `static/` は structure.md §Repository Layout に定義済み

## Code Reuse Analysis

### 再利用する既存コンポーネント

- **`core/designs.py` (DesignService)**: 4 操作を REST endpoint に直接マッピング
- **`core/catalog.py` (CatalogService)**: 8 操作を REST endpoint にマッピング
- **`core/reviews.py` (ReviewService)**: 5 操作を REST endpoint にマッピング
- **`core/rules.py` (RulesService)**: 2 操作を REST endpoint にマッピング
- **`models/*`**: Pydantic モデルをそのまま FastAPI のレスポンスモデルとして利用
- **`server.py` のエラーハンドリングパターン**: `ValueError` → error dict、`None` → not found
- **`storage/yaml_store.py`**: 間接利用（core/ 経由、web.py から直接呼ばない）

### Integration Points

- **cli.py**: サービス配線先を `server_module` → `_registry` に変更 + daemon thread 起動を追加
- **server.py**: getter を `_registry` からの import に置き換え（ロジック変更なし）
- **conftest.py**: テストフィクスチャの配線先を `_registry` に変更

## Architecture

### 全体構成

```
CLI (cli.py)
  │
  ├── _registry.py ← サービスインスタンスの一元管理
  │     ↑ import        ↑ import
  │     │               │
  ├── MCP Server ───────┘
  │   (server.py)
  │
  ├── HTTP Server ──────┘
  │   (web.py)
  │     ├── FastAPI app + REST endpoints
  │     ├── Static file serving (static/)
  │     └── ThreadedUvicorn (daemon thread)
  │
  └── mcp.run()  ← main thread をブロック
```

### Modular Design Principles

- **Single File Responsibility**: `_registry.py` はサービス参照のみ、`web.py` は
  HTTP ルーティングのみ。ビジネスロジックは `core/` に閉じる
- **Component Isolation**: web.py は core/ サービスの getter 呼び出しと
  HTTP ステータスコードの変換だけを行う薄いレイヤー
- **Service Layer Separation**: web.py → core/ → storage/ の 3 層。
  web.py から storage/ への直接アクセス禁止
- **Utility Modularity**: ID バリデーション (`_validate_design_id` 等) は
  server.py に既存。web.py では FastAPI の Path パラメータバリデーションを使い、
  重複ヘルパーを作らない

## Components and Interfaces

### Component 1: `_registry.py`

- **Purpose**: 全サービスインスタンスの一元管理。cli.py で 1 回配線し、
  server.py と web.py の両方からアクセスする
- **Interfaces**:
  ```python
  # Module-level references (cli.py が設定)
  design_service: DesignService | None = None
  catalog_service: CatalogService | None = None
  review_service: ReviewService | None = None
  rules_service: RulesService | None = None

  # Typed getters (未初期化時は RuntimeError)
  def get_design_service() -> DesignService: ...
  def get_catalog_service() -> CatalogService: ...
  def get_review_service() -> ReviewService: ...
  def get_rules_service() -> RulesService: ...
  ```
- **Dependencies**: `core/designs.py`, `core/catalog.py`, `core/reviews.py`, `core/rules.py`（型注釈のみ）
- **Reuses**: server.py の既存 getter パターンをそのまま移植

### Component 2: `web.py`

- **Purpose**: FastAPI アプリケーション。REST API endpoints + 静的ファイル配信 +
  daemon thread 起動
- **Interfaces**:
  ```python
  app = FastAPI(title="insight-blueprint")

  # Daemon thread 起動（127.0.0.1 固定バインド）
  def start_server(host: str = "127.0.0.1", port: int = 3000) -> int: ...

  # Path パラメータ: pattern=r"[a-zA-Z0-9_-]+" で ID バリデーション
  # (既存 server.py の _validate_*_id と同等)

  # REST Endpoints (17 メソッド / 14 URL パターン + health check)
  # --- Design ---
  GET    /api/designs                         # ?status= optional
  POST   /api/designs
  GET    /api/designs/{design_id}
  PUT    /api/designs/{design_id}
  # --- Catalog ---
  GET    /api/catalog/sources
  POST   /api/catalog/sources
  GET    /api/catalog/sources/{source_id}
  PUT    /api/catalog/sources/{source_id}
  GET    /api/catalog/sources/{source_id}/schema
  GET    /api/catalog/search                  # ?q= required, &source_id= optional
  GET    /api/catalog/knowledge
  # --- Review ---
  POST   /api/designs/{design_id}/review
  GET    /api/designs/{design_id}/comments
  POST   /api/designs/{design_id}/comments
  POST   /api/designs/{design_id}/knowledge
  # --- Rules ---
  GET    /api/rules/context
  GET    /api/rules/cautions                  # ?table_names= required
  # --- Health ---
  GET    /api/health                          # → {status, version}
  ```
- **Dependencies**: `_registry.py`（サービスアクセス）、`fastapi`、`uvicorn`
- **Reuses**: server.py のエラーハンドリングパターンを HTTP ステータスコードに変換
- **Query パラメータ設計**:
  - `GET /api/catalog/search`: `q` (必須) + `source_id` (任意)。サービスの
    `search(query)` 呼び出し後、`source_id` 指定時は結果を post-filter
  - `GET /api/rules/cautions`: `table_names` (必須、カンマ区切り)。
    requirements.md の `design_id` パラメータは v1 では未使用（サービス契約が
    `suggest_cautions(table_names)` のみのため）。SPEC-4b でフロントエンドが
    design からテーブル名を抽出して `table_names` に渡す想定

### Component 3: `ThreadedUvicorn`（web.py 内クラス）

- **Purpose**: daemon thread で uvicorn を起動する。signal handler を無効化し、
  stdout への出力を防ぐ（MCP stdio と競合するため）
- **Interfaces**:
  ```python
  class ThreadedUvicorn(uvicorn.Server):
      def install_signal_handlers(self) -> None:
          pass  # main thread でのみ有効なため無効化
  ```
- **Dependencies**: `uvicorn`
- **設計根拠**: uvicorn 0.13.0+ は非 main thread で自動スキップするが、
  明示的な override が安全。`log_level="warning"` + `access_log=False` で
  stdout 汚染を完全防止

### Component 4: `frontend/` scaffold

- **Purpose**: SPEC-4b への引き渡し用 React プロジェクト最小構成
- **Interfaces**: `npm run build` → `src/insight_blueprint/static/` に出力
- **Dependencies**: React 19, Vite 6, Tailwind CSS, shadcn/ui
- **構成**:
  ```
  frontend/
  ├── package.json
  ├── vite.config.ts      # outDir: '../src/insight_blueprint/static'
  ├── tailwind.config.ts
  ├── tsconfig.json
  ├── index.html
  └── src/
      └── main.tsx         # placeholder
  ```

### Component 5: CLI 統合（cli.py 変更）

- **Purpose**: サービス配線 + HTTP サーバー起動 + ブラウザ自動オープン（FR-11）
- **起動シーケンス**:
  ```python
  # 1. _registry にサービス配線
  import insight_blueprint._registry as registry
  registry.design_service = DesignService(project_path)
  # ... 他サービスも同様

  # 2. HTTP サーバー起動（daemon thread）
  from insight_blueprint.web import start_server
  port = start_server(host="127.0.0.1", port=3000)
  url = f"http://127.0.0.1:{port}"
  print(f"WebUI: {url}", file=sys.stderr)

  # 3. ブラウザ自動起動（--headless でない場合）
  if not headless:
      threading.Timer(1.5, webbrowser.open, args=[url]).start()

  # 4. MCP サーバー起動（main thread ブロック）
  mcp.run()
  ```
- **`start_server()` のレディネス保証**:
  `ThreadedUvicorn.started` フラグが `True` になるまで polling
  （`while not server.started: time.sleep(1e-3)`）してから port を返す
- **CORS 設定**:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

### Component 6: ビルドパイプライン（FR-14, FR-16）

- **Purpose**: フロントエンドビルド → wheel 同梱の自動化
- **pyproject.toml 変更**:
  ```toml
  # 依存追加 (FR-16)
  dependencies = [
      # ... 既存 ...
      "fastapi>=0.115",
      "uvicorn[standard]",
  ]

  [project.optional-dependencies]
  dev = [
      # ... 既存 ...
      "httpx>=0.27",
  ]

  # hatch artifacts (gitignore 対象の static/ を wheel に含める)
  [tool.hatch.build.targets.wheel]
  artifacts = ["src/insight_blueprint/static/**"]

  # poe タスク (FR-14)
  [tool.poe.tasks.build-frontend]
  shell = "cd frontend && npm install && npm run build"

  [tool.poe.tasks.build]
  sequence = ["build-frontend", {shell = "uv build"}]
  ```

## Data Models

SPEC-4a では新規データモデルを作成しない。既存の Pydantic モデルをそのまま利用する。

### FastAPI リクエストモデル（web.py 内で定義）

```python
class CreateDesignRequest(BaseModel):
    title: str
    hypothesis_statement: str
    hypothesis_background: str
    parent_id: str | None = None
    theme_id: str = "DEFAULT"
    metrics: dict | None = None
    explanatory: list[dict] | None = None
    chart: list[dict] | None = None
    next_action: dict | None = None

class AddCommentRequest(BaseModel):
    comment: str
    status: str
    reviewer: str = "analyst"

class AddSourceRequest(BaseModel):
    source_id: str
    name: str
    type: str
    description: str
    connection: dict
    columns: list[dict] | None = None
    tags: list[str] | None = None

class SaveKnowledgeRequest(BaseModel):
    entries: list[dict]
```

### レスポンス形式

MCP ツールと同じ JSON 構造を返す（`model.model_dump(mode="json")`）。
HTTP ステータスコードで成否を表現し、エラー時は FR-8 契約に準拠した
`{"error": str, "detail"?: str}` 形式で返す。

### エラーレスポンス統一ハンドラー

FastAPI のデフォルト `HTTPException` は `{"detail": ...}` 形式だが、
FR-8 は `{"error": ...}` を要求する。カスタム exception handler で変換する:

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )
```

## Error Handling

### MCP → HTTP のエラーマッピング

| server.py パターン | web.py 変換 |
|-------------------|-------------|
| `return {"error": str(e)}` (ValueError) | `raise HTTPException(400, detail=str(e))` |
| `if result is None: return {"error": "not found"}` | `raise HTTPException(404, detail="...")` |
| `if err := _validate_id(id): return err` | `Path(pattern=r"[a-zA-Z0-9_-]+")` で 422 自動返却 |
| 予期しない例外 | グローバル exception handler → 500 |

### Error Scenarios

1. **サービス未初期化**
   - Handling: `_registry.get_*_service()` が `RuntimeError` → グローバル handler が 500
   - User Impact: `{"error": "Internal server error"}`

2. **デザイン未存在**
   - Handling: service が `None` 返却 → endpoint が 404
   - User Impact: `{"error": "Design 'xxx' not found"}`

3. **無効なステータス遷移**
   - Handling: service が `ValueError` → endpoint が 400
   - User Impact: `{"error": "Design must be in 'active' status to submit for review"}`

3a. **無効な ID フォーマット**
   - Handling: `Path(pattern=...)` が 422 自動返却
   - User Impact: FastAPI 標準の validation error レスポンス

4. **ポート競合**
   - Handling: `start_server()` が `socket.bind(('', 0))` にフォールバック
   - User Impact: stderr にフォールバックポート番号を出力

5. **static/ 未配置**
   - Handling: StaticFiles mount が 404 を返す
   - User Impact: ブラウザに 404 表示（開発中の正常動作）

6. **予期しない例外**
   - Handling: FastAPI グローバル exception handler
   - User Impact: `{"error": "Internal server error"}`（stack trace 非公開、
     ValueError メッセージもそのまま返さず汎用化する場合は将来検討）

## Known Constraints

### スレッド安全性

MCP (main thread) と HTTP (daemon thread) が同一サービスインスタンスを共有する。
YAML ファイルの read-modify-write（`update_design`, `save_review_comment` 等）に
ファイルロックは実装しない。

**根拠**: v1 は localhost シングルユーザー想定であり、MCP と HTTP の同時書き込みは
実用上発生しない（ユーザーが MCP とブラウザで同時に同じデザインを更新する操作は想定外）。

**将来対応**: マルチユーザー対応時にファイルロック or atomic write を導入する。

### _registry の再配線禁止

`_registry` のサービス参照は `cli.py` で起動時に 1 回だけ設定する。
ランタイム中の再配線は禁止（CPython の module-level 代入はアトミックだが、
サービス状態の一貫性を保証できないため）。

## Testing Strategy

### Unit Testing

**`tests/test_registry.py`** — _registry.py のテスト
- 未初期化時の `RuntimeError` 送出
- 設定後の getter 正常動作
- 各テスト後のサービス参照リセット（autouse fixture）

**`tests/test_web.py`** — REST endpoint のテスト（httpx `TestClient` 使用）
- 全 17 endpoint の正常系・異常系
- エラーレスポンスの HTTP ステータスコード検証
- エラーレスポンス body が `{"error": ...}` 形式であることの検証
- Path パラメータの ID バリデーション（不正 ID → 422）
- `TestClient` は uvicorn なしで FastAPI app を直接テスト
- テストフィクスチャ:
  ```python
  @pytest.fixture
  def client(tmp_path: Path) -> TestClient:
      init_project(tmp_path)
      registry.design_service = DesignService(tmp_path)
      registry.catalog_service = CatalogService(tmp_path)
      registry.review_service = ReviewService(tmp_path, registry.design_service)
      registry.rules_service = RulesService(tmp_path, registry.catalog_service)
      from insight_blueprint.web import app
      return TestClient(app)
  ```

### Integration Testing

**既存テストのリグレッション確認**
- `_registry` への移行後、既存 183 テスト全通過を確認
- `tests/test_server.py` の autouse fixture を `_registry` 向けに更新
- `tests/conftest.py` の配線を `_registry` 経由に変更

### End-to-End Testing

**`tests/test_web_integration.py`** — フルフロー統合テスト
- `TestClient` 経由で Design 作成 → レビュー提出 → コメント → 知識抽出の一連フローを検証
- `start_server()` のポート取得と health check レスポンスの検証
  （実際の daemon thread 起動テスト）
- `start_server()` のポート競合フォールバック検証

**`tests/test_web_cli.py`** — CLI 統合テスト（FR-11）
- `--headless=True` 時にブラウザが開かないことの検証（`webbrowser.open` を mock）
- `--headless=False`（デフォルト）時に `threading.Timer` が設定されることの検証
- stderr への WebUI URL 出力検証

### Security Testing

- `start_server()` が `127.0.0.1` にバインドすることの検証
  （`0.0.0.0` でないことの確認）
- CORS middleware が localhost origin のみ許可することの検証

### Build Pipeline Testing

- `poe build-frontend` の実行と `static/` への出力確認
  （CI 環境に Node.js が必要。ローカル手動検証でも可）
- `uv build` で生成した wheel 内に static ファイルが含まれることを確認

### スレッド安全性に関するテスト方針

v1 はシングルユーザー localhost 想定のため、MCP + HTTP 同時書き込みの
並行テストは実施しない（Known Constraints 参照）。将来マルチユーザー対応時に追加する。

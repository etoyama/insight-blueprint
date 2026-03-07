# Project Structure

## Directory Organization

```
insight-blueprint/
├── src/insight_blueprint/          # Python パッケージ (メインソース)
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                     # CLI エントリポイント + サービス配線
│   ├── _registry.py               # Service Locator (サービス参照)
│   ├── server.py                  # MCP ツール定義 (15 tools)
│   ├── web.py                     # REST API エンドポイント (20+ endpoints)
│   ├── models/                    # Pydantic データモデル
│   │   ├── common.py              # 共通ユーティリティ (now_jst 等)
│   │   ├── catalog.py             # DataSource, KnowledgeCategory, DomainKnowledgeEntry
│   │   ├── design.py              # AnalysisDesign, DesignStatus
│   │   └── review.py              # ReviewComment, ReviewBatch
│   ├── storage/                   # 永続化層
│   │   ├── yaml_store.py          # YAML ファイル読み書き (atomic writes)
│   │   ├── sqlite_store.py        # SQLite FTS5 検索インデックス
│   │   └── project.py             # プロジェクトコンテキスト管理
│   ├── core/                      # ビジネスロジック (Service 層)
│   │   ├── designs.py             # DesignService (ステートマシン, CRUD)
│   │   ├── catalog.py             # CatalogService (データソース管理)
│   │   ├── reviews.py             # ReviewService (レビューワークフロー)
│   │   ├── rules.py               # RulesService (ドメイン知識管理)
│   │   └── validation.py          # バリデーションユーティリティ
│   ├── lineage/                   # データリネージ機能
│   │   ├── tracker.py             # pandas パイプライン行数追跡
│   │   └── exporter.py            # Mermaid ダイアグラム出力
│   ├── _rules/                    # バンドルルール定義
│   ├── _templates/                # バンドルテンプレート
│   └── static/                    # ビルド済みフロントエンド資産
├── frontend/                      # React フロントエンド
│   ├── src/
│   │   ├── main.tsx               # エントリポイント
│   │   ├── App.tsx                # ルートコンポーネント (2タブ構成: Designs / Catalog)
│   │   ├── api/
│   │   │   └── client.ts          # REST API クライアント
│   │   ├── types/
│   │   │   └── api.ts             # TypeScript 型定義
│   │   ├── lib/
│   │   │   ├── utils.ts           # ユーティリティ
│   │   │   └── constants.tsx      # 定数 (ステータスラベル等)
│   │   ├── components/            # 共通コンポーネント
│   │   │   ├── ui/                # shadcn/ui 基盤コンポーネント
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── DataTable.tsx
│   │   │   ├── ErrorBanner.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── JsonTree.tsx
│   │   └── pages/                 # ページコンポーネント
│   │       ├── DesignsPage.tsx    # Designs タブ
│   │       ├── catalog/           # Catalog タブ (検索, ソース一覧, スキーマ, ドメイン知識, 注意事項検索)
│   │       └── design-detail/     # 設計詳細ページ (Overview, History の2サブタブ)
│   ├── e2e/                       # Playwright E2E テスト
│   └── package.json
├── tests/                         # Python テストスイート (548+ tests)
│   ├── conftest.py                # 共通フィクスチャ
│   ├── skill_helpers.py           # スキル統合テストヘルパー
│   ├── test_designs.py            # DesignService テスト
│   ├── test_catalog.py            # CatalogService テスト
│   ├── test_reviews.py            # ReviewService テスト
│   ├── test_rules.py              # RulesService テスト
│   ├── test_server.py             # MCP ツールテスト
│   ├── test_web.py                # REST API テスト
│   ├── test_integration.py        # 統合テスト
│   ├── test_web_integration.py    # Web 統合テスト
│   └── lineage/                   # リネージテスト
├── .insight/                      # ランタイムデータ (Git 管理外)
│   ├── designs/                   # 分析設計 YAML
│   ├── catalog/                   # データカタログ YAML
│   ├── rules/                     # ドメイン知識 YAML
│   └── reviews/                   # レビューコメント YAML
└── pyproject.toml                 # プロジェクト設定
```

## Naming Conventions

### Files
- **Python modules**: `snake_case.py` (例: `yaml_store.py`, `design.py`)
- **React components**: `PascalCase.tsx` (例: `DesignsPage.tsx`, `StatusBadge.tsx`)
- **Tests**: `test_{module_name}.py` (例: `test_designs.py`)
- **UI components (shadcn)**: `kebab-case` ディレクトリ + `PascalCase` ファイル

### Spec IDs (spec-workflow)
- **現行規則**: `kebab-case` の説明的な名前 (例: `knowledge-suggestion`, `design-status-refactor`, `skills-distribution`)
- **レガシー**: `SPEC-{number}{suffix}` (例: `SPEC-1a`, `SPEC-3`, `SPEC-4b`) — 旧形式、新規作成では使用しない
- **配置**: `.spec-workflow/specs/{spec-id}/` ディレクトリに格納

### Code
- **Classes**: `PascalCase` (例: `DesignService`, `AnalysisDesign`)
- **Functions/Methods**: `snake_case` (例: `create_design`, `transition_status`)
- **Constants**: `UPPER_SNAKE_CASE` (例: `SECTION_KNOWLEDGE_MAP`, `ALLOWED_TARGET_SECTIONS`)
- **Enums**: `PascalCase` クラス名 + `snake_case` メンバー、全て `StrEnum` (例: `DesignStatus.in_review`)
- **Variables**: `snake_case`
- **TypeScript types/interfaces**: `PascalCase` (例: `AnalysisDesign`, `DesignStatus`)

## Import Patterns

### Import Order (Python, ruff isort)
1. Standard library (`from __future__ import annotations`, `os`, `pathlib`)
2. Third-party (`pydantic`, `ruamel.yaml`, `fastmcp`)
3. Internal (`insight_blueprint.models`, `insight_blueprint.core`)

### Module Organization
- 絶対インポート: `from insight_blueprint.models.design import AnalysisDesign`
- `TYPE_CHECKING` ガード: 循環参照回避に使用 (`_registry.py`)
- `__init__.py`: パブリック API の re-export に使用

## Code Structure Patterns

### Service クラスの構成
```python
class XxxService:
    def __init__(self, yaml_store: YamlStore, sqlite_store: SqliteStore):
        self._yaml = yaml_store
        self._sqlite = sqlite_store

    # Public methods (CRUD)
    def create_xxx(self, ...) -> dict: ...
    def get_xxx(self, ...) -> dict: ...
    def list_xxx(self, ...) -> list[dict]: ...
    def update_xxx(self, ...) -> dict: ...

    # Private methods (internal logic)
    def _validate_xxx(self, ...) -> None: ...
```

### MCP ツール定義パターン (server.py)
```python
@mcp.tool()
def tool_name(param: str, optional_param: str | None = None) -> dict:
    """Tool description."""
    svc = _registry.get_xxx_service()
    return svc.method(param, optional_param)
```

### モデル定義パターン (models/)
```python
class ModelName(BaseModel):
    id: str
    field: str
    optional_field: str | None = None
    status: SomeStatus = SomeStatus.default_value
    created_at: str = Field(default_factory=lambda: now_jst())
```

## Module Boundaries

### 依存方向 (厳守)
```
server.py, web.py  →  core/  →  storage/  →  models/
         ↘          ↗
        _registry.py
```

- `models/`: 他モジュールへの依存なし（Pure データモデル）
- `storage/`: `models/` のみに依存
- `core/`: `storage/` と `models/` に依存
- `server.py` / `web.py`: `core/` と `_registry.py` に依存
- `cli.py`: 全レイヤーを配線（唯一の composition root）

### Frontend / Backend 境界
- Backend (Python) → `static/` にビルド済み資産を配置
- Frontend → `api/client.ts` 経由で REST API にアクセス
- 型の同期: `types/api.ts` を Python モデルに合わせて手動更新

## Code Size Guidelines

- **File size**: 200-400 行を目安（最大 800 行）
- **Function size**: 50 行以内を目安
- **Nesting depth**: 最大 3 レベル（Early return で削減）
- **Test file**: テスト対象モジュールと 1:1 対応

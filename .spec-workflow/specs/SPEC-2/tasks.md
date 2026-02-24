# Tasks: SPEC-2 data-catalog

## Dependency Graph

```
1.1 (Models) ─────┬──→ 1.2 (FTS5 Store)
                   │
                   └──→ 2.1 (Service: add/get)
                              │
                              └──→ 2.2 (Service: update/search)
                                        │
                                        ├──→ 3.1 (MCP: add/update/get)
                                        │
                                        └──→ 3.2 (MCP: search/knowledge)
                                                   │
                                                   └──→ 4.1 (CLI wiring + integration)
                                                              │
                                                              └──→ 4.2 (Skill: /catalog-register)
```

---

- [x] 1.1 Implement Pydantic models for data catalog
  - File: src/insight_blueprint/models/catalog.py, src/insight_blueprint/models/__init__.py, tests/test_catalog_models.py
  - `SourceType(StrEnum)` を作成: csv, api, sql
  - `KnowledgeCategory(StrEnum)` を作成: methodology, caution, definition, context
  - `KnowledgeImportance(StrEnum)` を作成: high, medium, low
  - `ColumnSchema(BaseModel)` を作成: name/type/description (必須) + nullable/examples/range/unit (オプション)
  - `DataSource(BaseModel)` を作成: id/name/type/description/connection/schema_info/tags/created_at/updated_at
  - `DomainKnowledgeEntry(BaseModel)` を作成: key/title/content/category/importance/created_at/source/affects_columns
  - `DomainKnowledge(BaseModel)` を作成: source_id/entries (default empty list)
  - `models/__init__.py` に catalog models を re-export する
  - Purpose: storage・core・MCP 層で共有する data catalog 型を定義する
  - _Leverage: src/insight_blueprint/models/common.py (now_jst), src/insight_blueprint/models/design.py (StrEnum/BaseModel pattern)_
  - _Requirements: FR-1, FR-2_
  - **完了基準**:
    1. `tests/test_catalog_models.py` の 10 テストケースすべてが pass する
    2. `from insight_blueprint.models import DataSource, SourceType, ColumnSchema` が動作する
    3. `poe lint` と `poe typecheck` が pass する
  - **確認手続き**: `poe test -- tests/test_catalog_models.py -v` で全テスト pass を確認。`poe lint && poe typecheck` で品質チェック pass を確認
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer specializing in Pydantic v2 data modeling | Task: Implement catalog Pydantic models per FR-1 and FR-2 — SourceType(StrEnum), KnowledgeCategory(StrEnum), KnowledgeImportance(StrEnum), ColumnSchema, DataSource, DomainKnowledgeEntry, DomainKnowledge; use now_jst() from models/common.py for timestamp defaults; follow DesignStatus/AnalysisDesign pattern from models/design.py | Restrictions: Use Pydantic v2 (BaseModel, Field); all fields must have type annotations; StrEnum for enums (not Enum); connection field is untyped dict; schema_info is dict with columns key; DataSource must use model_config = ConfigDict(extra="ignore") for schema evolution | Success: 10 tests pass in test_catalog_models.py covering enum values, optional defaults, timestamp defaults, JSON round-trip, container defaults, invalid enum rejection; re-export from models/__init__.py works; poe lint and poe typecheck pass | After completing implementation and tests: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

- [x] 1.2 Implement SQLite FTS5 storage layer
  - File: src/insight_blueprint/storage/sqlite_store.py, tests/test_sqlite_store.py
  - `build_index(db_path, sources, knowledge)` を実装: DROP + CREATE VIRTUAL TABLE (trigram tokenizer) + executemany batch INSERT
  - `search_index(db_path, query, limit=20)` を実装: MATCH クエリ + snippet() + rank ordering。クエリは `"` → `""` エスケープ + ダブルクオートで囲む。空クエリは即座に空リスト返却
  - `insert_document(db_path, doc_type, source_id, title, content)` を実装: 単一行 INSERT（増分追加用）
  - `delete_source_documents(db_path, source_id)` を実装: source_id の全行 DELETE
  - `replace_source_documents(db_path, source_id, rows)` を実装: BEGIN IMMEDIATE トランザクション内で DELETE + INSERT を原子的に実行
  - 全接続に `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;` を設定
  - FTS5 unavailable 時: `OperationalError` を catch して `logging.warning()` → 空リスト返却（graceful degradation）
  - Purpose: FTS5 全文検索インデックスの構築・検索・増分更新を提供する
  - _Leverage: なし（新規 standalone モジュール）_
  - _Requirements: FR-7, FR-8_
  - **完了基準**:
    1. `tests/test_sqlite_store.py` の 15 テストケースすべてが pass する
    2. `build_index` → `search_index` のラウンドトリップで日本語・英語両方の検索が動作する
    3. `insert_document` 後に即座に `search_index` で検索可能
    4. `replace_source_documents` がトランザクション内で原子的に動作する
    5. FTS5 unavailable 時に例外が発生せず warning ログが出力される
    6. `poe lint` と `poe typecheck` が pass する
  - **確認手続き**: `poe test -- tests/test_sqlite_store.py -v` で全テスト pass を確認。`poe lint && poe typecheck` で品質チェック pass を確認
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer specializing in SQLite FTS5 and database operations | Task: Implement sqlite_store.py with build_index (full rebuild), search_index (MATCH + snippet + rank), insert_document (incremental add), delete_source_documents, and replace_source_documents (atomic DELETE+INSERT in BEGIN IMMEDIATE transaction) per FR-7 and FR-8; use trigram tokenizer for Japanese+English mixed content; set PRAGMA journal_mode=WAL and busy_timeout=5000 on all connections | Restrictions: No Pydantic dependency — receive plain dicts; all functions accept db_path as Path; parameterized queries only (no string interpolation in SQL); escape " to "" in user queries then wrap in double quotes; empty query returns [] immediately; catch OperationalError for FTS5 unavailable and log warning; per-call open/close for connections | Success: 15 tests pass covering build (file creation, empty data, source indexing, knowledge indexing, rebuild), search (matching, no match, ranking, snippets, missing DB), insert_document (immediate searchability), delete_source_documents, replace_source_documents (atomic), incremental ops with missing table (graceful no-op), FTS5 unavailable graceful degradation; poe lint and poe typecheck pass | After completing implementation and tests: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

- [x] 2.1 Implement CatalogService: add, get, list, get_schema, get_knowledge
  - File: src/insight_blueprint/core/catalog.py, tests/test_catalog.py, src/insight_blueprint/storage/project.py, tests/test_storage.py
  - `CatalogService(project_path)` constructor を実装: `_sources_dir`, `_knowledge_dir`, `_db_path` を設定
  - `add_source(source: DataSource)` を実装: `sources/{id}.yaml` 作成 + `knowledge/{id}.yaml` 作成（空 entries）+ FTS5 増分 INSERT
  - `get_source(source_id)` を実装: 単一ファイル読込 → DataSource | None
  - `list_sources()` を実装: glob `sources/*.yaml` → list[DataSource]（DesignService.list_designs パターン）
  - `get_schema(source_id)` を実装: source の columns リスト → list[ColumnSchema] | None
  - `get_knowledge(source_id, category?)` を実装: knowledge ファイル読込 + category フィルタ → DomainKnowledge | None
  - `init_project()` を修正: `catalog/sources.yaml` → `catalog/sources/` ディレクトリに変更 + `.sqlite/` ディレクトリ作成
  - 既存テスト `test_init_project_creates_catalog_sources_yaml` を `test_init_project_creates_sources_directory` に修正
  - Purpose: カタログ CRUD の基本操作（add/get/list/schema/knowledge）を提供する
  - _Leverage: src/insight_blueprint/core/designs.py (glob listing, read_yaml/write_yaml pattern), src/insight_blueprint/storage/yaml_store.py, src/insight_blueprint/storage/sqlite_store.py_
  - _Requirements: FR-3, FR-4, FR-5 (get_knowledge), FR-6 (get_knowledge filter), FR-16 (init changes)_
  - **完了基準**:
    1. `tests/test_catalog.py` の add/get/list/schema/knowledge テスト（14件）すべてが pass する
    2. `tests/test_storage.py` の既存テストが修正後も全 pass する（回帰なし）
    3. `add_source` が YAML + knowledge ファイル + FTS5 の 3 つを作成する
    4. duplicate ID で `ValueError` が発生する
    5. `get_knowledge(category="caution")` でカテゴリフィルタが正しく動作する
    6. `poe all` が pass する（既存 SPEC-1/1a テストも含めて全 pass）
  - **確認手続き**: `poe test -- tests/test_catalog.py tests/test_storage.py -v` で全テスト pass を確認。`poe all` で全体の回帰テスト + lint + typecheck pass を確認
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer specializing in service layer architecture | Task: Implement CatalogService with add_source, get_source, list_sources, get_schema, get_knowledge per FR-3/FR-4/FR-5/FR-6; follow DesignService pattern from core/designs.py; add_source creates sources/{id}.yaml + knowledge/{id}.yaml + FTS5 insert; modify init_project to create catalog/sources/ dir (replacing sources.yaml stub) and .sqlite/ dir; fix existing test | Restrictions: Use read_yaml/write_yaml from yaml_store.py; duplicate source_id raises ValueError; get_source returns None for missing; get_knowledge with category param filters entries; FTS5 insert_document failure must not cause add_source to fail (catch and warn); do NOT modify existing designs/ tests | Success: 14 tests pass in test_catalog.py; test_storage.py existing tests pass with directory change; add_source round-trip works; duplicate raises ValueError; get_knowledge filters by category; poe all passes (all existing + new tests green) | After completing implementation and tests: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

- [x] 2.2 Implement CatalogService: update_source, search, rebuild_index
  - File: src/insight_blueprint/core/catalog.py (拡張), tests/test_catalog.py (拡張)
  - `update_source(source_id, **fields)` を実装: `model_copy(update=...)` パターン + `updated_at` 自動更新 + FTS5 `replace_source_documents()` で原子的再インデックス
  - `search(query, source_type?, tags?)` を実装: FTS5 `search_index()` + Python post-filter (source_type, tags)
  - `rebuild_index()` を実装: 全ソース + 全ナレッジを収集して `build_index()` に渡す
  - Purpose: カタログの更新・検索・インデックス再構築を提供する
  - _Leverage: src/insight_blueprint/core/designs.py (model_copy pattern), src/insight_blueprint/storage/sqlite_store.py_
  - _Requirements: FR-5 (update), FR-9 (search/rebuild)_
  - **完了基準**:
    1. `tests/test_catalog.py` の update/search/rebuild テスト（12件追加、合計26件）すべてが pass する
    2. `update_source` が `updated_at` を自動更新し、変更されたフィールドのみ書き換える
    3. `search` が FTS5 結果を返し、`source_type` と `tags` フィルタが正しく動作する
    4. `add_source` 直後に `search` で即座に検索可能（`rebuild_index` 不要）
    5. `rebuild_index` 後にすべてのソース + ナレッジが検索可能
    6. FTS5 DB 未存在時に `search` が空リストを返す（例外なし）
    7. `poe all` が pass する
  - **確認手続き**: `poe test -- tests/test_catalog.py -v` で全テスト pass を確認。`poe all` で全体チェック
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer specializing in service layer and search integration | Task: Extend CatalogService with update_source (model_copy + updated_at + FTS5 replace_source_documents), search (FTS5 search_index + Python post-filter by source_type/tags), rebuild_index (collect all sources+knowledge then build_index) per FR-5/FR-9 | Restrictions: update_source follows DesignService.update_design pattern; search post-filter loads source YAML to check type/tags; rebuild_index must handle empty catalog gracefully; FTS5 failure in update must not cause update_source to fail | Success: 12 additional tests pass (update patches, updated_at refresh, untouched fields intact, missing returns None, persists to YAML, search matches, search filters by type, search filters by tags, search empty when no DB, rebuild creates DB, add then immediate search works); poe all passes | After completing implementation and tests: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

- [x] 3.1 Implement MCP tools: add_catalog_entry, update_catalog_entry, get_table_schema
  - File: src/insight_blueprint/server.py (拡張), tests/test_server.py (拡張)
  - `_catalog_service: CatalogService | None` モジュールレベル変数を追加
  - `get_catalog_service()` guard 関数を追加（`RuntimeError` on uninitialized）
  - `add_catalog_entry(source_id, name, type, description, connection, columns, tags?, primary_key?, row_count_estimate?)` を実装: DataSource 構築 → add_source → success dict
  - `update_catalog_entry(source_id, name?, description?, connection?, columns?, tags?)` を実装: 部分更新 → updated dict
  - `get_table_schema(source_id)` を実装: source の schema_info から columns/primary_key/row_count_estimate を返す
  - ValueError（duplicate ID, invalid type）は `{"error": ...}` dict に変換
  - Purpose: カタログ登録・更新・スキーマ取得を MCP ツールとして公開する
  - _Leverage: src/insight_blueprint/server.py (既存 design tools の error dict パターン)_
  - _Requirements: FR-10, FR-11, FR-12_
  - **完了基準**:
    1. `tests/test_server.py` の catalog tool テスト（8件追加）すべてが pass する
    2. `get_catalog_service()` が未初期化時に `RuntimeError` を raise する
    3. `add_catalog_entry` が success dict を返し、duplicate で error dict を返す
    4. `update_catalog_entry` が更新後の full dict を返し、missing で error dict を返す
    5. `get_table_schema` が columns list を返し、missing で error dict を返す
    6. invalid type (`"parquet"`) で error dict を返す
    7. `poe all` が pass する
  - **確認手続き**: `poe test -- tests/test_server.py -v` で全テスト pass を確認。`poe all` で全体チェック
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer specializing in FastMCP tool implementation | Task: Add 3 catalog MCP tools to server.py per FR-10/FR-11/FR-12 — add_catalog_entry (construct DataSource from flat params, call add_source), update_catalog_entry (partial update), get_table_schema (return columns+primary_key+row_count_estimate); add _catalog_service module-level var and get_catalog_service() guard | Restrictions: Follow existing design tool patterns exactly; all tools async def; return dicts not Pydantic models; catch ValueError for duplicate ID and invalid SourceType; add_catalog_entry accepts flat columns as list[dict] and builds schema_info internally | Success: 8 tests pass covering get_catalog_service guard, add success, add duplicate error, add invalid type error, update success, update missing error, get_table_schema success, get_table_schema missing error; poe all passes | After completing implementation and tests: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

- [x] 3.2 Implement MCP tools: search_catalog, get_domain_knowledge
  - File: src/insight_blueprint/server.py (拡張), tests/test_server.py (拡張)
  - `search_catalog(query, source_type?, tags?)` を実装: tags はカンマ区切り文字列 → list 変換 → CatalogService.search() → `{results, count}`
  - `get_domain_knowledge(source_id, category?)` を実装: category の KnowledgeCategory バリデーション → CatalogService.get_knowledge() → `{source_id, entries, count}`
  - invalid category は `{"error": ...}` dict に変換
  - Purpose: カタログ検索とドメインナレッジ参照を MCP ツールとして公開する
  - _Leverage: src/insight_blueprint/server.py (既存 error dict パターン)_
  - _Requirements: FR-13, FR-14_
  - **完了基準**:
    1. `tests/test_server.py` の search/knowledge ツールテスト（7件追加）すべてが pass する
    2. `search_catalog` が `{results: [...], count: N}` を返す
    3. `search_catalog` に `source_type` フィルタが正しく動作する
    4. `get_domain_knowledge` が `{source_id, entries, count}` を返す
    5. invalid category で error dict を返す
    6. missing source で error dict を返す
    7. `poe all` が pass する
  - **確認手続き**: `poe test -- tests/test_server.py -v` で全テスト pass を確認。`poe all` で全体チェック
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer specializing in FastMCP tool implementation | Task: Add 2 catalog MCP tools to server.py per FR-13/FR-14 — search_catalog (parse comma-separated tags string, call CatalogService.search, return {results, count}), get_domain_knowledge (validate category via KnowledgeCategory enum, call get_knowledge, return {source_id, entries, count}) | Restrictions: Follow existing tool patterns; tags param is comma-separated string split to list; invalid KnowledgeCategory returns error dict not exception; missing source returns error dict; all tools async def | Success: 7 tests pass covering search results dict, search empty returns zero count, search with source_type filter, get_domain_knowledge returns entries, get_domain_knowledge missing returns error, get_domain_knowledge with category filter, get_domain_knowledge invalid category returns error; poe all passes | After completing implementation and tests: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

- [x] 4.1 CLI wiring, project init updates, and integration test
  - File: src/insight_blueprint/cli.py, src/insight_blueprint/storage/project.py, tests/test_integration.py (拡張), tests/test_storage.py (拡張)
  - `cli.py` を修正: `CatalogService(project_path)` をインスタンス化し `server._catalog_service` に wire。`rebuild_index()` を `mcp.run()` の前に呼び出す
  - `storage/project.py` を修正: `_copy_skills_template()` を拡張して `catalog-register` skill もコピー
  - `tests/test_integration.py` にカタログラウンドトリップテストを追加: init → add_source → get_source → get_schema → search (即座に検索可能) → search with type filter (0 results) → get_knowledge
  - `tests/test_storage.py` に新テストを追加: `.sqlite/` dir 作成、catalog-register skill コピー
  - Purpose: CLI 起動時のカタログ初期化と、全レイヤー貫通の統合テストを完成させる
  - _Leverage: src/insight_blueprint/cli.py (既存の DesignService wiring pattern), src/insight_blueprint/storage/project.py (既存の _copy_skills_template pattern)_
  - _Requirements: FR-15, FR-16, AC 全般_
  - **完了基準**:
    1. `tests/test_integration.py` のカタログラウンドトリップテストが pass する
    2. `tests/test_storage.py` の新テスト（3件）すべてが pass する
    3. 既存の SPEC-1/1a テスト（43件）すべてが pass する（回帰なし）
    4. `poe all` が pass する（ruff + ty + pytest）
    5. `core/catalog.py` と `storage/sqlite_store.py` のカバレッジが 80% 以上
  - **確認手続き**:
    - `poe all` で全チェック pass を確認
    - `uv run pytest --cov=src/insight_blueprint --cov-report=term-missing` でカバレッジ確認（core/catalog.py, storage/sqlite_store.py が 80%+）
    - `uv run pytest -v` で全テスト数を確認（既存43件 + SPEC-2 新規テストすべて pass）
  - **手動確認手続き（ユーザー実施）**:
    - 以下のコマンドを実行して MCP サーバーの起動と `.insight/` 構造を確認してください:
      ```
      cd /tmp && mkdir -p spec2-test && uvx insight-blueprint --project /tmp/spec2-test
      ```
    - **期待値**: MCP サーバーが stdio モードで起動する（Ctrl+C で終了）
    - 起動後、別ターミナルで以下を確認:
      ```
      ls /tmp/spec2-test/.insight/catalog/sources/    # ディレクトリが存在する
      ls /tmp/spec2-test/.insight/.sqlite/             # ディレクトリが存在する
      ls /tmp/spec2-test/.claude/skills/catalog-register/  # SKILL.md が存在する
      ```
    - **期待値**: 3 つのパスすべてが存在する
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python developer specializing in CLI integration and end-to-end testing | Task: Wire CatalogService in cli.py (instantiate, set server._catalog_service, call rebuild_index before mcp.run); extend _copy_skills_template in project.py for catalog-register skill; add catalog round-trip integration test and storage tests per FR-15/FR-16 | Restrictions: CatalogService wiring must happen BEFORE mcp.run(); rebuild_index must not crash on empty catalog; catalog-register skill copy follows same pattern as analysis-design; do NOT modify existing SPEC-1 tests; integration test must verify immediate searchability after add (no rebuild needed) | Success: Integration test passes full round-trip (add → get → schema → search → type filter → knowledge); test_storage.py new tests pass (.sqlite dir, catalog-register skill copy); all 43 existing tests pass (no regression); poe all passes; coverage >= 80% for core/catalog.py and storage/sqlite_store.py | After completing implementation and tests: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

- [x] 4.2 Create /catalog-register bundled skill
  - File: src/insight_blueprint/_skills/catalog-register/SKILL.md
  - YAML frontmatter を含む SKILL.md を作成: `name: catalog-register`, `description` にトリガーフレーズ含む, `disable-model-invocation: true`
  - CSV ソース登録ワークフロー: ファイルヘッダー読込 → ColumnSchema 構築 → add_catalog_entry 呼び出し
  - API ソース登録ワークフロー: エンドポイント確認 → レスポンス構造分析 → ColumnSchema 構築 → add_catalog_entry 呼び出し
  - SQL ソース登録ワークフロー: INFORMATION_SCHEMA クエリ → カラムメタデータ取得 → add_catalog_entry 呼び出し
  - 各ソースタイプの `connection` dict フォーマットをガイドに含める
  - Purpose: データソースの自動探索と登録を Claude Code スキルとして提供する
  - _Leverage: src/insight_blueprint/_skills/analysis-design/SKILL.md (既存スキルフォーマット), .claude/rules/skill-format.md_
  - _Requirements: FR-17_
  - **完了基準**:
    1. SKILL.md が `.claude/rules/skill-format.md` の規則に準拠する
    2. YAML frontmatter に `name`, `description`, `disable-model-invocation: true` が含まれる
    3. CSV/API/SQL の 3 ソースタイプすべてのワークフローが記載されている
    4. 各ワークフローが `add_catalog_entry` MCP ツールの呼び出しで完了する
    5. `poe lint` が pass する（SKILL.md は lint 対象外だが、他ファイルに変更がないことを確認）
  - **手動確認手続き（ユーザー実施）**:
    1. **SKILL.md フォーマット確認**:
       - `src/insight_blueprint/_skills/catalog-register/SKILL.md` を開く
       - **期待値**: ファイル先頭に `---` で囲まれた YAML frontmatter があり、以下のキーが存在する:
         - `name: catalog-register`
         - `description:` （複数行、「データカタログ」「register」などのトリガーフレーズを含む）
         - `disable-model-invocation: true`
    2. **ワークフロー内容確認**:
       - SKILL.md 本文に CSV / API / SQL の 3 セクションがあることを確認
       - **期待値**: 各セクションに (a) データ構造探索手順, (b) ColumnSchema 構築方法, (c) `add_catalog_entry` 呼び出し例が含まれる
    3. **実際の動作確認（任意）**:
       - Claude Code で `/catalog-register` と入力し、スキルが読み込まれることを確認
       - **期待値**: Claude Code がソースタイプの選択を尋ね、選択したタイプに応じた探索ワークフローを開始する
  - _Prompt: Implement the task for spec SPEC-2, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Claude Code skill designer specializing in data exploration workflows | Task: Create SKILL.md for /catalog-register per FR-17 with YAML frontmatter (name, description with trigger phrases, disable-model-invocation: true); include 3 source type workflows — CSV (read headers, infer types), API (e-Stat pattern: getMetaInfo endpoint), SQL (BigQuery INFORMATION_SCHEMA queries); each workflow ends with add_catalog_entry MCP tool call; include connection dict format examples for each type | Restrictions: Follow .claude/rules/skill-format.md format rules; SKILL.md under 300 lines; description must include Japanese trigger phrases (「データカタログ登録」「ソース登録」); do NOT include implementation code — only Claude Code instructions; language of SKILL.md body is English (per skill-format.md) | Success: SKILL.md has valid frontmatter with name/description/disable-model-invocation; 3 source type workflows documented; each workflow references add_catalog_entry tool; file is under 300 lines | After completing implementation: (1) mark task [-] to [x] in tasks.md (2) log implementation with log-implementation tool_

# Tasks Document: Knowledge Suggestion

- [x] 1.1. KnowledgeCategory に finding 追加 + AnalysisDesign に referenced_knowledge 追加
  - File: src/insight_blueprint/models/catalog.py, src/insight_blueprint/models/design.py
  - Purpose: データモデル層の拡張。finding カテゴリと referenced_knowledge フィールドを追加
  - Leverage: 既存の StrEnum パターン (catalog.py L19-25)、Pydantic Field(default_factory=...) パターン (design.py L32-38)
  - Requirements: FR-1, FR-4 AC1/AC4
  - Prompt: TDD で実装。まず T-1.1〜T-1.3, T-4.1, T-4.6 のテストを書き、Red を確認してから models を変更する。KnowledgeCategory に finding を StrEnum メンバーとして追加。AnalysisDesign に referenced_knowledge: dict[str, list[str]] = Field(default_factory=dict) を追加。既存の YAML データとの後方互換を確認するテストを含める。

- [x] 1.2. DesignService で referenced_knowledge をサポート
  - File: src/insight_blueprint/core/designs.py
  - Purpose: create_design に referenced_knowledge パラメータ追加、update_design での merge ロジック実装
  - Leverage: 既存の create_design() パラメータ追加パターン (designs.py L20-61)、model_copy(update=...) パターン (designs.py L73)
  - Requirements: FR-4 AC2/AC3/AC5
  - Dependencies: 1.1
  - Prompt: TDD で実装。T-4.2〜T-4.5, T-4.7 のテストを先に書く。create_design に referenced_knowledge: dict[str, list[str]] | None = None を追加。update_design の referenced_knowledge merge はリスト和集合 + 重複排除で実装 (dict.fromkeys で順序保持)。update に含まれないセクションキーは保持。

- [x] 2.1. Finding 自動抽出: _extract_finding_if_terminal + _build_finding
  - File: src/insight_blueprint/core/reviews.py
  - Purpose: terminal 遷移時に finding を自動生成・保存するプライベートメソッドを実装
  - Leverage: save_extracted_knowledge() の保存パターン (reviews.py L371-406)、_TITLE_MAX_LENGTH 定数 (reviews.py L38)
  - Requirements: FR-2 AC1/AC2/AC3/AC4/AC5
  - Dependencies: 1.1
  - Prompt: TDD で実装。T-2.7〜T-2.12 のテストを先に書く (_build_finding の単体テスト + 抽出フックの動作テスト)。_extract_finding_if_terminal(design_id, target_status) は target_status が terminal の場合のみ実行。_build_finding(design, target_status) で DomainKnowledgeEntry を生成。STATUS は引数の target_status.value.upper() を使用。タイトルは80文字切り詰め (境界値 79/80/81 をテスト)。重複チェックは既存キーを確認。失敗時は try/except + logger.warning で fire-and-forget。

- [x] 2.2. 全遷移経路に finding 抽出フックを組み込み
  - File: src/insight_blueprint/core/reviews.py
  - Purpose: transition_status, save_review_comment, save_review_batch の3メソッドに _extract_finding_if_terminal の呼び出しを追加
  - Leverage: 既存の update_design 呼び出しパターン (reviews.py L149, L190, L247)
  - Requirements: FR-2 AC1
  - Dependencies: 2.1
  - Prompt: TDD で実装。T-2.1〜T-2.6c のテストを先に書く。各メソッドの update_design() 呼び出し直後に _extract_finding_if_terminal(design_id, target_status) を追加。transition_status では target (DesignStatus) を渡す。save_review_comment/save_review_batch では target_status を渡す。非 terminal 遷移では finding が生成されないことを全3経路でテスト確認。

- [x] 3.1. ALLOWED_TARGET_SECTIONS + COMMENTABLE_SECTIONS に referenced_knowledge 追加
  - File: src/insight_blueprint/core/reviews.py, frontend/src/pages/design-detail/components/sections.ts
  - Purpose: referenced_knowledge をレビュー対象セクションに追加。Backend/Frontend の契約テスト維持
  - Leverage: ALLOWED_TARGET_SECTIONS (reviews.py L41-48)、COMMENTABLE_SECTIONS (sections.ts L10-17)
  - Requirements: FR-5 AC1/AC2
  - Dependencies: 1.1
  - Prompt: T-5.1, T-5.2, T-5.3, T-5.4 のテストを先に書く。ALLOWED_TARGET_SECTIONS set に "referenced_knowledge" を追加。COMMENTABLE_SECTIONS 配列に `{ id: "referenced_knowledge", label: "Referenced Knowledge", type: "json" }` を追加。T-5.3: referenced_knowledge コメントが extract_domain_knowledge で抽出可能であることをテスト。既存の契約テスト (test_reviews.py) が通ることを確認。

- [x] 4.1. RulesService コンストラクタ拡張 + SECTION_KNOWLEDGE_MAP 定義
  - File: src/insight_blueprint/core/rules.py, src/insight_blueprint/_registry.py, src/insight_blueprint/cli.py
  - Purpose: RulesService に DesignService と db_path を注入可能にし、SECTION_KNOWLEDGE_MAP 定数を定義
  - Leverage: 既存の RulesService.__init__ (rules.py L16-19)、_registry.py の配線パターン
  - Requirements: FR-3 AC1
  - Dependencies: 1.1
  - Prompt: TDD で実装。T-3.15 のテストを先に書く。RulesService.__init__ に design_service: DesignService と db_path: Path を追加。既存の get_project_context() と suggest_cautions() が変わらず動くことをテストで確認。SECTION_KNOWLEDGE_MAP をモジュール定数として定義。_registry.py と cli.py の配線を更新。注意: RulesService を直接生成しているテストファイル (test_rules.py, test_server.py, test_integration.py, test_web.py, test_web_integration.py) のコンストラクタ呼び出しも更新すること。

- [x] 4.2. suggest_knowledge_for_design: カテゴリフィルタ + source_ids/theme_id マッチング
  - File: src/insight_blueprint/core/rules.py
  - Purpose: セクション別カテゴリフィルタ、source_ids マッチング (caution/definition)、theme_id マッチング (finding/context) を実装
  - Leverage: _collect_all_knowledge_entries() (rules.py L93-106)、suggest_cautions() のフィルタパターン (rules.py L75-91)
  - Requirements: FR-3 AC1/AC2/AC3/AC4/AC7/AC9/AC10
  - Dependencies: 4.1
  - Prompt: TDD で実装。T-3.1〜T-3.6, T-3.10, T-3.11, T-3.13, T-3.14 のテストを先に書く。suggest_knowledge_for_design(section, theme_id, source_ids, hypothesis_text, parent_id) を実装。source_ids は server.py でカンマ区切り文字列を list[str] に分解して RulesService には list[str] を渡す。section=None で全カテゴリ、未知 section で error dict。各マッチ結果に relevance フィールドを付与。

- [x] 4.3. suggest_knowledge_for_design: parent_id lineage 走査
  - File: src/insight_blueprint/core/rules.py
  - Purpose: parent_id チェーンを辿って祖先 design の finding を収集
  - Leverage: DesignService.get_design() (designs.py L78-85)
  - Requirements: FR-3 AC5/AC6
  - Dependencies: 4.2
  - Prompt: TDD で実装。T-3.7, T-3.8, T-3.9 のテストを先に書く。visited set で循環参照を検出。深度上限 10 で停止。各 ancestor の finding に relevance "ancestor design: {design_id}" を付与。

- [x] 4.4. suggest_knowledge_for_design: FTS5 methodology マッチング
  - File: src/insight_blueprint/core/rules.py
  - Purpose: hypothesis_text を FTS5 検索し、methodology カテゴリの knowledge をマッチング
  - Leverage: sqlite_store.search_index() (sqlite_store.py L105-147)
  - Requirements: FR-3 AC8
  - Dependencies: 4.2
  - Prompt: TDD で実装。T-3.12, T-3.16, T-3.17 のテストを先に書く。search_index(db_path, hypothesis_text) で FTS5 検索 → doc_type=="knowledge" をフィルタ → _collect_all_knowledge_entries() と title で突合 → category==methodology のみ返却。FTS5 例外時は methodology を空で返却 (他カテゴリは継続)。title 不一致はスキップ。

- [x] 5.1. MCP ツール: suggest_knowledge_for_design + referenced_knowledge パラメータ
  - File: src/insight_blueprint/server.py
  - Purpose: 新 MCP ツール追加と既存ツールへの referenced_knowledge パラメータ追加。source_ids のカンマ区切り文字列を list[str] に変換する責務はここで担う
  - Leverage: 既存の MCP ツール定義パターン (server.py L35-50)
  - Requirements: FR-3, FR-4 AC2/AC3
  - Dependencies: 4.2, 1.2
  - Prompt: TDD で実装。T-MCP.0〜T-MCP.3 のテストを先に書く。suggest_knowledge_for_design ツールを追加 (source_ids: str | None をカンマ分割して list[str] に変換してから RulesService に渡す)。create_analysis_design と update_analysis_design に referenced_knowledge: dict | None = None パラメータを追加。get_domain_knowledge のエラーメッセージのカテゴリ一覧に finding を追加。

- [x] 5.2. REST API: referenced_knowledge パラメータ対応
  - File: src/insight_blueprint/web.py
  - Purpose: CreateDesignRequest / UpdateDesignRequest に referenced_knowledge を追加し、REST API 経由でも referenced_knowledge の CRUD を可能にする
  - Leverage: 既存の Pydantic request model パターン (web.py)
  - Requirements: FR-4 AC2/AC3
  - Dependencies: 1.2
  - Prompt: web.py の CreateDesignRequest に referenced_knowledge: dict[str, list[str]] | None = None を追加。UpdateDesignRequest にも同様に追加。エンドポイントの create/update ハンドラで referenced_knowledge を DesignService に渡す。test_web.py にテストを追加。

- [x] 6.1. 統合テスト
  - File: tests/test_integration.py
  - Purpose: Finding ライフサイクル、トレーサビリティフロー、referenced_knowledge merge の E2E 検証
  - Leverage: 既存の統合テストパターン (test_integration.py)
  - Requirements: FR-1〜FR-5 (横断)
  - Dependencies: 4.3, 4.4, 5.1
  - Prompt: T-INT.1〜T-INT.4 を実装。design 作成 → terminal 遷移 (transition_status, save_review_batch) → finding 抽出 → suggest で返却の全フロー。suggest → create with referenced_knowledge → get で確認のトレーサビリティフロー。referenced_knowledge merge の和集合確認。

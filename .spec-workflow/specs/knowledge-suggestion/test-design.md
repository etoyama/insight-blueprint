# Test Design: Knowledge Suggestion

## Overview

knowledge-suggestion 機能のテスト設計。requirements.md の FR-1〜FR-5 の全 Acceptance Criteria をカバーし、design.md のコンポーネント構成に沿ってテストを構成する。

## Test Scope

| 対象 | テストレベル | 対象ファイル |
|------|------------|------------|
| KnowledgeCategory.finding | Unit | `tests/test_catalog_models.py` |
| AnalysisDesign.referenced_knowledge | Unit | `tests/test_designs.py` |
| Finding 自動抽出 (3経路) | Unit | `tests/test_reviews.py` |
| ALLOWED_TARGET_SECTIONS 拡張 | Unit + Contract | `tests/test_reviews.py` |
| suggest_knowledge_for_design | Unit | `tests/test_rules.py` |
| DesignService.create/update referenced_knowledge | Unit | `tests/test_designs.py` |
| MCP ツール | Unit | `tests/test_server.py` |
| Finding ライフサイクル | Integration | `tests/test_integration.py` |
| トレーサビリティフロー | Integration | `tests/test_integration.py` |

## FR-1: KnowledgeCategory への finding 追加

### Unit Tests (test_catalog_models.py)

#### T-1.1: finding メンバーの存在確認

```
AC: FR-1 AC1
Given: KnowledgeCategory enum
When: KnowledgeCategory.finding にアクセスする
Then: 値は "finding" であること
And: 全メンバーは methodology, caution, definition, context, finding の5つであること
```

#### T-1.2: 既存カテゴリの後方互換

```
AC: FR-1 AC2
Given: category="methodology" で作成された DomainKnowledgeEntry
When: entry.category にアクセスする
Then: KnowledgeCategory.methodology であること
And: entry の全フィールドが変更なしで読み書きできること
```

#### T-1.3: finding カテゴリで knowledge 作成

```
AC: FR-1 AC3
Given: category=KnowledgeCategory.finding のパラメータ
When: DomainKnowledgeEntry を作成する
Then: 正常に作成・シリアライズ・デシリアライズできること
And: 他カテゴリのエントリと同じ YAML 構造で保存されること
```

## FR-2: Terminal 遷移時の finding 自動抽出

### Unit Tests (test_reviews.py)

#### T-2.1: supported 遷移で finding 自動生成

```
AC: FR-2 AC1
Given: in_review ステータスの design "TEST-H01"
When: transition_status(design_id, "supported") を呼ぶ
Then: extracted_knowledge.yaml に category=finding のエントリが追加されること
```

#### T-2.2: rejected 遷移で finding 自動生成

```
AC: FR-2 AC1
Given: in_review ステータスの design "TEST-H02"
When: transition_status(design_id, "rejected") を呼ぶ
Then: extracted_knowledge.yaml に category=finding のエントリが追加されること
```

#### T-2.3: inconclusive 遷移で finding 自動生成

```
AC: FR-2 AC1
Given: in_review ステータスの design "TEST-H03"
When: transition_status(design_id, "inconclusive") を呼ぶ
Then: extracted_knowledge.yaml に category=finding のエントリが追加されること
```

#### T-2.4: save_review_comment 経由の terminal 遷移で finding 生成

```
AC: FR-2 AC1
Given: in_review ステータスの design
When: save_review_comment(design_id, comment, "supported") を呼ぶ
Then: extracted_knowledge.yaml に finding エントリが追加されること
```

#### T-2.5: save_review_batch 経由の terminal 遷移で finding 生成

```
AC: FR-2 AC1
Given: in_review ステータスの design
When: save_review_batch(design_id, "rejected", comments) を呼ぶ
Then: extracted_knowledge.yaml に finding エントリが追加されること
```

#### T-2.6: 非 terminal 遷移では finding を生成しない (transition_status)

```
AC: FR-2 AC1 (逆テスト)
Given: in_review ステータスの design
When: transition_status(design_id, "revision_requested") を呼ぶ
Then: extracted_knowledge.yaml に finding エントリが追加されないこと
```

#### T-2.6b: 非 terminal 遷移では finding を生成しない (save_review_comment)

```
AC: FR-2 AC1 (逆テスト)
Given: in_review ステータスの design
When: save_review_comment(design_id, comment, "revision_requested") を呼ぶ
Then: extracted_knowledge.yaml に finding エントリが追加されないこと
```

#### T-2.6c: 非 terminal 遷移では finding を生成しない (save_review_batch)

```
AC: FR-2 AC1 (逆テスト)
Given: in_review ステータスの design
When: save_review_batch(design_id, "analyzing", comments) を呼ぶ
Then: extracted_knowledge.yaml に finding エントリが追加されないこと
```

#### T-2.7: finding のフィールド値検証

```
AC: FR-2 AC2
Given: design (id="CHURN-H01", title="チャーン率仮説", hypothesis_statement="...", source_ids=["orders"])
When: transition_status(design_id, "supported") を呼ぶ
Then: finding の key == "CHURN-H01-finding"
And: title == "[SUPPORTED] チャーン率仮説" (80文字以内に切り詰め)
And: content == design.hypothesis_statement
And: source == "design:CHURN-H01"
And: affects_columns == ["orders"]
And: category == KnowledgeCategory.finding
```

#### T-2.8: finding のタイトル80文字切り詰め (境界値)

```
AC: FR-2 AC2
Given: "[SUPPORTED] " (12文字) + title で合計79/80/81文字になる3ケース
When: terminal 遷移で finding を生成する
Then: 79文字 → そのまま (79文字)
And: 80文字 → そのまま (80文字)
And: 81文字 → 80文字に切り詰められること
```

#### T-2.9: finding の永続化先

```
AC: FR-2 AC3
Given: terminal 遷移で finding が生成された
When: .insight/rules/extracted_knowledge.yaml を読む
Then: 生成された finding エントリが含まれていること
And: 既存の extracted knowledge エントリが保持されていること
```

#### T-2.10: 重複 finding の非生成

```
AC: FR-2 AC4
Given: "TEST-H01-finding" が既に extracted_knowledge.yaml に存在する
When: transition_status("TEST-H01", "supported") を再度呼ぶ
Then: 新しい finding エントリが追加されないこと
And: 既存のエントリが変更されないこと
```

#### T-2.11: finding 抽出失敗時のステータス遷移継続

```
AC: FR-2 AC5
Given: extracted_knowledge.yaml への書き込みが失敗する状態 (mock)
When: transition_status(design_id, "supported") を呼ぶ
Then: ステータス遷移は成功すること (design.status == "supported")
And: warning ログが出力されること
```

#### T-2.12: finding タイトルの STATUS は target_status を使用

```
AC: FR-2 AC2 (順序保証)
Given: in_review ステータスの design
When: transition_status(design_id, "rejected") を呼ぶ
Then: finding.title が "[REJECTED]" で始まること ("[IN_REVIEW]" ではないこと)
```

## FR-3: suggest_knowledge_for_design

### Unit Tests (test_rules.py)

#### T-3.1: section による カテゴリフィルタ

```
AC: FR-3 AC1
Given: finding, methodology, caution の knowledge entries が存在する
When: suggest_knowledge_for_design(section="hypothesis_statement") を呼ぶ
Then: suggestions に finding カテゴリのみが含まれること
And: methodology, caution は含まれないこと
```

#### T-3.2: SECTION_KNOWLEDGE_MAP の全セクションカバー

```
AC: FR-3 AC1
Given: 各カテゴリの knowledge entries が存在する
When: SECTION_KNOWLEDGE_MAP の全 7 セクションで suggest を呼ぶ
Then: 各セクションで期待されるカテゴリの knowledge のみが返却されること
```

#### T-3.3: section=None で全カテゴリ返却

```
AC: FR-3 AC2
Given: 全カテゴリの knowledge entries が存在する
When: suggest_knowledge_for_design(section=None) を呼ぶ
Then: 全カテゴリの knowledge が返却されること
```

#### T-3.4: 未知 section でエラー返却

```
AC: FR-3 AC3
Given: 任意の knowledge entries
When: suggest_knowledge_for_design(section="unknown_section") を呼ぶ
Then: {"error": "Unknown section 'unknown_section'. ..."} が返却されること
```

#### T-3.5: theme_id マッチ (finding)

```
AC: FR-3 AC4
Given: source="design:CHURN-H01" の finding (theme_id=CHURN の design 由来)
When: suggest_knowledge_for_design(section="hypothesis_statement", theme_id="CHURN") を呼ぶ
Then: finding が suggestions に含まれること
And: relevance に "theme_id match: CHURN" が含まれること
```

#### T-3.6: theme_id マッチ (context)

```
AC: FR-3 AC4
Given: theme_id=CHURN の design に紐づく context knowledge
When: suggest_knowledge_for_design(section="hypothesis_background", theme_id="CHURN") を呼ぶ
Then: context が suggestions に含まれること
```

#### T-3.7: parent_id lineage 走査

```
AC: FR-3 AC5
Given: CHURN-H03 (parent=CHURN-H02, parent=CHURN-H01) の lineage
And: CHURN-H01-finding, CHURN-H02-finding が存在する
When: suggest_knowledge_for_design(section="hypothesis_statement", parent_id="CHURN-H02") を呼ぶ
Then: CHURN-H01-finding と CHURN-H02-finding の両方が返却されること
And: relevance に "ancestor design: CHURN-H01", "ancestor design: CHURN-H02" が含まれること
```

#### T-3.8: lineage 走査の循環参照停止

```
AC: FR-3 AC6
Given: A (parent=B), B (parent=A) の循環参照
When: suggest_knowledge_for_design(parent_id="A") を呼ぶ
Then: 無限ループせず結果が返却されること
```

#### T-3.9: lineage 走査の深度上限

```
AC: FR-3 AC6
Given: 深度 15 の parent_id チェーン
When: suggest_knowledge_for_design(parent_id=末端) を呼ぶ
Then: 深度 10 で停止し、それまでの結果が返却されること
```

#### T-3.10: source_ids マッチ (caution)

```
AC: FR-3 AC7
Given: affects_columns=["orders"] の caution knowledge
When: suggest_knowledge_for_design(section="source_ids", source_ids="orders,users") を呼ぶ
Then: caution が suggestions に含まれること
And: relevance に "source_id match: orders" が含まれること
```

#### T-3.11: source_ids マッチ (definition)

```
AC: FR-3 AC7
Given: affects_columns=["users"] の definition knowledge
When: suggest_knowledge_for_design(section="source_ids", source_ids="users") を呼ぶ
Then: definition が suggestions に含まれること
```

#### T-3.12: hypothesis_text FTS5 マッチ (methodology)

```
AC: FR-3 AC8
Given: FTS5 インデックスに methodology knowledge が登録済み
When: suggest_knowledge_for_design(section="metrics", hypothesis_text="チャーン率") を呼ぶ
Then: マッチする methodology が返却されること
And: relevance に "FTS5 match" が含まれること
```

#### T-3.13: relevance フィールドの検証

```
AC: FR-3 AC9
Given: theme_id マッチする finding
When: suggest_knowledge_for_design で結果を取得する
Then: 各エントリに relevance フィールドが含まれること
And: relevance の内容がマッチ理由を記述していること
```

#### T-3.14: マッチなしで空結果

```
AC: FR-3 AC10
Given: knowledge entries が存在しない
When: suggest_knowledge_for_design(section="metrics") を呼ぶ
Then: {"section": "metrics", "suggestions": {}, "total": 0} が返却されること
```

#### T-3.15: RulesService コンストラクタ変更の互換性

```
AC: (design.md Component 4)
Given: RulesService に DesignService と db_path を渡す
When: コンストラクタで初期化する
Then: 既存の get_project_context(), suggest_cautions() が変わらず動作すること
```

#### T-3.16: FTS5 検索失敗時に methodology だけ空で他カテゴリは返却

```
AC: (design.md Error Handling 3)
Given: FTS5 データベースが破損 or 存在しない状態 (mock)
And: finding, caution の knowledge entries が存在する
When: suggest_knowledge_for_design(section="explanatory", hypothesis_text="...", source_ids="orders") を呼ぶ
Then: methodology の suggestions は空であること
And: caution の suggestions は正常に返却されること
```

#### T-3.17: FTS5 結果と knowledge の title 不一致時にスキップ

```
AC: (design.md Error Handling 5)
Given: FTS5 検索結果に title="不明なタイトル" の結果がある
And: _collect_all_knowledge_entries() に該当 title の methodology エントリが存在しない
When: methodology マッチングを実行する
Then: 不一致の結果はスキップされ suggestions に含まれないこと
And: 他のマッチした結果は正常に返却されること
```

## FR-4: referenced_knowledge フィールド

### Unit Tests (test_designs.py)

#### T-4.1: referenced_knowledge のデフォルト値

```
AC: FR-4 AC1
Given: referenced_knowledge を指定せずに AnalysisDesign を作成する
When: design.referenced_knowledge にアクセスする
Then: 空の dict {} が返却されること
```

#### T-4.2: create_design に referenced_knowledge を渡す

```
AC: FR-4 AC2
Given: referenced_knowledge={"hypothesis_statement": ["K-001"]} のパラメータ
When: DesignService.create_design(..., referenced_knowledge=referenced) を呼ぶ
Then: 作成された design の referenced_knowledge が {"hypothesis_statement": ["K-001"]} であること
```

#### T-4.3: update_design で referenced_knowledge を merge

```
AC: FR-4 AC3
Given: referenced_knowledge={"hypothesis_statement": ["K-001"]} の design
When: update_design(design_id, referenced_knowledge={"source_ids": ["K-002"]}) を呼ぶ
Then: referenced_knowledge == {"hypothesis_statement": ["K-001"], "source_ids": ["K-002"]}
```

#### T-4.4: update_design で同一セクションキーの和集合

```
AC: FR-4 AC3
Given: referenced_knowledge={"hypothesis_statement": ["K-001"]} の design
When: update_design(design_id, referenced_knowledge={"hypothesis_statement": ["K-002"]}) を呼ぶ
Then: referenced_knowledge == {"hypothesis_statement": ["K-001", "K-002"]}
```

#### T-4.5: 同一セクションキーの重複排除

```
AC: FR-4 AC3
Given: referenced_knowledge={"hypothesis_statement": ["K-001"]} の design
When: update_design(design_id, referenced_knowledge={"hypothesis_statement": ["K-001", "K-002"]}) を呼ぶ
Then: referenced_knowledge == {"hypothesis_statement": ["K-001", "K-002"]} (K-001 は重複しない)
```

#### T-4.6: 既存 YAML との後方互換

```
AC: FR-4 AC4
Given: referenced_knowledge フィールドのない既存 YAML ファイル
When: AnalysisDesign(**yaml_data) でロードする
Then: referenced_knowledge == {} でエラーなくロードできること
```

#### T-4.7: get_design で referenced_knowledge 返却

```
AC: FR-4 AC5
Given: referenced_knowledge 付きで作成された design
When: DesignService.get_design(design_id) を呼ぶ
Then: レスポンスに referenced_knowledge フィールドが含まれていること
```

## FR-5: レビューでの参照適切性指摘

### Unit Tests (test_reviews.py)

#### T-5.1: referenced_knowledge が ALLOWED_TARGET_SECTIONS に含まれる

```
AC: FR-5 AC1
Given: ALLOWED_TARGET_SECTIONS の定義
When: "referenced_knowledge" の存在を確認する
Then: set に含まれていること
```

#### T-5.2: save_review_batch で referenced_knowledge セクションを指定可能

```
AC: FR-5 AC1
Given: in_review ステータスの design
When: save_review_batch(design_id, "revision_requested", [{"target_section": "referenced_knowledge", "comment": "..."}]) を呼ぶ
Then: バリデーションエラーなく batch が保存されること
```

#### T-5.3: referenced_knowledge コメントからの knowledge 抽出

```
AC: FR-5 AC2
Given: target_section="referenced_knowledge" のレビューコメント付きの design
When: terminal 遷移後に extract_domain_knowledge を呼ぶ
Then: 既存の抽出ロジックで knowledge エントリとして抽出可能であること
```

### Contract Tests (test_reviews.py)

#### T-5.4: Backend/Frontend セクション一致

```
AC: (design.md Component 6)
Given: ALLOWED_TARGET_SECTIONS (backend) と COMMENTABLE_SECTIONS (frontend)
When: 両者のセクション ID を比較する
Then: 完全に一致すること (既存の契約テストが通ること)
```

## MCP Tool Tests (test_server.py)

#### T-MCP.0: get_domain_knowledge のカテゴリ一覧に finding

```
AC: (design.md Component 5)
Given: MCP ツール get_domain_knowledge のエラーメッセージ
When: 無効なカテゴリを指定して呼ぶ
Then: エラーメッセージのカテゴリ一覧に "finding" が含まれること
```

#### T-MCP.1: suggest_knowledge_for_design ツール呼び出し

```
AC: FR-3 全般
Given: knowledge entries が存在する
When: MCP ツール suggest_knowledge_for_design を呼ぶ
Then: suggestions dict が返却されること
```

#### T-MCP.2: create_analysis_design に referenced_knowledge

```
AC: FR-4 AC2
Given: referenced_knowledge パラメータ
When: MCP ツール create_analysis_design を呼ぶ
Then: 作成された design に referenced_knowledge が含まれること
```

#### T-MCP.3: update_analysis_design に referenced_knowledge

```
AC: FR-4 AC3
Given: 既存の design
When: MCP ツール update_analysis_design を referenced_knowledge 付きで呼ぶ
Then: referenced_knowledge が merge されていること
```

## Integration Tests (test_integration.py)

#### T-INT.1: finding ライフサイクル (transition_status)

```
AC: FR-1 + FR-2 + FR-3
Given: design 作成 → transition_status で supported に遷移
When: suggest_knowledge_for_design(section="hypothesis_statement", theme_id=design.theme_id) を呼ぶ
Then: 自動抽出された finding がサジェスト結果に含まれること
```

#### T-INT.2: finding ライフサイクル (save_review_batch)

```
AC: FR-2 + FR-3
Given: design 作成 → save_review_batch で rejected に遷移
When: suggest_knowledge_for_design で finding を検索する
Then: 自動抽出された finding がサジェスト結果に含まれること
```

#### T-INT.3: トレーサビリティ E2E

```
AC: FR-3 + FR-4
Given: suggest_knowledge_for_design(section="hypothesis_statement", theme_id="CHURN") で suggestions を取得
And: suggestions["finding"][0]["key"] を取得 (例: "CHURN-H01-finding")
When: create_analysis_design(referenced_knowledge={"hypothesis_statement": ["CHURN-H01-finding"]}) を呼ぶ
And: get_analysis_design(design_id) を呼ぶ
Then: referenced_knowledge["hypothesis_statement"] に "CHURN-H01-finding" が含まれること
```

#### T-INT.4: referenced_knowledge merge の統合テスト

```
AC: FR-4 AC3
Given: referenced_knowledge 付きで design を作成
When: update_analysis_design で同一セクションに新しい key を追加
And: get_analysis_design で取得
Then: 両方の key が和集合で含まれること
```

## Test Independence

- 各テストは `tmp_path` fixture で独立したプロジェクトディレクトリを使用する
- `TEST-H01` 等の固定 ID はテスト内で `DesignService.create_design()` を呼んで生成する（事前状態に依存しない）
- FTS5 テストは `tmp_path / "catalog.db"` を使用し、テスト間で DB を共有しない
- 全テストは任意の順序で実行可能であること

## Test Coverage Summary

| FR | AC 数 | テストケース数 | カバー率 |
|----|-------|--------------|---------|
| FR-1 | 3 | 3 (T-1.1〜T-1.3) | 100% |
| FR-2 | 5 | 14 (T-2.1〜T-2.12 + T-2.6b, T-2.6c) | 100% |
| FR-3 | 10 | 17 (T-3.1〜T-3.17) | 100% |
| FR-4 | 5 | 7 (T-4.1〜T-4.7) | 100% |
| FR-5 | 2 | 4 (T-5.1〜T-5.4) | 100% |
| MCP | - | 4 (T-MCP.0〜T-MCP.3) | - |
| Integration | - | 4 (T-INT.1〜T-INT.4) | - |
| **合計** | **25** | **53** | **100%** |

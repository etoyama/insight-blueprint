# Product Overview

## Product Purpose

insight-blueprint は、仮説駆動型データ分析を構造化・管理するための MCP (Model Context Protocol) サーバーである。データアナリストが Claude Code と協働して分析を進める際に、分析設計書（仮説ドキュメント）のライフサイクル管理、データカタログの登録・検索、ドメイン知識の蓄積と再利用を一元的に支援する。

解決する問題:
- 分析の設計・レビュー・結果判定のワークフローが属人的で、再現性がない
- 使用したデータソースの注意事項やドメイン知識が個人のメモに散逸し、チームで共有されない
- 過去の分析結果（仮説の支持/棄却）が蓄積されず、同じ仮説を繰り返し検証してしまう

## Target Users

### Primary: データアナリスト + Claude Code

Claude Code を分析パートナーとして使うデータアナリストが主要ユーザー。Claude Code が MCP プロトコル経由で全ツールを操作し、人間はレビューと判定を担当する。

- **Claude Code**: MCP ツール経由で分析設計書の作成・更新、データカタログの検索、ドメイン知識の参照を行う
- **データアナリスト**: WebUI ダッシュボードで設計書のレビュー、ステータス遷移の判定、ドメイン知識の確認を行う

### Secondary: MCP 互換クライアント

Claude Code 以外の MCP クライアントからも利用可能。ツールのインターフェースは汎用的に設計されている。

## Key Features

1. **分析設計管理 (Analysis Design)**: 仮説ドキュメントの作成・更新・一覧・ステータス遷移。ステートマシンによるワークフロー制御 (in_review -> revision_requested / analyzing -> supported / rejected / inconclusive)
2. **データカタログ (Data Catalog)**: データソースの登録・スキーマ管理・FTS5 全文検索。タグによる分類とフィルタリング
3. **レビューワークフロー (Review Workflow)**: 設計書に対するレビューコメント・バッチレビュー。セクション単位のインラインコメント。レビュー結果に基づくステータス遷移
4. **ドメイン知識管理 (Domain Knowledge)**: レビューコメントからの知識自動抽出、カタログに紐づく知識の登録・検索、注意事項の自動サジェスト
5. **データリネージ (Data Lineage)**: pandas パイプラインの行数変化追跡、Mermaid ダイアグラム出力
6. **WebUI ダッシュボード**: React ベースの4タブ構成 (Designs / Catalog / Rules / History) で分析設計のレビュー・閲覧

## Business Objectives

- **分析の再現性向上**: 仮説・手法・データソースの選択を構造化し、第三者が再現可能な形で記録する
- **知見の蓄積と再利用**: 過去の分析結果やデータの注意事項を蓄積し、次回の分析設計に自動的に反映する
- **レビュー品質の標準化**: ステートマシンベースのワークフローで、レビューのステップとタイミングを統一する
- **Claude Code との協働の効率化**: MCP ツールを通じて、分析の設計からレビューまでのワークフローをシームレスに進行する

## Success Metrics

- **Knowledge 蓄積率**: terminal ステータスに到達した分析の何割がドメイン知識として抽出されているか (目標: 80%以上)
- **知見の再利用率**: 新規分析設計で過去の knowledge が参照された割合 (目標: 50%以上)
- **レビューサイクル時間**: in_review から terminal ステータスまでの平均遷移回数 (目標: 3回以内)

## Product Principles

1. **Claude Code First**: MCP ツールが一級市民。WebUI は閲覧・レビュー用の補助インターフェース。全機能は MCP 経由で操作可能であること
2. **YAML as Source of Truth**: データは人間が読める YAML で永続化する。SQLite FTS5 は検索用の派生インデックスであり、YAML から常に再構築可能
3. **ステートマシンによるワークフロー制御**: ステータス遷移は明示的に定義されたルールに基づく。バイパスを許さない
4. **知識の自動蓄積**: 分析のライフサイクルを通じて、手動の記録作業を最小化しつつドメイン知識を蓄積する
5. **後方互換の優先**: 既存データを壊さない。enum 追加は可、リネームは不可。YAML フィールドの追加はデフォルト値付きで

## Monitoring & Visibility

- **Dashboard Type**: React ベース WebUI (http://127.0.0.1:3000)、MCP サーバーと同プロセスでデーモンスレッド起動
- **Real-time Updates**: ポーリングベース（WebSocket 未実装）
- **Key Metrics Displayed**: 分析設計の一覧・ステータス別フィルタ、カタログの検索結果、ドメイン知識の一覧、レビュー履歴
- **Sharing Capabilities**: 現時点ではローカルアクセスのみ

## Future Vision

### Potential Enhancements

- **Knowledge Suggestion**: 分析設計の各セクション作成時に、過去の knowledge を自動サジェスト（次期開発予定）
- **Cross-project Knowledge**: 複数プロジェクト間でのドメイン知識共有
- **Analytics Dashboard**: 分析の傾向（テーマ別の仮説支持率、よく使われるデータソース等）の可視化
- **Collaboration**: 複数アナリストによる同時レビュー、コメントへの返信機能

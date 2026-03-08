# Test Design Document

## Overview

verification-design スペックのテスト設計。AnalysisDesign の4フィールド型付け（explanatory, metrics, chart, methodology）に対し、Unit → Integration → E2E の順でテストカバレッジを定義する。

テストコードは正（仕様）。実装コードのみを修正対象とする（TDD 原則）。

---

## Coverage Matrix

### REQ-1: ExplanatoryVariable の型付け

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-1.1 | role なし dict → role=covariate デフォルト適用 | Unit-01 | Integ-01 | - |
| AC-1.2 | 無効な role 値 → ValidationError | Unit-02 | - | - |
| AC-1.3 | YAML シリアライズで role が文字列保存 | Unit-03 | Integ-02 | - |
| AC-1.4 | MCP ツールで dict / ExplanatoryVariable 両方受付 | - | Integ-03, Integ-04 | - |

### REQ-2: Metrics の型付けとリスト化

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-2.1 | 単一 dict → [Metric] 自動変換 | Unit-04 | Integ-05 | - |
| AC-2.2 | list 形式 → 各要素 Metric 変換 | Unit-05 | - | - |
| AC-2.3 | 空 dict {} → 空リスト [] | Unit-06 | - | - |
| AC-2.4 | tier なし dict → tier=primary デフォルト | Unit-07 | - | - |
| AC-2.5 | MCP ツールで dict → list[Metric] 変換保存 | - | Integ-06 | - |

### REQ-3: Chart の Intent 駆動化

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-3.1 | intent なし + type=scatter → intent=correlation | Unit-08 | - | - |
| AC-3.2 | intent なし + type=table → intent=comparison | Unit-09 | - | - |
| AC-3.3 | intent なし + 未知 type → intent=distribution | Unit-10 | - | - |
| AC-3.4 | YAML シリアライズで intent と type 両方保存 | Unit-11 | Integ-07 | - |

### REQ-4: Methodology フィールドの追加

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-4.1 | methodology なし YAML → None | Unit-12 | Integ-08 | - |
| AC-4.2 | dict → Methodology 自動変換 | Unit-13 | - | - |
| AC-4.3 | method 空文字列 → ValidationError | Unit-14 | - | - |
| AC-4.4 | MCP update_design で methodology 保存 | - | Integ-09, Integ-11 | - |

### REQ-5: Frontend 型定義の同期

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-5.1 | TypeScript コンパイルエラーなし | - | - | E2E-01 |
| AC-5.2 | REST API レスポンスが型定義と一致 | - | Integ-10 | - |

### REQ-6: SKILL ドキュメントの更新

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-6.1 | SKILL.md に role/tier/intent 例あり | - | - | - |
| AC-6.2 | decide→methodology 導線が記載 | - | - | - |

**備考**: AC-6.1, AC-6.2 はドキュメントの内容確認であり、自動テストの対象外。手動レビューで検証する。

---

## Test Scenarios

### Unit Tests — `tests/test_design_models.py`（新規作成）

**ID プレフィックス凡例**: Unit-N = AC 対応テスト / Unit-EN = Edge case / Unit-MN = Migration robustness / Unit-RTN = Round-trip

#### StrEnum 検証

**Unit-E01**: VariableRole の全メンバー確認
```python
def test_variable_role_members():
    members = set(VariableRole.__members__.keys())
    assert members == {"treatment", "confounder", "covariate", "instrumental", "mediator"}
```

**Unit-E02**: MetricTier の全メンバー確認
```python
def test_metric_tier_members():
    members = set(MetricTier.__members__.keys())
    assert members == {"primary", "secondary", "guardrail"}
```

**Unit-E03**: ChartIntent の全メンバー確認
```python
def test_chart_intent_members():
    members = set(ChartIntent.__members__.keys())
    assert members == {"distribution", "correlation", "trend", "comparison"}
```

#### ExplanatoryVariable テスト

**Unit-01**: role なし dict からの coercion でデフォルト covariate が適用される（AC-1.1）
```python
def test_explanatory_variable_role_default_covariate():
    data = {"name": "x1", "description": "desc", "data_source": "src", "time_points": "2020"}
    var = ExplanatoryVariable(**data)
    assert var.role == VariableRole.covariate
```

**Unit-02**: 無効な role 値で ValidationError（AC-1.2）
```python
def test_explanatory_variable_invalid_role_raises():
    with pytest.raises(ValidationError):
        ExplanatoryVariable(name="x1", role="invalid_role")
```

**Unit-03**: model_dump で role が文字列として出力される（AC-1.3）
```python
def test_explanatory_variable_dump_role_as_string():
    var = ExplanatoryVariable(name="x1", role=VariableRole.treatment)
    dumped = var.model_dump(mode="json")
    assert dumped["role"] == "treatment"
    assert isinstance(dumped["role"], str)
```

**Unit-E04**: 有効な全 role 値での構築成功
```python
@pytest.mark.parametrize("role", list(VariableRole))
def test_explanatory_variable_accepts_all_valid_roles(role):
    var = ExplanatoryVariable(name="x1", role=role)
    assert var.role == role
```

#### Metric テスト

**Unit-04**: AnalysisDesign の metrics に単一 dict → [Metric] 変換（AC-2.1）
```python
def test_migrate_metrics_single_dict_to_list():
    data = _minimal_design_data(metrics={"target": "crime_rate", "aggregation": "mean"})
    design = AnalysisDesign(**data)
    assert isinstance(design.metrics, list)
    assert len(design.metrics) == 1
    assert design.metrics[0].target == "crime_rate"
```

**Unit-05**: metrics が list 形式の場合はそのまま変換（AC-2.2）
```python
def test_migrate_metrics_list_preserved():
    metrics_list = [
        {"target": "primary_metric", "tier": "primary"},
        {"target": "guardrail_metric", "tier": "guardrail"},
    ]
    data = _minimal_design_data(metrics=metrics_list)
    design = AnalysisDesign(**data)
    assert len(design.metrics) == 2
    assert design.metrics[0].tier == MetricTier.primary
    assert design.metrics[1].tier == MetricTier.guardrail
```

**Unit-06**: 空 dict {} → 空リスト []（AC-2.3）
```python
def test_migrate_metrics_empty_dict_to_empty_list():
    data = _minimal_design_data(metrics={})
    design = AnalysisDesign(**data)
    assert design.metrics == []
```

**Unit-07**: tier なし dict → tier=primary デフォルト（AC-2.4）
```python
def test_metric_tier_default_primary():
    metric = Metric(target="some_metric")
    assert metric.tier == MetricTier.primary
```

**Unit-E05**: metrics が None → 空リスト
```python
def test_migrate_metrics_none_to_empty_list():
    data = _minimal_design_data(metrics=None)
    design = AnalysisDesign(**data)
    assert design.metrics == []
```

**Unit-E06**: 無効な tier 値で ValidationError
```python
def test_metric_invalid_tier_raises():
    with pytest.raises(ValidationError):
        Metric(target="m1", tier="invalid_tier")
```

**Unit-E07**: metrics に target なし dict → ValidationError
```python
def test_metric_without_target_raises():
    with pytest.raises(ValidationError):
        Metric(tier="primary")  # target is required
```

#### ChartSpec テスト

**Unit-08**: intent なし + type=scatter → intent=correlation（AC-3.1）
```python
def test_chart_spec_infer_intent_scatter_to_correlation():
    spec = ChartSpec(**{"type": "scatter", "description": "test"})
    assert spec.intent == ChartIntent.correlation
```

**Unit-09**: intent なし + type=table → intent=comparison（AC-3.2）
```python
def test_chart_spec_infer_intent_table_to_comparison():
    spec = ChartSpec(**{"type": "table"})
    assert spec.intent == ChartIntent.comparison
```

**Unit-10**: intent なし + 未知 type → intent=distribution（AC-3.3）
```python
def test_chart_spec_infer_intent_unknown_type_to_distribution():
    spec = ChartSpec(**{"type": "unknown_chart"})
    assert spec.intent == ChartIntent.distribution
```

**Unit-11**: model_dump で intent と type 両方出力（AC-3.4）
```python
def test_chart_spec_dump_intent_and_type():
    spec = ChartSpec(intent=ChartIntent.trend, type="line", description="trend")
    dumped = spec.model_dump(mode="json")
    assert dumped["intent"] == "trend"
    assert dumped["type"] == "line"
```

**Unit-E08**: 全 type→intent マッピングの検証
```python
@pytest.mark.parametrize("chart_type,expected_intent", [
    ("scatter", "correlation"),
    ("heatmap", "correlation"),
    ("bar", "comparison"),
    ("table", "comparison"),
    ("histogram", "distribution"),
    ("box", "distribution"),
    ("line", "trend"),
    ("area", "trend"),
])
def test_chart_spec_infer_intent_all_mappings(chart_type, expected_intent):
    spec = ChartSpec(**{"type": chart_type})
    assert spec.intent == ChartIntent(expected_intent)
```

**Unit-E09**: intent 明示指定時は type からの推論を上書きしない
```python
def test_chart_spec_explicit_intent_preserved():
    spec = ChartSpec(**{"intent": "trend", "type": "scatter"})
    assert spec.intent == ChartIntent.trend  # explicit intent wins
```

**Unit-E10**: intent なし + type なし → distribution（デフォルト）
```python
def test_chart_spec_no_intent_no_type_defaults_distribution():
    spec = ChartSpec(**{})
    assert spec.intent == ChartIntent.distribution
```

#### Methodology テスト

**Unit-12**: methodology なし AnalysisDesign → None（AC-4.1）
```python
def test_analysis_design_methodology_default_none():
    data = _minimal_design_data()
    design = AnalysisDesign(**data)
    assert design.methodology is None
```

**Unit-13**: dict → Methodology 自動変換（AC-4.2）
```python
def test_methodology_from_dict():
    data = _minimal_design_data(
        methodology={"method": "CausalImpact", "package": "tfcausalimpact", "reason": "因果推論"}
    )
    design = AnalysisDesign(**data)
    assert design.methodology is not None
    assert design.methodology.method == "CausalImpact"
    assert design.methodology.package == "tfcausalimpact"
```

**Unit-14**: method 空文字列 → ValidationError（AC-4.3）
```python
def test_methodology_empty_method_raises():
    with pytest.raises(ValidationError):
        Methodology(method="", package="pkg")
```

**Unit-E11**: Methodology の package と reason はデフォルト空文字列
```python
def test_methodology_defaults():
    m = Methodology(method="OLS")
    assert m.package == ""
    assert m.reason == ""
```

#### Migration 堅牢性テスト（Codex レビュー追加）

**Unit-M01**: metrics migration の冪等性 — 既に list の metrics を再投入しても変化しない
```python
def test_migrate_metrics_idempotent():
    data = _minimal_design_data(metrics=[{"target": "y", "tier": "primary"}])
    design1 = AnalysisDesign(**data)
    dumped = design1.model_dump(mode="json")
    design2 = AnalysisDesign(**dumped)
    assert len(design2.metrics) == 1
    assert design2.metrics[0].target == "y"
```

**Unit-M02**: metrics list 内に不正要素（target なし dict）→ ValidationError
```python
def test_migrate_metrics_list_with_invalid_element_raises():
    data = _minimal_design_data(metrics=[{"tier": "primary"}])  # no target
    with pytest.raises(ValidationError):
        AnalysisDesign(**data)
```

**Unit-M03**: update 時に typed fields を更新しても他フィールドが壊れない
```python
def test_analysis_design_update_preserves_other_fields():
    data = _minimal_design_data(
        explanatory=[{"name": "x1", "role": "treatment"}],
        metrics=[{"target": "y"}],
        referenced_knowledge={"metrics": ["k1"]},
    )
    design = AnalysisDesign(**data)
    updated = design.model_copy(update={"methodology": Methodology(method="OLS")})
    assert updated.explanatory[0].role == VariableRole.treatment
    assert len(updated.metrics) == 1
    assert updated.referenced_knowledge == {"metrics": ["k1"]}
```

**Unit-M04**: YAML round-trip で metrics が常に canonical list 形式になる
```python
def test_yaml_roundtrip_metrics_canonical_form():
    # Legacy single dict input
    data = _minimal_design_data(metrics={"target": "y"})
    design = AnalysisDesign(**data)
    dumped = design.model_dump(mode="json")
    assert isinstance(dumped["metrics"], list)  # canonical form
    assert len(dumped["metrics"]) == 1
```

#### YAML ラウンドトリップテスト

**Unit-RT01**: 全フィールド指定の AnalysisDesign が model_dump → 再構築で一致
```python
def test_analysis_design_roundtrip_with_typed_fields():
    data = _minimal_design_data(
        explanatory=[{"name": "x1", "role": "treatment", "data_source": "src1"}],
        metrics=[{"target": "y", "tier": "primary"}],
        chart=[{"intent": "correlation", "type": "scatter", "x": "x1", "y": "y"}],
        methodology={"method": "DID", "package": "statsmodels"},
    )
    design = AnalysisDesign(**data)
    dumped = design.model_dump(mode="json")
    restored = AnalysisDesign(**dumped)
    assert restored.explanatory[0].role == VariableRole.treatment
    assert restored.metrics[0].tier == MetricTier.primary
    assert restored.chart[0].intent == ChartIntent.correlation
    assert restored.methodology.method == "DID"
```

**Unit-RT02**: レガシー形式（role/tier/intent なし）の dict からのラウンドトリップ
```python
def test_analysis_design_roundtrip_legacy_format():
    data = _minimal_design_data(
        explanatory=[{"name": "x1"}],
        metrics={"target": "y", "aggregation": "mean"},
        chart=[{"type": "scatter", "description": "test"}],
    )
    design = AnalysisDesign(**data)
    assert design.explanatory[0].role == VariableRole.covariate  # default
    assert len(design.metrics) == 1
    assert design.metrics[0].tier == MetricTier.primary  # default
    assert design.chart[0].intent == ChartIntent.correlation  # inferred from scatter

    dumped = design.model_dump(mode="json")
    restored = AnalysisDesign(**dumped)
    assert restored.explanatory[0].role == VariableRole.covariate
    assert restored.metrics[0].tier == MetricTier.primary
    assert restored.chart[0].intent == ChartIntent.correlation
```

#### ヘルパー関数

```python
def _minimal_design_data(**overrides) -> dict:
    """Create minimal valid AnalysisDesign data dict."""
    base = {
        "id": "TEST-H01",
        "title": "Test",
        "hypothesis_statement": "stmt",
        "hypothesis_background": "bg",
    }
    base.update(overrides)
    return base
```

---

### Backward Compatibility Tests — `tests/test_design_backward_compat.py`（新規作成、Codex レビュー追加）

後方互換テストを専用ファイルに分離する（移行完了後に縮小可能）。

**BC-01**: レガシー YAML（role/tier/intent/methodology なし）の全フィールド読み込み
```python
def test_legacy_yaml_full_backward_compat():
    """Legacy format with no typed fields loads correctly."""
    data = {
        "id": "LEGACY-H01", "title": "Legacy", "hypothesis_statement": "s",
        "hypothesis_background": "b",
        "metrics": {"target": "y", "aggregation": "mean"},
        "explanatory": [{"name": "x1", "data_source": "src"}],
        "chart": [{"type": "scatter", "description": "test"}],
    }
    design = AnalysisDesign(**data)
    assert design.explanatory[0].role == VariableRole.covariate
    assert len(design.metrics) == 1
    assert design.metrics[0].tier == MetricTier.primary
    assert design.chart[0].intent == ChartIntent.correlation
    assert design.methodology is None
```

**BC-02**: DesignService で update 時に legacy dict metrics → 正しく migration が効く
```python
def test_update_design_with_legacy_metrics_format(service):
    design = service.create_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
    )
    # Simulate passing legacy single-dict format through update
    updated = service.update_design(design.id, metrics=[{"target": "new_metric"}])
    assert len(updated.metrics) == 1
    assert updated.metrics[0].target == "new_metric"
```

**BC-03**: MCP ツールで無効な enum 値を渡したときのエラー応答
```python
def test_create_design_invalid_role_returns_error(initialized_server):
    result = await create_analysis_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
        explanatory=[{"name": "x1", "role": "invalid_role"}],
    )
    assert "error" in result
```

**BC-04**: REST API で無効な enum 値を渡したときの 422 応答
```python
def test_create_design_api_invalid_role_returns_422(client):
    resp = client.post("/api/designs", json={
        "title": "t", "hypothesis_statement": "s", "hypothesis_background": "b",
        "explanatory": [{"name": "x1", "role": "invalid_role"}],
    })
    assert resp.status_code in (400, 422)
```

---

### Integration Tests — 既存テストファイルへの追加

#### `tests/test_designs.py` への追加

**Integ-01**: DesignService.create_design で role なし explanatory → 保存後に role=covariate で読み込み（AC-1.1）
```python
def test_create_design_with_untyped_explanatory_gets_default_role(service):
    design = service.create_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
        explanatory=[{"name": "x1", "description": "d"}],
    )
    reloaded = service.get_design(design.id)
    assert reloaded.explanatory[0].role == VariableRole.covariate
```

**Integ-02**: DesignService で typed explanatory → YAML 保存 → 読み込みで role 維持（AC-1.3）
```python
def test_create_design_with_typed_explanatory_persists_role(service):
    design = service.create_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
        explanatory=[{"name": "x1", "role": "treatment"}],
    )
    reloaded = service.get_design(design.id)
    assert reloaded.explanatory[0].role == VariableRole.treatment
```

**Integ-05**: DesignService.create_design で legacy dict metrics → 保存後に list[Metric] で読み込み（AC-2.1）
```python
def test_create_design_with_legacy_dict_metrics_migrated(service):
    design = service.create_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
        metrics=[{"target": "y", "aggregation": "mean"}],
    )
    reloaded = service.get_design(design.id)
    assert isinstance(reloaded.metrics, list)
    assert len(reloaded.metrics) == 1
    assert reloaded.metrics[0].target == "y"
```

**Integ-07**: DesignService で chart with intent → YAML 保存 → 読み込みで intent 維持（AC-3.4）
```python
def test_create_design_with_typed_chart_persists_intent(service):
    design = service.create_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
        chart=[{"intent": "trend", "type": "line", "x": "time", "y": "value"}],
    )
    reloaded = service.get_design(design.id)
    assert reloaded.chart[0].intent == ChartIntent.trend
```

**Integ-08**: DesignService.create_design で methodology なし → None（AC-4.1）
```python
def test_create_design_without_methodology_is_none(service):
    design = service.create_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
    )
    assert design.methodology is None
```

**Integ-09**: DesignService.update_design で methodology を追加（AC-4.4）
```python
def test_update_design_with_methodology(service):
    design = service.create_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
    )
    updated = service.update_design(
        design.id, methodology={"method": "DID", "package": "statsmodels"},
    )
    assert updated.methodology.method == "DID"
    reloaded = service.get_design(design.id)
    assert reloaded.methodology.method == "DID"
```

#### `tests/test_server.py` への追加

**Integ-03**: MCP create_analysis_design で dict explanatory 受付（AC-1.4）
```python
def test_create_analysis_design_with_typed_explanatory(initialized_server):
    result = await create_analysis_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
        explanatory=[{"name": "x1", "role": "treatment"}],
    )
    assert "error" not in result
```

**Integ-04**: MCP update_analysis_design で typed explanatory 更新（AC-1.4 update パス）
```python
def test_update_analysis_design_with_typed_explanatory(initialized_server):
    # create then update explanatory with role field
    result = await update_analysis_design(
        design_id=design_id,
        explanatory=[{"name": "x1", "role": "treatment"}, {"name": "x2", "role": "confounder"}],
    )
    assert "error" not in result
```

**Integ-11**: MCP update_analysis_design で methodology 更新（AC-4.4 MCP パス）
```python
def test_update_analysis_design_with_methodology(initialized_server):
    # create then update with methodology
    result = await update_analysis_design(
        design_id=design_id,
        methodology={"method": "CausalImpact", "package": "tfcausalimpact"},
    )
    assert "error" not in result
```

**Integ-06**: MCP create_analysis_design で metrics dict → list 変換保存（AC-2.5）
```python
def test_create_analysis_design_with_metrics_list(initialized_server):
    result = await create_analysis_design(
        title="t", hypothesis_statement="s", hypothesis_background="b",
        metrics=[{"target": "y", "tier": "primary"}],
    )
    assert "error" not in result
```

#### `tests/test_web.py` への追加

**Integ-10**: REST API GET /api/designs/{id} のレスポンスが typed フィールドを含む（AC-5.2）
```python
def test_get_design_returns_typed_fields(client):
    # create design with typed fields
    resp = client.post("/api/designs", json={
        "title": "t", "hypothesis_statement": "s", "hypothesis_background": "b",
        "explanatory": [{"name": "x1", "role": "treatment"}],
        "metrics": [{"target": "y", "tier": "guardrail"}],
        "chart": [{"intent": "correlation", "type": "scatter"}],
        "methodology": {"method": "OLS"},
    })
    design_id = resp.json()["design"]["id"]
    resp = client.get(f"/api/designs/{design_id}")
    data = resp.json()
    assert data["explanatory"][0]["role"] == "treatment"
    assert data["metrics"][0]["tier"] == "guardrail"
    assert data["chart"][0]["intent"] == "correlation"
    assert data["methodology"]["method"] == "OLS"
```

---

### E2E Tests

**E2E-01**: フロントエンドビルド成功確認（AC-5.1）
```bash
cd frontend && npm run build
# TypeScript コンパイルエラーがなければ成功
```

既存の Playwright E2E テストが通ることの確認。WebUI コンポーネント変更はスコープ外のため、新規 E2E テストの追加は不要。

---

## Test File Structure

```
tests/
├── test_design_models.py          ← 新規: Unit-01〜M04, RT01〜RT02 (モデル単体 + migration 堅牢性)
├── test_design_backward_compat.py ← 新規: BC-01〜BC-04 (後方互換、移行完了後に縮小可能)
├── test_designs.py                ← 追加: Integ-01,02,05,07,08,09 (DesignService)
├── test_server.py                 ← 追加: Integ-03,04,06,11 (MCP ツール)
├── test_web.py                    ← 追加: Integ-10 (REST API)
└── conftest.py                    ← 変更なし
```

## Coverage Target

- **新規ファイル** (`test_design_models.py`): 全新規モデルの行カバレッジ 90% 以上
- **既存テスト**: 624 テストが全て通ること（リグレッションなし）
- **全体カバレッジ**: models/design.py の行カバレッジ 95% 以上

## Success Criteria

1. 全 Unit テスト（Unit-01〜M04, RT01〜RT02、計 30 テスト）が pass
2. 全 Backward Compat テスト（BC-01〜BC-04、計 4 テスト）が pass
3. 全 Integration テスト（Integ-01〜11、計 11 テスト）が pass
4. 既存 624 テストが全て pass（リグレッションなし）
5. フロントエンドビルド（`npm run build`）が成功
6. `uv run pytest --cov=src/insight_blueprint/models/design --cov-report=term-missing` で design.py のカバレッジ 95% 以上

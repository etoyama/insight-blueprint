# Test Design Document

## Overview

yaml-edit-resilience スペックのテスト設計。F1（extra フィールド保全）と F2（corrupt ファイル隔離）に対し、Unit → Integration の順でテストカバレッジを定義する。

テストコードは正（仕様）。実装コードのみを修正対象とする（TDD 原則）。

E2E テストは不要: 本 spec は model 層 + service 層 + API 層の変更であり、フロントエンド UI の変更はない。REST API の動作は Integration テストでカバーする。

**Codex レビュー反映**: `model_dump(mode="json")` を全 extra フィールドテストで明示使用（実運用が `mode="json"` 前提のため）。corrupt パターンを5種に拡充。`referenced_knowledge` merge との相互作用テスト追加。`extra="allow"` でも不正 enum は弾くことの確認テスト追加。

---

## Coverage Matrix

### REQ-1: Extra Field Preservation

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-1.1 | AnalysisDesign トップレベル extra が model_dump() に含まれる | Unit-01 | - | - |
| AC-1.2 | Metric の extra が nested で保持される | Unit-02 | - | - |
| AC-1.3 | update_design() 後に extra が YAML に保持される | Unit-03 | Integ-01 | - |
| AC-1.4 | ChartSpec の extra が保持される | Unit-04 | - | - |
| AC-1.5 | ExplanatoryVariable の extra が保持される | Unit-05 | - | - |
| AC-1.6 | Methodology の extra が保持される | Unit-06 | - | - |

### REQ-2: Corrupt File Isolation

| AC | 内容 | Unit | Integ | E2E |
|----|------|------|-------|-----|
| AC-2.1 | 正常3 + corrupt 1 で list_designs() が3件返す | Unit-07 | - | - |
| AC-2.2 | corrupt skip 時に warning ログ出力 | Unit-08 | - | - |
| AC-2.3 | 必須フィールド欠損ファイルを skip | Unit-09 | - | - |
| AC-2.4 | get_design() で corrupt → ValidationError raise | Unit-10 | - | - |
| AC-2.5 | REST GET /api/designs/{id} で corrupt → 422 | - | Integ-02 | - |
| AC-2.6 | status フィルタ + corrupt で正常ファイルのみ返却 | Unit-11 | - | - |

### 後方互換 + 相互作用 (Codex レビュー反映)

| 検証項目 | Unit | Integ | E2E |
|---------|------|-------|-----|
| _migrate_metrics が extra 存在下で正常動作 | Unit-12 | - | - |
| _infer_intent_from_type が extra 存在下で正常動作 | Unit-13 | - | - |
| referenced_knowledge merge 後に extra 保持 | Unit-14 | - | - |
| corrupt file パターン5種を parametrize でカバー | Unit-15 | - | - |
| model_dump(mode="json") で extra が正しくシリアライズ | Unit-01〜06 で明示 | - | - |
| extra="allow" でも不正 enum は ValidationError | Unit-16 | - | - |
| 既存 681 テストが全て pass | - | CI | - |

---

## Test Scenarios

### Unit Tests

#### Unit-01: AnalysisDesign top-level extra field preserved

```
File: tests/test_design_models.py
Pattern: test_analysis_design_extra_field_preserved_in_model_dump

Arrange: AnalysisDesign(**{...required fields..., "analyst_note": "important"})
Act: result = design.model_dump(mode="json")
Assert: result["analyst_note"] == "important"
```

#### Unit-02: Metric nested extra field preserved

```
File: tests/test_design_models.py
Pattern: test_metric_extra_field_preserved_in_model_dump

Arrange: AnalysisDesign(**{...required..., "metrics": [{"target": "rev", "note": "seasonal"}]})
Act: result = design.model_dump(mode="json")
Assert: result["metrics"][0]["note"] == "seasonal"
```

#### Unit-03: Extra fields survive update_design round-trip

```
File: tests/test_designs.py
Pattern: test_update_design_preserves_extra_fields

Arrange:
  - Create a design via create_design()
  - Manually add extra field to YAML file (write_yaml with analyst_note)
Act: service.update_design(id, title="new title")
Assert:
  - Updated YAML file contains analyst_note
  - Updated YAML file has title="new title"
```

#### Unit-04: ChartSpec extra field preserved

```
File: tests/test_design_models.py
Pattern: test_chart_spec_extra_field_preserved

Arrange: ChartSpec(intent="distribution", type="histogram", color="red")
Act: result = spec.model_dump(mode="json")
Assert: result["color"] == "red"
```

#### Unit-05: ExplanatoryVariable extra field preserved

```
File: tests/test_design_models.py
Pattern: test_explanatory_variable_extra_field_preserved

Arrange: ExplanatoryVariable(name="age", memo="check outliers")
Act: result = var.model_dump(mode="json")
Assert: result["memo"] == "check outliers"
```

#### Unit-06: Methodology extra field preserved

```
File: tests/test_design_models.py
Pattern: test_methodology_extra_field_preserved

Arrange: Methodology(method="t-test", package="scipy", ref_paper="doi:xxx")
Act: result = m.model_dump(mode="json")
Assert: result["ref_paper"] == "doi:xxx"
```

#### Unit-07: list_designs skips corrupt file and returns valid ones

```
File: tests/test_designs.py
Pattern: test_list_designs_skips_corrupt_file

Arrange:
  - Create 3 valid designs via create_design()
  - Write a corrupt YAML file (status: "INVALID_STATUS") directly
Act: designs = service.list_designs()
Assert: len(designs) == 3
```

#### Unit-08: list_designs logs warning for corrupt file

```
File: tests/test_designs.py
Pattern: test_list_designs_logs_warning_for_corrupt_file

Arrange:
  - Create 1 valid design
  - Write 1 corrupt YAML file
Act: service.list_designs() with caplog
Assert: "Skipping corrupt design file" in caplog.text
  AND corrupt filename in caplog.text
```

#### Unit-09: list_designs skips file with missing required field

```
File: tests/test_designs.py
Pattern: test_list_designs_skips_file_missing_required_field

Arrange: Write YAML with no "id" field
Act: designs = service.list_designs()
Assert: corrupt file not in results
```

#### Unit-10: get_design raises ValidationError for corrupt file

```
File: tests/test_designs.py
Pattern: test_get_design_raises_validation_error_for_corrupt_file

Arrange: Write corrupt YAML file with known design_id
Act/Assert: pytest.raises(ValidationError, match=...) for service.get_design(id)
```

#### Unit-11: list_designs with status filter skips corrupt

```
File: tests/test_designs.py
Pattern: test_list_designs_with_status_filter_skips_corrupt

Arrange:
  - Create 2 in_review + 1 analyzing designs
  - Write 1 corrupt YAML
Act: designs = service.list_designs(status=DesignStatus.in_review)
Assert: len(designs) == 2
```

#### Unit-12: _migrate_metrics works with extra fields present

```
File: tests/test_design_models.py
Pattern: test_migrate_metrics_preserves_extra_fields

Arrange: AnalysisDesign(**{...required..., "metrics": {"target": "x"}, "custom": "keep"})
Act: result = design.model_dump(mode="json")
Assert:
  - result["metrics"] == [{"target": "x", "tier": "primary", ...}]  # migrated
  - result["custom"] == "keep"  # extra preserved
```

#### Unit-13: _infer_intent_from_type works with extra fields present

```
File: tests/test_design_models.py
Pattern: test_infer_intent_preserves_extra_fields_on_chart

Arrange: ChartSpec(**{"type": "scatter", "annotation": "check R²"})
Act: result = spec.model_dump(mode="json")
Assert:
  - result["intent"] == "correlation"  # inferred
  - result["annotation"] == "check R²"  # extra preserved
```

#### Unit-14: referenced_knowledge merge preserves extra fields (Codex recommended)

```
File: tests/test_designs.py
Pattern: test_update_design_referenced_knowledge_merge_preserves_extras

Arrange:
  - Create a design via create_design()
  - Manually add extra field "analyst_note" to YAML
Act: service.update_design(id, referenced_knowledge={"section": ["new_key"]})
Assert:
  - YAML file contains analyst_note (extra preserved)
  - referenced_knowledge is merged (not replaced)
```

#### Unit-15: list_designs skips all 5 corruption patterns (Codex recommended, parametrize)

```
File: tests/test_designs.py
Pattern: test_list_designs_skips_corrupt_patterns (parametrized)

Parameters:
  - yaml_syntax_error: "id: test\n  bad indent: [unclosed"
  - non_dict_root: "- item1\n- item2"  (list instead of dict)
  - missing_required: {"theme_id": "X"}  (no id, no title)
  - invalid_enum: {"id": "X-H01", "title": "t", ...full..., "status": "BOGUS"}
  - invalid_nested_enum: {"id": "X-H01", ...full..., "metrics": [{"target": "x", "tier": "BOGUS"}]}

Arrange: Create 1 valid design + write 1 corrupt file per parameter
Act: service.list_designs()
Assert: len(designs) == 1 for each case
  AND warning log contains filename
```

#### Unit-16: extra="allow" still rejects invalid enum values (Codex recommended)

```
File: tests/test_design_models.py
Pattern: test_extra_allow_still_rejects_invalid_enum

Arrange/Act/Assert:
  - AnalysisDesign(**{...required..., "status": "BOGUS"}) → raises ValidationError
  - Metric(target="x", tier="BOGUS") → raises ValidationError
  - ChartSpec(intent="BOGUS") → raises ValidationError
  - ExplanatoryVariable(name="x", role="BOGUS") → raises ValidationError
```

### Integration Tests

#### Integ-01: MCP update_design preserves extra fields in YAML

```
File: tests/test_designs.py
Pattern: test_update_design_extra_fields_survive_yaml_round_trip

Arrange:
  - create_design() to create YAML
  - Read YAML, add extra fields at top-level AND in metrics, write back
Act: update_design(id, title="updated")
Assert:
  - Read YAML after update
  - Top-level extra field present
  - Metrics-level extra field present
  - title == "updated"
```

#### Integ-02: REST API returns 422 for corrupt design

```
File: tests/test_web.py
Pattern: test_get_design_corrupt_returns_422

Arrange: Write corrupt YAML with known design_id
Act: GET /api/designs/{id}
Assert:
  - response.status_code == 422
  - response.json()["error"] contains "validation error"
```

---

## Test File Structure

| Test File | Target | Tests Added |
|-----------|--------|-------------|
| `tests/test_design_models.py` | models/design.py (F1) | Unit-01〜06, Unit-12〜13, Unit-16 |
| `tests/test_designs.py` | core/designs.py (F1+F2) | Unit-03, Unit-07〜11, Unit-14〜15, Integ-01 |
| `tests/test_web.py` | web.py (F2) | Integ-02 |

---

## Coverage Target

- **Unit test coverage**: models/design.py の `ConfigDict(extra="allow")` 関連パスを 100% カバー
- **Service layer coverage**: `list_designs()` の try/except パスを 100% カバー（正常/corrupt/空ファイル）
- **API layer coverage**: `ValidationError → 422` のレスポンスマッピングをカバー
- **Backward compatibility**: 既存 681 テスト全 pass が CI で確認されること

## Success Criteria

1. 上記 Unit-01〜16 + Integ-01〜02 の全18テストが pass（Unit-15 は parametrize 5ケース）
2. 既存テストにリグレッションなし
3. `pytest --cov=src/insight_blueprint/models/design --cov-report=term-missing` で design.py のカバレッジが 100% 維持

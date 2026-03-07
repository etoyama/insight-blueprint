# Design: UI Navigation Restructuring

## Steering Document Alignment

| Requirement | Design Response |
|-------------|----------------|
| REQ-1: Remove Rules/History tabs | App.tsx reduced to 2-tab layout; VALID_TABS narrowed; unknown tab values fallback to `designs` |
| REQ-2: Unified Domain Knowledge in Catalog | KnowledgeSection switches data source from `GET /api/catalog/knowledge` to `GET /api/rules/context`; adapter function extracts `knowledge_entries` |
| REQ-3: Caution Search in Catalog | New `CautionSearchSection.tsx` component added to CatalogPage, following existing section pattern |
| REQ-4: Remove Extract Knowledge | KnowledgePanel deleted; DesignDetail sub-tabs reduced to Overview + History |
| REQ-5: Auto-finding visibility | STATUS_GUIDE text updated for terminal statuses; no Knowledge tab references |
| REQ-6: TypeScript type fixes | `finding` added to KnowledgeCategory; `referenced_knowledge` added to Design interface |

---

## Architecture

### Before

```
App.tsx
├── [Designs]  → DesignsPage → DesignDetail
│                                ├── Overview (OverviewPanel)
│                                ├── History (ReviewHistoryPanel)
│                                └── Knowledge (KnowledgePanel) ← REMOVE
├── [Catalog]  → CatalogPage
│                 ├── SearchSection
│                 ├── SourceListSection
│                 ├── SchemaSection
│                 └── KnowledgeSection (catalog-only)
├── [Rules]    → RulesPage ← REMOVE
│                 ├── Sources (duplicate of Catalog)
│                 ├── Domain Knowledge (merged)
│                 ├── Rules (raw JSON)
│                 └── Caution Search
└── [History]  → HistoryPage ← REMOVE
```

### After

```
App.tsx
├── [Designs]  → DesignsPage → DesignDetail
│                                ├── Overview (OverviewPanel)
│                                └── History (ReviewHistoryPanel)
└── [Catalog]  → CatalogPage
                  ├── SearchSection
                  ├── SourceListSection
                  ├── SchemaSection
                  ├── KnowledgeSection (unified: catalog + findings)  ← MODIFIED
                  └── CautionSearchSection                            ← NEW
```

### Data Flow

```
KnowledgeSection
  → GET /api/rules/context
  → adapter: getUnifiedKnowledge(signal) → KnowledgeEntry[]
  → extracts knowledge_entries field from response

CautionSearchSection
  → GET /api/rules/cautions?table_names=...
  → existing getCautions() function in client.ts (no change)
```

---

## Data Model

No backend data model changes. Frontend type changes only:

| Type | Change | Description |
|------|--------|-------------|
| `KnowledgeCategory` | Add `"finding"` | Align with backend `KnowledgeCategory.finding` enum value |
| `Design` | Add `referenced_knowledge: Record<string, unknown>[] \| null` | Align with backend `AnalysisDesign.referenced_knowledge` field |

---

## API Design

No new API endpoints. Existing endpoints consumed differently:

| Endpoint | Current Consumer | New Consumer |
|----------|-----------------|--------------|
| `GET /api/rules/context` | RulesPage (to be deleted) | KnowledgeSection (via adapter) |
| `GET /api/rules/cautions?table_names=...` | RulesPage (to be deleted) | CautionSearchSection |
| `GET /api/catalog/knowledge` | KnowledgeSection | No longer used by frontend (endpoint remains) |
| `POST /api/designs/{id}/knowledge` | KnowledgePanel (to be deleted) | No frontend consumer (endpoint remains for MCP) |

### New adapter function in client.ts

```typescript
export async function getUnifiedKnowledge(
  signal?: AbortSignal,
): Promise<{ entries: KnowledgeEntry[]; count: number }> {
  const context = await getRulesContext(signal);
  return {
    entries: context.knowledge_entries,
    count: context.total_knowledge,
  };
}
```

Design rationale: `getRulesContext()` already exists in client.ts and fetches the merged dataset. A thin adapter avoids modifying the existing function while giving KnowledgeSection a clean interface. Over-fetching (sources, rules fields are discarded) is acceptable given the small data volume.

---

## Components and Interfaces

| Component | Responsibility | Status | Dependencies |
|-----------|---------------|--------|--------------|
| `App.tsx` | 2-tab layout, URL routing | MODIFY | DesignsPage, CatalogPage |
| `CatalogPage.tsx` | Catalog page composition | MODIFY | SearchSection, SourceListSection, SchemaSection, KnowledgeSection, CautionSearchSection |
| `KnowledgeSection.tsx` | Unified domain knowledge table | MODIFY | `getUnifiedKnowledge()` adapter |
| `CautionSearchSection.tsx` | Caution search by table name | CREATE | `getCautions()` in client.ts |
| `DesignDetail.tsx` | 2 sub-tab layout | MODIFY | OverviewPanel, ReviewHistoryPanel |
| `OverviewPanel.tsx` | Workflow guide text | MODIFY | (self-contained) |
| `api/client.ts` | API client functions | MODIFY | (remove extractKnowledge/saveKnowledge, add getUnifiedKnowledge) |
| `types/api.ts` | TypeScript type definitions | MODIFY | (add finding, referenced_knowledge) |
| `RulesPage.tsx` | Rules tab page | DELETE | - |
| `HistoryPage.tsx` | History tab page | DELETE | - |
| `KnowledgePanel.tsx` | Extract Knowledge UI | DELETE | - |

### CautionSearchSection component design

Extracted from RulesPage's Caution Search card. Follows the existing section pattern (self-contained data fetching, own error handling, own loading state):

```typescript
// frontend/src/pages/catalog/CautionSearchSection.tsx
export function CautionSearchSection() {
  // State: tableNames, cautions, loading, error, searched
  // Uses existing getCautions() from client.ts
  // Renders: Input + Search button + DataTable with CAUTION_COLUMNS
}
```

CAUTION_COLUMNS definition moves from RulesPage to either CautionSearchSection or constants.tsx.

### URL backward compatibility

Per Codex review recommendation: `getTabFromUrl()` in App.tsx maps unknown tab values (including `rules`, `history`) to `designs`. This is already the behavior of the current fallback logic — no special redirect handling needed.

---

## Code Reuse Analysis

| Existing Asset | Reuse Strategy | Modification Needed |
|---------------|----------------|-------------------|
| `getRulesContext()` in client.ts | Reuse as data source for KnowledgeSection | None (wrap with adapter) |
| `getCautions()` in client.ts | Reuse for CautionSearchSection | None |
| `CAUTION_COLUMNS` in RulesPage | Extract to CautionSearchSection | Move, no logic change |
| `KNOWLEDGE_COLUMNS` in constants.tsx | Reuse in KnowledgeSection | None |
| `ReviewHistoryPanel` | Continue use in DesignDetail History tab | None (NOT deleted) |
| `DataTable` component | Reuse in CautionSearchSection | None |
| `EmptyState` component | Reuse in CautionSearchSection | None |
| `ErrorBanner` component | Reuse in CautionSearchSection | None |

---

## Error Handling

| Error Category | Strategy | User Message |
|---------------|----------|--------------|
| KnowledgeSection API failure | Show ErrorBanner, no retry | "Failed to load domain knowledge" |
| CautionSearchSection API failure | Show ErrorBanner inline | Error message from API response |
| CautionSearch empty result | Show EmptyState | "No matching cautions found" |
| Invalid tab in URL | Fallback to `designs` | (silent redirect, no error) |

No new error categories. All patterns reuse existing ErrorBanner/EmptyState components.

---

## Testing Strategy

| Level | Scope | Tool | Coverage Target |
|-------|-------|------|----------------|
| Unit | TypeScript types | TypeScript compiler | 100% type safety |
| E2E | Tab navigation, Catalog sections, Design detail | Playwright | All acceptance criteria |
| Backend regression | Existing Python test suite | pytest | 604 tests pass, 0 modified |

### E2E test changes (per Codex review)

| Action | Tests | Rationale |
|--------|-------|-----------|
| **DELETE** | `#9` (extract knowledge), `#10` (save knowledge) in design-detail.spec.ts | Feature A removed |
| **DELETE** | `#30` (rules tab empty state) in cross-tab.spec.ts | Rules tab removed |
| **UPDATE** | Tab Restructuring test in design-detail.spec.ts | Assert 2 sub-tabs (Overview, History) instead of 3 |
| **UPDATE** | `#27` (cross-tab navigation) in cross-tab.spec.ts | Remove rules/history tab assertions |
| **UPDATE** | smoke.spec.ts | Remove knowledge tab assertion; verify 2 top-level tabs |
| **UPDATE** | rules.spec.ts `#17` | Convert to catalog integration test verifying Domain Knowledge + Caution Search in Catalog tab |
| **KEEP** | catalog.spec.ts `#16` (knowledge list) | Update mock to use unified endpoint if needed |
| **ADD** | 1 regression test | Assert Rules/History tabs do NOT exist in top-level navigation |

### E2E fixture changes

| File | Changes |
|------|---------|
| `api-routes.ts` | Remove `mockExtractKnowledge`, `mockSaveKnowledge`; add `mockUnifiedKnowledge` if needed |
| `mock-data.ts` | No changes needed (makeKnowledgeEntry, makeRulesContext remain) |

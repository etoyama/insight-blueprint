# Requirements: UI Navigation Restructuring

## Introduction

insight-blueprint の WebUI ダッシュボードにおけるトップレベルナビゲーション（4タブ: Designs / Catalog / Rules / History）を、ユーザーの実際の利用動線に合わせて再構成する。同時に、Design 詳細ページの Extract Knowledge 機能（feature A）を削除し、auto-finding（feature B）と knowledge suggestion（feature C）の可視性を改善する。

### Alignment with Product Vision

- **Claude Code First 原則**: WebUI は閲覧・レビュー用の補助インターフェース。ユーザーが実際に使う動線のみを残し、MCP 側で十分な機能は UI から削除する
- **知識の自動蓄積**: 手動の Extract Knowledge（feature A）を廃止し、自動抽出（feature B）に一本化することで、手動の記録作業を最小化する product principle に沿う
- **Knowledge 蓄積率の向上**: auto-finding の結果がユーザーに見えるようにすることで、知見蓄積の信頼感を高める

---

## Requirements

### REQ-1: Remove Rules and History top-level tabs

**User Story**: As a data analyst, I want the dashboard to show only Designs and Catalog tabs, so that I can quickly access the two views I actually use without navigating through irrelevant tabs.

**Functional Requirements**:
- FR-1.1: Top-level navigation SHALL consist of exactly 2 tabs: Designs and Catalog
- FR-1.2: Rules tab SHALL be removed from `App.tsx`
- FR-1.3: History tab SHALL be removed from `App.tsx`
- FR-1.4: URL routing (`?tab=`) SHALL support only `designs` and `catalog` values; any other value SHALL default to `designs`
- FR-1.5: `RulesPage.tsx` component SHALL be deleted
- FR-1.6: `HistoryPage.tsx` component SHALL be deleted

**Acceptance Criteria**:
- AC-1.1: Given the dashboard is loaded, when the user views the navigation, then only "Designs" and "Catalog" tabs are visible
- AC-1.2: Given the URL contains `?tab=rules` or `?tab=history`, when the page loads, then the active tab defaults to "Designs"
- AC-1.3: Given the `RulesPage.tsx` and `HistoryPage.tsx` files, when the codebase is checked, then they no longer exist

### REQ-2: Integrate Domain Knowledge into Catalog tab

**User Story**: As a data analyst, I want to see all domain knowledge (including auto-extracted findings) in the Catalog tab, so that I can review accumulated knowledge alongside the data sources it relates to.

**Functional Requirements**:
- FR-2.1: Catalog tab SHALL display a unified Domain Knowledge section that includes both catalog-registered knowledge entries AND extracted findings from `extracted_knowledge.yaml`
- FR-2.2: The unified knowledge list SHALL use the `get_project_context()` API (or equivalent) to fetch the merged dataset, replacing the current `getKnowledgeList()` call that only returns catalog entries
- FR-2.3: The knowledge table SHALL display the `category` column, which includes the `finding` value for auto-extracted entries
- FR-2.4: The `KnowledgeCategory` TypeScript type SHALL include `"finding"` as a valid value

**Acceptance Criteria**:
- AC-2.1: Given a design has reached terminal status (supported/rejected/inconclusive), when the user views the Catalog tab's Domain Knowledge section, then the auto-extracted finding entry is visible in the list
- AC-2.2: Given knowledge entries exist with category `finding`, when the knowledge table renders, then the category badge displays "finding"
- AC-2.3: Given both catalog-registered and extracted knowledge entries exist, when the Domain Knowledge section loads, then all entries are shown in a single unified table

### REQ-3: Integrate Caution Search into Catalog tab

**User Story**: As a data analyst, I want to search for cautions by table name within the Catalog tab, so that I can check data handling notes while browsing data sources.

**Functional Requirements**:
- FR-3.1: Catalog tab SHALL include a Caution Search section with a text input for comma-separated table names and a Search button
- FR-3.2: Caution Search SHALL call the existing `/api/rules/cautions` endpoint
- FR-3.3: Search results SHALL display in a table with title, content, category, importance, and affects_columns columns

**Acceptance Criteria**:
- AC-3.1: Given the user is on the Catalog tab, when they enter a table name and click Search, then matching caution entries are displayed
- AC-3.2: Given no matching cautions exist for the entered table name, when the search completes, then an empty state message is shown

### REQ-4: Remove Extract Knowledge feature (feature A) from Design detail

**User Story**: As a data analyst, I want the Design detail page to not show a confusing Extract Knowledge button, so that I am not confused by a feature that requires undocumented annotation conventions.

**Functional Requirements**:
- FR-4.1: Design detail sub-tabs SHALL consist of exactly 2 tabs: Overview and History
- FR-4.2: Knowledge sub-tab SHALL be removed from `DesignDetail.tsx`
- FR-4.3: `KnowledgePanel.tsx` component SHALL be deleted
- FR-4.4: `extractKnowledge()` and `saveKnowledge()` functions SHALL be removed from `client.ts`
- FR-4.5: The REST API endpoint `POST /api/designs/{design_id}/knowledge` SHALL be retained (used by MCP tools indirectly); only the frontend consumer is removed

**Acceptance Criteria**:
- AC-4.1: Given a design detail page is open, when the user views the sub-tabs, then only "Overview" and "History" tabs are visible
- AC-4.2: Given the frontend codebase, when checked, then `KnowledgePanel.tsx` does not exist
- AC-4.3: Given the frontend codebase, when checked, then `extractKnowledge` and `saveKnowledge` are not exported from `client.ts`

### REQ-5: Improve auto-finding visibility (feature B)

**User Story**: As a data analyst, I want to know that domain knowledge is automatically recorded when a design reaches a terminal status, so that I trust the system is capturing analysis outcomes without manual effort.

**Functional Requirements**:
- FR-5.1: The workflow guide for terminal statuses (supported, rejected, inconclusive) in `OverviewPanel.tsx` SHALL inform the user that a finding has been automatically recorded
- FR-5.2: The guide text SHALL NOT reference the removed Knowledge tab

**Acceptance Criteria**:
- AC-5.1: Given a design with status `supported`, when the Overview panel renders, then the workflow guide mentions automatic finding recording and does not mention "Knowledge tab"
- AC-5.2: Given a design with status `rejected`, when the Overview panel renders, then the workflow guide mentions automatic finding recording and does not mention "Knowledge tab"
- AC-5.3: Given a design with status `inconclusive`, when the Overview panel renders, then the workflow guide mentions automatic finding recording and does not mention "Knowledge tab"

### REQ-6: Fix frontend type definitions

**User Story**: As a developer, I want the TypeScript type definitions to accurately reflect the backend data model, so that type safety is maintained.

**Functional Requirements**:
- FR-6.1: The `Design` interface in `api.ts` SHALL include `referenced_knowledge: Record<string, unknown>[] | null`
- FR-6.2: The `KnowledgeCategory` type in `api.ts` SHALL include `"finding"`

**Acceptance Criteria**:
- AC-6.1: Given the `Design` interface, when inspected, then `referenced_knowledge` field is present with correct type
- AC-6.2: Given the `KnowledgeCategory` type, when inspected, then `"finding"` is a valid value

---

## Non-Functional Requirements

### Performance
- NFR-P1: Catalog tab load time SHALL remain under 500ms with the added Domain Knowledge and Caution Search sections (no additional API calls beyond existing endpoints)

### Security
- NFR-S1: No new security considerations. Existing local-access-only model is unchanged.

### Scalability
- NFR-SC1: No new scalability considerations. Knowledge entry count is bounded by the same limits as before.

### Reliability
- NFR-R1: Backend REST API endpoints (`/api/rules/context`, `/api/rules/cautions`) and MCP tools SHALL remain unchanged and fully functional
- NFR-R2: All existing Python tests (604) SHALL continue to pass without modification

### Maintainability
- NFR-M1: Deleted frontend files SHALL have their E2E test coverage updated or removed accordingly
- NFR-M2: Frontend component count SHALL decrease (net deletion of RulesPage, HistoryPage, KnowledgePanel)
- NFR-M3: Steering document `product.md` and `structure.md` SHALL be updated to reflect 2-tab structure after implementation

---

## Out of Scope

- Backend code changes (Python): no modifications to `rules.py`, `reviews.py`, `web.py`, `server.py`, or any MCP tools
- Removal of REST API endpoints (`/api/rules/context`, `/api/rules/cautions`, `POST /api/designs/{id}/knowledge`): these remain for MCP and potential future use
- Removal of MCP tools (`extract_domain_knowledge`, `save_extracted_knowledge`, `get_project_context`, `suggest_cautions`): these remain as-is
- Adding new UI features (e.g., filters, sorting controls to Designs page)
- Redesigning the Catalog page layout beyond the additions specified
- Steering document updates (deferred to post-implementation)

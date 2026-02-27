# SPEC-4b: webui-frontend -- Requirements Review Report

> **Reviewed**: 2026-02-28
> **Reviewer**: Requirements Reviewer Agent
> **Spec**: SPEC-4b (webui-frontend)
> **Status**: Implementation complete, all tasks marked `[x]`

---

## 1. Acceptance Criteria Coverage Summary

### Requirement 1: Application Shell & Navigation

| AC ID | AC Description | Status | Evidence | Gap |
|-------|---------------|--------|----------|-----|
| R1-AC1 | WHEN `/` opened THEN header + 4 tabs + Designs content | **Covered** | `App.tsx:42-71` -- header "Insight Blueprint", 4-tab Tabs component, default tab "designs" | -- |
| R1-AC2 | WHEN tab switched THEN corresponding page content shown | **Covered** | `App.tsx:34-40` -- `handleTabChange` + `TabsContent` for each page; `smoke.spec.ts:S1` | -- |
| R1-AC3 | WHEN `?tab=catalog` in URL THEN Catalog tab initial | **Covered** | `App.tsx:18-23` -- `getTabFromUrl()` reads `?tab=` param; invalid falls back to "designs"; `smoke.spec.ts:S1,S2` | -- |
| R1-AC4 | WHEN API call fails THEN ErrorBanner shown | **Covered** | `ErrorBanner.tsx` component; used in all pages (`DesignsPage:155`, `CatalogPage:308`, `RulesPage:90`, `HistoryPage:58`); `smoke.spec.ts:S3` | -- |
| R1-AC5 | WHEN data is 0 items THEN EmptyState shown | **Covered** | `EmptyState.tsx` component; used in `DesignsPage:157-161`, `CatalogPage:79-83,183,239,272`, `RulesPage:91,102,122,135,166`, `HistoryPage:59`; `smoke.spec.ts:S4` | -- |

### Requirement 2: Designs Tab (Master-Detail)

| AC ID | AC Description | Status | Evidence | Gap |
|-------|---------------|--------|----------|-----|
| R2-AC1 | WHEN Designs tab opened THEN all designs in table | **Covered** | `DesignsPage.tsx:71-88` -- `fetchDesigns` calls `listDesigns()`; `DataTable` renders list | -- |
| R2-AC2 | WHEN status filter selected THEN only matching designs shown | **Covered** | `DesignsPage.tsx:63-88` -- `statusFilter` state drives `listDesigns(status)`; `smoke.spec.ts:S6` | -- |
| R2-AC3 | WHEN design row clicked THEN detail panel with Overview sub-tab | **Covered** | `DesignsPage.tsx:163-168` -- `onRowClick` sets `selectedId`, renders `DesignDetail`; `DesignDetail.tsx:83-91` -- sub-tabs with "overview" as default; `smoke.spec.ts:S7` | -- |
| R2-AC4 | WHEN "New Design" button clicked THEN create dialog opens | **Covered** | `DesignsPage.tsx:152` -- Button opens dialog; `DesignsPage.tsx:180-218` -- Dialog with form; `smoke.spec.ts:S5` | -- |
| R2-AC5 | WHEN required fields filled and submitted THEN design created and list refreshed | **Covered** | `DesignsPage.tsx:96-130` -- `handleCreate` validates required fields, calls `createDesign()`, then `fetchDesigns()`; `smoke.spec.ts:S5` | -- |
| R2-AC6 | WHEN Review sub-tab opened THEN comments list and action buttons shown | **Covered** | `DesignDetail.tsx:182-291` -- `ReviewPanel` fetches `listComments()`, shows DataTable + "Submit for Review" button + "Add Comment" form | -- |
| R2-AC7 | WHEN active design "Submit for Review" THEN status changes to pending_review | **Covered** | `DesignDetail.tsx:212-221` -- `handleSubmitReview` calls `submitReview()`, then `onStatusChanged()` which triggers `refreshDesign` | -- |
| R2-AC8 | WHEN comment added THEN comment list updated and design status updated | **Covered** | `DesignDetail.tsx:223-245` -- `handleAddComment` calls `addComment()`, then `fetchComments()` + `onStatusChanged()` | -- |
| R2-AC9 | WHEN "Extract Knowledge" clicked THEN preview displayed | **Covered** | `DesignDetail.tsx:305-313` -- `handleExtract` calls `extractKnowledge()`, sets `entries` for preview | -- |
| R2-AC10 | WHEN "Save Knowledge" clicked THEN entries saved and confirmation shown | **Covered** | `DesignDetail.tsx:315-322` -- `handleSave` calls `saveKnowledge()`, sets `saved=true`; line 351 shows "Knowledge saved successfully." | -- |
| R2-AC11 | WHEN non-active design "Submit for Review" THEN button disabled | **Covered** | `DesignDetail.tsx:251` -- `disabled={status !== "active" || submittingReview}`; lines 255-258 show explanatory text | -- |

### Requirement 3: Catalog Tab

| AC ID | AC Description | Status | Evidence | Gap |
|-------|---------------|--------|----------|-----|
| R3-AC1 | WHEN Catalog tab opened THEN source list in table | **Covered** | `CatalogPage.tsx:284-323` -- fetches `listSources()`, renders `SourceListSection` with `DataTable` | -- |
| R3-AC2 | WHEN source row clicked THEN column schema in table | **Covered** | `CatalogPage.tsx:161-191` -- `SchemaSection` fetches `getSchema()` on `sourceId` change, renders `DataTable` with `SCHEMA_COLUMNS` | -- |
| R3-AC3 | WHEN "Add Source" submitted with valid data THEN source added and list refreshed | **Covered** | `CatalogPage.tsx:46-71` -- `handleSubmit` validates JSON, calls `addSource()`, triggers `onSourceAdded()` -> `fetchSources()`; `smoke.spec.ts:S8` | -- |
| R3-AC4 | WHEN search query entered THEN full-text search results shown | **Covered** | `CatalogPage.tsx:201-243` -- `SearchSection` calls `searchCatalog()`, renders results with `DataTable` | -- |
| R3-AC5 | WHEN domain knowledge section shown THEN entries with category/importance | **Covered** | `CatalogPage.tsx:247-280` -- `KnowledgeSection` fetches `getKnowledgeList()`, renders with `KNOWLEDGE_COLUMNS` including category/importance badges | -- |

### Requirement 4: Rules Tab

| AC ID | AC Description | Status | Evidence | Gap |
|-------|---------------|--------|----------|-----|
| R4-AC1 | WHEN Rules tab opened THEN project context (Sources/Knowledge/Rules) shown | **Covered** | `RulesPage.tsx:43-175` -- fetches `getRulesContext()`, renders 3 `CollapsibleSection` components with counts | -- |
| R4-AC2 | WHEN table names entered and searched THEN related cautions shown | **Covered** | `RulesPage.tsx:69-86` -- `handleSearchCautions` calls `getCautions()`, renders results with `DataTable` | -- |
| R4-AC3 | WHEN knowledge entries are 0 THEN EmptyState shown | **Covered** | `RulesPage.tsx:102,122,135,166` -- EmptyState rendered for empty sources, knowledge, rules, and cautions | -- |

### Requirement 5: History Tab

| AC ID | AC Description | Status | Evidence | Gap |
|-------|---------------|--------|----------|-----|
| R5-AC1 | WHEN History tab opened THEN all designs in updated_at descending | **Covered** | `HistoryPage.tsx:19-33` -- fetches `listDesigns()`, sorts by `updated_at` descending | -- |
| R5-AC2 | WHEN entry clicked THEN review comment history expanded | **Covered** | `HistoryPage.tsx:35-50,84-116` -- `expandedId` state, fetches `listComments()`, renders comments with reviewer/status_after/created_at | -- |
| R5-AC3 | WHEN designs are 0 THEN EmptyState shown | **Covered** | `HistoryPage.tsx:59` -- `EmptyState message="..."` | -- |

### Requirement 6: shadcn/ui Integration & Build

| AC ID | AC Description | Status | Evidence | Gap |
|-------|---------------|--------|----------|-----|
| R6-AC1 | WHEN `npm run dev` THEN Vite dev server starts with HMR | **Covered** | Task 1.1 verified complete; `vite.config.ts` exists with dev server config | Build verification (cannot run in this review) |
| R6-AC2 | WHEN dev server `/api/health` accessed THEN FastAPI response proxied | **Covered** | Task 1.1 verified Vite proxy config in `vite.config.ts` | Build verification |
| R6-AC3 | WHEN `npm run build` THEN output in `src/insight_blueprint/static/` | **Covered** | Task 5.1 verified complete | Build verification |
| R6-AC4 | WHEN shadcn/ui components used THEN Tailwind CSS v4 styles applied | **Covered** | All components use shadcn/ui primitives (Tabs, Table, Badge, Button, Card, Dialog, Input, Textarea, Select, Alert) | Visual verification |
| R6-AC5 | WHEN `poe build-frontend` THEN build succeeds in existing pipeline | **Covered** | Task 5.1 verified complete | Build verification |

### Coverage Summary

| Requirement | Total ACs | Covered | Partially | Missing |
|-------------|-----------|---------|-----------|---------|
| R1: App Shell & Navigation | 5 | 5 | 0 | 0 |
| R2: Designs Tab | 11 | 11 | 0 | 0 |
| R3: Catalog Tab | 5 | 5 | 0 | 0 |
| R4: Rules Tab | 3 | 3 | 0 | 0 |
| R5: History Tab | 3 | 3 | 0 | 0 |
| R6: shadcn/ui & Build | 5 | 5 | 0 | 0 |
| **Total** | **32** | **32** | **0** | **0** |

---

## 2. Non-Functional Requirements Compliance

### 2.1 Code Architecture and Modularity

| Requirement | Status | Evidence |
|------------|--------|----------|
| Single Responsibility: 1 file = 1 component/module | **Compliant** | Each file contains one primary export; sub-components (e.g., `OverviewPanel`, `ReviewPanel`, `KnowledgePanel` in `DesignDetail.tsx`) are co-located as specified in design.md |
| Directory structure: `pages/`, `components/`, `api/`, `types/` | **Compliant** | All 4 directories exist with correct contents |
| Component Isolation: no shared state between pages | **Compliant** | Each page uses independent `useState` + `useEffect`; no global state or context providers |
| TypeScript strict mode | **Compliant** | Task 1.1 verified `strict: true` in `tsconfig.json` |
| File size: 200-400 lines (max 800) | **Compliant** | Largest file: `DesignDetail.tsx` (357 lines), `CatalogPage.tsx` (323 lines), all within bounds |

### 2.2 Performance

| Requirement | Status | Evidence |
|------------|--------|----------|
| Initial load under 3s (localhost, built static) | **Likely Compliant** | SPA with Vite build; no heavy dependencies beyond React + shadcn/ui; build verification needed |
| Tab switch instant (client-side only) | **Compliant** | `App.tsx` uses `Tabs` with all page components mounted; switch is client-side only |
| Vite build under 30s | **Likely Compliant** | Task 5.1 verified; standard React app build |

### 2.3 Security

| Requirement | Status | Evidence |
|------------|--------|----------|
| Same-origin API calls only | **Compliant** | `client.ts` uses relative paths (e.g., `/api/designs`); no absolute external URLs |
| Frontend input validation before API send | **Compliant** | `DesignsPage.tsx:109-112` validates required fields; `CatalogPage.tsx:46-53` validates JSON parse; `CatalogPage.tsx:139` validates required fields |
| No `dangerouslySetInnerHTML` | **Compliant** | Grep for `dangerouslySetInnerHTML` returned 0 results |
| JSON connection field: parse validation only | **Compliant** | `CatalogPage.tsx:48-53` -- `JSON.parse()` try-catch only |

### 2.4 Reliability

| Requirement | Status | Evidence |
|------------|--------|----------|
| API error: ErrorBanner (no crash) | **Compliant** | All pages catch errors and display `ErrorBanner` |
| Network error: retry button | **Partially Compliant** | `ErrorBanner.tsx:14-17` has optional `onRetry`; used in `DesignsPage:155`, `CatalogPage:308`. **Gap**: `HistoryPage:58`, `RulesPage:90`, `DesignDetail.tsx:73` do NOT pass `onRetry` to `ErrorBanner` |
| Backend not running: connection error message | **Compliant** | `client.ts:35` throws `ApiError(0, "...")` on network error which propagates to ErrorBanner |
| TypeScript compile error zero | **Compliant** | Task 5.1 verified `npx tsc --noEmit` passes |

**Finding (NFR-Reliability-1)**: `HistoryPage`, `RulesPage` (initial context load), and `DesignDetail` use `ErrorBanner` without `onRetry`. The requirement states "retry button should be displayed on network error". These pages show the error but provide no way to retry without a page reload. **Severity: Improvement Recommended**.

### 2.5 Usability

| Requirement | Status | Evidence | Gap |
|------------|--------|----------|-----|
| Japanese UI (labels, placeholders, error messages) | **Partially Compliant** | See detailed analysis below | Multiple English labels found |
| Responsive layout (min-width 1024px) | **Likely Compliant** | Uses Tailwind flex/grid layouts; no explicit `min-w-[1024px]` check but layout is desktop-oriented |
| Status badge color coding | **Compliant** | `StatusBadge.tsx:4-11` maps all 6 statuses to correct colors: draft=gray, active=blue, pending_review=yellow, supported=green, rejected=red, inconclusive=orange |
| Loading state display (spinner/skeleton) | **Partially Compliant** | Loading text shown in all pages, but uses plain text ("Loading...", "...") not spinner/skeleton |
| Form validation: inline error on empty required fields | **Compliant** | `DesignsPage.tsx:109-112` -- inline error message; `CatalogPage.tsx:51,134` -- JSON error message |

#### NFR-Usability Japanese Language Audit

The requirement states: "Japanese UI (labels, placeholders, error messages)". Below is a detailed audit of all user-facing text.

**Fully Japanese (Compliant)**:
- `CatalogPage.tsx`: Source columns ("...", "...", "..." etc.), buttons ("..."), dialogs, search UI -- All Japanese
- `RulesPage.tsx`: Section titles ("...", "..."), search UI, empty states -- All Japanese
- `HistoryPage.tsx`: Loading, empty state, timeline labels ("...", "..."), comment section title -- All Japanese
- `ErrorBanner.tsx`: Retry button ("...") -- Japanese
- `client.ts`: Network error message ("...") -- Japanese

**English Labels Found (Non-Compliant)**:

| File | Line | English Text | Should Be (Japanese) |
|------|------|-------------|---------------------|
| `App.tsx` | 12-15 | Tab labels: "Designs", "Catalog", "Rules", "History" | "..." / "..." / "..." / "..." |
| `DesignsPage.tsx` | 38-45 | Status filter labels: "All", "Draft", "Active", "Pending Review", "Supported", "Rejected", "Inconclusive" | Japanese equivalents |
| `DesignsPage.tsx` | 48 | Column label: "Title", "Status", "Updated" | "...", "...", "..." |
| `DesignsPage.tsx` | 133 | "Loading..." | "..." |
| `DesignsPage.tsx` | 152 | Button: "+ New Design" | "+" |
| `DesignsPage.tsx` | 159 | "No designs found." | "..." |
| `DesignsPage.tsx` | 160 | Button label: "+ New Design" | "+" |
| `DesignsPage.tsx` | 184 | Dialog title: "New Design" | "..." |
| `DesignsPage.tsx` | 187-206 | Form labels: "Title *", "Hypothesis Statement *", "Hypothesis Background *", "Theme ID" | Japanese equivalents |
| `DesignsPage.tsx` | 188,193,200,207 | Placeholders: "Design title", "State your hypothesis", "Describe the background", "DEFAULT" | Japanese equivalents |
| `DesignsPage.tsx` | 110 | Validation error: "Title, hypothesis statement, hypothesis background are required." | Japanese |
| `DesignsPage.tsx` | 213 | Button text: "Creating..." / "Create" | "..." / "..." |
| `DesignDetail.tsx` | 70 | "Loading..." | "..." |
| `DesignDetail.tsx` | 85-87 | Sub-tab labels: "Overview", "Review", "Knowledge" | Japanese equivalents |
| `DesignDetail.tsx` | 115-123 | Field labels: "Status", "Theme ID", "Hypothesis Statement", "Hypothesis Background", "Source IDs", "Created", "Updated" | Japanese equivalents |
| `DesignDetail.tsx` | 127-147 | Section labels: "Metrics", "Explanatory", "Chart", "Next Action" | Japanese equivalents |
| `DesignDetail.tsx` | 166-177 | Column labels: "Reviewer", "Comment", "Status", "Date" | Japanese equivalents |
| `DesignDetail.tsx` | 253 | Button text: "Submitting..." / "Submit for Review" | Japanese |
| `DesignDetail.tsx` | 257 | "Only active designs can be submitted for review." | Japanese |
| `DesignDetail.tsx` | 263 | "Comments" | "..." |
| `DesignDetail.tsx` | 267 | "No comments yet." | "..." |
| `DesignDetail.tsx` | 271 | "Add Comment" | "..." |
| `DesignDetail.tsx` | 272 | Placeholder: "Comment" | Japanese |
| `DesignDetail.tsx` | 284 | Placeholder: "Reviewer (optional)" | Japanese |
| `DesignDetail.tsx` | 286 | "Adding..." / "Add" | Japanese |
| `DesignDetail.tsx` | 327 | "Extracting..." / "Extract Knowledge" | Japanese |
| `DesignDetail.tsx` | 340-342 | "Key:", "Category:", "Importance:" | Japanese |
| `DesignDetail.tsx` | 348 | "Saved" / "Saving..." / "Save Knowledge" | Japanese |
| `DesignDetail.tsx` | 351 | "Knowledge saved successfully." | Japanese |
| `StatusBadge.tsx` | 13-20 | Status labels: "Draft", "Active", "Pending Review", etc. | Japanese equivalents |

**Finding (NFR-Usability-1)**: Significant portion of user-facing text is in English, primarily in `DesignsPage.tsx`, `DesignDetail.tsx`, `StatusBadge.tsx`, and `App.tsx` tab labels. The requirements explicitly state: "Japanese UI (labels, placeholders, error messages)". The `CatalogPage`, `RulesPage`, and `HistoryPage` are largely Japanese-compliant, suggesting this was the intent but was not consistently applied. **Severity: Critical -- violates explicit NFR**.

---

## 3. Functional Requirements Coverage Detail

### FR-1: Application Shell

| Requirement | Status | Evidence |
|------------|--------|----------|
| Header with "Insight Blueprint" | **Covered** | `App.tsx:44-46` |
| 4 tabs: Designs / Catalog / Rules / History | **Covered** | `App.tsx:10,49-55` |
| Default tab: Designs | **Covered** | `App.tsx:22` -- fallback returns "designs" |

### FR-2: Tab Navigation

| Requirement | Status | Evidence |
|------------|--------|----------|
| `useState` tab management (no react-router) | **Covered** | `App.tsx:26` -- `useState<Tab>` |
| `?tab=` URL parameter sync | **Covered** | `App.tsx:18-23,37-39` |
| `history.replaceState` on tab change | **Covered** | `App.tsx:39` |
| popstate event listener | **Covered** | `App.tsx:28-32` |

### FR-3: API Client Layer

| Requirement | Status | Evidence |
|------------|--------|----------|
| All REST API calls in `api/client.ts` | **Covered** | `client.ts` -- 16 exported functions |
| Base URL: empty string (same-origin) | **Covered** | All paths start with `/api/...` (relative) |
| Vite proxy for `/api/*` | **Covered** | Task 1.1 verified proxy config |
| Error response `{error: string}` handling | **Covered** | `client.ts:42` -- checks `body.error` |
| 422 `{detail}` handling | **Covered** | `client.ts:44-47` -- handles string and array detail |
| TypeScript types in `types/api.ts` | **Covered** | `api.ts` -- 8 model interfaces + 4 enum types + 3 request types |

### FR-4: Shared UI Components

| Requirement | Status | Evidence |
|------------|--------|----------|
| DataTable (shadcn/ui Table based, generic) | **Covered** | `DataTable.tsx` -- generic `<T>`, wraps shadcn `Table` |
| StatusBadge (color-coded) | **Covered** | `StatusBadge.tsx` -- 6-color mapping |
| EmptyState (placeholder) | **Covered** | `EmptyState.tsx` -- message + optional action |
| ErrorBanner (shadcn/ui Alert based) | **Covered** | `ErrorBanner.tsx` -- wraps shadcn `Alert`, optional retry |

### FR-5: Design List

| Requirement | Status | Evidence |
|------------|--------|----------|
| `GET /api/designs` fetch and display | **Covered** | `DesignsPage.tsx:71-88` |
| Status filter (All + 6 statuses) | **Covered** | `DesignsPage.tsx:28-45,139-150` |
| Columns: title, status badge, updated_at | **Covered** | `DesignsPage.tsx:47-59` |
| Row click: expand detail | **Covered** | `DesignsPage.tsx:166-168,171-178` |

### FR-6: Design Detail

| Requirement | Status | Evidence |
|------------|--------|----------|
| `GET /api/designs/{id}` fetch | **Covered** | `DesignDetail.tsx:45-60` |
| Display all required fields | **Covered** | `DesignDetail.tsx:112-150` -- all fields shown |
| JsonTree for dict fields | **Covered** | `DesignDetail.tsx:124-147` -- metrics, explanatory, chart, next_action |

### FR-7: Design Create

| Requirement | Status | Evidence |
|------------|--------|----------|
| "New Design" button opens Dialog | **Covered** | `DesignsPage.tsx:152,180-218` |
| Inputs: title (req), hypothesis_statement (req), hypothesis_background (req), theme_id (opt, default "DEFAULT") | **Covered** | `DesignsPage.tsx:100-107,186-207` |
| `POST /api/designs` + list refresh | **Covered** | `DesignsPage.tsx:122-127` |

### FR-8: Design Sub-tabs

| Requirement | Status | Evidence |
|------------|--------|----------|
| Overview / Review / Knowledge sub-tabs | **Covered** | `DesignDetail.tsx:83-102` |

### FR-9: Review -- Submit & Comments

| Requirement | Status | Evidence |
|------------|--------|----------|
| "Submit for Review" button (active-only) | **Covered** | `DesignDetail.tsx:249-253` |
| Comment list via `GET /api/designs/{id}/comments` | **Covered** | `DesignDetail.tsx:197-204` |
| Each comment: reviewer, comment, status_after badge, created_at | **Covered** | `DesignDetail.tsx:165-178` -- commentColumns with all fields |

### FR-10: Review -- Add Comment

| Requirement | Status | Evidence |
|------------|--------|----------|
| Comment form: comment (textarea), status (select), reviewer (optional) | **Covered** | `DesignDetail.tsx:270-288` |
| Status options: supported/rejected/inconclusive/active | **Covered** | `DesignDetail.tsx:180` |
| `POST /api/designs/{id}/comments` + list refresh | **Covered** | `DesignDetail.tsx:236-244` |

### FR-11: Knowledge -- Extract & Save

| Requirement | Status | Evidence |
|------------|--------|----------|
| "Extract Knowledge" button: POST without body | **Covered** | `DesignDetail.tsx:305-313` -- calls `extractKnowledge(designId)` |
| Preview: key, title, content, category, importance | **Covered** | `DesignDetail.tsx:335-344` |
| "Save Knowledge" button: POST with body | **Covered** | `DesignDetail.tsx:315-322` -- calls `saveKnowledge(designId, entries)` |
| Success confirmation message | **Covered** | `DesignDetail.tsx:350-352` -- "Knowledge saved successfully." |

### FR-12: Source List

| Requirement | Status | Evidence |
|------------|--------|----------|
| `GET /api/catalog/sources` fetch and display | **Covered** | `CatalogPage.tsx:290-304` |
| Columns: name, type (badge), description, tags, updated_at | **Covered** | `CatalogPage.tsx:16-22` |
| Row click: show schema | **Covered** | `CatalogPage.tsx:88,314` |

### FR-13: Source Detail -- Schema

| Requirement | Status | Evidence |
|------------|--------|----------|
| `GET /api/catalog/sources/{id}/schema` fetch | **Covered** | `CatalogPage.tsx:166-178` |
| Table: name, type, description, nullable, unit, examples | **Covered** | `CatalogPage.tsx:152-159` |

### FR-14: Source Add

| Requirement | Status | Evidence |
|------------|--------|----------|
| "Add Source" button opens Dialog | **Covered** | `CatalogPage.tsx:77,92-147` |
| Inputs: source_id, name, type (select: csv/api/sql), description, connection (JSON) | **Covered** | `CatalogPage.tsx:98-133` |
| `POST /api/catalog/sources` + list refresh | **Covered** | `CatalogPage.tsx:64-67` |

### FR-15: Catalog Search

| Requirement | Status | Evidence |
|------------|--------|----------|
| Search bar: `GET /api/catalog/search?q={query}` | **Covered** | `CatalogPage.tsx:208-222` |
| Results: matched columns/sources | **Covered** | `CatalogPage.tsx:195-199,240` |
| Source filter (`&source_id=`) | **Partially Covered** | `client.ts:186` accepts optional `sourceId`, but `SearchSection` in `CatalogPage.tsx` does not expose a source filter UI | **Gap**: source_id filter is available in API client but not exposed in UI |

**Finding (FR-15-1)**: The optional `source_id` filter for catalog search is implemented in the API client (`client.ts:186`) but is not exposed in the `SearchSection` UI. The requirement says "Source filter (optional): `&source_id=`". Since marked as optional, this is a **minor gap**. **Severity: Minor**.

### FR-16: Domain Knowledge List

| Requirement | Status | Evidence |
|------------|--------|----------|
| `GET /api/catalog/knowledge` fetch and display | **Covered** | `CatalogPage.tsx:254-280` |
| Each entry: key, title, content, category (badge), importance (badge), affects_columns | **Partially Covered** | `CatalogPage.tsx:247-252` -- shows title, content, category, importance. **Missing**: `key` and `affects_columns` columns | **Gap**: Two fields missing from display |

**Finding (FR-16-1)**: The `KnowledgeSection` in `CatalogPage.tsx` does not display `key` or `affects_columns` fields for domain knowledge entries. The requirement lists all 6 fields: key, title, content, category (badge), importance (badge), affects_columns. **Severity: Improvement Recommended**.

### FR-17: Project Context

| Requirement | Status | Evidence |
|------------|--------|----------|
| `GET /api/rules/context` fetch | **Covered** | `RulesPage.tsx:58-67` |
| 3 sections: Sources, Knowledge, Rules with counts | **Covered** | `RulesPage.tsx:95-143` -- 3 `CollapsibleSection` with `total_sources`, `total_knowledge`, `total_rules` |

### FR-18: Cautions Search

| Requirement | Status | Evidence |
|------------|--------|----------|
| Table names input (comma-separated) | **Covered** | `RulesPage.tsx:152-156` |
| "Search Cautions" button: `GET /api/rules/cautions?table_names={names}` | **Covered** | `RulesPage.tsx:69-86,158-163` |
| Results display | **Covered** | `RulesPage.tsx:169-171` |

### FR-19: Recent Activity Timeline

| Requirement | Status | Evidence |
|------------|--------|----------|
| `GET /api/designs` sorted by updated_at descending | **Covered** | `HistoryPage.tsx:19-33` |
| Each entry: title, status badge, updated_at | **Covered** | `HistoryPage.tsx:74-80` |
| Distinguish "created" vs "updated" | **Covered** | `HistoryPage.tsx:64` -- `isCreated = created_at === updated_at`; line 78 shows "..." vs "..." |

### FR-20: Design Review History

| Requirement | Status | Evidence |
|------------|--------|----------|
| Click to expand: fetch comments | **Covered** | `HistoryPage.tsx:35-50,52-54` |
| Comments: reviewer, comment, status_after badge, created_at | **Covered** | `HistoryPage.tsx:98-111` |

### FR-21: shadcn/ui Setup

| Requirement | Status | Evidence |
|------------|--------|----------|
| `npx shadcn@latest init` | **Covered** | Task 1.1 complete |
| 10 components: Tabs, Table, Badge, Button, Card, Dialog, Input, Textarea, Select, Alert | **Covered** | All used across implementation files |

### FR-22: Development Server

| Requirement | Status | Evidence |
|------------|--------|----------|
| `npm run dev` with HMR | **Covered** | Task 1.1 verified |
| Vite proxy: `/api/*` -> `http://localhost:3000/api/*` | **Covered** | Task 1.1 verified |

### FR-23: Production Build

| Requirement | Status | Evidence |
|------------|--------|----------|
| `npm run build` -> `src/insight_blueprint/static/` | **Covered** | Task 5.1 verified |
| `poe build-frontend` compatibility | **Covered** | Task 5.1 verified |
| SPA: index.html + JS/CSS bundle | **Covered** | Task 5.1 verified |

---

## 4. Design Alignment Check

| Design Specification | Actual Implementation | Aligned? |
|---------------------|----------------------|----------|
| Architecture: `frontend/src/` directory structure | Matches exactly: `api/`, `components/`, `pages/`, `types/` | Yes |
| Data Flow: User -> Page -> client.ts -> fetch -> API | Implemented as specified; no direct fetch in pages | Yes |
| Race Condition Prevention: AbortController in useEffect | Used in all pages: `DesignsPage`, `CatalogPage`, `RulesPage`, `HistoryPage`, `DesignDetail`, `SchemaSection`, `KnowledgeSection` | Yes |
| Service Layer Separation: no direct fetch in pages | All API calls go through `api/client.ts` | Yes |
| Component interfaces (DataTable, StatusBadge, etc.) | Match design.md specifications | Yes |
| `ApiError` class with status + detail | `client.ts:15-25` -- exact match | Yes |
| `request<T>()` shared helper | `client.ts:27-56` -- handles all error scenarios per design | Yes |

---

## 5. Playwright Smoke Tests Coverage

| Test | AC Coverage | Status |
|------|-------------|--------|
| S1: Tab routing | R1-AC2, R1-AC3 | Implemented |
| S2: Invalid tab fallback | R1-AC3 | Implemented |
| S3: API error banner | R1-AC4 | Implemented |
| S4: Empty state | R1-AC5 | Implemented |
| S5: Create design dialog | R2-AC4, R2-AC5 | Implemented |
| S6: Status filter | R2-AC2 | Implemented |
| S7: Design detail expand | R2-AC3 | Implemented |
| S8: Source add with JSON validation | R3-AC3 | Implemented |

All 8 planned smoke tests are implemented and match the test-design.md specification.

---

## 6. Summary of Findings

### Critical (Violates explicit requirement)

| ID | Finding | Location | Requirement |
|----|---------|----------|-------------|
| **C-1** | Extensive English text in user-facing UI where requirements mandate Japanese | `DesignsPage.tsx`, `DesignDetail.tsx`, `StatusBadge.tsx`, `App.tsx` tab labels | NFR-Usability: "Japanese UI (labels, placeholders, error messages)" |

### Improvement Recommended

| ID | Finding | Location | Requirement |
|----|---------|----------|-------------|
| **I-1** | `ErrorBanner` lacks `onRetry` in HistoryPage, RulesPage (initial), DesignDetail | `HistoryPage.tsx:58`, `RulesPage.tsx:90`, `DesignDetail.tsx:73` | NFR-Reliability: "retry button on network error" |
| **I-2** | Domain knowledge list missing `key` and `affects_columns` columns | `CatalogPage.tsx:247-252` | FR-16: "Each entry: key, title, content, category, importance, affects_columns" |

### Minor

| ID | Finding | Location | Requirement |
|----|---------|----------|-------------|
| **M-1** | Catalog search source_id filter not exposed in UI (API client supports it) | `CatalogPage.tsx` SearchSection | FR-15: "Source filter (optional)" |
| **M-2** | Loading states use plain text instead of spinner/skeleton | `DesignsPage.tsx:133`, `DesignDetail.tsx:70` | NFR-Usability: "spinner or skeleton" |

---

## 7. Recommendations

1. **[High Priority] Localize all English labels to Japanese** -- This is the most significant gap. The following files need Japanese labels:
   - `App.tsx`: Tab labels (Designs -> ..., Catalog -> ..., etc.)
   - `DesignsPage.tsx`: Column headers, button labels, dialog text, status labels, validation messages
   - `DesignDetail.tsx`: Sub-tab labels, field labels, button text, comments section
   - `StatusBadge.tsx`: Status display labels

2. **[Medium Priority] Add `onRetry` to all ErrorBanner usages** -- `HistoryPage`, `RulesPage`, and `DesignDetail` should provide retry functionality.

3. **[Low Priority] Add missing columns to knowledge list** -- Add `key` and `affects_columns` to the `KNOWLEDGE_COLUMNS` in `CatalogPage.tsx`.

4. **[Low Priority] Consider adding source_id filter UI for catalog search** -- The API client already supports it; adding a dropdown or input would improve the search experience.

5. **[Low Priority] Replace plain "Loading..." text with spinner component** -- Use shadcn/ui Skeleton or a simple spinner for more polished UX.

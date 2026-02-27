# Quality Review Report: SPEC-4b (webui-frontend)

**Reviewer**: Quality Review Agent
**Date**: 2026-02-28
**Scope**: 16 changed files in `frontend/src/`

## Summary Table

| # | Severity | File | Line(s) | Issue |
|---|----------|------|---------|-------|
| 1 | High | CatalogPage.tsx | 16-323 | Single file contains 5 components (323 lines) -- SRP violation |
| 2 | High | DesignDetail.tsx | 1-357 | Single file contains 5 components (357 lines) -- SRP violation |
| 3 | High | CatalogPage.tsx / RulesPage.tsx | Multiple | Duplicated KNOWLEDGE_COLUMNS definition |
| 4 | High | Multiple pages | Multiple | Inconsistent loading/error/empty state handling patterns |
| 5 | Medium | SearchSection (CatalogPage.tsx) | 208-222 | AbortController created in handler but never aborted |
| 6 | Medium | DesignDetail.tsx | 62-67 | refreshDesign calls onDesignUpdated before getDesign resolves |
| 7 | Medium | DataTable.tsx | 40-42 | Uses array index as React key |
| 8 | Medium | RulesPage.tsx | 139 | Uses array index as key for rules list |
| 9 | Medium | DesignsPage.tsx | 107 | Magic string "DEFAULT" |
| 10 | Medium | CatalogPage.tsx | 66 | Magic string "csv" used as default |
| 11 | Medium | DesignDetail.tsx | 195 | commentStatus typed as `string` instead of `DesignStatus` |
| 12 | Medium | api/client.ts | 35 | Japanese string in error message inside non-UI layer |
| 13 | Medium | DesignsPage.tsx / RulesPage.tsx | Multiple | STATUS_LABELS duplicated across files |
| 14 | Low | DesignDetail.tsx | 112-150 | OverviewPanel has repetitive Field rendering -- extractable pattern |
| 15 | Low | JsonTree.tsx | 30-77 | JsonNode function length (50+ lines) with nested conditionals |
| 16 | Low | RulesPage.tsx | 140 | `JSON.stringify(rule)` as display -- raw JSON in UI |
| 17 | Low | CatalogPage.tsx | 46-70 | handleSubmit has mixed concerns (JSON parse + API call + form reset) |
| 18 | Low | HistoryPage.tsx | 91-95 | Deeply nested conditional rendering |
| 19 | Low | Multiple pages | Multiple | Mixed language in UI text (Japanese and English) |
| 20 | Low | lib/utils.ts | -- | Only contains shadcn utility -- no custom utilities extracted |

---

## Detailed Findings

### 1. [High] CatalogPage.tsx -- SRP Violation (5 components in one file)

**Lines**: 1-323

CatalogPage.tsx defines 5 separate components in a single 323-line file:
- `SourceListSection` (lines 24-148)
- `SchemaSection` (lines 161-191)
- `SearchSection` (lines 201-243)
- `KnowledgeSection` (lines 254-280)
- `CatalogPage` (lines 284-323)

Each sub-component has its own state, API calls, and rendering logic. This violates the Single Responsibility principle and makes the file harder to navigate.

**Suggestion**: Extract each section into its own file under `pages/catalog/` or `components/catalog/`:
```
pages/catalog/
  CatalogPage.tsx
  SourceListSection.tsx
  SchemaSection.tsx
  SearchSection.tsx
  KnowledgeSection.tsx
```

---

### 2. [High] DesignDetail.tsx -- SRP Violation (5 components in one file)

**Lines**: 1-357

DesignDetail.tsx defines 5 components in 357 lines:
- `DesignDetail` (lines 40-106)
- `OverviewPanel` (lines 112-150)
- `Field` (lines 152-159)
- `ReviewPanel` (lines 182-292)
- `KnowledgePanel` (lines 298-357)

`ReviewPanel` alone is 110 lines with form handling, comment listing, and status management.

**Suggestion**: Same as above -- extract into `pages/designs/` sub-directory.

---

### 3. [High] Duplicated KNOWLEDGE_COLUMNS

**Files**: CatalogPage.tsx (lines 247-252) and RulesPage.tsx (lines 28-33)

```tsx
// CatalogPage.tsx line 247
const KNOWLEDGE_COLUMNS: ColumnDef<KnowledgeEntry>[] = [
  { key: "title", label: "..." },
  { key: "content", label: "..." },
  { key: "category", label: "...", render: ... },
  { key: "importance", label: "...", render: ... },
];

// RulesPage.tsx line 28 -- identical definition
const KNOWLEDGE_COLUMNS: ColumnDef<KnowledgeEntry>[] = [
  { key: "title", label: "..." },
  { key: "content", label: "..." },
  { key: "category", label: "...", render: ... },
  { key: "importance", label: "...", render: ... },
];
```

**Suggestion**: Extract to a shared `columns/knowledge.tsx` or `lib/column-defs.ts` file.

---

### 4. [High] Inconsistent Loading/Error/Empty State Patterns

Different pages handle loading/error/empty states differently:

| Page | Loading | Error | Empty |
|------|---------|-------|-------|
| DesignsPage | `<p>` text | ErrorBanner with retry | EmptyState with action |
| CatalogPage | `<p>` text | ErrorBanner with retry | EmptyState with action |
| HistoryPage | `<p>` text | ErrorBanner (no retry) | EmptyState (no action) |
| RulesPage | `<p>` text | ErrorBanner (no retry) | EmptyState (no action) |
| DesignDetail | `<p>` text | ErrorBanner (no retry) | `null` |

Inconsistencies:
- **Loading text**: "Loading..." (English) vs "..." (Japanese) -- varies by page
- **Error recovery**: Some pages provide `onRetry`, some do not
- **Empty state**: Some have action buttons, some do not
- DesignDetail returns `null` for empty instead of EmptyState

**Suggestion**: Create a `useDataFetch` hook or a `LoadingContainer` component that standardizes the pattern:

```tsx
function LoadingContainer({ loading, error, empty, onRetry, children }) {
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onRetry={onRetry} />;
  if (empty) return <EmptyState message={emptyMessage} />;
  return children;
}
```

---

### 5. [Medium] AbortController Created but Never Aborted in SearchSection

**File**: CatalogPage.tsx, lines 208-222

```tsx
const handleSearch = () => {
  if (!query.trim()) return;
  const ctrl = new AbortController();  // created but never aborted
  setLoading(true);
  setError(null);
  searchCatalog(query.trim(), undefined, ctrl.signal)
    .then(...)
    .catch(...)
    .finally(() => setLoading(false));
};
```

The `AbortController` is created in the event handler, but there is no mechanism to abort it (e.g., on component unmount or new search). The `ctrl` variable is local to the function and unreachable after the function returns.

**Suggestion**: Either remove the `AbortController` (since it serves no purpose here) or store it as a ref and abort the previous request when a new search starts:

```tsx
const abortRef = useRef<AbortController | null>(null);
const handleSearch = () => {
  abortRef.current?.abort();
  const ctrl = new AbortController();
  abortRef.current = ctrl;
  // ...
};
useEffect(() => () => abortRef.current?.abort(), []);
```

---

### 6. [Medium] refreshDesign Race Condition

**File**: DesignDetail.tsx, lines 62-67

```tsx
const refreshDesign = () => {
  getDesign(designId)
    .then(setDesign)
    .catch((err) => setError(err.message));
  onDesignUpdated();  // called immediately, not after getDesign resolves
};
```

`onDesignUpdated()` is called synchronously before `getDesign` resolves. This triggers the parent's `fetchDesigns()` which may complete before the detail data is refreshed, leading to inconsistent UI state.

**Suggestion**: Chain `onDesignUpdated` inside the `.then()`:

```tsx
const refreshDesign = () => {
  getDesign(designId)
    .then((d) => {
      setDesign(d);
      onDesignUpdated();
    })
    .catch((err) => setError(err.message));
};
```

---

### 7. [Medium] DataTable Uses Array Index as Key

**File**: DataTable.tsx, line 40-42

```tsx
{data.map((row, i) => (
  <TableRow key={i} ...>
```

Using array index as a key can cause rendering issues if the list is reordered, filtered, or items are inserted/removed. This affects all tables across the application.

**Suggestion**: Add an optional `rowKey` prop to `DataTableProps`:

```tsx
interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  rowKey?: (row: T, index: number) => string | number;
  // ...
}
// Usage: key={rowKey ? rowKey(row, i) : i}
```

---

### 8. [Medium] Rules List Uses Array Index as Key

**File**: RulesPage.tsx, line 139

```tsx
{context.rules.map((rule, i) => (
  <li key={i}>{JSON.stringify(rule)}</li>
))}
```

Same issue as #7, compounded by the fact that `JSON.stringify` as a display value is not user-friendly (see finding #16).

---

### 9. [Medium] Magic String "DEFAULT"

**File**: DesignsPage.tsx, line 107

```tsx
const theme_id = (data.get("theme_id") as string).trim() || "DEFAULT";
```

**Suggestion**: Extract to a named constant:

```tsx
const DEFAULT_THEME_ID = "DEFAULT";
```

---

### 10. [Medium] Magic String "csv" as Default Source Type

**File**: CatalogPage.tsx, line 39

```tsx
const [form, setForm] = useState({
  source_id: "",
  name: "",
  type: "csv" as SourceType,  // magic default
  // ...
});
```

**Suggestion**: Extract to a named constant:

```tsx
const DEFAULT_SOURCE_TYPE: SourceType = "csv";
```

---

### 11. [Medium] Loose Typing for commentStatus

**File**: DesignDetail.tsx, line 195

```tsx
const [commentStatus, setCommentStatus] = useState<string>("supported");
```

This is typed as `string` while `COMMENT_STATUSES` is typed as `DesignStatus[]`. The state should use the same type:

```tsx
const [commentStatus, setCommentStatus] = useState<DesignStatus>("supported");
```

---

### 12. [Medium] Japanese Error Message in API Client

**File**: api/client.ts, line 35

```tsx
throw new ApiError(0, "...........!");
```

The API client layer is not a UI component. Error messages from this layer may be displayed in different contexts. Hardcoding Japanese here mixes concerns.

**Suggestion**: Either use an English error code/key and translate at the UI layer, or document that this client is Japanese-only. At minimum, extract the string to a constant.

---

### 13. [Medium] Duplicated STATUS_LABELS

**Files**: DesignsPage.tsx (lines 37-45) and StatusBadge.tsx (lines 13-20)

Both files define a `STATUS_LABELS` mapping with the same keys and values. `DesignsPage` uses it for the filter dropdown, `StatusBadge` uses it for badge display.

**Suggestion**: Extract to a shared constant in `types/api.ts` or a new `lib/design-status.ts`:

```tsx
export const DESIGN_STATUS_LABELS: Record<DesignStatus, string> = { ... };
```

---

### 14. [Low] Repetitive Field Rendering in OverviewPanel

**File**: DesignDetail.tsx, lines 112-150

The `OverviewPanel` renders many `<Field>` components with a repetitive pattern. The conditional blocks for `metrics`, `explanatory`, `chart`, and `next_action` (lines 124-147) all follow the same structure:

```tsx
{Object.keys(design.metrics).length > 0 && (
  <div>
    <span className="font-medium">Metrics</span>
    <JsonTree data={design.metrics} />
  </div>
)}
```

**Suggestion**: Extract a helper function:

```tsx
function JsonField({ label, data }: { label: string; data: unknown }) {
  const isEmpty = Array.isArray(data) ? data.length === 0 : !data || Object.keys(data).length === 0;
  if (isEmpty) return null;
  return (
    <div>
      <span className="font-medium">{label}</span>
      <JsonTree data={data} />
    </div>
  );
}
```

---

### 15. [Low] JsonNode Function Length

**File**: JsonTree.tsx, lines 16-81 (65 lines)

The `JsonNode` component handles null, boolean, number, string, array, and object types all in one function body with nested conditionals. While each branch is simple, the overall function exceeds the 30-line guideline.

**Suggestion**: Consider splitting into `PrimitiveNode`, `ArrayNode`, `ObjectNode` sub-components, or accept the current length given the cohesion of the switch-like logic. This is a borderline case.

---

### 16. [Low] Raw JSON.stringify in UI

**File**: RulesPage.tsx, line 140

```tsx
<li key={i}>{JSON.stringify(rule)}</li>
```

Displaying raw JSON to users is not user-friendly. Even for admin dashboards, structured display is preferred.

**Suggestion**: Use the existing `JsonTree` component:

```tsx
<li key={i}><JsonTree data={rule} defaultExpanded={false} /></li>
```

---

### 17. [Low] Mixed Concerns in handleSubmit

**File**: CatalogPage.tsx, lines 46-71

The `handleSubmit` function in `SourceListSection` handles JSON parsing, validation, API call, dialog close, and form reset. This is acceptable for form handlers but is at the boundary of single-responsibility.

**Suggestion**: Could be improved with a separate `parseConnection` function, but not critical given the current size.

---

### 18. [Low] Deeply Nested Conditional Rendering

**File**: HistoryPage.tsx, lines 91-95

```tsx
{!commentsLoading && !commentsError && comments.length === 0 && (
  <p className="text-sm text-muted-foreground">
    ...
  </p>
)}
```

This triple-negation check is hard to read at a glance.

**Suggestion**: Extract to a helper variable:

```tsx
const showEmptyMessage = !commentsLoading && !commentsError && comments.length === 0;
```

---

### 19. [Low] Mixed Language in UI Text

UI text mixes Japanese and English inconsistently:

| File | Example | Language |
|------|---------|----------|
| DesignsPage.tsx | "Loading...", "No designs found." | English |
| CatalogPage.tsx | "...........!", "...............!" | Japanese |
| HistoryPage.tsx | "...........!", "............!" | Japanese |
| RulesPage.tsx | "...........!", "......" | Japanese |
| DesignDetail.tsx | "Loading...", "Submit for Review" | English |

Designs page and DesignDetail use English, while Catalog/History/Rules use Japanese. Pick one and apply consistently. Given the project rule that user-facing content should be in Japanese, the English pages should be updated.

---

### 20. [Low] No Custom Utilities in lib/utils.ts

**File**: lib/utils.ts

Only contains the shadcn `cn()` utility. Common patterns like date formatting (`new Date(v).toLocaleString("ja-JP")`) appear in multiple files and could be extracted here.

**Suggestion**: Add shared utility functions:

```tsx
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ja-JP");
}
```

This would reduce duplication across DesignDetail, DesignsPage, and HistoryPage.

---

## Positive Observations

1. **Types are well-defined**: `types/api.ts` provides comprehensive TypeScript interfaces for all API entities and requests.
2. **API client is well-structured**: `client.ts` has clean error handling, proper `encodeURIComponent` usage, and AbortSignal support.
3. **Shared components are good**: `DataTable`, `EmptyState`, `ErrorBanner`, and `StatusBadge` are properly typed with clean interfaces.
4. **Consistent use of AbortController for data fetching**: Most `useEffect` hooks properly create and clean up AbortControllers.
5. **Early return pattern**: Most pages use early returns for loading/error states before the main render.
6. **No hardcoded API URLs**: All API paths are relative, handled by Vite proxy configuration.

## Priority Recommendations

1. **[Must Fix]** Extract duplicated `KNOWLEDGE_COLUMNS` and `STATUS_LABELS` to shared modules.
2. **[Must Fix]** Fix the `SearchSection` AbortController (either remove or implement properly).
3. **[Must Fix]** Fix the `refreshDesign` race condition in DesignDetail.
4. **[Should Fix]** Standardize loading/error/empty state handling across all pages.
5. **[Should Fix]** Use `DesignStatus` type for `commentStatus` state.
6. **[Should Fix]** Add `rowKey` support to DataTable to avoid index-based keys.
7. **[Should Fix]** Unify UI language (all Japanese or all English for user-facing text).
8. **[Consider]** Split large files (CatalogPage, DesignDetail) into sub-component files.
9. **[Consider]** Extract common utilities (date formatting) to `lib/utils.ts`.
10. **[Consider]** Replace `JSON.stringify` in RulesPage with `JsonTree` component.

# Security Review: SPEC-4b (webui-frontend)

**Date:** 2026-02-28
**Reviewer:** Security Reviewer (Agent)
**Scope:** All frontend source files changed in SPEC-4b

## Summary

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | Medium | `frontend/src/api/client.ts:38-52` | Server error details forwarded to UI without sanitization |
| 2 | Medium | `frontend/src/components/JsonTree.tsx:28` | User-controlled strings rendered without escaping in JSON viewer |
| 3 | Medium | `frontend/src/pages/CatalogPage.tsx:127` | Connection JSON textarea accepts arbitrary input without schema validation |
| 4 | Low | `frontend/src/api/client.ts:27-56` | No request timeout — potential for hung connections |
| 5 | Low | `frontend/src/pages/DesignDetail.tsx:223-234` | No max-length on comment/reviewer inputs |
| 6 | Low | `frontend/src/pages/DesignsPage.tsx:96-130` | No max-length on design creation form fields |
| 7 | Low | `frontend/src/pages/RulesPage.tsx:140` | `JSON.stringify(rule)` renders raw API data to DOM |
| 8 | Low | `frontend/vite.config.ts:14-18` | Dev proxy has no path restrictions — proxies all `/api` paths |
| 9 | Low | `frontend/package.json` | Dependency versions use `^` ranges instead of pinned versions |
| 10 | Info | All pages | No CSRF protection mechanism visible (relies on backend) |
| 11 | Info | All pages | No authentication/authorization checks on frontend |

**Overall Assessment:** No critical vulnerabilities found. The codebase follows React best practices (JSX auto-escaping, no `dangerouslySetInnerHTML`, no `eval`). The findings are primarily defense-in-depth improvements. The most actionable items are #1, #2, and #3.

---

## Detailed Findings

### Finding 1: Server Error Details Forwarded to UI

**Severity:** Medium
**File:** `frontend/src/api/client.ts`, lines 38-52
**Category:** Sensitive Data Exposure

**Description:**
The `request()` function extracts error details from the server response body (`body.error`, `body.detail`, or validation error messages) and stores them in `ApiError.detail`. These error messages are then displayed directly to users via `ErrorBanner` components across all pages. If the backend leaks internal details (stack traces, SQL errors, file paths), the frontend will faithfully display them.

```typescript
// Lines 38-52 — server error body forwarded as-is
if (typeof body.error === "string") {
  detail = body.error;
} else if (typeof body.detail === "string") {
  detail = body.detail;
} else if (Array.isArray(body.detail)) {
  detail = body.detail.map((d: { msg: string }) => d.msg).join(", ");
}
throw new ApiError(res.status, detail);
```

**Risk:**
An attacker probing API endpoints could trigger error responses that reveal internal server structure, database schema, or library versions.

**Recommended Fix:**
1. Truncate or sanitize error messages before displaying to users.
2. Map known HTTP status codes to generic user-friendly messages.
3. Log the full error detail to the browser console (in development only) for debugging.

```typescript
// Example fix
const USER_MESSAGES: Record<number, string> = {
  400: "Invalid request",
  401: "Authentication required",
  403: "Access denied",
  404: "Resource not found",
  422: "Validation error",
  500: "Internal server error",
};

function sanitizeErrorDetail(status: number, detail: string): string {
  if (status >= 500) return USER_MESSAGES[status] ?? "Server error";
  // For 4xx, allow detail but truncate
  return detail.length > 200 ? detail.slice(0, 200) + "..." : detail;
}
```

---

### Finding 2: Unsanitized String Rendering in JsonTree

**Severity:** Medium
**File:** `frontend/src/components/JsonTree.tsx`, line 28
**Category:** XSS (Potential)

**Description:**
The `JsonTree` component renders arbitrary string values from API responses:

```tsx
// Line 28
if (typeof value === "string") return <span className="text-amber-700">"{value}"</span>;
```

While React's JSX auto-escaping prevents most XSS, this component renders data from `design.metrics`, `design.explanatory`, `design.chart`, and `design.next_action` -- all of which are `Record<string, unknown>` types containing arbitrary server data. If a future change introduces `dangerouslySetInnerHTML` or if the data is used in a non-JSX context (e.g., `title` attributes, `href`), this could become exploitable.

Additionally, line 70 renders object keys directly:
```tsx
<span className="text-purple-600">{k}</span>
```

**Risk:**
Low immediate risk due to React's auto-escaping, but the component processes untrusted data with no sanitization layer. Defense-in-depth is recommended.

**Recommended Fix:**
1. Add explicit string sanitization/truncation for display values.
2. Consider adding a maximum depth/size limit to prevent rendering massive payloads from crafted API responses.

---

### Finding 3: Connection JSON Accepts Arbitrary Input

**Severity:** Medium
**File:** `frontend/src/pages/CatalogPage.tsx`, lines 46-63
**Category:** Input Validation

**Description:**
The "Add Source" dialog accepts a JSON string in the connection textarea. The only validation is `JSON.parse()` — any valid JSON is accepted and sent to the backend:

```typescript
// Lines 47-53
let parsed: Record<string, unknown>;
try {
  parsed = JSON.parse(form.connection);
} catch {
  setJsonError("Valid JSON required");
  return;
}
```

This means users can submit:
- Deeply nested JSON (potential DoS on backend processing)
- Very large JSON payloads
- JSON with unexpected keys that could confuse backend logic

**Risk:**
Depending on how the backend processes `connection` data, this could lead to injection attacks (e.g., if connection strings are used to connect to databases), resource exhaustion, or unexpected behavior.

**Recommended Fix:**
1. Add a max-length check on the raw JSON string (e.g., 10KB).
2. Validate the parsed JSON structure against expected schema before sending.
3. Display guidance on expected connection format per source type (csv/api/sql).

```typescript
const MAX_CONNECTION_JSON_LENGTH = 10240;
if (form.connection.length > MAX_CONNECTION_JSON_LENGTH) {
  setJsonError("Connection JSON is too large (max 10KB)");
  return;
}
```

---

### Finding 4: No Request Timeout

**Severity:** Low
**File:** `frontend/src/api/client.ts`, lines 27-56
**Category:** Availability / Denial of Service

**Description:**
The `request()` function uses `fetch()` without a default timeout. While some callers pass `AbortSignal` from component lifecycle cleanup, mutation calls (POST requests like `createDesign`, `submitReview`, `addComment`, `addSource`) have no signal/timeout:

```typescript
// Example: no signal, no timeout
export async function createDesign(body: CreateDesignRequest) {
  return request("/api/designs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
```

**Risk:**
If the backend hangs, the UI will appear frozen with no feedback. Users may click buttons repeatedly, creating duplicate requests.

**Recommended Fix:**
Add a default timeout to the `request()` function:

```typescript
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  const signal = init?.signal
    ? anySignal([init.signal, controller.signal])
    : controller.signal;
  try {
    // ... existing logic with { ...init, signal }
  } finally {
    clearTimeout(timeoutId);
  }
}
```

---

### Finding 5: No Input Length Limits on Comment/Reviewer Fields

**Severity:** Low
**File:** `frontend/src/pages/DesignDetail.tsx`, lines 272-284
**Category:** Input Validation

**Description:**
The comment form has no `maxLength` on textarea or input fields:

```tsx
<Textarea name="comment" placeholder="Comment" required />
<Input name="reviewer" placeholder="Reviewer (optional)" className="w-48" />
```

**Risk:**
Users could submit extremely long comments or reviewer names, potentially causing display issues or backend processing problems.

**Recommended Fix:**
Add `maxLength` attributes:
```tsx
<Textarea name="comment" placeholder="Comment" required maxLength={5000} />
<Input name="reviewer" placeholder="Reviewer (optional)" maxLength={100} />
```

---

### Finding 6: No Input Length Limits on Design Creation Form

**Severity:** Low
**File:** `frontend/src/pages/DesignsPage.tsx`, lines 186-207
**Category:** Input Validation

**Description:**
The design creation form fields have no `maxLength` constraints:

```tsx
<Input name="title" placeholder="Design title" />
<Textarea name="hypothesis_statement" placeholder="State your hypothesis" />
<Textarea name="hypothesis_background" placeholder="Describe the background" />
<Input name="theme_id" placeholder="DEFAULT" />
```

**Risk:**
Same as Finding 5 -- excessively long inputs could cause display or processing issues.

**Recommended Fix:**
Add appropriate `maxLength` attributes (e.g., title: 200, hypothesis fields: 5000, theme_id: 100).

---

### Finding 7: Raw JSON.stringify Output in Rules Page

**Severity:** Low
**File:** `frontend/src/pages/RulesPage.tsx`, line 140
**Category:** Information Disclosure

**Description:**
Rules data from the API is rendered using `JSON.stringify(rule)` without any filtering:

```tsx
{context.rules.map((rule, i) => (
  <li key={i}>{JSON.stringify(rule)}</li>
))}
```

**Risk:**
If rules contain sensitive internal configuration (e.g., regex patterns for validation, internal system names), they would be exposed to any user with frontend access. The raw JSON display is also not user-friendly.

**Recommended Fix:**
1. Create a proper display component for rules (similar to how knowledge entries are displayed).
2. If rules may contain sensitive fields, filter them before rendering.

---

### Finding 8: Dev Proxy Proxies All /api Paths

**Severity:** Low
**File:** `frontend/vite.config.ts`, lines 13-19
**Category:** Configuration

**Description:**
The Vite dev server proxy forwards all `/api` requests to `http://localhost:3000`:

```typescript
server: {
  proxy: {
    "/api": {
      target: "http://localhost:3000",
      changeOrigin: true,
    },
  },
},
```

**Risk:**
This is development-only and does not affect production builds. However, `changeOrigin: true` modifies the `Host` header which could bypass host-based access controls on the backend during development.

**Recommended Fix:**
This is acceptable for development. Ensure production deployment does not use Vite's dev server. Consider adding a comment noting this is dev-only.

---

### Finding 9: Unpinned Dependency Versions

**Severity:** Low
**File:** `frontend/package.json`
**Category:** Supply Chain

**Description:**
All dependencies use `^` (caret) ranges:

```json
"react": "^19.0.0",
"radix-ui": "^1.4.3",
"vite": "^6.0.0",
```

**Risk:**
`^` ranges allow minor and patch updates automatically. While convenient, a compromised or buggy minor release could be pulled in without explicit review. This is a general supply chain risk.

**Recommended Fix:**
1. Use a lockfile (`package-lock.json` or `pnpm-lock.yaml`) and commit it.
2. Consider pinning exact versions for production dependencies.
3. Run `npm audit` / `pnpm audit` regularly.
4. No known critical CVEs exist for the listed packages at their current versions as of this review.

---

### Finding 10: No CSRF Protection Visible

**Severity:** Info
**File:** All pages
**Category:** CSRF

**Description:**
The frontend makes POST requests using `fetch()` with `Content-Type: application/json`. There is no CSRF token mechanism visible in the frontend code. The API client does not set any custom CSRF headers.

**Risk:**
JSON `Content-Type` POST requests cannot be triggered by simple HTML forms (which only support `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`), providing some natural CSRF protection. However, if the backend accepts non-JSON content types or if CORS is misconfigured, CSRF attacks could be possible.

**Recommended Fix:**
1. Verify the backend enforces `Content-Type: application/json` strictly.
2. Verify CORS policy only allows the expected origin.
3. Consider adding a custom header (e.g., `X-Requested-With: XMLHttpRequest`) as defense-in-depth.

---

### Finding 11: No Frontend Auth Checks

**Severity:** Info
**File:** All pages
**Category:** Authentication / Authorization

**Description:**
There is no authentication or authorization mechanism in the frontend. All API endpoints are called without auth tokens, session cookies, or any identity verification. This appears intentional for the current scope (internal tool / development dashboard).

**Risk:**
If deployed on a network accessible to untrusted users, anyone can view and modify all data.

**Recommended Fix:**
1. If this is intended as an internal-only tool, document this assumption.
2. If public deployment is planned, add authentication before deploying.
3. Consider at minimum a `--read-only` mode for the frontend.

---

## Positive Observations

The following security best practices were correctly followed:

1. **No `dangerouslySetInnerHTML`** -- All rendering uses JSX auto-escaping.
2. **No `eval()` or `Function()`** -- No dynamic code execution.
3. **No hardcoded secrets** -- No API keys, tokens, or passwords in source.
4. **No `console.log`** -- No accidental data leakage via browser console.
5. **No `localStorage`/`sessionStorage`** -- No client-side sensitive data storage.
6. **URL parameter encoding** -- `encodeURIComponent()` is used consistently for path parameters.
7. **Query parameter encoding** -- `URLSearchParams` is used for query strings, preventing injection.
8. **AbortController usage** -- Proper cleanup in `useEffect` prevents memory leaks and race conditions.
9. **Form validation** -- Required fields are checked before submission.
10. **Type safety** -- TypeScript interfaces provide compile-time validation of API shapes.
11. **No inline event handlers with string evaluation** -- All event handlers are function references.

---

## Risk Matrix

| Category | Status |
|----------|--------|
| Hardcoded Secrets | PASS |
| XSS (dangerouslySetInnerHTML) | PASS |
| XSS (eval/Function) | PASS |
| Command Injection | PASS (N/A for frontend) |
| Input Validation | PARTIAL -- needs length limits |
| Error Detail Exposure | NEEDS IMPROVEMENT |
| CSRF | ACCEPTABLE (JSON content-type mitigation) |
| Dependency Security | ACCEPTABLE -- use lockfile + audit |
| Client-side Storage | PASS |
| Console Logging | PASS |

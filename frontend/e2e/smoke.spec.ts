import { test, expect } from "@playwright/test";

// S1: Tab routing — navigate all 4 tabs, verify URL ?tab= sync
test("S1: tab routing syncs URL with tab selection", async ({ page }) => {
  await page.goto("/");
  // Skip "designs" (default tab) — Radix Tabs doesn't fire onValueChange for already-active tab
  const tabs = ["catalog", "rules", "history", "designs"] as const;
  for (const tab of tabs) {
    await page.getByRole("tab", { name: new RegExp(tab, "i") }).click();
    await expect(page).toHaveURL(new RegExp(`[?&]tab=${tab}`));
  }
});

// S2: Invalid tab fallback — ?tab=invalid → designs tab
test("S2: invalid tab parameter falls back to designs", async ({ page }) => {
  await page.goto("/?tab=invalid");
  await expect(page.getByRole("tab", { name: /designs/i })).toHaveAttribute(
    "data-state",
    "active",
  );
});

// S3: API error banner — load without backend → ErrorBanner visible
test("S3: API error shows ErrorBanner", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/?tab=designs");
  await expect(page.getByRole("alert")).toBeVisible({ timeout: 5000 });
});

// S4: Empty state — load with empty project → EmptyState visible
test("S4: empty project shows EmptyState", async ({ page }) => {
  await page.route("**/api/designs**", (route) =>
    route.fulfill({ json: { designs: [], count: 0 } }),
  );
  await page.goto("/?tab=designs");
  await expect(page.getByText(/No designs found/)).toBeVisible({
    timeout: 5000,
  });
});

// S5: Create design dialog — open, fill form, submit, verify design appears
test("S5: create design dialog submits and refreshes list", async ({
  page,
}) => {
  const mockDesign = {
    id: "d-001",
    title: "Test Design",
    status: "draft",
    theme_id: "t-001",
    hypothesis_statement: "Test hypothesis",
    hypothesis_background: "Test background",
    parent_id: null,
    metrics: {},
    explanatory: [],
    chart: [],
    source_ids: [],
    next_action: null,
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
  };
  await page.route("**/api/designs", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { designs: [mockDesign], count: 1 } });
    }
    return route.fulfill({
      json: { design: mockDesign, message: "created" },
    });
  });
  await page.goto("/?tab=designs");
  await page.getByRole("button", { name: /New Design/ }).click();
  await page.getByPlaceholder("Design title").fill("Test Design");
  await page.getByPlaceholder("State your hypothesis").fill("Test hypothesis");
  await page.getByPlaceholder("Describe the background").fill("Test background");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByText("Test Design")).toBeVisible({ timeout: 5000 });
});

// S6: Status filter — select "draft" filter, verify filtered results
test("S6: status filter sends correct API request", async ({ page }) => {
  let requestedUrl = "";
  await page.route("**/api/designs**", (route) => {
    requestedUrl = route.request().url();
    return route.fulfill({ json: { designs: [], count: 0 } });
  });
  await page.goto("/?tab=designs");
  await page.getByRole("combobox").click();
  await page.getByRole("option", { name: /draft/i }).click();
  await expect(() => expect(requestedUrl).toContain("status=draft")).toPass({
    timeout: 5000,
  });
});

// S7: Design detail expand — click design row, verify sub-tabs visible
test("S7: clicking design row shows detail sub-tabs", async ({ page }) => {
  const mockDesign = {
    id: "d-001",
    title: "Detail Test",
    status: "active",
    theme_id: "t-001",
    hypothesis_statement: "Hypothesis",
    hypothesis_background: "Background",
    parent_id: null,
    metrics: {},
    explanatory: [],
    chart: [],
    source_ids: [],
    next_action: null,
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
  };
  await page.route("**/api/designs", (route) =>
    route.fulfill({ json: { designs: [mockDesign], count: 1 } }),
  );
  await page.route("**/api/designs/d-001", (route) =>
    route.fulfill({ json: mockDesign }),
  );
  await page.goto("/?tab=designs");
  await page.getByText("Detail Test").click();
  await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByRole("tab", { name: /review/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /knowledge/i })).toBeVisible();
});

// S8: Source add with JSON validation — invalid JSON → error, valid JSON → success
test("S8: source add validates JSON and submits", async ({ page }) => {
  await page.route("**/api/catalog/sources**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { sources: [], count: 0 } });
    }
    return route.fulfill({
      json: {
        source: {
          id: "s-001",
          source_id: "test-src",
          name: "Test",
          type: "csv",
          description: "",
          connection: {},
          schema_info: [],
          tags: [],
          created_at: "2026-01-01T00:00:00",
          updated_at: "2026-01-01T00:00:00",
        },
        message: "Source created",
      },
    });
  });
  await page.route("**/api/catalog/knowledge**", (route) =>
    route.fulfill({ json: { entries: [], count: 0 } }),
  );
  await page.goto("/?tab=catalog");
  await page.getByRole("button", { name: "Add Source" }).first().click();
  await page.getByPlaceholder("Source ID").fill("s-001");
  await page.getByPlaceholder("Name").fill("Test Source");
  await page.getByPlaceholder("Description").fill("A test source");
  await page.getByPlaceholder(/Connection JSON/).fill("not-json");
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.getByText(/valid JSON/i)).toBeVisible();
  await page.getByPlaceholder(/Connection JSON/).fill('{"host": "localhost"}');
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.getByText(/valid JSON/i)).not.toBeVisible({
    timeout: 5000,
  });
});

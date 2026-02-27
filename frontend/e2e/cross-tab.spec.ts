import { test, expect } from "@playwright/test";
import { makeDesign, makeRulesContext } from "./fixtures/mock-data";
import { mockAllRoutesEmpty } from "./fixtures/api-routes";

// #27: Browser back — tab switch then browser back returns to previous tab
test("#27: browser back navigates to previous tab via popstate", async ({
  page,
}) => {
  // Mock all routes so every tab can render
  await mockAllRoutesEmpty(page);
  await page.route("**/api/rules/context", (route) =>
    route.fulfill({
      json: makeRulesContext({
        sources: [],
        knowledge_entries: [],
        rules: [],
        total_sources: 0,
        total_knowledge: 0,
        total_rules: 0,
      }),
    }),
  );

  await page.goto("/?tab=designs");
  await expect(page.getByRole("tab", { name: /designs/i })).toHaveAttribute(
    "data-state",
    "active",
    { timeout: 5000 },
  );

  // Navigate: designs → catalog → rules (creates 2 pushState entries)
  await page.getByRole("tab", { name: /catalog/i }).click();
  await expect(page).toHaveURL(/tab=catalog/);

  await page.getByRole("tab", { name: /rules/i }).click();
  await expect(page).toHaveURL(/tab=rules/);

  // First goBack: rules → catalog
  await page.goBack();
  await expect(page).toHaveURL(/tab=catalog/);
  await expect(page.getByRole("tab", { name: /catalog/i })).toHaveAttribute(
    "data-state",
    "active",
  );

  // Second goBack: catalog → designs
  await page.goBack();
  await expect(page).toHaveURL(/tab=designs/);
  await expect(page.getByRole("tab", { name: /designs/i })).toHaveAttribute(
    "data-state",
    "active",
  );
});

// #29: Loading spinner — visible during data fetch, disappears after response
test("#29: loading spinner visible during fetch", async ({ page }) => {
  // Promise gate pattern: hold the API response until we verify the spinner
  let resolveGate!: () => void;
  const gate = new Promise<void>((resolve) => {
    resolveGate = resolve;
  });

  await page.route("**/api/designs**", async (route) => {
    await gate;
    await route.fulfill({ json: { designs: [], count: 0 } });
  });

  // Navigate — the fetch is now blocked by the gate
  await page.goto("/?tab=designs");

  // Spinner/loading text should be visible while waiting
  await expect(page.getByText("Loading...")).toBeVisible({ timeout: 5000 });

  // Release the gate — response flows through
  resolveGate();

  // Loading indicator should disappear, replaced by empty state
  await expect(page.getByText("Loading...")).not.toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByText(/no designs found/i)).toBeVisible();
});

// #30: Empty state for all tabs (Designs covered by S4; this covers Catalog, Rules, History)
test("#30: empty state shown for catalog tab", async ({ page }) => {
  await page.route("**/api/catalog/sources**", (route) =>
    route.fulfill({ json: { sources: [], count: 0 } }),
  );
  await page.route("**/api/catalog/knowledge", (route) =>
    route.fulfill({ json: { entries: [], count: 0 } }),
  );

  await page.goto("/?tab=catalog");
  await expect(page.getByText(/no data sources found/i)).toBeVisible({
    timeout: 5000,
  });
});

test("#30: empty state shown for rules tab (no context)", async ({ page }) => {
  await page.route("**/api/rules/context", (route) =>
    route.fulfill({
      json: {
        sources: [],
        knowledge_entries: [],
        rules: [],
        total_sources: 0,
        total_knowledge: 0,
        total_rules: 0,
      },
    }),
  );

  await page.goto("/?tab=rules");
  // Rules page with 0 counts in all sections
  await expect(page.getByText("Sources (0)")).toBeVisible({ timeout: 5000 });
  await expect(page.getByText("Domain Knowledge (0)")).toBeVisible();
  await expect(page.getByText("Rules (0)")).toBeVisible();
});

test("#30: empty state shown for history tab", async ({ page }) => {
  await page.route("**/api/designs**", (route) =>
    route.fulfill({ json: { designs: [], count: 0 } }),
  );

  await page.goto("/?tab=history");
  await expect(page.getByText(/no designs found/i)).toBeVisible({
    timeout: 5000,
  });
});

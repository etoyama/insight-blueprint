import { test, expect } from "@playwright/test";
import { makeDesign, makeSource } from "./fixtures/mock-data";
import {
  mockDesignList,
  mockDesignDetail,
  mockSourceList,
  mockUnifiedKnowledge,
} from "./fixtures/api-routes";

// S1: Tab routing — navigate all 2 tabs, verify URL ?tab= sync
test("S1: tab routing syncs URL with tab selection", async ({ page }) => {
  await page.goto("/");
  const tabs = ["catalog", "designs"] as const;
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

// T-1.2: ?tab=rules falls back to designs
test("T-1.2: tab=rules falls back to designs", async ({ page }) => {
  await page.goto("/?tab=rules");
  await expect(page.getByRole("tab", { name: /designs/i })).toHaveAttribute(
    "data-state",
    "active",
  );
});

// T-1.3: ?tab=history falls back to designs
test("T-1.3: tab=history falls back to designs", async ({ page }) => {
  await page.goto("/?tab=history");
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
  await mockDesignList(page, []);
  await page.goto("/?tab=designs");
  await expect(page.getByText(/No designs found/)).toBeVisible({
    timeout: 5000,
  });
});

// S5: Create design dialog — open, fill form, submit, verify design appears
test("S5: create design dialog submits and refreshes list", async ({
  page,
}) => {
  const design = makeDesign({ status: "in_review" });
  await page.route("**/api/designs", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { designs: [design], count: 1 } });
    }
    return route.fulfill({
      json: { design, message: "created" },
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

// S6: Status filter — select "in_review" filter, verify filtered results
test("S6: status filter sends correct API request", async ({ page }) => {
  let requestedUrl = "";
  await page.route("**/api/designs**", (route) => {
    requestedUrl = route.request().url();
    return route.fulfill({ json: { designs: [], count: 0 } });
  });
  await page.goto("/?tab=designs");
  await page.getByRole("combobox").click();
  await page.getByRole("option", { name: /in.review/i }).click();
  await expect(() => expect(requestedUrl).toContain("status=in_review")).toPass({
    timeout: 5000,
  });
});

// S7: Design detail expand — click design row, verify sub-tabs visible
test("S7: clicking design row shows detail sub-tabs", async ({ page }) => {
  const design = makeDesign({ title: "Detail Test" });
  await mockDesignList(page, [design]);
  await mockDesignDetail(page, design);
  await page.goto("/?tab=designs");
  await page.getByText("Detail Test").click();
  await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByRole("tab", { name: /history/i }).first()).toBeVisible();
});

// S8: Source add with JSON validation — invalid JSON → error, valid JSON → success
test("S8: source add validates JSON and submits", async ({ page }) => {
  await mockSourceList(page, []);
  await mockUnifiedKnowledge(page, []);
  // POST handler for source creation (not covered by mockSourceList)
  await page.route("**/api/catalog/sources", (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      json: {
        source: makeSource(),
        message: "Source created",
      },
    });
  });
  await page.goto("/?tab=catalog");
  await page.getByRole("button", { name: "Add Source" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByPlaceholder("Source ID").fill("s-001");
  await dialog.getByPlaceholder("Name").fill("Test Source");
  await dialog.getByPlaceholder("Description").fill("A test source");
  await dialog.getByPlaceholder(/Connection JSON/).fill("not-json");
  await dialog.getByRole("button", { name: "Add" }).click();
  await expect(dialog.getByText(/valid JSON/i)).toBeVisible();
  await dialog.getByPlaceholder(/Connection JSON/).fill('{"host": "localhost"}');
  await dialog.getByRole("button", { name: "Add" }).click();
  await expect(dialog.getByText(/valid JSON/i)).not.toBeVisible({
    timeout: 5000,
  });
});

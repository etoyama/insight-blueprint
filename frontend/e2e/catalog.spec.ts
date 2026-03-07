import { test, expect } from "@playwright/test";
import {
  makeSource,
  makeColumnSchema,
  makeSearchResult,
  makeKnowledgeEntry,
  makeCaution,
} from "./fixtures/mock-data";
import {
  mockSourceList,
  mockSchema,
  mockCatalogSearch,
  mockUnifiedKnowledge,
} from "./fixtures/api-routes";

const source = makeSource({ id: "s-cat-1", name: "Sales Data" });

// #14: Schema display — click source row, column schema table appears
test("#14: clicking source row shows schema table", async ({ page }) => {
  const columns = [
    makeColumnSchema({ name: "user_id", type: "integer", description: "User ID" }),
    makeColumnSchema({ name: "email", type: "varchar", description: "Email address", nullable: true }),
  ];

  await mockSourceList(page, [source]);
  await mockSchema(page, source.id, columns);
  await mockUnifiedKnowledge(page, []);

  await page.goto("/?tab=catalog");
  // Click the source row
  await page.getByText("Sales Data").click();

  // Schema section should appear with column names
  await expect(page.getByText("Schema")).toBeVisible({ timeout: 5000 });
  await expect(page.getByText("user_id")).toBeVisible();
  await expect(page.getByRole("cell", { name: "email", exact: true })).toBeVisible();
  await expect(page.getByText("Email address")).toBeVisible();
});

// #15: Catalog search — enter query, search results shown
test("#15: catalog search displays results", async ({ page }) => {
  const results = [
    makeSearchResult({ source_id: "s-1", title: "revenue", snippet: "Monthly <b>revenue</b>" }),
    makeSearchResult({ source_id: "s-2", title: "cost", snippet: "Operating <b>cost</b>" }),
  ];

  await mockSourceList(page, [source]);
  await mockUnifiedKnowledge(page, []);
  await mockCatalogSearch(page, results);

  await page.goto("/?tab=catalog");

  // Fill search input and click Search (scoped to Catalog Search section)
  await page.getByPlaceholder("Search query...").fill("revenue");
  const catalogSearchSection = page.locator("section").filter({ hasText: "Catalog Search" });
  await catalogSearchSection.getByRole("button", { name: "Search" }).click();

  // Results should be visible
  await expect(page.getByText("Monthly revenue")).toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByText("Operating cost")).toBeVisible();
});

// #16: Knowledge list — domain knowledge entries with category/importance badges
test("#16: knowledge list shows entries with badges", async ({ page }) => {
  const entries = [
    makeKnowledgeEntry({
      key: "k-cat-1",
      title: "Revenue Seasonality",
      category: "methodology",
      importance: "high",
    }),
    makeKnowledgeEntry({
      key: "k-cat-2",
      title: "NULL Handling",
      category: "caution",
      importance: "medium",
    }),
    makeKnowledgeEntry({
      key: "k-cat-3",
      title: "Auto Finding",
      category: "finding",
      importance: "high",
    }),
  ];

  await mockSourceList(page, [source]);
  await mockUnifiedKnowledge(page, entries);

  await page.goto("/?tab=catalog");

  await expect(page.getByText("Domain Knowledge")).toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByText("Revenue Seasonality")).toBeVisible();
  await expect(page.getByText("NULL Handling")).toBeVisible();
  await expect(page.getByText("Auto Finding")).toBeVisible();
  await expect(page.getByText("methodology").first()).toBeVisible();
  await expect(page.getByText("caution").first()).toBeVisible();
  await expect(page.getByText("finding").first()).toBeVisible();
});

// T-2.3: Both catalog-registered and extracted entries in unified table
test("T-2.3: unified knowledge table shows both catalog and finding entries", async ({ page }) => {
  const entries = [
    makeKnowledgeEntry({ key: "k-meth", title: "Methodology Entry", category: "methodology" }),
    makeKnowledgeEntry({ key: "k-find", title: "Finding Entry", category: "finding" }),
  ];

  await mockSourceList(page, [source]);
  await mockUnifiedKnowledge(page, entries);

  await page.goto("/?tab=catalog");
  await expect(page.getByText("Domain Knowledge")).toBeVisible({ timeout: 5000 });
  await expect(page.getByText("Methodology Entry")).toBeVisible();
  await expect(page.getByText("Finding Entry")).toBeVisible();
});

// T-3.1: Caution search returns matching results
test("T-3.1: caution search in catalog returns matching results", async ({ page }) => {
  const cautions = [
    makeCaution({ key: "cau-1", title: "NULL Revenue", affects_columns: ["revenue"] }),
  ];

  await mockSourceList(page, [source]);
  await mockUnifiedKnowledge(page, []);
  await page.route("**/api/rules/cautions**", (route) =>
    route.fulfill({
      json: { table_names: ["sales"], cautions, count: cautions.length },
    }),
  );

  await page.goto("/?tab=catalog");
  const cautionSection = page.locator("section").filter({ hasText: "Caution Search" });
  await expect(cautionSection).toBeVisible({ timeout: 5000 });

  await page.getByPlaceholder("Table names (comma separated)").fill("sales");
  await cautionSection.getByRole("button", { name: "Search" }).click();

  await expect(page.getByText("NULL Revenue")).toBeVisible({ timeout: 5000 });
  await expect(page.getByRole("cell", { name: "revenue", exact: true })).toBeVisible();
});

// T-3.2: Caution search with no results shows empty state
test("T-3.2: caution search with no results shows empty state", async ({ page }) => {
  await mockSourceList(page, [source]);
  await mockUnifiedKnowledge(page, []);
  await page.route("**/api/rules/cautions**", (route) =>
    route.fulfill({
      json: { table_names: ["nonexistent"], cautions: [], count: 0 },
    }),
  );

  await page.goto("/?tab=catalog");
  const cautionSection = page.locator("section").filter({ hasText: "Caution Search" });
  await expect(cautionSection).toBeVisible({ timeout: 5000 });

  await page.getByPlaceholder("Table names (comma separated)").fill("nonexistent");
  await cautionSection.getByRole("button", { name: "Search" }).click();

  await expect(page.getByText(/no matching cautions/i)).toBeVisible({ timeout: 5000 });
});

// T-3.3: Caution search API error shows ErrorBanner
test("T-3.3: caution search API error shows error banner", async ({ page }) => {
  await mockSourceList(page, [source]);
  await mockUnifiedKnowledge(page, []);
  await page.route("**/api/rules/cautions**", (route) =>
    route.fulfill({
      status: 500,
      json: { error: "Internal server error" },
    }),
  );

  await page.goto("/?tab=catalog");
  const cautionSection = page.locator("section").filter({ hasText: "Caution Search" });
  await expect(cautionSection).toBeVisible({ timeout: 5000 });

  await page.getByPlaceholder("Table names (comma separated)").fill("sales");
  await cautionSection.getByRole("button", { name: "Search" }).click();

  await expect(page.getByRole("alert")).toBeVisible({ timeout: 5000 });
});

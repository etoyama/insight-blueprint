import { test, expect } from "@playwright/test";
import {
  makeSource,
  makeColumnSchema,
  makeSearchResult,
  makeKnowledgeEntry,
} from "./fixtures/mock-data";
import {
  mockSourceList,
  mockSchema,
  mockCatalogSearch,
  mockKnowledgeList,
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
  await mockKnowledgeList(page, []);

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
  await mockKnowledgeList(page, []);
  await mockCatalogSearch(page, results);

  await page.goto("/?tab=catalog");

  // Fill search input and click Search
  await page.getByPlaceholder("Search query...").fill("revenue");
  await page.getByRole("button", { name: "Search" }).click();

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
  ];

  await mockSourceList(page, [source]);
  await mockKnowledgeList(page, entries);

  await page.goto("/?tab=catalog");

  // Knowledge section with entries
  await expect(page.getByText("Domain Knowledge")).toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByText("Revenue Seasonality")).toBeVisible();
  await expect(page.getByText("NULL Handling")).toBeVisible();
  // Category and importance badges
  await expect(page.getByText("methodology").first()).toBeVisible();
  await expect(page.getByText("caution").first()).toBeVisible();
});

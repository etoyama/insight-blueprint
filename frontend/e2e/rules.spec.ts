import { test, expect } from "@playwright/test";
import { makeRulesContext, makeCaution } from "./fixtures/mock-data";
import { mockRulesContext, mockCautions } from "./fixtures/api-routes";

const context = makeRulesContext();

// #17: Context display — Rules tab shows Sources/Knowledge/Rules sections with counts
test("#17: rules context shows three collapsible sections with counts", async ({
  page,
}) => {
  await mockRulesContext(page, context);

  await page.goto("/?tab=rules");

  // Three sections with counts
  await expect(
    page.getByText(`Sources (${context.total_sources})`),
  ).toBeVisible({ timeout: 5000 });
  await expect(
    page.getByText(`Domain Knowledge (${context.total_knowledge})`),
  ).toBeVisible();
  await expect(
    page.getByText(`Rules (${context.total_rules})`),
  ).toBeVisible();
});

// #18: Section expand/collapse — click each section header, content toggles
test("#18: collapsible sections expand and collapse", async ({ page }) => {
  await mockRulesContext(page, context);

  await page.goto("/?tab=rules");
  await expect(
    page.getByText(`Sources (${context.total_sources})`),
  ).toBeVisible({ timeout: 5000 });

  // Initially collapsed — source name should not be visible
  await expect(page.getByText("Sales DB")).not.toBeVisible();

  // Click Sources section to expand
  await page.getByText(`Sources (${context.total_sources})`).click();
  await expect(page.getByText("Sales DB")).toBeVisible({ timeout: 3000 });

  // Click again to collapse
  await page.getByText(`Sources (${context.total_sources})`).click();
  await expect(page.getByText("Sales DB")).not.toBeVisible();
});

// #19: Cautions search — enter table name, see related cautions
test("#19: cautions search returns matching results", async ({ page }) => {
  const cautions = [
    makeCaution({ key: "cau-1", title: "NULL Revenue", affects_columns: ["revenue"] }),
  ];

  await mockRulesContext(page, context);
  await mockCautions(page, cautions);

  await page.goto("/?tab=rules");
  await expect(page.getByText("Caution Search")).toBeVisible({ timeout: 5000 });

  await page.getByPlaceholder("Table names (comma separated)").fill("sales");
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page.getByText("NULL Revenue")).toBeVisible({ timeout: 5000 });
  await expect(page.getByRole("cell", { name: "revenue", exact: true })).toBeVisible();
});

// #20: Empty cautions — non-existent table name shows EmptyState
test("#20: cautions search with no results shows empty state", async ({
  page,
}) => {
  await mockRulesContext(page, context);
  await mockCautions(page, []);

  await page.goto("/?tab=rules");
  await expect(page.getByText("Caution Search")).toBeVisible({ timeout: 5000 });

  await page
    .getByPlaceholder("Table names (comma separated)")
    .fill("nonexistent_table");
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page.getByText(/no matching cautions/i)).toBeVisible({
    timeout: 5000,
  });
});

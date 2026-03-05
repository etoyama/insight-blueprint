import { test, expect } from "@playwright/test";
import { makeDesign, makeReviewBatch, makeBatchComment } from "./fixtures/mock-data";

// #21: Timeline display — all designs in updated_at descending order
test("#21: history timeline shows designs in descending order", async ({
  page,
}) => {
  const designs = [
    makeDesign({
      id: "d-old",
      title: "Old Design",
      status: "supported",
      updated_at: "2026-01-01T00:00:00",
      created_at: "2025-12-01T00:00:00",
    }),
    makeDesign({
      id: "d-new",
      title: "New Design",
      status: "active",
      updated_at: "2026-02-15T00:00:00",
      created_at: "2026-02-15T00:00:00",
    }),
  ];

  await page.route("**/api/designs**", (route) =>
    route.fulfill({ json: { designs, count: designs.length } }),
  );

  await page.goto("/?tab=history");

  // Both designs visible
  await expect(page.getByText("New Design")).toBeVisible({ timeout: 5000 });
  await expect(page.getByText("Old Design")).toBeVisible();

  // Verify order: "New Design" should appear before "Old Design" in the DOM
  const cards = page.locator('[class*="cursor-pointer"]');
  const firstCardText = await cards.first().textContent();
  expect(firstCardText).toContain("New Design");
});

// #22: History expand — click entry, review batch history shown
test("#22: clicking history entry shows review batches", async ({ page }) => {
  const design = makeDesign({ id: "d-hist", title: "History Design" });
  const batches = [
    makeReviewBatch({
      id: "RB-h1",
      design_id: "d-hist",
      status_after: "supported",
      reviewer: "alice",
      comments: [makeBatchComment({ comment: "First review note" })],
    }),
    makeReviewBatch({
      id: "RB-h2",
      design_id: "d-hist",
      status_after: "rejected",
      reviewer: "bob",
      comments: [makeBatchComment({ comment: "Second review note" })],
    }),
  ];

  await page.route("**/api/designs**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { designs: [design], count: 1 },
      });
    }
    return route.continue();
  });
  await page.route(`**/api/designs/${design.id}/review-batches`, (route) =>
    route.fulfill({
      json: { design_id: design.id, batches, count: batches.length },
    }),
  );

  await page.goto("/?tab=history");
  await expect(page.getByText("History Design")).toBeVisible({ timeout: 5000 });

  // Click to expand
  await page.getByText("History Design").click();

  // Review batch comments should appear
  await expect(page.getByText("First review note")).toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByText("Second review note")).toBeVisible();
  await expect(page.getByText("alice")).toBeVisible();
  await expect(page.getByText("bob")).toBeVisible();
});

// #23: Empty history — 0 designs shows EmptyState
test("#23: empty history shows empty state", async ({ page }) => {
  await page.route("**/api/designs**", (route) =>
    route.fulfill({ json: { designs: [], count: 0 } }),
  );

  await page.goto("/?tab=history");
  await expect(page.getByText(/no designs found/i)).toBeVisible({
    timeout: 5000,
  });
});

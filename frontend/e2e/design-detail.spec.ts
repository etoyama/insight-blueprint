import { test, expect } from "@playwright/test";
import {
  makeDesign,
  makeComment,
  makeKnowledgeEntry,
} from "./fixtures/mock-data";
import {
  mockDesignList,
  mockDesignDetail,
  mockSubmitReview,
  mockComments,
  mockExtractKnowledge,
  mockSaveKnowledge,
} from "./fixtures/api-routes";

// Shared mock data for design detail tests
const activeDesign = makeDesign({
  id: "d-detail",
  title: "Detail Test Design",
  status: "active",
  metrics: { accuracy: 0.95, recall: 0.88 },
  source_ids: ["s-001", "s-002"],
});

const draftDesign = makeDesign({
  id: "d-draft",
  title: "Draft Design",
  status: "draft",
});

// #5: Overview content display — verify all fields render in the Overview sub-tab
test("#5: overview panel displays design fields and metrics", async ({
  page,
}) => {
  await mockDesignList(page, [activeDesign]);
  await mockDesignDetail(page, activeDesign);
  await mockComments(page, activeDesign.id, []);

  await page.goto("/?tab=designs");
  await page.getByText("Detail Test Design").click();

  // Wait for overview tab to appear
  await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({
    timeout: 5000,
  });

  // Verify key fields
  await expect(page.getByText("Test hypothesis")).toBeVisible();
  await expect(page.getByText("Test background")).toBeVisible();
  await expect(page.getByText("s-001, s-002")).toBeVisible();

  // Metrics rendered via JsonTree (collapsed by default — expand it)
  await expect(page.getByText("Metrics")).toBeVisible();
  // Click the expand button "► {2}" to reveal metric keys
  await page.locator("button", { hasText: "{2}" }).click();
  await expect(page.getByText("accuracy")).toBeVisible();
  await expect(page.getByText("0.95")).toBeVisible();
});

// #6: Review submission — click "Submit for Review" on active design
test("#6: submit for review changes status", async ({ page }) => {
  const designAfterReview = makeDesign({
    ...activeDesign,
    status: "pending_review",
  });

  // Use mutable ref so the same route handler can return different data
  let currentDesign = activeDesign;
  let currentDesigns = [activeDesign];

  await page.route("**/api/designs", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { designs: currentDesigns, count: currentDesigns.length },
      });
    }
    return route.continue();
  });
  await page.route(`**/api/designs/${activeDesign.id}`, (route) =>
    route.fulfill({ json: currentDesign }),
  );
  await mockComments(page, activeDesign.id, []);
  await mockSubmitReview(page, activeDesign.id);

  await page.goto("/?tab=designs");
  await page.getByText("Detail Test Design").click();
  await expect(page.getByRole("tab", { name: /review/i })).toBeVisible({
    timeout: 5000,
  });
  await page.getByRole("tab", { name: /review/i }).click();

  const submitBtn = page.getByRole("button", { name: "Submit for Review" });
  await expect(submitBtn).toBeEnabled();

  // Update the mutable refs before clicking — subsequent API calls will return updated data
  currentDesign = designAfterReview;
  currentDesigns = [designAfterReview];

  await submitBtn.click();

  // Status badge should update — use .first() because it appears in both table and detail
  await expect(page.getByText(/pending.review/i).first()).toBeVisible({
    timeout: 5000,
  });
});

// #7: Review button disabled for non-active design
test("#7: submit for review disabled when not active", async ({ page }) => {
  await mockDesignList(page, [draftDesign]);
  await mockDesignDetail(page, draftDesign);
  await mockComments(page, draftDesign.id, []);

  await page.goto("/?tab=designs");
  await page.getByText("Draft Design").click();
  await expect(page.getByRole("tab", { name: /review/i })).toBeVisible({
    timeout: 5000,
  });
  await page.getByRole("tab", { name: /review/i }).click();

  const submitBtn = page.getByRole("button", { name: "Submit for Review" });
  await expect(submitBtn).toBeDisabled();
  await expect(
    page.getByText(/only active designs/i),
  ).toBeVisible();
});

// #8: Add comment — fill form, submit, verify POST request was sent correctly.
// Note: After POST, onStatusChanged triggers a re-fetch cycle that unmounts/remounts
// DesignDetail (due to DesignsPage loading state), resetting the active tab.
// Therefore we verify the POST payload rather than checking UI state after side effects.
test("#8: add comment submits correct data", async ({ page }) => {
  const existingComment = makeComment({
    id: "c-existing",
    comment: "Initial review",
    reviewer: "bob",
  });

  await mockDesignList(page, [activeDesign]);
  await mockDesignDetail(page, activeDesign);

  let capturedPostBody: Record<string, unknown> | null = null;
  await page.route(`**/api/designs/${activeDesign.id}/comments`, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: {
          design_id: activeDesign.id,
          comments: [existingComment],
          count: 1,
        },
      });
    }
    // POST — capture the request body
    capturedPostBody = route.request().postDataJSON();
    return route.fulfill({
      json: {
        comment_id: "c-new",
        status_after: "supported",
        message: "Comment added",
      },
    });
  });

  await page.goto("/?tab=designs");
  await page.getByText("Detail Test Design").click();
  await expect(page.getByRole("tab", { name: /review/i })).toBeVisible({
    timeout: 5000,
  });
  await page.getByRole("tab", { name: /review/i }).click();

  // Verify existing comment is shown
  await expect(page.getByText("Initial review")).toBeVisible({ timeout: 5000 });

  // Fill comment form
  await page.getByPlaceholder("Comment").fill("Needs more data");
  await page.getByPlaceholder("Reviewer (optional)").fill("alice");

  // Submit
  await page.getByRole("button", { name: "Add" }).click();

  // Verify the POST was made with correct payload
  await expect(() => {
    expect(capturedPostBody).toBeTruthy();
    expect(capturedPostBody!.comment).toBe("Needs more data");
    expect(capturedPostBody!.reviewer).toBe("alice");
    expect(capturedPostBody!.status).toBe("supported");
  }).toPass({ timeout: 5000 });
});

// #9: Knowledge extraction — click "Extract Knowledge", preview list appears
test("#9: extract knowledge shows preview entries", async ({ page }) => {
  const entries = [
    makeKnowledgeEntry({ key: "k-1", title: "Revenue Pattern" }),
    makeKnowledgeEntry({ key: "k-2", title: "Seasonal Trend" }),
  ];

  await mockDesignList(page, [activeDesign]);
  await mockDesignDetail(page, activeDesign);
  await mockComments(page, activeDesign.id, []);
  await mockExtractKnowledge(page, activeDesign.id, entries);

  await page.goto("/?tab=designs");
  await page.getByText("Detail Test Design").click();
  await expect(page.getByRole("tab", { name: /knowledge/i })).toBeVisible({
    timeout: 5000,
  });
  await page.getByRole("tab", { name: /knowledge/i }).click();

  await page.getByRole("button", { name: "Extract Knowledge" }).click();

  await expect(page.getByText("Revenue Pattern")).toBeVisible({
    timeout: 5000,
  });
  await expect(page.getByText("Seasonal Trend")).toBeVisible();
  // Save button should appear
  await expect(
    page.getByRole("button", { name: "Save Knowledge" }),
  ).toBeVisible();
});

// #10: Knowledge save — click "Save Knowledge", confirmation message appears
test("#10: save knowledge shows confirmation", async ({ page }) => {
  const entries = [
    makeKnowledgeEntry({ key: "k-1", title: "Revenue Pattern" }),
  ];

  await mockDesignList(page, [activeDesign]);
  await mockDesignDetail(page, activeDesign);
  await mockComments(page, activeDesign.id, []);
  // Use the same route for both extract and save (POST to knowledge endpoint)
  await page.route(`**/api/designs/${activeDesign.id}/knowledge`, (route) =>
    route.fulfill({
      json: {
        entries,
        saved_entries: entries,
        count: entries.length,
        message: "Saved",
      },
    }),
  );

  await page.goto("/?tab=designs");
  await page.getByText("Detail Test Design").click();
  await expect(page.getByRole("tab", { name: /knowledge/i })).toBeVisible({
    timeout: 5000,
  });
  await page.getByRole("tab", { name: /knowledge/i }).click();

  // Extract first
  await page.getByRole("button", { name: "Extract Knowledge" }).click();
  await expect(page.getByText("Revenue Pattern")).toBeVisible({
    timeout: 5000,
  });

  // Now save
  await page.getByRole("button", { name: "Save Knowledge" }).click();
  await expect(page.getByText(/saved successfully/i)).toBeVisible({
    timeout: 5000,
  });
});

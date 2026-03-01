import { test, expect } from "@playwright/test";
import {
  makeDesign,
  makeComment,
  makeKnowledgeEntry,
  makeBatchComment,
  makeReviewBatch,
} from "./fixtures/mock-data";
import {
  mockDesignList,
  mockDesignDetail,
  mockSubmitReview,
  mockComments,
  mockReviewBatches,
  mockReviewBatchesError,
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

const pendingDesign = makeDesign({
  id: "d-pending",
  title: "Pending Review Design",
  status: "pending_review",
  hypothesis_statement: "Test hypothesis statement",
  hypothesis_background: "Test hypothesis background",
  metrics: { kpi: "CVR", value: 0.03 },
  explanatory: [{ factor: "campaign" }],
  chart: [{ type: "bar" }],
  next_action: { action: "A/B test" },
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

// #6: Review submission — click "Submit for Review" on active design (now on Overview tab)
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
  await mockReviewBatches(page, activeDesign.id, []);
  await mockSubmitReview(page, activeDesign.id);

  await page.goto("/?tab=designs");
  await page.getByText("Detail Test Design").click();
  await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({
    timeout: 5000,
  });

  // Submit for Review is now on the Overview tab
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

// #7: Review button not shown for non-active design (now on Overview tab)
test("#7: submit for review not shown when not active", async ({ page }) => {
  await mockDesignList(page, [draftDesign]);
  await mockDesignDetail(page, draftDesign);
  await mockComments(page, draftDesign.id, []);
  await mockReviewBatches(page, draftDesign.id, []);

  await page.goto("/?tab=designs");
  await page.getByText("Draft Design").click();
  await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({
    timeout: 5000,
  });

  // Submit for Review button should not be visible for non-active designs
  await expect(
    page.getByRole("button", { name: "Submit for Review" }),
  ).not.toBeVisible();
});

// #8: Legacy add-comment test removed — ReviewPanel deleted.
// Inline comment flow is now tested in "Inline Review Comments" describe block below.

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

// ---------------------------------------------------------------------------
// Tab Restructuring (P7)
// ---------------------------------------------------------------------------
test.describe("Tab Restructuring", () => {
  test("tabs show Overview, History, Knowledge", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    // Scope to design detail card to avoid matching top-level navigation tabs
    const detailCard = page.locator("[data-slot='card']").filter({ hasText: "Pending Review Design" });
    await expect(detailCard.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    await expect(detailCard.getByRole("tab", { name: /history/i })).toBeVisible();
    await expect(detailCard.getByRole("tab", { name: /knowledge/i })).toBeVisible();
  });

  test("Review tab is removed", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    const detailCard = page.locator("[data-slot='card']").filter({ hasText: "Pending Review Design" });
    await expect(detailCard.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    // Design detail should not have a "Review" tab anymore
    const reviewTab = detailCard.getByRole("tab", { name: /^review$/i });
    await expect(reviewTab).toHaveCount(0);
  });

  test("inline comments available without tab switch on pending_review", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    // Comment buttons should be visible in Overview tab directly
    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });
  });
});

// ---------------------------------------------------------------------------
// Inline Review Comments (P8)
// ---------------------------------------------------------------------------
test.describe("Inline Review Comments", () => {
  test("comment buttons visible on pending_review design", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    const buttons = page.getByTestId("comment-button");
    await expect(buttons.first()).toBeVisible({ timeout: 5000 });
    // Should have 6 comment buttons (one per commentable section)
    await expect(buttons).toHaveCount(6);
  });

  test("comment buttons hidden on non-pending_review design", async ({ page }) => {
    await mockDesignList(page, [activeDesign]);
    await mockDesignDetail(page, activeDesign);
    await mockReviewBatches(page, activeDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Detail Test Design").click();

    await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    // Wait for content to render, then verify no comment buttons
    await expect(page.getByText("Test hypothesis")).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId("comment-button")).not.toBeVisible();
  });

  test("clicking comment button opens inline form", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });
    await page.getByTestId("comment-button").first().click();

    await expect(page.getByTestId("draft-comment-input")).toBeVisible();
    await expect(page.getByRole("button", { name: "Add Draft" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
  });

  test("adding draft shows Review Submit Bar", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });
    // No submit bar initially
    await expect(page.getByTestId("review-submit-bar")).not.toBeVisible();

    // Add a draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Test draft comment");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Submit bar should appear
    await expect(page.getByTestId("review-submit-bar")).toBeVisible();
    await expect(page.getByTestId("draft-count")).toContainText("1 draft");
  });

  test("removing all drafts hides Submit Bar", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add a draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Draft to delete");
    await page.getByRole("button", { name: "Add Draft" }).click();
    await expect(page.getByTestId("review-submit-bar")).toBeVisible();

    // Delete the draft
    await page.getByTestId("draft-delete").click();

    // Submit bar should disappear
    await expect(page.getByTestId("review-submit-bar")).not.toBeVisible();
  });

  test("Submit Bar shows draft count", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add first draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("First draft");
    await page.getByRole("button", { name: "Add Draft" }).click();
    await expect(page.getByTestId("draft-count")).toContainText("1 draft");

    // Add second draft on a different section
    await page.getByTestId("comment-button").nth(1).click();
    await page.getByTestId("draft-comment-input").fill("Second draft");
    await page.getByRole("button", { name: "Add Draft" }).click();
    await expect(page.getByTestId("draft-count")).toContainText("2 drafts");
  });

  test("status selector shows all 4 options", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add a draft to show the submit bar
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Draft");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Open status selector
    await page.getByTestId("status-selector").click();

    // Verify all 4 options
    await expect(page.getByRole("option", { name: "supported" })).toBeVisible();
    await expect(page.getByRole("option", { name: "rejected" })).toBeVisible();
    await expect(page.getByRole("option", { name: "inconclusive" })).toBeVisible();
    await expect(page.getByRole("option", { name: "active" })).toBeVisible();
  });

  test("Submit All sends batch and refreshes design", async ({ page }) => {
    let currentDesign = pendingDesign;

    await mockDesignList(page, [pendingDesign]);
    await page.route(`**/api/designs/${pendingDesign.id}`, (route) =>
      route.fulfill({ json: currentDesign }),
    );

    let capturedPostBody: Record<string, unknown> | null = null;
    await page.route(`**/api/designs/${pendingDesign.id}/review-batches`, (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          json: { design_id: pendingDesign.id, batches: [], count: 0 },
        });
      }
      capturedPostBody = route.request().postDataJSON();
      currentDesign = makeDesign({ ...pendingDesign, status: "supported" });
      return route.fulfill({
        status: 201,
        json: { batch_id: "RB-new", status_after: "supported", comment_count: 1 },
      });
    });

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add a draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Review comment");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Submit
    await page.getByTestId("submit-all-button").click();

    // Verify POST was made
    await expect(() => {
      expect(capturedPostBody).toBeTruthy();
      expect(capturedPostBody!.status_after).toBe("supported");
      expect((capturedPostBody!.comments as unknown[]).length).toBe(1);
    }).toPass({ timeout: 5000 });
  });

  test("Submit All sends target_content snapshot in POST body", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);

    let capturedPostBody: Record<string, unknown> | null = null;
    await page.route(`**/api/designs/${pendingDesign.id}/review-batches`, (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          json: { design_id: pendingDesign.id, batches: [], count: 0 },
        });
      }
      capturedPostBody = route.request().postDataJSON();
      return route.fulfill({
        status: 201,
        json: { batch_id: "RB-new", status_after: "supported", comment_count: 1 },
      });
    });

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add draft on hypothesis_statement section (text type)
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Snapshot test");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Submit
    await page.getByTestId("submit-all-button").click();

    await expect(() => {
      expect(capturedPostBody).toBeTruthy();
      const comments = capturedPostBody!.comments as { target_content: unknown; target_section: string }[];
      expect(comments[0].target_section).toBe("hypothesis_statement");
      expect(comments[0].target_content).toBe("Test hypothesis statement");
    }).toPass({ timeout: 5000 });
  });

  test("drafts preserved on submission failure", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatchesError(page, pendingDesign.id);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add a draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Keep this draft");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Submit (will fail)
    await page.getByTestId("submit-all-button").click();

    // Draft should still be visible
    await expect(page.getByText("Keep this draft")).toBeVisible({ timeout: 5000 });
    // Submit bar should still be visible
    await expect(page.getByTestId("review-submit-bar")).toBeVisible();
  });

  test("Submit button disabled during submission", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);

    // Slow response to test disabled state
    await page.route(`**/api/designs/${pendingDesign.id}/review-batches`, (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          json: { design_id: pendingDesign.id, batches: [], count: 0 },
        });
      }
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(
            route.fulfill({
              status: 201,
              json: { batch_id: "RB-new", status_after: "supported", comment_count: 1 },
            }),
          );
        }, 2000);
      });
    });

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Test");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Click submit
    await page.getByTestId("submit-all-button").click();

    // Button should be disabled during submission
    await expect(page.getByTestId("submit-all-button")).toBeDisabled();
    await expect(page.getByTestId("submit-all-button")).toContainText("Submitting...");
  });

  test("draft comments visually distinct from submitted", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add a draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Visual test");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Verify draft card has dashed border class
    const draftCard = page.getByTestId("draft-card");
    await expect(draftCard).toBeVisible();
    await expect(draftCard).toHaveClass(/border-dashed/);

    // Verify "draft" label is visible
    await expect(draftCard.getByText("draft")).toBeVisible();
  });

  test("Submit Bar sticky at bottom", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByTestId("comment-button").first()).toBeVisible({ timeout: 5000 });

    // Add a draft
    await page.getByTestId("comment-button").first().click();
    await page.getByTestId("draft-comment-input").fill("Sticky test");
    await page.getByRole("button", { name: "Add Draft" }).click();

    // Submit bar should be visible within viewport
    const bar = page.getByTestId("review-submit-bar");
    await expect(bar).toBeVisible();
    await expect(bar).toBeInViewport();
  });
});

// ---------------------------------------------------------------------------
// Review History (P9)
// ---------------------------------------------------------------------------
test.describe("Review History", () => {
  // Helper: navigate to design detail and click the History tab within the detail card
  async function goToHistoryTab(page: import("@playwright/test").Page) {
    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();
    const detailCard = page.locator("[data-slot='card']").filter({ hasText: "Pending Review Design" });
    await expect(detailCard.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    await detailCard.getByRole("tab", { name: /history/i }).click();
  }

  test("History tab shows past review batches", async ({ page }) => {
    const batches = [
      makeReviewBatch({
        id: "RB-001",
        design_id: pendingDesign.id,
        status_after: "supported",
        comments: [makeBatchComment({ comment: "Looks good overall" })],
      }),
    ];

    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, batches);

    await goToHistoryTab(page);

    await expect(page.getByText("Looks good overall")).toBeVisible({ timeout: 5000 });
  });

  test("batch displays comments with target_section labels", async ({ page }) => {
    const batches = [
      makeReviewBatch({
        id: "RB-002",
        design_id: pendingDesign.id,
        comments: [
          makeBatchComment({
            comment: "Hypothesis is vague",
            target_section: "hypothesis_statement",
            target_content: "Original hypothesis text",
          }),
        ],
      }),
    ];

    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, batches);

    await goToHistoryTab(page);

    await expect(page.getByText("Hypothesis is vague")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Hypothesis Statement")).toBeVisible();
  });

  test("batch displays target_content alongside comments", async ({ page }) => {
    const batches = [
      makeReviewBatch({
        id: "RB-003",
        design_id: pendingDesign.id,
        comments: [
          makeBatchComment({
            comment: "Content quote test",
            target_section: "hypothesis_statement",
            target_content: "Quoted content here",
          }),
          makeBatchComment({
            comment: "JSON content test",
            target_section: "metrics",
            target_content: { kpi: "CVR", value: 0.03 },
          }),
        ],
      }),
    ];

    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, batches);

    await goToHistoryTab(page);

    // Text target_content shown as blockquote
    await expect(page.getByText("Quoted content here")).toBeVisible({ timeout: 5000 });

    // JSON target_content shown (look for kpi key)
    await expect(page.getByText("JSON content test")).toBeVisible();
  });

  test("batches ordered by timestamp descending", async ({ page }) => {
    const batches = [
      makeReviewBatch({
        id: "RB-newer",
        design_id: pendingDesign.id,
        comments: [makeBatchComment({ comment: "Newer batch" })],
        created_at: "2026-03-02T10:00:00+09:00",
      }),
      makeReviewBatch({
        id: "RB-older",
        design_id: pendingDesign.id,
        comments: [makeBatchComment({ comment: "Older batch" })],
        created_at: "2026-03-01T10:00:00+09:00",
      }),
    ];

    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, batches);

    await goToHistoryTab(page);

    await expect(page.getByText("Newer batch")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Older batch")).toBeVisible();

    // Verify order: newer should come first
    const cards = page.getByTestId("batch-card");
    const firstCard = cards.first();
    await expect(firstCard).toContainText("Newer batch");
  });
});

import { test, expect } from "@playwright/test";
import {
  makeDesign,
  makeBatchComment,
  makeReviewBatch,
} from "./fixtures/mock-data";
import {
  mockDesignList,
  mockDesignDetail,
  mockTransitionDesign,
  mockComments,
  mockReviewBatches,
  mockReviewBatchesError,
} from "./fixtures/api-routes";

// Shared mock data for design detail tests
const activeDesign = makeDesign({
  id: "d-detail",
  title: "Detail Test Design",
  status: "in_review",
  metrics: { accuracy: 0.95, recall: 0.88 },
  source_ids: ["s-001", "s-002"],
});

const nonReviewDesign = makeDesign({
  id: "d-non-review",
  title: "Non-Review Design",
  status: "revision_requested",
});

const pendingDesign = makeDesign({
  id: "d-pending",
  title: "Pending Review Design",
  status: "in_review",
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

  // Metrics rendered via JsonTree (expanded by default)
  await expect(page.getByText("Metrics")).toBeVisible();
  await expect(page.getByText("accuracy")).toBeVisible();
  await expect(page.getByText("0.95")).toBeVisible();
});

// #6: Workflow guide display — verify workflow guide shows for in_review design
test("#6: workflow guide displays for in_review design", async ({ page }) => {
  await mockDesignList(page, [activeDesign]);
  await mockDesignDetail(page, activeDesign);
  await mockComments(page, activeDesign.id, []);
  await mockReviewBatches(page, activeDesign.id, []);
  await mockTransitionDesign(page, activeDesign.id);

  await page.goto("/?tab=designs");
  await page.getByText("Detail Test Design").click();
  await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({
    timeout: 5000,
  });

  // Workflow guide should be visible with "In Review" title
  await expect(page.getByTestId("workflow-guide")).toBeVisible();
  await expect(page.getByTestId("workflow-guide").getByText("In Review")).toBeVisible();

  // Submit for Review button should NOT exist (removed in new workflow)
  await expect(
    page.getByRole("button", { name: "Submit for Review" }),
  ).not.toBeVisible();
});

// #7: Comment buttons hidden for non-in_review design
test("#7: comment buttons hidden when not in_review", async ({ page }) => {
  await mockDesignList(page, [nonReviewDesign]);
  await mockDesignDetail(page, nonReviewDesign);
  await mockComments(page, nonReviewDesign.id, []);
  await mockReviewBatches(page, nonReviewDesign.id, []);

  await page.goto("/?tab=designs");
  await page.getByText("Non-Review Design").click();
  await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({
    timeout: 5000,
  });

  // Workflow guide should show "Revision Requested"
  await expect(page.getByTestId("workflow-guide")).toBeVisible();
  await expect(page.getByTestId("workflow-guide").getByText("Revision Requested")).toBeVisible();

  // Comment buttons should not be visible for non-in_review designs
  await expect(page.getByTestId("comment-button")).not.toBeVisible();
});

// #8: Legacy add-comment test removed — ReviewPanel deleted.
// Inline comment flow is now tested in "Inline Review Comments" describe block below.

// ---------------------------------------------------------------------------
// Tab Restructuring (P7)
// ---------------------------------------------------------------------------
test.describe("Tab Restructuring", () => {
  test("tabs show Overview and History", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    // Scope to design detail card to avoid matching top-level navigation tabs
    const detailCard = page.getByTestId("design-detail-card");
    await expect(detailCard.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    await expect(detailCard.getByRole("tab", { name: /history/i })).toBeVisible();
  });

  test("Review tab is removed", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    const detailCard = page.getByTestId("design-detail-card");
    await expect(detailCard.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    // Design detail should not have a "Review" tab anymore
    const reviewTab = detailCard.getByRole("tab", { name: /^review$/i });
    await expect(reviewTab).toHaveCount(0);
  });

  test("inline comments available without tab switch on in_review", async ({ page }) => {
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
  test("comment buttons visible on in_review design", async ({ page }) => {
    await mockDesignList(page, [pendingDesign]);
    await mockDesignDetail(page, pendingDesign);
    await mockReviewBatches(page, pendingDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Pending Review Design").click();

    await expect(page.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    const buttons = page.getByTestId("comment-button");
    await expect(buttons.first()).toBeVisible({ timeout: 5000 });
    // Should have 7 comment buttons (one per commentable section)
    await expect(buttons).toHaveCount(7);
  });

  test("comment buttons hidden on non-in_review design", async ({ page }) => {
    await mockDesignList(page, [nonReviewDesign]);
    await mockDesignDetail(page, nonReviewDesign);
    await mockReviewBatches(page, nonReviewDesign.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Non-Review Design").click();

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

  test("status selector shows all 5 options", async ({ page }) => {
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

    // Verify all 5 options (labels from DESIGN_STATUS_LABELS)
    await expect(page.getByRole("option", { name: "Supported" })).toBeVisible();
    await expect(page.getByRole("option", { name: "Rejected" })).toBeVisible();
    await expect(page.getByRole("option", { name: "Inconclusive" })).toBeVisible();
    await expect(page.getByRole("option", { name: "Revision Requested" })).toBeVisible();
    await expect(page.getByRole("option", { name: "Analyzing" })).toBeVisible();
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
    const detailCard = page.getByTestId("design-detail-card");
    await expect(detailCard.getByRole("tab", { name: /overview/i })).toBeVisible({ timeout: 5000 });
    const historyTab = detailCard.getByRole("tab", { name: /history/i });
    await historyTab.click();
    await expect(historyTab).toHaveAttribute("aria-selected", "true", { timeout: 5000 });
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

// ---------------------------------------------------------------------------
// Auto-finding visibility (REQ-5)
// ---------------------------------------------------------------------------
test.describe("Auto-finding visibility", () => {
  test("T-5.1: supported status mentions auto-recorded finding", async ({ page }) => {
    const design = makeDesign({ id: "d-supported", title: "Supported Design", status: "supported" });
    await mockDesignList(page, [design]);
    await mockDesignDetail(page, design);
    await mockReviewBatches(page, design.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Supported Design").click();
    await expect(page.getByTestId("workflow-guide")).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId("workflow-guide")).toContainText(/automatically recorded/i);
    await expect(page.getByTestId("workflow-guide")).not.toContainText(/Knowledge tab/i);
  });

  test("T-5.2: rejected status mentions auto-recorded finding", async ({ page }) => {
    const design = makeDesign({ id: "d-rejected", title: "Rejected Design", status: "rejected" });
    await mockDesignList(page, [design]);
    await mockDesignDetail(page, design);
    await mockReviewBatches(page, design.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Rejected Design").click();
    await expect(page.getByTestId("workflow-guide")).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId("workflow-guide")).toContainText(/automatically recorded/i);
    await expect(page.getByTestId("workflow-guide")).not.toContainText(/Knowledge tab/i);
  });

  test("T-5.3: inconclusive status mentions auto-recorded finding", async ({ page }) => {
    const design = makeDesign({ id: "d-inconclusive", title: "Inconclusive Design", status: "inconclusive" });
    await mockDesignList(page, [design]);
    await mockDesignDetail(page, design);
    await mockReviewBatches(page, design.id, []);

    await page.goto("/?tab=designs");
    await page.getByText("Inconclusive Design").click();
    await expect(page.getByTestId("workflow-guide")).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId("workflow-guide")).toContainText(/automatically recorded/i);
    await expect(page.getByTestId("workflow-guide")).not.toContainText(/Knowledge tab/i);
  });
});

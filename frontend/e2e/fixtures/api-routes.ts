// Route-setup helpers for Playwright E2E tests.
// Each helper registers page.route() interceptors for a specific API group.
// Tests call these in beforeEach or at the top of each test body.

import type { Page } from "@playwright/test";
import type {
  Design,
  ReviewComment,
  ReviewBatch,
  KnowledgeEntry,
  DataSource,
  ColumnSchema,
  SearchResult,
} from "./mock-data";
import { makeRulesContext } from "./mock-data";

// ---------------------------------------------------------------------------
// Designs
// ---------------------------------------------------------------------------

export async function mockDesignList(page: Page, designs: Design[]) {
  await page.route("**/api/designs", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { designs, count: designs.length },
      });
    }
    return route.continue();
  });
}

export async function mockDesignDetail(page: Page, design: Design) {
  await page.route(`**/api/designs/${design.id}`, (route) =>
    route.fulfill({ json: design }),
  );
}

export async function mockTransitionDesign(
  page: Page,
  designId: string,
  response?: Record<string, unknown>,
) {
  await page.route(`**/api/designs/${designId}/transition`, (route) =>
    route.fulfill({
      json: response ?? {
        design_id: designId,
        status: "in_review",
        message: "Transition completed",
      },
    }),
  );
}

export async function mockComments(
  page: Page,
  designId: string,
  comments: ReviewComment[],
) {
  await page.route(`**/api/designs/${designId}/comments`, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { design_id: designId, comments, count: comments.length },
      });
    }
    // POST — add comment
    return route.fulfill({
      json: {
        comment_id: "c-new",
        status_after: "supported",
        message: "Comment added",
      },
    });
  });
}


// ---------------------------------------------------------------------------
// Review Batches
// ---------------------------------------------------------------------------

export async function mockReviewBatches(
  page: Page,
  designId: string,
  batches: ReviewBatch[] = [],
) {
  await page.route(`**/api/designs/${designId}/review-batches`, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { design_id: designId, batches, count: batches.length },
      });
    }
    // POST — submit batch
    return route.fulfill({
      status: 201,
      json: {
        batch_id: "RB-new00001",
        status_after: "supported",
        comment_count: 1,
      },
    });
  });
}

export async function mockReviewBatchesError(page: Page, designId: string) {
  await page.route(`**/api/designs/${designId}/review-batches`, (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 500,
        json: { error: "Internal server error" },
      });
    }
    return route.fulfill({
      json: { design_id: designId, batches: [], count: 0 },
    });
  });
}

// ---------------------------------------------------------------------------
// Catalog
// ---------------------------------------------------------------------------

export async function mockSourceList(page: Page, sources: DataSource[]) {
  await page.route("**/api/catalog/sources", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: { sources, count: sources.length },
      });
    }
    return route.continue();
  });
}

export async function mockSchema(
  page: Page,
  sourceId: string,
  columns: ColumnSchema[],
) {
  await page.route(`**/api/catalog/sources/${sourceId}/schema`, (route) =>
    route.fulfill({ json: { source_id: sourceId, columns } }),
  );
}

export async function mockCatalogSearch(
  page: Page,
  results: SearchResult[],
) {
  await page.route("**/api/catalog/search**", (route) =>
    route.fulfill({
      json: {
        query: "test",
        results,
        count: results.length,
      },
    }),
  );
}

export async function mockUnifiedKnowledge(
  page: Page,
  entries: KnowledgeEntry[],
) {
  await page.route("**/api/rules/context", (route) =>
    route.fulfill({
      json: makeRulesContext({
        knowledge_entries: entries,
        total_knowledge: entries.length,
      }),
    }),
  );
}

// ---------------------------------------------------------------------------
// Catch-all: mock all routes with empty/minimal data (for cross-tab tests)
// ---------------------------------------------------------------------------

export async function mockAllRoutesEmpty(page: Page) {
  await page.route("**/api/designs**", (route) =>
    route.fulfill({ json: { designs: [], count: 0 } }),
  );
  await page.route("**/api/catalog/sources**", (route) =>
    route.fulfill({ json: { sources: [], count: 0 } }),
  );
  await page.route("**/api/catalog/search**", (route) =>
    route.fulfill({ json: { query: "", results: [], count: 0 } }),
  );
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
  await page.route("**/api/rules/cautions**", (route) =>
    route.fulfill({
      json: { table_names: [], cautions: [], count: 0 },
    }),
  );
}

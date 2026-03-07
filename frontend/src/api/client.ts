import type {
  Design,
  DataSource,
  ColumnSchema,
  ReviewComment,
  ReviewBatch,
  KnowledgeEntry,
  RulesContext,
  SearchResult,
  Caution,
  CreateDesignRequest,
  AddCommentRequest,
  AddSourceRequest,
  SubmitBatchRequest,
} from "@/types/api";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// For 5xx, use generic message. For 4xx, truncate.
function sanitizeErrorDetail(status: number, detail: string): string {
  if (status >= 500) return "Internal server error";
  return detail.length > 200 ? detail.slice(0, 200) + "..." : detail;
}

const DEFAULT_TIMEOUT_MS = 30_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    // Apply default timeout unless caller already provides an AbortSignal
    const signal = init?.signal ?? AbortSignal.timeout(DEFAULT_TIMEOUT_MS);
    res = await fetch(path, { ...init, signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new ApiError(0, "Server is not responding. Please check if the backend is running.");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.error === "string") {
        detail = body.error;
      } else if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((d: { msg: string }) => d.msg).join(", ");
      }
    } catch {
      // non-JSON response, use statusText
    }
    throw new ApiError(res.status, sanitizeErrorDetail(res.status, detail));
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Design endpoints
// ---------------------------------------------------------------------------

export async function listDesigns(
  status?: string,
  signal?: AbortSignal,
): Promise<{ designs: Design[]; count: number }> {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/designs${params}`, { signal });
}

export async function createDesign(
  body: CreateDesignRequest,
): Promise<{ design: Design; message: string }> {
  return request("/api/designs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getDesign(
  id: string,
  signal?: AbortSignal,
): Promise<Design> {
  return request(`/api/designs/${encodeURIComponent(id)}`, { signal });
}

// ---------------------------------------------------------------------------
// Review endpoints
// ---------------------------------------------------------------------------

export async function transitionDesign(
  designId: string,
  status: string,
): Promise<{ design_id: string; status: string; message: string }> {
  return request(`/api/designs/${encodeURIComponent(designId)}/transition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export async function listComments(
  designId: string,
  signal?: AbortSignal,
): Promise<{ design_id: string; comments: ReviewComment[]; count: number }> {
  return request(
    `/api/designs/${encodeURIComponent(designId)}/comments`,
    { signal },
  );
}

export async function addComment(
  designId: string,
  body: AddCommentRequest,
): Promise<{ comment_id: string; status_after: string; message: string }> {
  return request(`/api/designs/${encodeURIComponent(designId)}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function submitReviewBatch(
  designId: string,
  body: SubmitBatchRequest,
): Promise<{ batch_id: string; status_after: string; comment_count: number }> {
  return request(
    `/api/designs/${encodeURIComponent(designId)}/review-batches`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export async function listReviewBatches(
  designId: string,
  signal?: AbortSignal,
): Promise<{ design_id: string; batches: ReviewBatch[]; count: number }> {
  return request(
    `/api/designs/${encodeURIComponent(designId)}/review-batches`,
    { signal },
  );
}

// ---------------------------------------------------------------------------
// Catalog endpoints
// ---------------------------------------------------------------------------

export async function listSources(
  signal?: AbortSignal,
): Promise<{ sources: DataSource[]; count: number }> {
  return request("/api/catalog/sources", { signal });
}

export async function addSource(
  body: AddSourceRequest,
): Promise<{ source: DataSource; message: string }> {
  return request("/api/catalog/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getSource(
  id: string,
  signal?: AbortSignal,
): Promise<DataSource> {
  return request(`/api/catalog/sources/${encodeURIComponent(id)}`, { signal });
}

export async function getSchema(
  sourceId: string,
  signal?: AbortSignal,
): Promise<{ source_id: string; columns: ColumnSchema[] }> {
  return request(
    `/api/catalog/sources/${encodeURIComponent(sourceId)}/schema`,
    { signal },
  );
}

export async function searchCatalog(
  query: string,
  sourceId?: string,
  signal?: AbortSignal,
): Promise<{ query: string; results: SearchResult[]; count: number }> {
  const params = new URLSearchParams({ q: query });
  if (sourceId) params.set("source_id", sourceId);
  return request(`/api/catalog/search?${params.toString()}`, { signal });
}

export async function getUnifiedKnowledge(
  signal?: AbortSignal,
): Promise<{ entries: KnowledgeEntry[]; count: number }> {
  const context = await getRulesContext(signal);
  return {
    entries: context.knowledge_entries,
    count: context.total_knowledge,
  };
}

// ---------------------------------------------------------------------------
// Rules endpoints
// ---------------------------------------------------------------------------

export async function getRulesContext(
  signal?: AbortSignal,
): Promise<RulesContext> {
  return request("/api/rules/context", { signal });
}

export async function getCautions(
  tableNames: string[],
  signal?: AbortSignal,
): Promise<{ table_names: string[]; cautions: Caution[]; count: number }> {
  const params = new URLSearchParams({
    table_names: tableNames.join(","),
  });
  return request(`/api/rules/cautions?${params.toString()}`, { signal });
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function healthCheck(
  signal?: AbortSignal,
): Promise<{ status: string; version: string }> {
  return request("/api/health", { signal });
}

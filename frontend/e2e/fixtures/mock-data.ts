// Factory functions for mock API data used in E2E tests.
// Each factory returns a valid object with sensible defaults;
// callers override only the fields they care about.

export interface Design {
  id: string;
  title: string;
  status: string;
  theme_id: string;
  hypothesis_statement: string;
  hypothesis_background: string;
  parent_id: string | null;
  metrics: Record<string, unknown>;
  explanatory: Record<string, unknown>[];
  chart: Record<string, unknown>[];
  source_ids: string[];
  next_action: Record<string, unknown> | null;
  referenced_knowledge: Record<string, unknown>[] | null;
  created_at: string;
  updated_at: string;
}

export function makeDesign(overrides?: Partial<Design>): Design {
  return {
    id: "d-001",
    title: "Test Design",
    status: "in_review",
    theme_id: "t-001",
    hypothesis_statement: "Test hypothesis",
    hypothesis_background: "Test background",
    parent_id: null,
    metrics: {},
    explanatory: [],
    chart: [],
    source_ids: [],
    next_action: null,
    referenced_knowledge: null,
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
    ...overrides,
  };
}

export interface ReviewComment {
  id: string;
  design_id: string;
  comment: string;
  reviewer: string;
  status_after: string;
  created_at: string;
  extracted_knowledge: string[];
}

export function makeComment(overrides?: Partial<ReviewComment>): ReviewComment {
  return {
    id: "c-001",
    design_id: "d-001",
    comment: "Looks good",
    reviewer: "alice",
    status_after: "supported",
    created_at: "2026-01-02T00:00:00",
    extracted_knowledge: [],
    ...overrides,
  };
}

export interface KnowledgeEntry {
  key: string;
  title: string;
  content: string;
  category: string;
  importance: string;
  created_at: string;
  source: string | null;
  affects_columns: string[];
}

export function makeKnowledgeEntry(
  overrides?: Partial<KnowledgeEntry>,
): KnowledgeEntry {
  return {
    key: "k-001",
    title: "Sample Knowledge",
    content: "This is sample knowledge content",
    category: "methodology",
    importance: "high",
    created_at: "2026-01-01T00:00:00",
    source: null,
    affects_columns: [],
    ...overrides,
  };
}

export interface DataSource {
  id: string;
  name: string;
  type: string;
  description: string;
  connection: Record<string, unknown>;
  schema_info: { columns: ColumnSchema[] };
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface ColumnSchema {
  name: string;
  type: string;
  description: string;
  nullable: boolean;
  examples: string[] | null;
  range: Record<string, unknown> | null;
  unit: string | null;
}

export function makeSource(overrides?: Partial<DataSource>): DataSource {
  return {
    id: "s-001",
    name: "Test Source",
    type: "csv",
    description: "A test data source",
    connection: { host: "localhost" },
    schema_info: { columns: [] },
    tags: ["test"],
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
    ...overrides,
  };
}

export function makeColumnSchema(
  overrides?: Partial<ColumnSchema>,
): ColumnSchema {
  return {
    name: "user_id",
    type: "integer",
    description: "Unique user identifier",
    nullable: false,
    examples: ["1", "2", "3"],
    range: null,
    unit: null,
    ...overrides,
  };
}

export interface BatchComment {
  comment: string;
  target_section: string | null;
  target_content: unknown;
}

export function makeBatchComment(
  overrides?: Partial<BatchComment>,
): BatchComment {
  return {
    comment: "Test comment",
    target_section: "hypothesis_statement",
    target_content: "Test hypothesis content",
    ...overrides,
  };
}

export interface ReviewBatch {
  id: string;
  design_id: string;
  status_after: string;
  reviewer: string;
  comments: BatchComment[];
  created_at: string;
}

export function makeReviewBatch(
  overrides?: Partial<ReviewBatch>,
): ReviewBatch {
  return {
    id: "RB-test0001",
    design_id: "DES-test",
    status_after: "supported",
    reviewer: "analyst",
    comments: [makeBatchComment()],
    created_at: "2026-03-01T10:00:00+09:00",
    ...overrides,
  };
}

export interface SearchResult {
  doc_type: string;
  source_id: string;
  title: string;
  snippet: string;
  rank: number;
}

export function makeSearchResult(
  overrides?: Partial<SearchResult>,
): SearchResult {
  return {
    doc_type: "source",
    source_id: "s-001",
    title: "email",
    snippet: "User <b>email</b> address",
    rank: -1.5,
    ...overrides,
  };
}

export interface RulesContext {
  sources: { id: string; name: string; type: string; description: string; tags: string[] }[];
  knowledge_entries: KnowledgeEntry[];
  rules: Record<string, unknown>[];
  total_sources: number;
  total_knowledge: number;
  total_rules: number;
}

export function makeRulesContext(
  overrides?: Partial<RulesContext>,
): RulesContext {
  return {
    sources: [
      { id: "s-001", name: "Sales DB", type: "sql", description: "Sales database", tags: ["sales"] },
    ],
    knowledge_entries: [
      makeKnowledgeEntry({ key: "k-rules-1", title: "Domain Rule 1" }),
    ],
    rules: [{ id: "r-001", description: "Sample rule" }],
    total_sources: 1,
    total_knowledge: 1,
    total_rules: 1,
    ...overrides,
  };
}

export interface Caution {
  key: string;
  title: string;
  content: string;
  category: string;
  importance: string;
  affects_columns: string[];
}

export function makeCaution(overrides?: Partial<Caution>): Caution {
  return {
    key: "cau-001",
    title: "Watch out for NULLs",
    content: "Column may contain NULL values after 2025",
    category: "caution",
    importance: "high",
    affects_columns: ["revenue"],
    ...overrides,
  };
}

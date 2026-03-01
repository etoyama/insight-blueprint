// Enum union types
export type DesignStatus =
  | "draft"
  | "active"
  | "pending_review"
  | "supported"
  | "rejected"
  | "inconclusive";

export type SourceType = "csv" | "api" | "sql";

export type KnowledgeCategory =
  | "methodology"
  | "caution"
  | "definition"
  | "context";

export type KnowledgeImportance = "high" | "medium" | "low";

// Model interfaces
export interface Design {
  id: string;
  theme_id: string;
  title: string;
  hypothesis_statement: string;
  hypothesis_background: string;
  status: DesignStatus;
  parent_id: string | null;
  metrics: Record<string, unknown>;
  explanatory: Record<string, unknown>[];
  chart: Record<string, unknown>[];
  source_ids: string[];
  next_action: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface DataSource {
  id: string;
  name: string;
  type: SourceType;
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

export interface ReviewComment {
  id: string;
  design_id: string;
  comment: string;
  reviewer: string;
  status_after: DesignStatus;
  created_at: string;
  extracted_knowledge: string[];
}

export interface KnowledgeEntry {
  key: string;
  title: string;
  content: string;
  category: KnowledgeCategory;
  importance: KnowledgeImportance;
  created_at: string;
  source: string | null;
  affects_columns: string[];
}

export interface RulesContext {
  sources: {
    id: string;
    name: string;
    type: string;
    description: string;
    tags: string[];
  }[];
  knowledge_entries: KnowledgeEntry[];
  rules: Record<string, unknown>[];
  total_sources: number;
  total_knowledge: number;
  total_rules: number;
}

export interface SearchResult {
  doc_type: string;
  source_id: string;
  title: string;
  snippet: string;
  rank: number;
  [key: string]: unknown;
}

export interface Caution {
  key: string;
  title: string;
  content: string;
  category: KnowledgeCategory;
  importance: KnowledgeImportance;
  affects_columns: string[];
  [key: string]: unknown;
}

// JSON-compatible recursive type (matches backend JsonValue)
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

// Batch review types
export interface BatchComment {
  comment: string;
  target_section: string | null;
  target_content: JsonValue;
}

export interface ReviewBatch {
  id: string;
  design_id: string;
  status_after: DesignStatus;
  reviewer: string;
  comments: BatchComment[];
  created_at: string;
}

export interface DraftComment {
  id: string;
  target_section: string;
  target_content: JsonValue;
  comment: string;
}

export interface SubmitBatchRequest {
  status_after: DesignStatus;
  reviewer?: string;
  comments: {
    comment: string;
    target_section?: string;
    target_content?: JsonValue;
  }[];
}

// Request types
export interface CreateDesignRequest {
  title: string;
  hypothesis_statement: string;
  hypothesis_background: string;
  theme_id?: string;
}

export interface AddCommentRequest {
  comment: string;
  status: string;
  reviewer?: string;
}

export interface AddSourceRequest {
  source_id: string;
  name: string;
  type: SourceType;
  description: string;
  connection: Record<string, unknown>;
  columns?: ColumnSchema[];
  tags?: string[];
}

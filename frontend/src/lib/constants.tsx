import { Badge } from "@/components/ui/badge";
import type { ColumnDef } from "@/components/DataTable";
import type { DesignStatus, KnowledgeEntry, SourceType } from "@/types/api";

export const DEFAULT_THEME_ID = "DEFAULT";
export const DEFAULT_SOURCE_TYPE: SourceType = "csv";

export const DESIGN_STATUS_LABELS: Record<DesignStatus, string> = {
  draft: "Draft",
  active: "Active",
  pending_review: "Pending Review",
  supported: "Supported",
  rejected: "Rejected",
  inconclusive: "Inconclusive",
};

export const KNOWLEDGE_COLUMNS: ColumnDef<KnowledgeEntry>[] = [
  { key: "title", label: "Title" },
  { key: "content", label: "Content" },
  {
    key: "category",
    label: "Category",
    render: (v) => <Badge variant="outline">{String(v)}</Badge>,
  },
  {
    key: "importance",
    label: "Importance",
    render: (v) => <Badge variant="secondary">{String(v)}</Badge>,
  },
];

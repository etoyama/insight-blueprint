// Section registry — single source of truth for commentable sections.
// IDs must match backend ALLOWED_TARGET_SECTIONS in core/reviews.py.

export interface CommentableSection {
  id: string;
  label: string;
  type: "text" | "json";
}

export const COMMENTABLE_SECTIONS: readonly CommentableSection[] = [
  { id: "hypothesis_statement", label: "Hypothesis Statement", type: "text" },
  { id: "hypothesis_background", label: "Hypothesis Background", type: "text" },
  { id: "metrics", label: "Metrics", type: "json" },
  { id: "explanatory", label: "Explanatory", type: "json" },
  { id: "chart", label: "Chart", type: "json" },
  { id: "next_action", label: "Next Action", type: "json" },
] as const;

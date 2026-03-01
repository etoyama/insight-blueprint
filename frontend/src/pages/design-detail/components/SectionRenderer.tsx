import { JsonTree } from "@/components/JsonTree";
import { Button } from "@/components/ui/button";
import type { DraftComment } from "@/types/api";
import type { CommentableSection } from "./sections";
import { InlineCommentAnchor } from "./InlineCommentAnchor";

interface SectionRendererProps {
  section: CommentableSection;
  value: unknown;
  isReviewMode: boolean;
  drafts: DraftComment[];
  onAddDraft: (comment: string) => void;
  onRemoveDraft: (draftId: string) => void;
}

export function SectionRenderer({
  section,
  value,
  isReviewMode,
  drafts,
  onAddDraft,
  onRemoveDraft,
}: SectionRendererProps) {
  const isEmpty =
    value === null ||
    value === undefined ||
    value === "" ||
    (typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value as Record<string, unknown>).length === 0) ||
    (Array.isArray(value) && value.length === 0);

  if (isEmpty && drafts.length === 0 && !isReviewMode) return null;

  return (
    <div data-section-id={section.id}>
      <div className="flex items-start gap-2">
        <span className="font-medium">{section.label}</span>
      </div>
      {!isEmpty && (
        <div className="mt-1">
          {section.type === "text" ? (
            <p className="text-sm">{String(value)}</p>
          ) : (
            <JsonTree
              data={value as Record<string, unknown> | Record<string, unknown>[]}
            />
          )}
        </div>
      )}
      {isEmpty && <p className="text-sm text-muted-foreground">-</p>}

      <InlineCommentAnchor onAdd={onAddDraft} isReviewMode={isReviewMode} />

      {drafts.length > 0 && (
        <div className="mt-2 space-y-2">
          {drafts.map((draft) => (
            <div
              key={draft.id}
              className="flex items-start justify-between rounded border border-dashed p-2 text-sm"
              data-testid="draft-card"
            >
              <div>
                <span className="text-xs font-medium text-muted-foreground">
                  draft
                </span>
                <p className="mt-0.5">{draft.comment}</p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="shrink-0 text-xs text-destructive"
                onClick={() => onRemoveDraft(draft.id)}
                data-testid="draft-delete"
              >
                Delete
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

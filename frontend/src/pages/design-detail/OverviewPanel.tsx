import { useState } from "react";
import { submitReview } from "@/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorBanner } from "@/components/ErrorBanner";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { Design } from "@/types/api";
import { COMMENTABLE_SECTIONS } from "./components/sections";
import { SectionRenderer } from "./components/SectionRenderer";
import { ReviewBatchComposer } from "./components/ReviewBatchComposer";
import { useReviewDrafts } from "./components/useReviewDrafts";

interface OverviewPanelProps {
  design: Design;
  designId: string;
  onDesignUpdated: () => void;
}

export function OverviewPanel({
  design,
  designId,
  onDesignUpdated,
}: OverviewPanelProps) {
  const [submittingReview, setSubmittingReview] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { drafts, addDraft, removeDraft, clearAll, hasDrafts, draftsBySection } =
    useReviewDrafts();

  const isReviewMode = design.status === "pending_review";

  const getSectionValue = (sectionId: string): unknown => {
    return (design as unknown as Record<string, unknown>)[sectionId];
  };

  const handleSubmitReview = () => {
    setSubmittingReview(true);
    setError(null);
    submitReview(designId)
      .then(() => onDesignUpdated())
      .catch((err) => setError(err.message))
      .finally(() => setSubmittingReview(false));
  };

  return (
    <div className="space-y-3 py-4 text-sm">
      <Field label="Status">
        <StatusBadge status={design.status} />
      </Field>
      <Field label="Theme ID">{design.theme_id}</Field>
      <Field label="Source IDs">
        {design.source_ids.length > 0 ? design.source_ids.join(", ") : "-"}
      </Field>
      <Field label="Created">{formatDateTime(design.created_at)}</Field>
      <Field label="Updated">{formatDateTime(design.updated_at)}</Field>

      {design.status === "active" && (
        <div className="border-t pt-3">
          <Button
            onClick={handleSubmitReview}
            disabled={submittingReview}
          >
            {submittingReview ? "Submitting..." : "Submit for Review"}
          </Button>
        </div>
      )}

      {error && <ErrorBanner message={error} />}

      <div className="space-y-4 border-t pt-3">
        {COMMENTABLE_SECTIONS.map((section) => (
          <SectionRenderer
            key={section.id}
            section={section}
            value={getSectionValue(section.id)}
            isReviewMode={isReviewMode}
            drafts={draftsBySection.get(section.id) ?? []}
            onAddDraft={(comment) =>
              addDraft(
                section.id,
                comment,
                structuredClone(getSectionValue(section.id)),
              )
            }
            onRemoveDraft={removeDraft}
          />
        ))}
      </div>

      {hasDrafts && (
        <ReviewBatchComposer
          designId={designId}
          drafts={drafts}
          onSubmitted={onDesignUpdated}
          onClearDrafts={clearAll}
        />
      )}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-2">
      <span className="w-40 shrink-0 font-medium">{label}</span>
      <span>{children}</span>
    </div>
  );
}

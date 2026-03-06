import { StatusBadge } from "@/components/StatusBadge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { formatDateTime } from "@/lib/utils";
import type { Design, DesignStatus } from "@/types/api";
import { COMMENTABLE_SECTIONS } from "./components/sections";
import { SectionRenderer } from "./components/SectionRenderer";
import { ReviewBatchComposer } from "./components/ReviewBatchComposer";
import { useReviewDrafts } from "./components/useReviewDrafts";

const STATUS_GUIDE: Record<DesignStatus, { title: string; description: string }> = {
  in_review: {
    title: "In Review",
    description:
      'Add comments to sections below, then submit with a verdict. Choose "Revision Requested" to request changes, or a final verdict when the design is solid.',
  },
  revision_requested: {
    title: "Revision Requested",
    description:
      "Waiting for Claude to address your feedback and resubmit for review.",
  },
  analyzing: {
    title: "Analyzing",
    description:
      "Analysis is being executed. Results will be available for review once complete.",
  },
  supported: {
    title: "Approved",
    description:
      "Design is finalized. Proceed with your analysis, then return to the Knowledge tab to extract and save domain insights.",
  },
  rejected: {
    title: "Rejected",
    description:
      "Hypothesis was rejected. Go to the Knowledge tab to capture lessons learned.",
  },
  inconclusive: {
    title: "Inconclusive",
    description:
      "Results are inconclusive. Go to the Knowledge tab to capture observations, then consider refining the hypothesis.",
  },
};

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
  const { drafts, addDraft, removeDraft, clearAll, hasDrafts, draftsBySection } =
    useReviewDrafts();

  const isReviewMode = design.status === "in_review";

  const getSectionValue = (sectionId: string): unknown => {
    return design[sectionId as keyof Design];
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

      {(() => {
        const guide = STATUS_GUIDE[design.status];
        return (
          <Alert data-testid="workflow-guide">
            <AlertTitle>{guide.title}</AlertTitle>
            <AlertDescription>
              <p>{guide.description}</p>
            </AlertDescription>
          </Alert>
        );
      })()}

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

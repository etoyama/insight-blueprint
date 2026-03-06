import { useState } from "react";
import { submitReviewBatch } from "@/api/client";
import type { DraftComment, DesignStatus } from "@/types/api";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const BATCH_STATUSES: DesignStatus[] = [
  "supported",
  "rejected",
  "inconclusive",
  "revision_requested",
  "analyzing",
];

interface ReviewBatchComposerProps {
  designId: string;
  drafts: DraftComment[];
  onSubmitted: () => void;
  onClearDrafts: () => void;
}

export function ReviewBatchComposer({
  designId,
  drafts,
  onSubmitted,
  onClearDrafts,
}: ReviewBatchComposerProps) {
  const [status, setStatus] = useState<DesignStatus>("supported");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (drafts.length === 0) return null;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await submitReviewBatch(designId, {
        status_after: status,
        comments: drafts.map((d) => ({
          comment: d.comment,
          target_section: d.target_section,
          target_content: d.target_content,
        })),
      });
      onClearDrafts();
      onSubmitted();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to submit review batch",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="sticky bottom-0 mt-4 flex flex-wrap items-center gap-3 rounded-t border bg-background p-3 shadow-md"
      data-testid="review-submit-bar"
    >
      <Badge variant="secondary" data-testid="draft-count">
        {drafts.length} draft{drafts.length !== 1 ? "s" : ""}
      </Badge>

      <Select
        value={status}
        onValueChange={(v) => setStatus(v as DesignStatus)}
      >
        <SelectTrigger className="w-40" data-testid="status-selector">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {BATCH_STATUSES.map((s) => (
            <SelectItem key={s} value={s}>
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        onClick={handleSubmit}
        disabled={submitting}
        data-testid="submit-all-button"
      >
        {submitting ? "Submitting..." : "Submit All"}
      </Button>

      {error && (
        <div className="w-full">
          <ErrorBanner message={error} />
        </div>
      )}
    </div>
  );
}

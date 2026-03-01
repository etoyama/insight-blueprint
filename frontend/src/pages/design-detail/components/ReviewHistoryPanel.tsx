import { useEffect, useState } from "react";
import { listReviewBatches } from "@/api/client";
import type { ReviewBatch } from "@/types/api";
import { StatusBadge } from "@/components/StatusBadge";
import { JsonTree } from "@/components/JsonTree";
import { ErrorBanner } from "@/components/ErrorBanner";
import { formatDateTime } from "@/lib/utils";
import { COMMENTABLE_SECTIONS } from "./sections";

const sectionLabelMap = new Map(
  COMMENTABLE_SECTIONS.map((s) => [s.id, s.label]),
);

interface ReviewHistoryPanelProps {
  designId: string;
}

export function ReviewHistoryPanel({ designId }: ReviewHistoryPanelProps) {
  const [batches, setBatches] = useState<ReviewBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    listReviewBatches(designId, ctrl.signal)
      .then((res) => {
        setBatches(res.batches);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
    return () => ctrl.abort();
  }, [designId]);

  if (loading) {
    return <p className="py-4 text-center text-muted-foreground">Loading...</p>;
  }

  if (error) {
    return <ErrorBanner message={error} />;
  }

  if (batches.length === 0) {
    return (
      <p className="py-4 text-sm text-muted-foreground">
        No review batches yet.
      </p>
    );
  }

  return (
    <div className="space-y-4 py-4">
      {batches.map((batch) => (
        <div
          key={batch.id}
          className="rounded border p-4 text-sm"
          data-testid="batch-card"
        >
          <div className="flex items-center gap-3">
            <StatusBadge status={batch.status_after} />
            <span className="text-muted-foreground">{batch.reviewer}</span>
            <span className="text-muted-foreground">
              {formatDateTime(batch.created_at)}
            </span>
          </div>

          <div className="mt-3 space-y-2">
            {batch.comments.map((comment, idx) => (
              <div key={idx} className="rounded bg-muted/50 p-2">
                <p>{comment.comment}</p>
                {comment.target_section && (
                  <div className="mt-1">
                    <span className="text-xs font-medium text-muted-foreground">
                      {sectionLabelMap.get(comment.target_section) ??
                        comment.target_section}
                    </span>
                    {comment.target_content != null && (
                      <div className="mt-1">
                        {typeof comment.target_content === "string" ? (
                          <blockquote className="border-l-2 pl-2 text-xs text-muted-foreground">
                            {comment.target_content}
                          </blockquote>
                        ) : (
                          <JsonTree
                            data={
                              comment.target_content as
                                | Record<string, unknown>
                                | Record<string, unknown>[]
                            }
                          />
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

import { useEffect, useState } from "react";
import { submitReview, listComments, addComment } from "@/api/client";
import type { DesignStatus, ReviewComment, AddCommentRequest } from "@/types/api";
import { StatusBadge } from "@/components/StatusBadge";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { ErrorBanner } from "@/components/ErrorBanner";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const commentColumns: ColumnDef<ReviewComment>[] = [
  { key: "reviewer", label: "Reviewer" },
  { key: "comment", label: "Comment" },
  {
    key: "status_after",
    label: "Status",
    render: (_, row) => <StatusBadge status={row.status_after} />,
  },
  {
    key: "created_at",
    label: "Date",
    render: (v) => formatDateTime(v as string),
  },
];

const COMMENT_STATUSES: DesignStatus[] = ["supported", "rejected", "inconclusive", "active"];

export function ReviewPanel({
  designId,
  status,
  onStatusChanged,
}: {
  designId: string;
  status: DesignStatus;
  onStatusChanged: () => void;
}) {
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submittingReview, setSubmittingReview] = useState(false);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [commentStatus, setCommentStatus] = useState<DesignStatus>("supported");

  const fetchComments = (signal?: AbortSignal) => {
    listComments(designId, signal)
      .then((res) => setComments(res.comments))
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message);
      });
  };

  useEffect(() => {
    const ctrl = new AbortController();
    fetchComments(ctrl.signal);
    return () => ctrl.abort();
  }, [designId]);

  const handleSubmitReview = () => {
    setSubmittingReview(true);
    submitReview(designId)
      .then(() => {
        onStatusChanged();
        fetchComments();
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmittingReview(false));
  };

  const handleAddComment = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const comment = (data.get("comment") as string).trim();
    if (!comment) return;

    const body: AddCommentRequest = {
      comment,
      status: commentStatus,
      reviewer: (data.get("reviewer") as string).trim() || undefined,
    };
    setSubmittingComment(true);
    addComment(designId, body)
      .then(() => {
        form.reset();
        setCommentStatus("supported");
        fetchComments();
        onStatusChanged();
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmittingComment(false));
  };

  return (
    <div className="space-y-4 py-4">
      <Button
        onClick={handleSubmitReview}
        disabled={status !== "active" || submittingReview}
      >
        {submittingReview ? "Submitting..." : "Submit for Review"}
      </Button>
      {status !== "active" && (
        <p className="text-xs text-muted-foreground">
          Only active designs can be submitted for review.
        </p>
      )}

      {error && <ErrorBanner message={error} />}

      <h4 className="font-medium">Comments</h4>
      {comments.length > 0 ? (
        <DataTable data={comments} columns={commentColumns} />
      ) : (
        <p className="text-sm text-muted-foreground">No comments yet.</p>
      )}

      <form onSubmit={handleAddComment} className="space-y-3 border-t pt-4">
        <h4 className="font-medium">Add Comment</h4>
        <Textarea name="comment" placeholder="Comment" required maxLength={2000} />
        <div className="flex gap-2">
          <Select value={commentStatus} onValueChange={(v) => setCommentStatus(v as DesignStatus)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {COMMENT_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input name="reviewer" placeholder="Reviewer (optional)" className="w-48" maxLength={100} />
          <Button type="submit" disabled={submittingComment}>
            {submittingComment ? "Adding..." : "Add"}
          </Button>
        </div>
      </form>
    </div>
  );
}

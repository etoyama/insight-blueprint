import { useEffect, useState } from "react";
import {
  getDesign,
  submitReview,
  listComments,
  addComment,
  extractKnowledge,
  saveKnowledge,
} from "@/api/client";
import type {
  Design,
  DesignStatus,
  ReviewComment,
  KnowledgeEntry,
  AddCommentRequest,
} from "@/types/api";
import { StatusBadge } from "@/components/StatusBadge";
import { DataTable } from "@/components/DataTable";
import type { ColumnDef } from "@/components/DataTable";
import { JsonTree } from "@/components/JsonTree";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

interface DesignDetailProps {
  designId: string;
  onDesignUpdated: () => void;
}

export function DesignDetail({ designId, onDesignUpdated }: DesignDetailProps) {
  const [design, setDesign] = useState<Design | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    getDesign(designId, ctrl.signal)
      .then((d) => {
        setDesign(d);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
    return () => ctrl.abort();
  }, [designId]);

  const refreshDesign = () => {
    getDesign(designId)
      .then((d) => {
        setDesign(d);
        onDesignUpdated();
      })
      .catch((err) => setError(err.message));
  };

  if (loading) {
    return <p className="py-4 text-center text-muted-foreground">Loading...</p>;
  }
  if (error) {
    return <ErrorBanner message={error} onRetry={() => {
      setError(null);
      setLoading(true);
      getDesign(designId)
        .then((d) => {
          setDesign(d);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    }} />;
  }
  if (!design) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{design.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="review">Review</TabsTrigger>
            <TabsTrigger value="knowledge">Knowledge</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <OverviewPanel design={design} />
          </TabsContent>
          <TabsContent value="review">
            <ReviewPanel
              designId={designId}
              status={design.status}
              onStatusChanged={refreshDesign}
            />
          </TabsContent>
          <TabsContent value="knowledge">
            <KnowledgePanel designId={designId} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// OverviewPanel
// ---------------------------------------------------------------------------

function OverviewPanel({ design }: { design: Design }) {
  return (
    <div className="space-y-3 py-4 text-sm">
      <Field label="Status"><StatusBadge status={design.status} /></Field>
      <Field label="Theme ID">{design.theme_id}</Field>
      <Field label="Hypothesis Statement">{design.hypothesis_statement}</Field>
      <Field label="Hypothesis Background">{design.hypothesis_background}</Field>
      <Field label="Source IDs">
        {design.source_ids.length > 0 ? design.source_ids.join(", ") : "-"}
      </Field>
      <Field label="Created">{new Date(design.created_at).toLocaleString("ja-JP")}</Field>
      <Field label="Updated">{new Date(design.updated_at).toLocaleString("ja-JP")}</Field>
      {Object.keys(design.metrics).length > 0 && (
        <div>
          <span className="font-medium">Metrics</span>
          <JsonTree data={design.metrics} />
        </div>
      )}
      {design.explanatory.length > 0 && (
        <div>
          <span className="font-medium">Explanatory</span>
          <JsonTree data={design.explanatory} />
        </div>
      )}
      {design.chart.length > 0 && (
        <div>
          <span className="font-medium">Chart</span>
          <JsonTree data={design.chart} />
        </div>
      )}
      {design.next_action && (
        <div>
          <span className="font-medium">Next Action</span>
          <JsonTree data={design.next_action} />
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <span className="w-40 shrink-0 font-medium">{label}</span>
      <span>{children}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ReviewPanel
// ---------------------------------------------------------------------------

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
    render: (v) => new Date(v as string).toLocaleString("ja-JP"),
  },
];

const COMMENT_STATUSES: DesignStatus[] = ["supported", "rejected", "inconclusive", "active"];

function ReviewPanel({
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
        <Textarea name="comment" placeholder="Comment" required />
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
          <Input name="reviewer" placeholder="Reviewer (optional)" className="w-48" />
          <Button type="submit" disabled={submittingComment}>
            {submittingComment ? "Adding..." : "Add"}
          </Button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// KnowledgePanel
// ---------------------------------------------------------------------------

function KnowledgePanel({ designId }: { designId: string }) {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const handleExtract = () => {
    setExtracting(true);
    setError(null);
    setSaved(false);
    extractKnowledge(designId)
      .then((res) => setEntries(res.entries))
      .catch((err) => setError(err.message))
      .finally(() => setExtracting(false));
  };

  const handleSave = () => {
    setSaving(true);
    setError(null);
    saveKnowledge(designId, entries)
      .then(() => setSaved(true))
      .catch((err) => setError(err.message))
      .finally(() => setSaving(false));
  };

  return (
    <div className="space-y-4 py-4">
      <Button onClick={handleExtract} disabled={extracting}>
        {extracting ? "Extracting..." : "Extract Knowledge"}
      </Button>

      {error && <ErrorBanner message={error} />}

      {entries.length > 0 && (
        <>
          <div className="space-y-2">
            {entries.map((entry) => (
              <div key={entry.key} className="rounded border p-3 text-sm">
                <div className="font-medium">{entry.title}</div>
                <div className="text-muted-foreground">{entry.content}</div>
                <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                  <span>Key: {entry.key}</span>
                  <span>Category: {entry.category}</span>
                  <span>Importance: {entry.importance}</span>
                </div>
              </div>
            ))}
          </div>
          <Button onClick={handleSave} disabled={saving || saved}>
            {saved ? "Saved" : saving ? "Saving..." : "Save Knowledge"}
          </Button>
          {saved && (
            <p className="text-sm text-green-600">Knowledge saved successfully.</p>
          )}
        </>
      )}
    </div>
  );
}

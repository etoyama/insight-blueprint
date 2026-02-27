import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { listDesigns, listComments } from "@/api/client";
import type { Design, ReviewComment } from "@/types/api";

export function HistoryPage() {
  const [designs, setDesigns] = useState<Design[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentsError, setCommentsError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    listDesigns(undefined, ctrl.signal)
      .then((res) => {
        const sorted = [...res.designs].sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
        );
        setDesigns(sorted);
      })
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    if (!expandedId) {
      setComments([]);
      return;
    }
    const ctrl = new AbortController();
    setCommentsLoading(true);
    setCommentsError(null);
    listComments(expandedId, ctrl.signal)
      .then((res) => setComments(res.comments))
      .catch((err) => {
        if (err.name !== "AbortError") setCommentsError(err.message);
      })
      .finally(() => setCommentsLoading(false));
    return () => ctrl.abort();
  }, [expandedId]);

  const handleToggle = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  if (loading)
    return <p className="py-8 text-center text-muted-foreground">読み込み中...</p>;
  if (error) return <ErrorBanner message={error} />;
  if (designs.length === 0) return <EmptyState message="デザインがありません" />;

  return (
    <div className="flex flex-col gap-3">
      {designs.map((design) => {
        const isCreated = design.created_at === design.updated_at;
        const isExpanded = expandedId === design.id;

        return (
          <Card
            key={design.id}
            className="cursor-pointer"
            onClick={() => handleToggle(design.id)}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <span className="flex-1">{design.title}</span>
                <StatusBadge status={design.status} />
                <span className="text-sm font-normal text-muted-foreground">
                  {isCreated ? "作成" : "更新"}:{" "}
                  {new Date(design.updated_at).toLocaleString("ja-JP")}
                </span>
              </CardTitle>
            </CardHeader>

            {isExpanded && (
              <CardContent onClick={(e) => e.stopPropagation()}>
                <h3 className="mb-2 text-sm font-semibold">レビュー履歴</h3>
                {commentsLoading && (
                  <p className="text-sm text-muted-foreground">読み込み中...</p>
                )}
                {commentsError && <ErrorBanner message={commentsError} />}
                {!commentsLoading && !commentsError && comments.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    レビューコメントがありません
                  </p>
                )}
                {comments.length > 0 && (
                  <div className="space-y-3">
                    {comments.map((c) => (
                      <div
                        key={c.id}
                        className="rounded border p-3 text-sm"
                      >
                        <div className="mb-1 flex items-center gap-2">
                          <span className="font-medium">{c.reviewer}</span>
                          <StatusBadge status={c.status_after} />
                          <span className="text-muted-foreground">
                            {new Date(c.created_at).toLocaleString("ja-JP")}
                          </span>
                        </div>
                        <p>{c.comment}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
}

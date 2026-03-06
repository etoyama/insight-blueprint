import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { listDesigns } from "@/api/client";
import type { Design } from "@/types/api";
import { formatDateTime } from "@/lib/utils";
import { ReviewHistoryPanel } from "@/pages/design-detail/components/ReviewHistoryPanel";

export function HistoryPage() {
  const [designs, setDesigns] = useState<Design[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchDesigns = useCallback((signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    listDesigns(undefined, signal)
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
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchDesigns(ctrl.signal);
    return () => ctrl.abort();
  }, [fetchDesigns]);

  const handleToggle = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  if (loading)
    return <p className="py-8 text-center text-muted-foreground">Loading...</p>;
  if (error) return <ErrorBanner message={error} onRetry={fetchDesigns} />;
  if (designs.length === 0) return <EmptyState message="No designs found" />;

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
                  {isCreated ? "Created" : "Updated"}:{" "}
                  {formatDateTime(design.updated_at)}
                </span>
              </CardTitle>
            </CardHeader>

            {isExpanded && (
              <CardContent onClick={(e) => e.stopPropagation()}>
                <ReviewHistoryPanel designId={design.id} />
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
}

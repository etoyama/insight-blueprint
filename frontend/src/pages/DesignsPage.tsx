import { useEffect, useState, useCallback } from "react";
import { listDesigns, createDesign } from "@/api/client";
import type { Design, DesignStatus, CreateDesignRequest } from "@/types/api";
import { DESIGN_STATUS_LABELS, DEFAULT_THEME_ID } from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";
import { DesignDetail } from "@/pages/design-detail";
import { DataTable } from "@/components/DataTable";
import type { ColumnDef } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

const ALL_STATUSES: DesignStatus[] = [
  "draft",
  "active",
  "pending_review",
  "supported",
  "rejected",
  "inconclusive",
];

const STATUS_FILTER_OPTIONS: Record<string, string> = {
  all: "All",
  ...DESIGN_STATUS_LABELS,
};

const columns: ColumnDef<Design>[] = [
  { key: "title", label: "Title" },
  {
    key: "status",
    label: "Status",
    render: (_, row) => <StatusBadge status={row.status} />,
  },
  {
    key: "updated_at",
    label: "Updated",
    render: (v) => formatDateTime(v as string),
  },
];

export function DesignsPage() {
  const [designs, setDesigns] = useState<Design[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchDesigns = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      const status = statusFilter === "all" ? undefined : statusFilter;
      listDesigns(status, signal)
        .then((res) => {
          setDesigns(res.designs);
          setLoading(false);
        })
        .catch((err) => {
          if (err.name === "AbortError") return;
          setError(err.message);
          setLoading(false);
        });
    },
    [statusFilter],
  );

  useEffect(() => {
    const ctrl = new AbortController();
    fetchDesigns(ctrl.signal);
    return () => ctrl.abort();
  }, [fetchDesigns]);

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const title = (data.get("title") as string).trim();
    const hypothesis_statement = (
      data.get("hypothesis_statement") as string
    ).trim();
    const hypothesis_background = (
      data.get("hypothesis_background") as string
    ).trim();
    const theme_id = (data.get("theme_id") as string).trim() || DEFAULT_THEME_ID;

    if (!title || !hypothesis_statement || !hypothesis_background) {
      setFormError("Title, hypothesis statement, hypothesis background are required.");
      return;
    }

    setSubmitting(true);
    setFormError(null);
    const body: CreateDesignRequest = {
      title,
      hypothesis_statement,
      hypothesis_background,
      theme_id,
    };
    createDesign(body)
      .then(() => {
        setDialogOpen(false);
        form.reset();
        fetchDesigns();
      })
      .catch((err) => setFormError(err.message))
      .finally(() => setSubmitting(false));
  };

  if (loading) {
    return <p className="py-8 text-center text-muted-foreground">Loading...</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{STATUS_FILTER_OPTIONS.all}</SelectItem>
            {ALL_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {STATUS_FILTER_OPTIONS[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={() => setDialogOpen(true)}>+ New Design</Button>
      </div>

      {error && <ErrorBanner message={error} onRetry={() => fetchDesigns()} />}

      {!error && designs.length === 0 ? (
        <EmptyState
          message="No designs found."
          action={{ label: "+ New Design", onClick: () => setDialogOpen(true) }}
        />
      ) : (
        <DataTable
          data={designs}
          columns={columns}
          onRowClick={(row) => setSelectedId(row.id)}
          selectedRow={(row) => row.id === selectedId}
        />
      )}

      {selectedId && (
        <div className="mt-4">
          <DesignDetail
            designId={selectedId}
            onDesignUpdated={() => fetchDesigns()}
          />
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Design</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Title *</label>
              <Input name="title" placeholder="Design title" maxLength={200} />
            </div>
            <div>
              <label className="text-sm font-medium">Hypothesis Statement *</label>
              <Textarea
                name="hypothesis_statement"
                placeholder="State your hypothesis"
                maxLength={2000}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Hypothesis Background *</label>
              <Textarea
                name="hypothesis_background"
                placeholder="Describe the background"
                maxLength={5000}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Theme ID</label>
              <Input name="theme_id" placeholder="DEFAULT" maxLength={50} />
            </div>
            {formError && (
              <p className="text-sm text-destructive">{formError}</p>
            )}
            <DialogFooter>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

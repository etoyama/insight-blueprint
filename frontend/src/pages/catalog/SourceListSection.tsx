import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { addSource } from "@/api/client";
import type { DataSource, SourceType, AddSourceRequest } from "@/types/api";

const SOURCE_COLUMNS: ColumnDef<DataSource>[] = [
  { key: "name", label: "Name" },
  { key: "type", label: "Type", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "description", label: "Description" },
  { key: "tags", label: "Tags", render: (v) => <span>{(v as string[]).join(", ")}</span> },
  { key: "updated_at", label: "Updated At" },
];

export function SourceListSection({
  sources,
  onSelect,
  selectedId,
  onSourceAdded,
}: {
  sources: DataSource[];
  onSelect: (id: string) => void;
  selectedId: string | null;
  onSourceAdded: () => void;
}) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    source_id: "",
    name: "",
    type: "csv" as SourceType,
    description: "",
    connection: "",
  });
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const MAX_CONNECTION_JSON_LENGTH = 10240;

  function parseConnection(raw: string): Record<string, unknown> | null {
    if (raw.length > MAX_CONNECTION_JSON_LENGTH) {
      setJsonError("Connection JSON is too large (max 10KB)");
      return null;
    }
    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      setJsonError(null);
      return parsed;
    } catch {
      setJsonError("Please enter valid JSON");
      return null;
    }
  }

  const handleSubmit = async () => {
    const connection = parseConnection(form.connection);
    if (connection === null) return;
    setSubmitting(true);
    try {
      const body: AddSourceRequest = {
        source_id: form.source_id,
        name: form.name,
        type: form.type,
        description: form.description,
        connection,
      };
      await addSource(body);
      setDialogOpen(false);
      setForm({ source_id: "", name: "", type: "csv", description: "", connection: "" });
      onSourceAdded();
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : "Failed to add source");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Data Sources</h2>
        <Button onClick={() => setDialogOpen(true)}>Add Source</Button>
      </div>
      {sources.length === 0 ? (
        <EmptyState
          message="No data sources found"
          action={{ label: "Add Source", onClick: () => setDialogOpen(true) }}
        />
      ) : (
        <DataTable
          data={sources}
          columns={SOURCE_COLUMNS}
          onRowClick={(row) => onSelect(row.id)}
          selectedRow={(row) => row.id === selectedId}
        />
      )}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Source</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <Input
              placeholder="Source ID"
              value={form.source_id}
              onChange={(e) => setForm({ ...form, source_id: e.target.value })}
            />
            <Input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <Select
              value={form.type}
              onValueChange={(v) => setForm({ ...form, type: v as SourceType })}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">CSV</SelectItem>
                <SelectItem value="api">API</SelectItem>
                <SelectItem value="sql">SQL</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
            <Textarea
              placeholder='Connection JSON e.g. {"host": "localhost"}'
              value={form.connection}
              onChange={(e) => {
                setForm({ ...form, connection: e.target.value });
                setJsonError(null);
              }}
            />
            {jsonError && <p className="text-sm text-destructive">{jsonError}</p>}
          </div>
          <DialogFooter>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !form.source_id || !form.name || !form.description}
            >
              {submitting ? "Adding..." : "Add"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

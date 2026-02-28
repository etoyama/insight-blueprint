import { useEffect, useState } from "react";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { getSchema } from "@/api/client";
import type { ColumnSchema } from "@/types/api";

const SCHEMA_COLUMNS: ColumnDef<ColumnSchema>[] = [
  { key: "name", label: "Column Name" },
  { key: "type", label: "Type" },
  { key: "description", label: "Description" },
  { key: "nullable", label: "Nullable", render: (v) => (v ? "Yes" : "No") },
  { key: "unit", label: "Unit", render: (v) => String(v ?? "-") },
  { key: "examples", label: "Examples", render: (v) => ((v as string[] | null)?.join(", ") ?? "-") },
];

export function SchemaSection({ sourceId }: { sourceId: string | null }) {
  const [columns, setColumns] = useState<ColumnSchema[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sourceId) return;
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    getSchema(sourceId, ctrl.signal)
      .then((res) => setColumns(res.columns))
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [sourceId]);

  if (!sourceId) return null;
  if (loading) return <p className="py-4 text-muted-foreground">Loading schema...</p>;
  if (error) return <ErrorBanner message={error} />;
  if (columns.length === 0) return <EmptyState message="No schema information available" />;

  return (
    <section className="mt-6">
      <h2 className="mb-2 text-lg font-semibold">Schema</h2>
      <DataTable data={columns} columns={SCHEMA_COLUMNS} />
    </section>
  );
}

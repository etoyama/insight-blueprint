import { useEffect, useState } from "react";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { KNOWLEDGE_COLUMNS } from "@/lib/constants";
import { getKnowledgeList } from "@/api/client";
import type { KnowledgeEntry } from "@/types/api";

const EXTENDED_KNOWLEDGE_COLUMNS: ColumnDef<KnowledgeEntry>[] = [
  { key: "key", label: "Key" },
  ...KNOWLEDGE_COLUMNS,
  { key: "affects_columns", label: "Affects Columns", render: (v) => Array.isArray(v) ? v.join(", ") : String(v ?? "") },
];

export function KnowledgeSection() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    getKnowledgeList(ctrl.signal)
      .then((res) => setEntries(res.entries))
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  if (loading) return <p className="py-4 text-muted-foreground">Loading domain knowledge...</p>;
  if (error) return <ErrorBanner message={error} />;
  if (entries.length === 0) return <EmptyState message="No domain knowledge entries found" />;

  return (
    <section className="mt-6">
      <h2 className="mb-2 text-lg font-semibold">Domain Knowledge</h2>
      <DataTable data={entries} columns={EXTENDED_KNOWLEDGE_COLUMNS} />
    </section>
  );
}

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { getCautions } from "@/api/client";
import type { Caution } from "@/types/api";

const CAUTION_COLUMNS: ColumnDef<Caution>[] = [
  { key: "title", label: "Title" },
  { key: "content", label: "Content" },
  { key: "category", label: "Category", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "importance", label: "Importance", render: (v) => <Badge variant="secondary">{String(v)}</Badge> },
  { key: "affects_columns", label: "Affects Columns", render: (v) => Array.isArray(v) ? v.join(", ") : String(v ?? "") },
];

export function CautionSearchSection() {
  const [tableNames, setTableNames] = useState("");
  const [cautions, setCautions] = useState<Caution[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = () => {
    const names = tableNames
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (names.length === 0) return;
    setLoading(true);
    setError(null);
    getCautions(names)
      .then((res) => {
        setCautions(res.cautions);
        setSearched(true);
      })
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  return (
    <section className="mt-6">
      <Card>
        <CardHeader>
          <CardTitle>Caution Search</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex gap-2">
            <Input
              placeholder="Table names (comma separated)"
              value={tableNames}
              onChange={(e) => setTableNames(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Button
              onClick={handleSearch}
              disabled={loading || !tableNames.trim()}
            >
              {loading ? "Searching..." : "Search"}
            </Button>
          </div>
          {error && <ErrorBanner message={error} />}
          {searched && cautions.length === 0 && (
            <EmptyState message="No matching cautions found" />
          )}
          {cautions.length > 0 && (
            <DataTable data={cautions} columns={CAUTION_COLUMNS} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}

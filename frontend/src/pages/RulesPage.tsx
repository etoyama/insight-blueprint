import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { KNOWLEDGE_COLUMNS } from "@/lib/constants";
import { getRulesContext, getCautions } from "@/api/client";
import type { RulesContext, Caution } from "@/types/api";

function CollapsibleSection({ title, count, expanded, onToggle, children }: {
  title: string; count: number; expanded: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="cursor-pointer select-none" onClick={onToggle}>
        <CardTitle className="flex items-center justify-between">
          <span>{title} ({count})</span>
          <span className="text-muted-foreground text-sm">{expanded ? "Collapse" : "Expand"}</span>
        </CardTitle>
      </CardHeader>
      {expanded && <CardContent>{children}</CardContent>}
    </Card>
  );
}

const CAUTION_COLUMNS: ColumnDef<Caution>[] = [
  { key: "title", label: "Title" },
  { key: "content", label: "Content" },
  { key: "category", label: "Category", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "importance", label: "Importance", render: (v) => <Badge variant="secondary">{String(v)}</Badge> },
  { key: "affects_columns", label: "Affects Columns", render: (v) => (v as string[]).join(", ") },
];

export function RulesPage() {
  const [context, setContext] = useState<RulesContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);

  const [tableNames, setTableNames] = useState("");
  const [cautions, setCautions] = useState<Caution[]>([]);
  const [cautionsSearched, setCautionsSearched] = useState(false);
  const [cautionsLoading, setCautionsLoading] = useState(false);
  const [cautionsError, setCautionsError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    getRulesContext(ctrl.signal)
      .then(setContext)
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  const handleSearchCautions = () => {
    const names = tableNames
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (names.length === 0) return;
    setCautionsLoading(true);
    setCautionsError(null);
    getCautions(names)
      .then((res) => {
        setCautions(res.cautions);
        setCautionsSearched(true);
      })
      .catch((err) => {
        if (err.name !== "AbortError") setCautionsError(err.message);
      })
      .finally(() => setCautionsLoading(false));
  };

  const fetchContext = () => {
    setLoading(true);
    setError(null);
    const ctrl = new AbortController();
    getRulesContext(ctrl.signal)
      .then(setContext)
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  if (loading)
    return <p className="py-8 text-center text-muted-foreground">Loading...</p>;
  if (error) return <ErrorBanner message={error} onRetry={fetchContext} />;
  if (!context) return <EmptyState message="No context information available" />;

  return (
    <div className="flex flex-col gap-4">
      <CollapsibleSection
        title="Sources"
        count={context.total_sources}
        expanded={sourcesOpen}
        onToggle={() => setSourcesOpen(!sourcesOpen)}
      >
        {context.sources.length === 0 ? (
          <EmptyState message="No sources found" />
        ) : (
          <ul className="space-y-1 text-sm">
            {context.sources.map((s) => (
              <li key={s.id}>
                <span className="font-medium">{s.name}</span>{" "}
                <Badge variant="outline">{s.type}</Badge>{" "}
                <span className="text-muted-foreground">{s.description}</span>
              </li>
            ))}
          </ul>
        )}
      </CollapsibleSection>

      <CollapsibleSection
        title="Domain Knowledge"
        count={context.total_knowledge}
        expanded={knowledgeOpen}
        onToggle={() => setKnowledgeOpen(!knowledgeOpen)}
      >
        {context.knowledge_entries.length === 0 ? (
          <EmptyState message="No domain knowledge entries found" />
        ) : (
          <DataTable data={context.knowledge_entries} columns={KNOWLEDGE_COLUMNS} />
        )}
      </CollapsibleSection>

      <CollapsibleSection
        title="Rules"
        count={context.total_rules}
        expanded={rulesOpen}
        onToggle={() => setRulesOpen(!rulesOpen)}
      >
        {context.rules.length === 0 ? (
          <EmptyState message="No rules found" />
        ) : (
          <ul className="space-y-1 text-sm">
            {context.rules.map((rule, i) => (
              <li key={i}>{JSON.stringify(rule)}</li>
            ))}
          </ul>
        )}
      </CollapsibleSection>

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
              onKeyDown={(e) => e.key === "Enter" && handleSearchCautions()}
            />
            <Button
              onClick={handleSearchCautions}
              disabled={cautionsLoading || !tableNames.trim()}
            >
              {cautionsLoading ? "Searching..." : "Search"}
            </Button>
          </div>
          {cautionsError && <ErrorBanner message={cautionsError} />}
          {cautionsSearched && cautions.length === 0 && (
            <EmptyState message="No matching cautions found" />
          )}
          {cautions.length > 0 && (
            <DataTable data={cautions} columns={CAUTION_COLUMNS} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

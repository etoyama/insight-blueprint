import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { KNOWLEDGE_COLUMNS } from "@/lib/constants";
import { listSources, addSource, getSchema, searchCatalog, getKnowledgeList } from "@/api/client";
import type { DataSource, ColumnSchema, SearchResult, KnowledgeEntry, SourceType, AddSourceRequest } from "@/types/api";

// --- SourceListSection ---

const SOURCE_COLUMNS: ColumnDef<DataSource>[] = [
  { key: "name", label: "Name" },
  { key: "type", label: "Type", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "description", label: "Description" },
  { key: "tags", label: "Tags", render: (v) => <span>{(v as string[]).join(", ")}</span> },
  { key: "updated_at", label: "Updated At" },
];

function SourceListSection({
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

// --- SchemaSection ---

const SCHEMA_COLUMNS: ColumnDef<ColumnSchema>[] = [
  { key: "name", label: "Column Name" },
  { key: "type", label: "Type" },
  { key: "description", label: "Description" },
  { key: "nullable", label: "Nullable", render: (v) => (v ? "Yes" : "No") },
  { key: "unit", label: "Unit", render: (v) => String(v ?? "-") },
  { key: "examples", label: "Examples", render: (v) => ((v as string[] | null)?.join(", ") ?? "-") },
];

function SchemaSection({ sourceId }: { sourceId: string | null }) {
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

// --- SearchSection ---

const SEARCH_COLUMNS: ColumnDef<SearchResult>[] = [
  { key: "source_id", label: "Source ID" },
  { key: "column_name", label: "Column Name" },
  { key: "description", label: "Description" },
];

function SearchSection() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const handleSearch = () => {
    if (!query.trim()) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setError(null);
    searchCatalog(query.trim(), undefined, ctrl.signal)
      .then((res) => {
        setResults(res.results);
        setSearched(true);
      })
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  return (
    <section className="mt-6">
      <h2 className="mb-2 text-lg font-semibold">Catalog Search</h2>
      <div className="mb-4 flex gap-2">
        <Input
          placeholder="Search query..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <Button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </Button>
      </div>
      {error && <ErrorBanner message={error} />}
      {searched && results.length === 0 && <EmptyState message="No search results found" />}
      {results.length > 0 && <DataTable data={results} columns={SEARCH_COLUMNS} />}
    </section>
  );
}

// --- KnowledgeSection ---

const EXTENDED_KNOWLEDGE_COLUMNS: ColumnDef<KnowledgeEntry>[] = [
  { key: "key", label: "Key" },
  ...KNOWLEDGE_COLUMNS,
  { key: "affects_columns", label: "Affects Columns", render: (v) => Array.isArray(v) ? v.join(", ") : String(v ?? "") },
];

function KnowledgeSection() {
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

// --- CatalogPage ---

export function CatalogPage() {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    listSources(signal)
      .then((res) => setSources(res.sources))
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const ctrl = new AbortController();
    fetchSources(ctrl.signal);
    return () => ctrl.abort();
  }, []);

  if (loading) return <p className="py-8 text-center text-muted-foreground">Loading...</p>;
  if (error) return <ErrorBanner message={error} onRetry={() => fetchSources()} />;

  return (
    <div>
      <SourceListSection
        sources={sources}
        onSelect={setSelectedSourceId}
        selectedId={selectedSourceId}
        onSourceAdded={() => fetchSources()}
      />
      <SchemaSection sourceId={selectedSourceId} />
      <SearchSection />
      <KnowledgeSection />
    </div>
  );
}

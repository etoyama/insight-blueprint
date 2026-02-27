import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { listSources, addSource, getSchema, searchCatalog, getKnowledgeList } from "@/api/client";
import type { DataSource, ColumnSchema, SearchResult, KnowledgeEntry, SourceType, AddSourceRequest } from "@/types/api";

// --- SourceListSection ---

const SOURCE_COLUMNS: ColumnDef<DataSource>[] = [
  { key: "name", label: "名前" },
  { key: "type", label: "タイプ", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "description", label: "説明" },
  { key: "tags", label: "タグ", render: (v) => <span>{(v as string[]).join(", ")}</span> },
  { key: "updated_at", label: "更新日時" },
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

  const handleSubmit = async () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(form.connection);
    } catch {
      setJsonError("有効な JSON を入力してください");
      return;
    }
    setJsonError(null);
    setSubmitting(true);
    try {
      const body: AddSourceRequest = {
        source_id: form.source_id,
        name: form.name,
        type: form.type,
        description: form.description,
        connection: parsed,
      };
      await addSource(body);
      setDialogOpen(false);
      setForm({ source_id: "", name: "", type: "csv", description: "", connection: "" });
      onSourceAdded();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">データソース</h2>
        <Button onClick={() => setDialogOpen(true)}>ソース追加</Button>
      </div>
      {sources.length === 0 ? (
        <EmptyState
          message="データソースがありません"
          action={{ label: "ソースを追加", onClick: () => setDialogOpen(true) }}
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
            <DialogTitle>ソース追加</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <Input
              placeholder="ソースID"
              value={form.source_id}
              onChange={(e) => setForm({ ...form, source_id: e.target.value })}
            />
            <Input
              placeholder="名前"
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
              placeholder="説明"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
            <Textarea
              placeholder='接続情報 (JSON) 例: {"host": "localhost"}'
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
              {submitting ? "追加中..." : "追加"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

// --- SchemaSection ---

const SCHEMA_COLUMNS: ColumnDef<ColumnSchema>[] = [
  { key: "name", label: "カラム名" },
  { key: "type", label: "型" },
  { key: "description", label: "説明" },
  { key: "nullable", label: "Nullable", render: (v) => (v ? "Yes" : "No") },
  { key: "unit", label: "単位", render: (v) => String(v ?? "-") },
  { key: "examples", label: "例", render: (v) => ((v as string[] | null)?.join(", ") ?? "-") },
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
  if (loading) return <p className="py-4 text-muted-foreground">スキーマを読み込み中...</p>;
  if (error) return <ErrorBanner message={error} />;
  if (columns.length === 0) return <EmptyState message="スキーマ情報がありません" />;

  return (
    <section className="mt-6">
      <h2 className="mb-2 text-lg font-semibold">スキーマ</h2>
      <DataTable data={columns} columns={SCHEMA_COLUMNS} />
    </section>
  );
}

// --- SearchSection ---

const SEARCH_COLUMNS: ColumnDef<SearchResult>[] = [
  { key: "source_id", label: "ソースID" },
  { key: "column_name", label: "カラム名" },
  { key: "description", label: "説明" },
];

function SearchSection() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = () => {
    if (!query.trim()) return;
    const ctrl = new AbortController();
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
      <h2 className="mb-2 text-lg font-semibold">カタログ検索</h2>
      <div className="mb-4 flex gap-2">
        <Input
          placeholder="検索クエリ..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <Button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "検索中..." : "検索"}
        </Button>
      </div>
      {error && <ErrorBanner message={error} />}
      {searched && results.length === 0 && <EmptyState message="検索結果がありません" />}
      {results.length > 0 && <DataTable data={results} columns={SEARCH_COLUMNS} />}
    </section>
  );
}

// --- KnowledgeSection ---

const KNOWLEDGE_COLUMNS: ColumnDef<KnowledgeEntry>[] = [
  { key: "title", label: "タイトル" },
  { key: "content", label: "内容" },
  { key: "category", label: "カテゴリ", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "importance", label: "重要度", render: (v) => <Badge variant="secondary">{String(v)}</Badge> },
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

  if (loading) return <p className="py-4 text-muted-foreground">ドメイン知識を読み込み中...</p>;
  if (error) return <ErrorBanner message={error} />;
  if (entries.length === 0) return <EmptyState message="ドメイン知識がありません" />;

  return (
    <section className="mt-6">
      <h2 className="mb-2 text-lg font-semibold">ドメイン知識</h2>
      <DataTable data={entries} columns={KNOWLEDGE_COLUMNS} />
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

  if (loading) return <p className="py-8 text-center text-muted-foreground">読み込み中...</p>;
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

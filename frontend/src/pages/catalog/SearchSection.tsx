import { type ReactNode, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { searchCatalog } from "@/api/client";
import type { SearchResult } from "@/types/api";

/** Parse FTS5 snippet with <b> highlight markers into React nodes. */
function renderSnippet(raw: unknown): ReactNode {
  const text = String(raw ?? "");
  const parts = text.split(/(<b>|<\/b>)/);
  const nodes: ReactNode[] = [];
  let bold = false;
  for (const part of parts) {
    if (part === "<b>") {
      bold = true;
    } else if (part === "</b>") {
      bold = false;
    } else if (part) {
      nodes.push(
        bold ? (
          <mark key={nodes.length} className="bg-yellow-200 dark:bg-yellow-800">
            {part}
          </mark>
        ) : (
          part
        ),
      );
    }
  }
  return <>{nodes}</>;
}

const SEARCH_COLUMNS: ColumnDef<SearchResult>[] = [
  { key: "source_id", label: "Source" },
  { key: "title", label: "Title" },
  { key: "snippet", label: "Snippet", render: renderSnippet },
];

export function SearchSection() {
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
    <section className="mb-6">
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

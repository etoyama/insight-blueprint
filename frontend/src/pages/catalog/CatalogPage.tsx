import { useEffect, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { listSources } from "@/api/client";
import type { DataSource } from "@/types/api";
import { SourceListSection } from "./SourceListSection";
import { SchemaSection } from "./SchemaSection";
import { SearchSection } from "./SearchSection";
import { KnowledgeSection } from "./KnowledgeSection";

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
      <SearchSection />
      <SourceListSection
        sources={sources}
        onSelect={setSelectedSourceId}
        selectedId={selectedSourceId}
        onSourceAdded={() => fetchSources()}
      />
      <SchemaSection sourceId={selectedSourceId} />
      <KnowledgeSection />
    </div>
  );
}

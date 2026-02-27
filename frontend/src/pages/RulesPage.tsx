import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import { getRulesContext, getCautions } from "@/api/client";
import type { RulesContext, Caution, KnowledgeEntry } from "@/types/api";

function CollapsibleSection({ title, count, expanded, onToggle, children }: {
  title: string; count: number; expanded: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="cursor-pointer select-none" onClick={onToggle}>
        <CardTitle className="flex items-center justify-between">
          <span>{title} ({count})</span>
          <span className="text-muted-foreground text-sm">{expanded ? "折りたたむ" : "展開する"}</span>
        </CardTitle>
      </CardHeader>
      {expanded && <CardContent>{children}</CardContent>}
    </Card>
  );
}

const KNOWLEDGE_COLUMNS: ColumnDef<KnowledgeEntry>[] = [
  { key: "title", label: "タイトル" },
  { key: "content", label: "内容" },
  { key: "category", label: "カテゴリ", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "importance", label: "重要度", render: (v) => <Badge variant="secondary">{String(v)}</Badge> },
];

const CAUTION_COLUMNS: ColumnDef<Caution>[] = [
  { key: "title", label: "タイトル" },
  { key: "content", label: "内容" },
  { key: "category", label: "カテゴリ", render: (v) => <Badge variant="outline">{String(v)}</Badge> },
  { key: "importance", label: "重要度", render: (v) => <Badge variant="secondary">{String(v)}</Badge> },
  { key: "affects_columns", label: "対象カラム", render: (v) => (v as string[]).join(", ") },
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

  if (loading)
    return <p className="py-8 text-center text-muted-foreground">読み込み中...</p>;
  if (error) return <ErrorBanner message={error} />;
  if (!context) return <EmptyState message="コンテキスト情報がありません" />;

  return (
    <div className="flex flex-col gap-4">
      <CollapsibleSection
        title="ソース"
        count={context.total_sources}
        expanded={sourcesOpen}
        onToggle={() => setSourcesOpen(!sourcesOpen)}
      >
        {context.sources.length === 0 ? (
          <EmptyState message="ソースがありません" />
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
        title="ドメイン知識"
        count={context.total_knowledge}
        expanded={knowledgeOpen}
        onToggle={() => setKnowledgeOpen(!knowledgeOpen)}
      >
        {context.knowledge_entries.length === 0 ? (
          <EmptyState message="ドメイン知識がありません" />
        ) : (
          <DataTable data={context.knowledge_entries} columns={KNOWLEDGE_COLUMNS} />
        )}
      </CollapsibleSection>

      <CollapsibleSection
        title="ルール"
        count={context.total_rules}
        expanded={rulesOpen}
        onToggle={() => setRulesOpen(!rulesOpen)}
      >
        {context.rules.length === 0 ? (
          <EmptyState message="ルールがありません" />
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
          <CardTitle>注意事項検索</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex gap-2">
            <Input
              placeholder="テーブル名（カンマ区切り）"
              value={tableNames}
              onChange={(e) => setTableNames(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearchCautions()}
            />
            <Button
              onClick={handleSearchCautions}
              disabled={cautionsLoading || !tableNames.trim()}
            >
              {cautionsLoading ? "検索中..." : "検索"}
            </Button>
          </div>
          {cautionsError && <ErrorBanner message={cautionsError} />}
          {cautionsSearched && cautions.length === 0 && (
            <EmptyState message="該当する注意事項がありません" />
          )}
          {cautions.length > 0 && (
            <DataTable data={cautions} columns={CAUTION_COLUMNS} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

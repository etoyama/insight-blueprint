import { useEffect, useState } from "react";
import { getDesign } from "@/api/client";
import type { Design } from "@/types/api";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OverviewPanel } from "./OverviewPanel";
import { ReviewHistoryPanel } from "./components/ReviewHistoryPanel";
import { KnowledgePanel } from "./KnowledgePanel";

interface DesignDetailProps {
  designId: string;
  onDesignUpdated: () => void;
}

export function DesignDetail({ designId, onDesignUpdated }: DesignDetailProps) {
  const [design, setDesign] = useState<Design | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDesign = (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    getDesign(designId, signal)
      .then((d) => {
        setDesign(d);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    const ctrl = new AbortController();
    fetchDesign(ctrl.signal);
    return () => ctrl.abort();
  }, [designId]);

  const refreshDesign = () => {
    getDesign(designId)
      .then((d) => {
        setDesign(d);
        onDesignUpdated();
      })
      .catch((err) => setError(err.message));
  };

  if (loading) {
    return <p className="py-4 text-center text-muted-foreground">Loading...</p>;
  }
  if (error) {
    return <ErrorBanner message={error} onRetry={() => fetchDesign()} />;
  }
  if (!design) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{design.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="knowledge">Knowledge</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <OverviewPanel
              design={design}
              designId={designId}
              onDesignUpdated={refreshDesign}
            />
          </TabsContent>
          <TabsContent value="history">
            <ReviewHistoryPanel designId={designId} />
          </TabsContent>
          <TabsContent value="knowledge">
            <KnowledgePanel designId={designId} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

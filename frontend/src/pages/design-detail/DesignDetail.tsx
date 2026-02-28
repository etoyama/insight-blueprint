import { useEffect, useState } from "react";
import { getDesign } from "@/api/client";
import type { Design } from "@/types/api";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OverviewPanel } from "./OverviewPanel";
import { ReviewPanel } from "./ReviewPanel";
import { KnowledgePanel } from "./KnowledgePanel";

interface DesignDetailProps {
  designId: string;
  onDesignUpdated: () => void;
}

export function DesignDetail({ designId, onDesignUpdated }: DesignDetailProps) {
  const [design, setDesign] = useState<Design | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    getDesign(designId, ctrl.signal)
      .then((d) => {
        setDesign(d);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
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
    return <ErrorBanner message={error} onRetry={() => {
      setError(null);
      setLoading(true);
      getDesign(designId)
        .then((d) => {
          setDesign(d);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    }} />;
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
            <TabsTrigger value="review">Review</TabsTrigger>
            <TabsTrigger value="knowledge">Knowledge</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <OverviewPanel design={design} />
          </TabsContent>
          <TabsContent value="review">
            <ReviewPanel
              designId={designId}
              status={design.status}
              onStatusChanged={refreshDesign}
            />
          </TabsContent>
          <TabsContent value="knowledge">
            <KnowledgePanel designId={designId} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

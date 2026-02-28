import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DesignsPage } from "@/pages/DesignsPage";
import { CatalogPage } from "@/pages/catalog";
import { RulesPage } from "@/pages/RulesPage";
import { HistoryPage } from "@/pages/HistoryPage";

type Tab = "designs" | "catalog" | "rules" | "history";

const VALID_TABS: Tab[] = ["designs", "catalog", "rules", "history"];
const TAB_LABELS: Record<Tab, string> = {
  designs: "Designs",
  catalog: "Catalog",
  rules: "Rules",
  history: "History",
};

function getTabFromUrl(): Tab {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  if (tab && VALID_TABS.includes(tab as Tab)) return tab as Tab;
  return "designs";
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>(getTabFromUrl);

  useEffect(() => {
    const onPopState = () => setActiveTab(getTabFromUrl());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleTabChange = (value: string) => {
    const tab = value as Tab;
    setActiveTab(tab);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    history.pushState(null, "", url.toString());
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b px-6 py-4">
        <h1 className="text-2xl font-bold">Insight Blueprint</h1>
      </header>
      <main className="px-6 py-4">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList>
            {VALID_TABS.map((tab) => (
              <TabsTrigger key={tab} value={tab}>
                {TAB_LABELS[tab]}
              </TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="designs">
            <DesignsPage />
          </TabsContent>
          <TabsContent value="catalog">
            <CatalogPage />
          </TabsContent>
          <TabsContent value="rules">
            <RulesPage />
          </TabsContent>
          <TabsContent value="history">
            <HistoryPage />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

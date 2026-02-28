import { useState } from "react";
import { extractKnowledge, saveKnowledge } from "@/api/client";
import type { KnowledgeEntry } from "@/types/api";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/ui/button";

export function KnowledgePanel({ designId }: { designId: string }) {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const handleExtract = () => {
    setExtracting(true);
    setError(null);
    setSaved(false);
    extractKnowledge(designId)
      .then((res) => setEntries(res.entries))
      .catch((err) => setError(err.message))
      .finally(() => setExtracting(false));
  };

  const handleSave = () => {
    setSaving(true);
    setError(null);
    saveKnowledge(designId, entries)
      .then(() => setSaved(true))
      .catch((err) => setError(err.message))
      .finally(() => setSaving(false));
  };

  return (
    <div className="space-y-4 py-4">
      <Button onClick={handleExtract} disabled={extracting}>
        {extracting ? "Extracting..." : "Extract Knowledge"}
      </Button>

      {error && <ErrorBanner message={error} />}

      {entries.length > 0 && (
        <>
          <div className="space-y-2">
            {entries.map((entry) => (
              <div key={entry.key} className="rounded border p-3 text-sm">
                <div className="font-medium">{entry.title}</div>
                <div className="text-muted-foreground">{entry.content}</div>
                <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                  <span>Key: {entry.key}</span>
                  <span>Category: {entry.category}</span>
                  <span>Importance: {entry.importance}</span>
                </div>
              </div>
            ))}
          </div>
          <Button onClick={handleSave} disabled={saving || saved}>
            {saved ? "Saved" : saving ? "Saving..." : "Save Knowledge"}
          </Button>
          {saved && (
            <p className="text-sm text-green-600">Knowledge saved successfully.</p>
          )}
        </>
      )}
    </div>
  );
}

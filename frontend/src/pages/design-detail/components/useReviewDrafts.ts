import { useState, useEffect, useCallback, useMemo } from "react";
import type { DraftComment, JsonValue } from "@/types/api";

export function useReviewDrafts() {
  const [drafts, setDrafts] = useState<DraftComment[]>([]);

  const hasDrafts = drafts.length > 0;

  const addDraft = useCallback(
    (section: string, comment: string, content: unknown) => {
      const draft: DraftComment = {
        id: crypto.randomUUID(),
        target_section: section,
        target_content: structuredClone(content) as JsonValue,
        comment,
      };
      setDrafts((prev) => [...prev, draft]);
    },
    [],
  );

  const removeDraft = useCallback((draftId: string) => {
    setDrafts((prev) => prev.filter((d) => d.id !== draftId));
  }, []);

  const clearAll = useCallback(() => {
    setDrafts([]);
  }, []);

  const draftsBySection = useMemo(() => {
    const map = new Map<string, DraftComment[]>();
    for (const draft of drafts) {
      const existing = map.get(draft.target_section);
      if (existing) {
        existing.push(draft);
      } else {
        map.set(draft.target_section, [draft]);
      }
    }
    return map;
  }, [drafts]);

  // Warn on page unload when drafts exist
  useEffect(() => {
    if (!hasDrafts) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasDrafts]);

  return { drafts, addDraft, removeDraft, clearAll, hasDrafts, draftsBySection };
}

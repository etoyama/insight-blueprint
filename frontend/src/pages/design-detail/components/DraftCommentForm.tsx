import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface DraftCommentFormProps {
  onSubmit: (comment: string) => void;
  onCancel: () => void;
}

export function DraftCommentForm({ onSubmit, onCancel }: DraftCommentFormProps) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setText("");
  };

  return (
    <div className="mt-2 space-y-2 rounded border border-dashed p-3">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Add a comment on this section..."
        maxLength={2000}
        data-testid="draft-comment-input"
      />
      <div className="flex gap-2">
        <Button size="sm" onClick={handleSubmit} disabled={!text.trim()}>
          Add Draft
        </Button>
        <Button size="sm" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

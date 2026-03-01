import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DraftCommentForm } from "./DraftCommentForm";

interface InlineCommentAnchorProps {
  onAdd: (comment: string) => void;
  isReviewMode: boolean;
}

export function InlineCommentAnchor({
  onAdd,
  isReviewMode,
}: InlineCommentAnchorProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!isReviewMode) return null;

  return (
    <div>
      {!isOpen && (
        <Button
          size="sm"
          variant="ghost"
          className="mt-1 text-xs"
          onClick={() => setIsOpen(true)}
          data-testid="comment-button"
        >
          Comment
        </Button>
      )}
      {isOpen && (
        <DraftCommentForm
          onSubmit={(comment) => {
            onAdd(comment);
            setIsOpen(false);
          }}
          onCancel={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}

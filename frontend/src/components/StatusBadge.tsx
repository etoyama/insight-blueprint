import { Badge } from "@/components/ui/badge";
import type { DesignStatus } from "@/types/api";
import { DESIGN_STATUS_LABELS } from "@/lib/constants";

const STATUS_STYLES: Record<DesignStatus, string> = {
  draft: "bg-gray-100 text-gray-800 hover:bg-gray-100",
  active: "bg-blue-100 text-blue-800 hover:bg-blue-100",
  pending_review: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100",
  supported: "bg-green-100 text-green-800 hover:bg-green-100",
  rejected: "bg-red-100 text-red-800 hover:bg-red-100",
  inconclusive: "bg-orange-100 text-orange-800 hover:bg-orange-100",
};

interface StatusBadgeProps {
  status: DesignStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant="secondary" className={STATUS_STYLES[status]}>
      {DESIGN_STATUS_LABELS[status]}
    </Badge>
  );
}

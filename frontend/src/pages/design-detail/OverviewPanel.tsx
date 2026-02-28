import { StatusBadge } from "@/components/StatusBadge";
import { JsonTree } from "@/components/JsonTree";
import { formatDateTime } from "@/lib/utils";
import type { Design } from "@/types/api";

export function OverviewPanel({ design }: { design: Design }) {
  return (
    <div className="space-y-3 py-4 text-sm">
      <Field label="Status"><StatusBadge status={design.status} /></Field>
      <Field label="Theme ID">{design.theme_id}</Field>
      <Field label="Hypothesis Statement">{design.hypothesis_statement}</Field>
      <Field label="Hypothesis Background">{design.hypothesis_background}</Field>
      <Field label="Source IDs">
        {design.source_ids.length > 0 ? design.source_ids.join(", ") : "-"}
      </Field>
      <Field label="Created">{formatDateTime(design.created_at)}</Field>
      <Field label="Updated">{formatDateTime(design.updated_at)}</Field>
      {Object.keys(design.metrics).length > 0 && (
        <JsonField label="Metrics" data={design.metrics} />
      )}
      {design.explanatory.length > 0 && (
        <JsonField label="Explanatory" data={design.explanatory} />
      )}
      {design.chart.length > 0 && (
        <JsonField label="Chart" data={design.chart} />
      )}
      {design.next_action && (
        <JsonField label="Next Action" data={design.next_action} />
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <span className="w-40 shrink-0 font-medium">{label}</span>
      <span>{children}</span>
    </div>
  );
}

function JsonField({ label, data }: { label: string; data: Record<string, unknown> | Record<string, unknown>[] }) {
  return (
    <div>
      <span className="font-medium">{label}</span>
      <JsonTree data={data} />
    </div>
  );
}

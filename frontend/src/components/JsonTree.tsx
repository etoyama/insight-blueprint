import { useState } from "react";

interface JsonTreeProps {
  data: Record<string, unknown> | Record<string, unknown>[];
  defaultExpanded?: boolean;
}

export function JsonTree({ data, defaultExpanded = true }: JsonTreeProps) {
  return (
    <div className="font-mono text-sm">
      <JsonNode value={data} defaultExpanded={defaultExpanded} />
    </div>
  );
}

function JsonNode({
  value,
  defaultExpanded,
}: {
  value: unknown;
  defaultExpanded: boolean;
}) {
  if (value === null) return <PrimitiveNode className="text-muted-foreground" text="null" />;
  if (typeof value === "boolean") return <PrimitiveNode className="text-blue-600" text={String(value)} />;
  if (typeof value === "number") return <PrimitiveNode className="text-green-600" text={String(value)} />;
  if (typeof value === "string") return <PrimitiveNode className="text-amber-700" text={`"${value}"`} />;
  if (Array.isArray(value)) return <ArrayNode items={value} defaultExpanded={defaultExpanded} />;
  if (typeof value === "object") return <ObjectNode entries={Object.entries(value as Record<string, unknown>)} defaultExpanded={defaultExpanded} />;
  return <span>{String(value)}</span>;
}

function PrimitiveNode({ className, text }: { className: string; text: string }) {
  return <span className={className}>{text}</span>;
}

function ArrayNode({ items, defaultExpanded }: { items: unknown[]; defaultExpanded: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  if (items.length === 0) return <span>{"[]"}</span>;
  return (
    <div>
      <button
        className="text-muted-foreground hover:text-foreground"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "▼" : "▶"} [{items.length}]
      </button>
      {expanded && (
        <div className="ml-4 border-l pl-2">
          {items.map((item, i) => (
            <div key={i}>
              <JsonNode value={item} defaultExpanded={defaultExpanded} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ObjectNode({ entries, defaultExpanded }: { entries: [string, unknown][]; defaultExpanded: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  if (entries.length === 0) return <span>{"{}"}</span>;
  return (
    <div>
      <button
        className="text-muted-foreground hover:text-foreground"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "▼" : "▶"} {"{"}
        {entries.length}
        {"}"}
      </button>
      {expanded && (
        <div className="ml-4 border-l pl-2">
          {entries.map(([k, v]) => (
            <div key={k}>
              <span className="text-purple-600">{k}</span>:{" "}
              <JsonNode value={v} defaultExpanded={defaultExpanded} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

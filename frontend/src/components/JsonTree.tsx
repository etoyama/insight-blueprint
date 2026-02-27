import { useState } from "react";

interface JsonTreeProps {
  data: Record<string, unknown> | Record<string, unknown>[];
  defaultExpanded?: boolean;
}

export function JsonTree({ data, defaultExpanded = false }: JsonTreeProps) {
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
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (value === null) return <span className="text-muted-foreground">null</span>;
  if (typeof value === "boolean") return <span className="text-blue-600">{String(value)}</span>;
  if (typeof value === "number") return <span className="text-green-600">{value}</span>;
  if (typeof value === "string") return <span className="text-amber-700">"{value}"</span>;

  if (Array.isArray(value)) {
    if (value.length === 0) return <span>{"[]"}</span>;
    return (
      <div>
        <button
          className="text-muted-foreground hover:text-foreground"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "▼" : "▶"} [{value.length}]
        </button>
        {expanded && (
          <div className="ml-4 border-l pl-2">
            {value.map((item, i) => (
              <div key={i}>
                <JsonNode value={item} defaultExpanded={false} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
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
                <JsonNode value={v} defaultExpanded={false} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return <span>{String(value)}</span>;
}

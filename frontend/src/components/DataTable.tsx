import type { ReactNode } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface ColumnDef<T> {
  key: keyof T;
  label: string;
  render?: (value: T[keyof T], row: T) => ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  onRowClick?: (row: T) => void;
  selectedRow?: (row: T) => boolean;
  rowKey?: (row: T, index: number) => string | number;
}

export function DataTable<T>({
  data,
  columns,
  onRowClick,
  selectedRow,
  rowKey,
}: DataTableProps<T>) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead key={String(col.key)}>{col.label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, i) => (
          <TableRow
            key={rowKey ? rowKey(row, i) : i}
            className={[
              onRowClick ? "cursor-pointer" : "",
              selectedRow?.(row) ? "bg-muted" : "",
            ].join(" ")}
            onClick={() => onRowClick?.(row)}
          >
            {columns.map((col) => (
              <TableCell key={String(col.key)}>
                {col.render
                  ? col.render(row[col.key], row)
                  : String(row[col.key] ?? "")}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

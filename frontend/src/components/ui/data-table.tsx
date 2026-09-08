import React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "./skeleton";
import { EmptyState } from "./empty-state";

export interface Column<T> {
  key: keyof T;
  label: string;
  align?: "left" | "right" | "center";
  render?: (value: T[keyof T], row: T) => React.ReactNode;
  width?: string;
}

interface DataTableProps<T extends Record<string, unknown>> {
  columns: Column<T>[];
  rows: T[];
  onRowClick?: (row: T) => void;
  isLoading?: boolean;
  emptyState?: React.ReactNode;
  stickyHeader?: boolean;
  rowKey?: keyof T;
  className?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  onRowClick,
  isLoading = false,
  emptyState,
  stickyHeader = false,
  rowKey,
  className,
}: DataTableProps<T>) {
  // Render loading skeleton rows
  if (isLoading) {
    return (
      <div className={cn("border border-border rounded-lg overflow-hidden", className)}>
        <table className="w-full">
          <thead className="bg-n-50 border-b border-border">
            <tr>
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className={cn(
                    "px-4 py-2.5 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground h-11",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center"
                  )}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, idx) => (
              <tr key={idx} className="border-b border-border h-14">
                {columns.map((col) => (
                  <td key={String(col.key)} className="px-4 py-3">
                    <Skeleton className="h-4 w-24" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Render empty state
  if (rows.length === 0) {
    return (
      emptyState || (
        <div className="rounded-lg border border-border bg-card">
          <EmptyState icon={() => <div />} title="No data" description="No items to display" />
        </div>
      )
    );
  }

  // Render table
  return (
    <div className={cn("border border-border rounded-lg overflow-hidden", className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className={cn("bg-n-50 border-b border-border", stickyHeader && "sticky top-0 z-10")}>
            <tr>
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className={cn(
                    "px-4 py-2.5 text-2xs font-semibold uppercase tracking-wider text-muted-foreground h-11",
                    col.align === "left" && "text-left",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center"
                  )}
                  style={col.width ? { width: col.width } : {}}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row, idx) => (
              <tr
                key={rowKey ? String(row[rowKey]) : idx}
                className={cn(
                  "h-14 hover:bg-teal-50/50 transition-colors",
                  onRowClick && "cursor-pointer"
                )}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col) => (
                  <td
                    key={String(col.key)}
                    className={cn(
                      "px-4 py-3",
                      col.align === "right" && "text-right tabular-nums",
                      col.align === "center" && "text-center"
                    )}
                  >
                    {/* A cell with no render function is printed as-is, so it
                        has to be coerced — an arbitrary T[keyof T] is not a
                        ReactNode. */}
                    {col.render
                      ? col.render(row[col.key], row)
                      : (row[col.key] as React.ReactNode)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
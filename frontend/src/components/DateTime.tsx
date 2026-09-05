import { ReactNode } from "react";

export interface DateTimeProps {
  date: Date | string | null | undefined;
  format?: "date" | "time" | "datetime";
  className?: string;
}

/**
 * Format and display dates and times in Pakistan locale (en-PK).
 * - format: "date" = 04 Sep 2026
 *          "time" = 15:02:30
 *          "datetime" = 04 Sep 2026, 15:02:30
 */
export function DateTime({
  date,
  format = "date",
  className,
}: DateTimeProps): ReactNode {
  if (!date) {
    return "—";
  }

  const d = typeof date === "string" ? new Date(date) : date;

  if (isNaN(d.getTime())) {
    return "—";
  }

  switch (format) {
    case "date":
      return d.toLocaleDateString("en-PK", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });

    case "time":
      return d.toLocaleTimeString("en-PK", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });

    case "datetime":
      return (
        <>
          {d.toLocaleDateString("en-PK", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}{" "}
          {d.toLocaleTimeString("en-PK", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
          })}
        </>
      );
  }
}
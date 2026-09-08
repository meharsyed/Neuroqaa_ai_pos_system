import React from "react";
import { cn } from "@/lib/utils";

interface DateDisplayProps extends React.HTMLAttributes<HTMLSpanElement> {
  value: string | Date;
  format?: "short" | "long" | "relative";
}

export function DateTime({ value, format = "short", className }: DateDisplayProps) {
  const date = typeof value === "string" ? new Date(value) : value;

  let formatted: string;

  if (format === "relative") {
    // "2 hours ago", "3 days ago", etc.
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) {
      formatted = "just now";
    } else if (minutes < 60) {
      formatted = `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
    } else if (hours < 24) {
      formatted = `${hours} hour${hours > 1 ? "s" : ""} ago`;
    } else if (days < 30) {
      formatted = `${days} day${days > 1 ? "s" : ""} ago`;
    } else {
      formatted = date.toLocaleDateString("en-PK", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    }
  } else if (format === "long") {
    // "02 September 2026"
    formatted = date.toLocaleDateString("en-PK", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } else {
    // "02 Sep 2026" (default short)
    formatted = date.toLocaleDateString("en-PK", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  return <span className={cn("text-foreground", className)}>{formatted}</span>;
}

export function Time({ value, className }: { value: string | Date; className?: string }) {
  const date = typeof value === "string" ? new Date(value) : value;
  const formatted = date.toLocaleTimeString("en-PK", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return <span className={cn("tabular-nums font-mono text-foreground", className)}>{formatted}</span>;
}
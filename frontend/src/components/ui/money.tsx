import React from "react";
import { cn } from "@/lib/utils";

interface MoneyProps extends React.HTMLAttributes<HTMLSpanElement> {
  paise: number;
  compact?: boolean;
  sign?: boolean;
}

export function Money({ paise, compact, sign, className }: MoneyProps) {
  const rs = paise / 100;

  let formatted: string;
  if (compact) {
    // 147911.40 → Rs 147.9k
    if (Math.abs(rs) >= 1_000_000) {
      formatted = `Rs ${(rs / 1_000_000).toFixed(1)}M`;
    } else if (Math.abs(rs) >= 1_000) {
      formatted = `Rs ${(rs / 1_000).toFixed(1)}k`;
    } else {
      formatted = `Rs ${rs.toFixed(0)}`;
    }
  } else {
    // 147911.40 → Rs 147,911.40
    formatted = `Rs ${rs.toLocaleString("en-PK", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  if (sign) {
    // Handle positive/negative with sign
    if (rs > 0) {
      formatted = `+ ${formatted}`;
    } else if (rs < 0) {
      formatted = `− ${formatted.replace("-", "")}`;
    } else {
      formatted = `± ${formatted}`;
    }
  }

  return (
    <span className={cn("tabular-nums font-mono text-foreground", className)}>
      {formatted}
    </span>
  );
}
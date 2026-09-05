import React from "react";
import { cn } from "@/lib/utils";

interface MoneyProps extends React.HTMLAttributes<HTMLSpanElement> {
  paise: number;
  compact?: boolean;
  sign?: boolean;
  /** "always" (default) = 1,200.00 · "auto" = drop .00 on whole rupees */
  decimals?: "always" | "auto";
}

export function Money({ paise, compact, sign, decimals = "always", className }: MoneyProps) {
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
    const whole = decimals === "auto" && Number.isInteger(rs);
    formatted = `Rs ${rs.toLocaleString("en-PK", {
      minimumFractionDigits: whole ? 0 : 2,
      maximumFractionDigits: whole ? 0 : 2,
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
    <span className={cn("tabular-nums", className)}>
      {formatted}
    </span>
  );
}
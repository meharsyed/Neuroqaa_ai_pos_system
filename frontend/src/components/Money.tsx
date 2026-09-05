import { ReactNode } from "react";

export interface MoneyProps {
  paise: number | null | undefined;
  decimals?: "auto" | "always" | "never";
  className?: string;
  symbol?: true | false;
}

/**
 * Format and display money amounts.
 * - Input in paise (integer)
 * - Displays as rupees with proper formatting
 * - Decimals: "auto" = show .00 only if needed (14,000 vs 14,000.50)
 *            "always" = always show .00
 *            "never" = never show decimals
 */
export function Money({
  paise,
  decimals = "auto",
  className,
  symbol = true,
}: MoneyProps): ReactNode {
  if (paise === null || paise === undefined) {
    return symbol ? "Rs —" : "—";
  }

  const rupees = paise / 100;
  let formatted: string;

  if (decimals === "never") {
    formatted = Math.round(rupees).toLocaleString("en-IN");
  } else if (decimals === "always") {
    formatted = rupees.toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  } else {
    // "auto" - show decimals only if fractional part exists
    const rounded = Math.round(rupees * 100) / 100;
    const hasDecimals = rounded % 1 !== 0;
    formatted = rupees.toLocaleString("en-IN", {
      minimumFractionDigits: hasDecimals ? 2 : 0,
      maximumFractionDigits: 2,
    });
  }

  return symbol ? `Rs ${formatted}` : formatted;
}
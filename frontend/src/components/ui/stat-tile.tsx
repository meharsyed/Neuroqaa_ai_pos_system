import React from "react";
import { ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "./card";

interface StatTileProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  delta?: string | number;
  deltaDirection?: "up" | "down";
  hint?: string;
  tone?: "neutral" | "warning" | "danger";
  href?: string;
  className?: string;
}

export function StatTile({
  label,
  value,
  icon: Icon,
  delta,
  deltaDirection,
  hint,
  tone = "neutral",
  className,
}: StatTileProps) {
  const toneStyles = {
    neutral: "text-muted-foreground",
    warning: "text-warning",
    danger: "text-destructive",
  };

  const deltaColor = {
    up: "text-success",
    down: "text-destructive",
  };

  return (
    <Card className={cn("flex flex-col space-y-3", className)}>
      <div className="flex items-start justify-between">
        <div className="space-y-0.5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
        </div>
        {Icon && <Icon className={cn("h-5 w-5", toneStyles[tone])} />}
      </div>

      <div className="space-y-1.5">
        <p className="text-3xl font-semibold tabular-nums text-foreground">{value}</p>

        {(delta || hint) && (
          <div className="flex items-center gap-2">
            {delta && deltaDirection && (
              <>
                {deltaDirection === "up" ? (
                  <ArrowUp className="h-3.5 w-3.5 text-success" />
                ) : (
                  <ArrowDown className="h-3.5 w-3.5 text-destructive" />
                )}
                <span className={cn("text-xs font-medium", deltaColor[deltaDirection])}>{delta}</span>
              </>
            )}
            {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
          </div>
        )}
      </div>
    </Card>
  );
}
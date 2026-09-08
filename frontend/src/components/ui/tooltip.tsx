import * as React from "react";
import { cn } from "@/lib/utils";

interface SimpleTooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function SimpleTooltip({ content, children, className }: SimpleTooltipProps) {
  const [isVisible, setIsVisible] = React.useState(false);

  return (
    <div className={cn("relative inline-block group", className)}>
      <div onMouseEnter={() => setIsVisible(true)} onMouseLeave={() => setIsVisible(false)}>
        {children}
      </div>
      {isVisible && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-n-900 text-n-0 text-xs rounded whitespace-nowrap z-50 pointer-events-none animate-fade-up">
          {content}
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-4 border-transparent border-t-n-900" />
        </div>
      )}
    </div>
  );
}
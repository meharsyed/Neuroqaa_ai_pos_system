import { cn } from "@/lib/utils";

function Skeleton({ className }: { className?: string }) {
  return <div className={cn("bg-muted animate-shimmer", className)} />;
}

export { Skeleton };
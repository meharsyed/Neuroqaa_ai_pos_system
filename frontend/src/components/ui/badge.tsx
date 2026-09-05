import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        neutral: "border-transparent bg-n-100 text-n-700",
        success: "border-transparent bg-success-bg text-success",
        warning: "border-transparent bg-warning-bg text-warning",
        danger: "border-transparent bg-destructive-bg text-destructive",
        info: "border-transparent bg-info-bg text-info",
        outline: "border-border text-foreground bg-transparent",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({ className, variant, dot, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span className={cn(
          "inline-block h-1.5 w-1.5 rounded-full mr-1.5",
          variant === "success" && "bg-success",
          variant === "warning" && "bg-warning",
          variant === "danger" && "bg-destructive",
          variant === "info" && "bg-info",
          (variant === "default" || variant === "neutral" || variant === "outline") && "bg-foreground"
        )} />
      )}
      {props.children}
    </div>
  );
}
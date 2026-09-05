import React from "react";
import { cn } from "@/lib/utils";

const FormField = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("space-y-1.5", className)} {...props} />
);

const FormLabel = React.forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => (
  <label
    ref={ref}
    className={cn("text-sm font-medium text-foreground block", className)}
    {...props}
  />
));
FormLabel.displayName = "FormLabel";

const FormHint = ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn("text-xs text-muted-foreground mt-0.5", className)} {...props} />
);

const FormError = ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn("text-xs text-destructive mt-0.5", className)} {...props} />
);

export { FormField, FormLabel, FormHint, FormError };
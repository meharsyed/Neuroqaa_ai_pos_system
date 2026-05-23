import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { catalogApi, rupeesToPaise } from "@/lib/catalog";
import type { Product } from "@/types/catalog";

const schema = z.object({
  qty: z.string().refine((v) => parseFloat(v) > 0, "Quantity must be greater than 0"),
  cost_price: z.string().optional(),
  reference: z.string().optional().default(""),
  notes: z.string().optional().default(""),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  product: Product | null;
}

export function StockInModal({ open, onOpenChange, product }: Props) {
  const qc = useQueryClient();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { qty: "", cost_price: "", reference: "", notes: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!product) throw new Error("No product selected");
      return catalogApi.inventory.stockIn({
        product: product.id,
        qty: values.qty,
        cost_price_paise: values.cost_price ? rupeesToPaise(values.cost_price) : undefined,
        reference: values.reference || "",
        notes: values.notes || "",
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["inventory"] });
      qc.invalidateQueries({ queryKey: ["low-stock"] });
      reset();
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Stock In</DialogTitle>
          {product && (
            <DialogDescription>
              <span className="font-mono text-xs">{product.sku}</span> — {product.name}
              <span className="ml-2 text-muted-foreground">
                (current: {product.stock_qty} {product.unit})
              </span>
            </DialogDescription>
          )}
        </DialogHeader>

        <form
          id="stock-in-form"
          onSubmit={handleSubmit((v) => mutation.mutate(v))}
          className="space-y-4"
        >
          <div className="space-y-1">
            <Label htmlFor="qty">
              Quantity ({product?.unit ?? "units"}) *
            </Label>
            <Input
              id="qty"
              type="number"
              step="0.001"
              min="0.001"
              placeholder="e.g. 100"
              autoFocus
              {...register("qty")}
            />
            {errors.qty && <p className="text-xs text-destructive">{errors.qty.message}</p>}
          </div>

          <div className="space-y-1">
            <Label htmlFor="cost_price">
              Cost Price (Rs) <span className="text-muted-foreground text-xs">optional</span>
            </Label>
            <Input
              id="cost_price"
              type="number"
              step="0.01"
              min="0"
              placeholder={product ? String(product.cost_price_paise / 100) : ""}
              {...register("cost_price")}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="reference">
              Reference <span className="text-muted-foreground text-xs">e.g. PO-001</span>
            </Label>
            <Input id="reference" placeholder="Purchase order / supplier ref" {...register("reference")} />
          </div>

          <div className="space-y-1">
            <Label htmlFor="notes">Notes</Label>
            <Textarea id="notes" rows={2} placeholder="Any additional notes..." {...register("notes")} />
          </div>

          {mutation.isError && (
            <p className="text-sm text-destructive">Failed to record stock. Please try again.</p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => { reset(); onOpenChange(false); }}>
            Cancel
          </Button>
          <Button type="submit" form="stock-in-form" disabled={mutation.isPending || !product}>
            {mutation.isPending ? "Recording…" : "Record Stock In"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
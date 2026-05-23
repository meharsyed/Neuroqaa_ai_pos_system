import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { catalogApi, rupeesToPaise } from "@/lib/catalog";
import type { Category, Product, UNIT_OPTIONS } from "@/types/catalog";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  sku: z.string().min(1, "SKU is required"),
  barcode: z.string().optional().default(""),
  category: z.coerce.number().nullable().optional(),
  unit: z.string().min(1, "Unit is required"),
  description: z.string().optional().default(""),
  cost_price: z.string().min(1, "Cost price is required"),
  sell_price: z.string().min(1, "Sell price is required"),
  low_stock_threshold: z.string().optional().default("0"),
  is_active: z.boolean().default(true),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  product?: Product | null;
}

const UNIT_OPTIONS_LIST = [
  { value: "pcs", label: "Pieces" },
  { value: "kg", label: "Kilograms" },
  { value: "litre", label: "Litres" },
  { value: "metre", label: "Metres" },
  { value: "sq_metre", label: "Square Metres" },
  { value: "box", label: "Box" },
  { value: "dozen", label: "Dozen" },
  { value: "bundle", label: "Bundle" },
];

export function ProductModal({ open, onOpenChange, product }: Props) {
  const qc = useQueryClient();
  const isEdit = Boolean(product);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogApi.categories.list,
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "", sku: "", barcode: "", unit: "pcs",
      description: "", cost_price: "", sell_price: "",
      low_stock_threshold: "0", is_active: true,
    },
  });

  useEffect(() => {
    if (product) {
      reset({
        name: product.name,
        sku: product.sku,
        barcode: product.barcode,
        category: product.category ?? undefined,
        unit: product.unit,
        description: product.description,
        cost_price: String(product.cost_price_paise / 100),
        sell_price: String(product.sell_price_paise / 100),
        low_stock_threshold: product.low_stock_threshold,
        is_active: product.is_active,
      });
    } else {
      reset({ name: "", sku: "", barcode: "", unit: "pcs", description: "", cost_price: "", sell_price: "", low_stock_threshold: "0", is_active: true });
    }
  }, [product, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = {
        name: values.name,
        sku: values.sku,
        barcode: values.barcode || "",
        category: values.category || null,
        unit: values.unit,
        description: values.description || "",
        cost_price_paise: rupeesToPaise(values.cost_price),
        sell_price_paise: rupeesToPaise(values.sell_price),
        low_stock_threshold: values.low_stock_threshold || "0",
        is_active: values.is_active,
      };
      return isEdit && product
        ? catalogApi.products.update(product.id, payload)
        : catalogApi.products.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["low-stock"] });
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Product" : "New Product"}</DialogTitle>
        </DialogHeader>

        <form
          id="product-form"
          onSubmit={handleSubmit((v) => mutation.mutate(v))}
          className="grid grid-cols-2 gap-4"
        >
          {/* Name */}
          <div className="col-span-2 space-y-1">
            <Label htmlFor="name">Product Name *</Label>
            <Input id="name" placeholder="e.g. Blue Ceramic Tile 30×30" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          {/* SKU */}
          <div className="space-y-1">
            <Label htmlFor="sku">SKU *</Label>
            <Input id="sku" placeholder="e.g. TILE-001" {...register("sku")} />
            {errors.sku && <p className="text-xs text-destructive">{errors.sku.message}</p>}
          </div>

          {/* Barcode */}
          <div className="space-y-1">
            <Label htmlFor="barcode">Barcode</Label>
            <Input id="barcode" placeholder="e.g. 8901234567890" {...register("barcode")} />
          </div>

          {/* Category */}
          <div className="space-y-1">
            <Label htmlFor="category">Category</Label>
            <Select
              id="category"
              options={categories.map((c: Category) => ({ value: c.id, label: c.name }))}
              placeholder="— Select category —"
              {...register("category")}
            />
          </div>

          {/* Unit */}
          <div className="space-y-1">
            <Label htmlFor="unit">Unit *</Label>
            <Select id="unit" options={UNIT_OPTIONS_LIST} {...register("unit")} />
            {errors.unit && <p className="text-xs text-destructive">{errors.unit.message}</p>}
          </div>

          {/* Cost Price */}
          <div className="space-y-1">
            <Label htmlFor="cost_price">Cost Price (Rs) *</Label>
            <Input id="cost_price" type="number" step="0.01" min="0" placeholder="250.00" {...register("cost_price")} />
            {errors.cost_price && <p className="text-xs text-destructive">{errors.cost_price.message}</p>}
          </div>

          {/* Sell Price */}
          <div className="space-y-1">
            <Label htmlFor="sell_price">Sell Price (Rs) *</Label>
            <Input id="sell_price" type="number" step="0.01" min="0" placeholder="350.00" {...register("sell_price")} />
            {errors.sell_price && <p className="text-xs text-destructive">{errors.sell_price.message}</p>}
          </div>

          {/* Low Stock Threshold */}
          <div className="space-y-1">
            <Label htmlFor="low_stock_threshold">Low Stock Alert (qty)</Label>
            <Input id="low_stock_threshold" type="number" step="0.001" min="0" placeholder="10" {...register("low_stock_threshold")} />
          </div>

          {/* Active */}
          <div className="flex items-center gap-2 pt-6">
            <input id="is_active" type="checkbox" className="h-4 w-4 rounded border" {...register("is_active")} />
            <Label htmlFor="is_active">Active</Label>
          </div>

          {/* Description */}
          <div className="col-span-2 space-y-1">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" rows={2} placeholder="Optional product notes..." {...register("description")} />
          </div>

          {mutation.isError && (
            <p className="col-span-2 text-sm text-destructive">
              Failed to save. Please check your inputs.
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" type="button" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="product-form" disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : isEdit ? "Save Changes" : "Create Product"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
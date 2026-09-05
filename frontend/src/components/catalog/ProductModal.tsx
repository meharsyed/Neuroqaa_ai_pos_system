import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload, X, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { ProductImage } from "@/components/ProductImage";
import { catalogApi, rupeesToPaise } from "@/lib/catalog";
import { useToast } from "@/lib/use-toast";
import { cn } from "@/lib/utils";
import type { Category, Product } from "@/types/catalog";

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
  const { toast } = useToast();
  const isEdit = Boolean(product);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);

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
      if (product.image_url) {
        setImagePreview(product.image_url);
      }
    } else {
      reset({ name: "", sku: "", barcode: "", unit: "pcs", description: "", cost_price: "", sell_price: "", low_stock_threshold: "0", is_active: true });
      setImagePreview(null);
      setImageFile(null);
    }
    setImageError(null);
  }, [product, reset, open]);

  const validateAndSelectImage = (file: File) => {
    const MAX_SIZE = 20 * 1024 * 1024; // 20MB

    if (file.size > MAX_SIZE) {
      setImageError(`File is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max 20MB.`);
      return;
    }

    setImageFile(file);
    setImageError(null);
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      validateAndSelectImage(file);
    }
  };

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
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

      let savedProduct;
      if (isEdit && product) {
        savedProduct = await catalogApi.products.update(product.id, payload);
      } else {
        savedProduct = await catalogApi.products.create(payload);
      }

      if (imageFile) {
        const formData = new FormData();
        formData.append("image", imageFile);
        await catalogApi.products.uploadImage(savedProduct.id, formData);
      }

      return savedProduct;
    },
    onSuccess: (saved) => {
      toast({ title: isEdit ? "Product updated" : "Product created", description: `${saved.name} saved successfully` });
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["low-stock"] });
      setImageFile(null);
      setImagePreview(null);
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
          {/* Product Image Upload */}
          <div className="col-span-2 space-y-2">
            <Label>Product Image</Label>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={cn(
                "relative rounded-lg border-2 border-dashed transition-all p-6 cursor-pointer",
                dragActive
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 bg-muted/30 hover:border-primary/50",
                imageError ? "border-destructive bg-destructive/5" : ""
              )}
            >
              {imagePreview ? (
                <div className="flex items-start justify-between gap-4">
                  <ProductImage
                    imageUrl={imagePreview}
                    productName="Preview"
                    size="lg"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Image selected</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {imageFile?.name || "Existing image"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {imageFile ? `${(imageFile.size / 1024 / 1024).toFixed(2)}MB` : ""}
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setImageFile(null);
                        setImagePreview(null);
                        setImageError(null);
                      }}
                      className="mt-3 inline-flex items-center gap-1.5 text-xs text-destructive hover:underline"
                    >
                      <X className="h-3 w-3" />
                      Remove image
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex flex-col items-center justify-center w-full cursor-pointer"
                >
                  <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm font-medium text-foreground">
                    Drop image here or click to browse
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Any image format • Max 20MB
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    JPEG, PNG, GIF, WebP, BMP, TIFF, SVG, etc.
                  </p>
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={(e) => {
                  const file = e.currentTarget.files?.[0];
                  if (file) {
                    validateAndSelectImage(file);
                  }
                }}
                className="hidden"
              />
            </div>
            {imageError && (
              <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{imageError}</span>
              </div>
            )}
          </div>

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
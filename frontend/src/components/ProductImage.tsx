import { useState } from "react";
import { Package } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProductImageProps {
  imageUrl?: string | null;
  productName: string;
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

const sizeClasses = {
  sm: "h-8 w-8",
  md: "h-12 w-12",
  lg: "h-24 w-24",
  xl: "h-32 w-32",
};

const iconSizes = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-12 w-12",
  xl: "h-16 w-16",
};

export function ProductImage({
  imageUrl,
  productName,
  size = "md",
  className,
}: ProductImageProps) {
  const [imageError, setImageError] = useState(false);

  const hasImage = imageUrl && !imageError;

  if (hasImage) {
    return (
      <img
        src={imageUrl}
        alt={productName}
        loading="lazy"
        onError={() => setImageError(true)}
        className={cn(
          "object-cover rounded-lg bg-muted",
          sizeClasses[size],
          className
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-lg bg-muted text-muted-foreground",
        sizeClasses[size],
        className
      )}
    >
      <Package className={iconSizes[size]} />
    </div>
  );
}
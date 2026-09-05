import { cn } from "@/lib/utils";
import type { Setting } from "@/types/config";

interface TemplateSelectorProps {
  setting: Setting;
  value: string;
  onChange: (templateType: string) => void;
  disabled?: boolean;
  saved?: boolean;
}

export default function ReceiptTemplateSelector({
  setting,
  value,
  onChange,
  disabled = false,
  saved = false,
}: TemplateSelectorProps) {
  const templates = [
    {
      id: "classic",
      name: "Classic",
      emoji: "🎯",
      description: "Professional Traditional",
      preview: `
        ═══════════════════════════════════
          NEUROQAA SANITARY & TILES
        ═══════════════════════════════════

        INVOICE #: INV-000001
        Date: 14 Jun 2026

        BILL TO:
        Customer Name
        Phone: +92-300-1234567

        ───────────────────────────────────
        Description      Qty  Price   Total
        ───────────────────────────────────
        Blue Tile         2   1200    2400
        Red Tile          3   1500    4500

        Subtotal:              6900
        Tax:                      0
        Total Due:             6900
        ═══════════════════════════════════
      `,
    },
    {
      id: "modern",
      name: "Modern",
      emoji: "✨",
      description: "Clean Contemporary",
      preview: `
        ┌─────────────────────────────────┐
        │ Neuroqaa  INV-000001           │
        │ Modern    14 Jun 2026          │
        └─────────────────────────────────┘

        Customer: Ali Ahmed
        Phone: +92-300-1234567

        ┌─────────────────────────────────┐
        │ Item    │ Qty │ Price │ Total   │
        ├─────────────────────────────────┤
        │ Tile    │  2  │ 1200  │ 2400    │
        │ Tile    │  3  │ 1500  │ 4500    │
        └─────────────────────────────────┘

        Subtotal .......... 6900
        Tax ................ 0
        Total ............ 6900
      `,
    },
    {
      id: "itemized",
      name: "Itemized",
      emoji: "📋",
      description: "Detailed with Borders",
      preview: `
        ╔═════════════════════════════════╗
        ║   NEUROQAA - INVOICE            ║
        ║   Professional POS System       ║
        ╠═════════════════════════════════╣
        ║ Invoice #: INV-000001           ║
        ║ Date: 14 Jun 2026, 03:15 PM    ║
        ╠═════════════════════════════════╣
        ║ CUSTOMER                        ║
        ║ Name: Ali Ahmed                 ║
        ║ Phone: +92-300-1234567          ║
        ╠═════════════════════════════════╣
        ║                                 ║
        ║ 1. Blue Ceramic Tile 30×30     ║
        ║    Qty: 2 × Rs. 1,200 = Rs. 2400║
        ║                                 ║
        ║ 2. Red Floor Tile 20×20        ║
        ║    Qty: 3 × Rs. 1,500 = Rs. 4500║
        ║                                 ║
        ╠═════════════════════════════════╣
        ║ Subtotal: Rs. 6,900             ║
        ║ Tax: Rs. 0                      ║
        ║ TOTAL: Rs. 6,900                ║
        ╚═════════════════════════════════╝
      `,
    },
    {
      id: "compact",
      name: "Compact",
      emoji: "📄",
      description: "Thermal Printer (80mm)",
      preview: `
        ════════════════════════
          NEUROQAA - RECEIPT
        ════════════════════════

        Quetta, Balochistan
        Ph: +92-123-456-7890

        INV: 1 | 14 Jun 2026

        Customer: Ali Ahmed
        Phone: +92-300-1234567

        ────────────────────────
        Item     Qty  Price Total
        ────────────────────────
        Blue       2  1200  2400
        Red        3  1500  4500
        ────────────────────────

        Subtotal: 6900
        Tax: 0
        TOTAL: 6900

        ════════════════════════
        Thank you! Visit again.
        ════════════════════════
      `,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Description */}
      <div className="text-sm text-muted-foreground">
        {setting.description}
      </div>

      {/* Visual Template Selector */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {templates.map((template) => (
          <button
            key={template.id}
            onClick={() => !disabled && onChange(template.id)}
            disabled={disabled}
            className={cn(
              "group relative text-left p-4 rounded-lg border-2 transition-all",
              value === template.id
                ? "border-primary bg-primary/5 shadow-lg shadow-primary/20"
                : "border-border hover:border-primary/50 hover:shadow-md",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            {/* Header with emoji and name */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-2xl">{template.emoji}</span>
                  <div>
                    <h3 className="font-semibold text-sm">{template.name}</h3>
                    <p className="text-xs text-muted-foreground">
                      {template.description}
                    </p>
                  </div>
                </div>
              </div>

              {/* Selection indicator */}
              <div
                className={cn(
                  "w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all",
                  value === template.id
                    ? "border-primary bg-primary"
                    : "border-border"
                )}
              >
                {value === template.id && (
                  <div className="w-2 h-2 bg-primary-foreground rounded-full" />
                )}
              </div>
            </div>

            {/* Preview */}
            <div className="bg-n-50 dark:bg-n-900 rounded p-3 border border-border mb-3 overflow-hidden">
              <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap break-words line-clamp-6">
                {template.preview}
              </pre>
            </div>

            {/* Use Case Badge */}
            <div className="flex items-center gap-2">
              {template.id === "classic" && (
                <span className="inline-block px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded font-medium">
                  Default • Best for retail
                </span>
              )}
              {template.id === "modern" && (
                <span className="inline-block px-2 py-1 bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 text-xs rounded font-medium">
                  Contemporary design
                </span>
              )}
              {template.id === "itemized" && (
                <span className="inline-block px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs rounded font-medium">
                  High detail • Best for audit
                </span>
              )}
              {template.id === "compact" && (
                <span className="inline-block px-2 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-xs rounded font-medium">
                  Thermal printer • 80mm
                </span>
              )}
            </div>

            {/* Hover effect indicator */}
            <div className="absolute inset-0 rounded-lg bg-primary/0 group-hover:bg-primary/5 transition-colors pointer-events-none" />
          </button>
        ))}
      </div>

      {/* Save status */}
      {saved && (
        <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400 font-medium mt-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          Template setting saved successfully
        </div>
      )}
    </div>
  );
}
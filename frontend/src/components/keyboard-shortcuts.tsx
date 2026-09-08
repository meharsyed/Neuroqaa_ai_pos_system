import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Shortcut {
  category: string;
  shortcuts: { keys: string; description: string }[];
}

const SHORTCUTS: Shortcut[] = [
  {
    category: "Navigation",
    shortcuts: [
      { keys: "Cmd+K / Ctrl+K", description: "Open command palette" },
      { keys: "?", description: "Show this help" },
    ],
  },
  {
    category: "Checkout (F-Keys)",
    shortcuts: [
      { keys: "F2", description: "Focus product search" },
      { keys: "F3", description: "Focus barcode scanner" },
      { keys: "F9", description: "Focus bill discount" },
      { keys: "F12", description: "Proceed to payment" },
      { keys: "+", description: "Increase item quantity" },
      { keys: "-", description: "Decrease item quantity" },
      { keys: "Esc", description: "Close payment modal" },
    ],
  },
  {
    category: "General",
    shortcuts: [
      { keys: "Esc", description: "Close dialogs and overlays" },
      { keys: "Enter", description: "Confirm/Submit" },
    ],
  },
];

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "?") {
        e.preventDefault();
        setOpen(!open);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Keyboard Shortcuts</span>
            <span className="text-xs font-normal text-muted-foreground">Press ? to toggle</span>
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {SHORTCUTS.map((group) => (
            <div key={group.category}>
              <h3 className="font-semibold text-sm mb-3">{group.category}</h3>
              <div className="space-y-2">
                {group.shortcuts.map((shortcut) => (
                  <div key={shortcut.keys} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{shortcut.description}</span>
                    <kbd className="px-2 py-1 text-xs font-mono bg-muted border border-border rounded">
                      {shortcut.keys}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="pt-4 border-t text-xs text-muted-foreground">
          <p>Tip: Use the command palette (Cmd+K) to quickly jump between pages.</p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
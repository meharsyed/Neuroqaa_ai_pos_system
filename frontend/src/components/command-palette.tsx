import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Home, Package, Receipt, Users, Zap, Settings, BarChart3, RotateCcw, Clock } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";

interface CommandItem {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  category: "Navigation" | "Actions" | "Search";
}

export function CommandPalette() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const commands: CommandItem[] = [
    // Navigation
    { id: "home", label: "Dashboard", description: "Go to dashboard", icon: <Home className="h-4 w-4" />, action: () => { navigate("/dashboard"); setOpen(false); }, category: "Navigation" },
    { id: "checkout", label: "New Sale", description: "Start a new checkout", icon: <Zap className="h-4 w-4" />, action: () => { navigate("/checkout"); setOpen(false); }, category: "Navigation" },
    { id: "products", label: "Products", description: "View product catalog", icon: <Package className="h-4 w-4" />, action: () => { navigate("/products"); setOpen(false); }, category: "Navigation" },
    { id: "bills", label: "Bills", description: "View sales history", icon: <Receipt className="h-4 w-4" />, action: () => { navigate("/bills"); setOpen(false); }, category: "Navigation" },
    { id: "customers", label: "Customers", description: "Manage customers", icon: <Users className="h-4 w-4" />, action: () => { navigate("/customers"); setOpen(false); }, category: "Navigation" },
    { id: "returns", label: "Returns", description: "Process returns", icon: <RotateCcw className="h-4 w-4" />, action: () => { navigate("/returns"); setOpen(false); }, category: "Navigation" },
    { id: "shifts", label: "Shifts", description: "Manage shifts", icon: <Clock className="h-4 w-4" />, action: () => { navigate("/shifts"); setOpen(false); }, category: "Navigation" },
    { id: "reports", label: "Reports", description: "View reports", icon: <BarChart3 className="h-4 w-4" />, action: () => { navigate("/reports"); setOpen(false); }, category: "Navigation" },
    { id: "settings", label: "Settings", description: "Configure settings", icon: <Settings className="h-4 w-4" />, action: () => { navigate("/settings"); setOpen(false); }, category: "Navigation" },
  ];

  const filtered = commands.filter(cmd =>
    cmd.label.toLowerCase().includes(search.toLowerCase()) ||
    cmd.description.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K to open
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(!open);
        setSearch("");
        setSelectedIndex(0);
      }

      // Navigation when open
      if (open) {
        switch (e.key) {
          case "ArrowDown":
            e.preventDefault();
            setSelectedIndex(i => (i + 1) % filtered.length);
            break;
          case "ArrowUp":
            e.preventDefault();
            setSelectedIndex(i => (i - 1 + filtered.length) % filtered.length);
            break;
          case "Enter":
            e.preventDefault();
            if (filtered[selectedIndex]) {
              filtered[selectedIndex].action();
            }
            break;
          case "Escape":
            e.preventDefault();
            setOpen(false);
            break;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, filtered, selectedIndex]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md p-0">
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            autoFocus
            placeholder="Search pages, actions... (Cmd+K)"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
            className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
          />
        </div>

        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-muted-foreground">No results found</p>
          </div>
        ) : (
          <div className="max-h-80 overflow-y-auto">
            {filtered.map((cmd, idx) => (
              <button
                key={cmd.id}
                onClick={() => cmd.action()}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left border-b last:border-b-0 transition-colors ${
                  idx === selectedIndex
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-muted"
                }`}
              >
                <div className="text-muted-foreground shrink-0">{cmd.icon}</div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm">{cmd.label}</p>
                  <p className="text-xs text-muted-foreground">{cmd.description}</p>
                </div>
              </button>
            ))}
          </div>
        )}

        <div className="border-t px-4 py-2 flex gap-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">↑↓ Navigate</span>
          <span className="flex items-center gap-1">⏎ Select</span>
          <span className="flex items-center gap-1">Esc Close</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
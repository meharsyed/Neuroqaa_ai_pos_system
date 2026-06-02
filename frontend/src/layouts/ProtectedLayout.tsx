import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  BarChart3,
  Clock,
  Settings,
  LogOut,
  Zap,
  Receipt,
  Users,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { catalogApi } from "@/lib/catalog";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  {
    label: "Operations",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/products",  label: "Products",  icon: Package, badgeKey: "lowStock" },
      { to: "/checkout",  label: "Checkout",  icon: ShoppingCart },
      { to: "/bills",     label: "Bills",     icon: Receipt },
    ],
  },
  {
    label: "Management",
    items: [
      { to: "/customers", label: "Customers", icon: Users },
      { to: "/reports",   label: "Reports",   icon: BarChart3 },
      { to: "/shifts",    label: "Shifts",    icon: Clock },
      { to: "/settings",  label: "Settings",  icon: Settings },
    ],
  },
];

export default function ProtectedLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  const { data: lowStockProducts = [] } = useQuery({
    queryKey: ["low-stock"],
    queryFn: catalogApi.products.lowStock,
    staleTime: 60_000,
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  const badges: Record<string, number> = {
    lowStock: lowStockProducts.length,
  };

  return (
    <div className="flex h-screen bg-background">

      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside className="w-56 flex flex-col shrink-0 border-r bg-card shadow-[1px_0_0_0_hsl(var(--border))]">

        {/* Brand header */}
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-900 px-4 py-4">
          {/* Subtle dot grid */}
          <div className="absolute inset-0 bg-dot-grid opacity-60 pointer-events-none" />
          {/* Glow blob */}
          <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-blue-500/20 blur-xl pointer-events-none" />

          <div className="relative z-10">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="h-8 w-8 rounded-lg glass flex items-center justify-center shrink-0">
                <Zap className="h-4 w-4 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="font-bold text-sm text-white leading-tight">Neuroqaa POS</h1>
                <p className="text-[10px] text-white/50 leading-tight">Point of Sale</p>
              </div>
            </div>
            <div className="rounded-lg bg-white/10 px-3 py-1.5 border border-white/10">
              <p className="text-xs font-medium text-white truncate">
                {user?.first_name || user?.email}
              </p>
              <p className="text-[10px] text-white/55 capitalize">{user?.role}</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
          {NAV_SECTIONS.map(({ label, items }) => (
            <div key={label}>
              <p className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/50">
                {label}
              </p>
              <div className="space-y-0.5">
                {items.map(({ to, label: itemLabel, icon: Icon, badgeKey }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) =>
                      cn(
                        "group flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150",
                        isActive
                          ? "bg-primary text-primary-foreground font-medium shadow-sm shadow-primary/20"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )
                    }
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1">{itemLabel}</span>
                    {badgeKey && badges[badgeKey] > 0 ? (
                      <Badge variant="warning" className="text-[10px] px-1.5 h-4 leading-none">
                        {badges[badgeKey]}
                      </Badge>
                    ) : null}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Logout */}
        <div className="px-2 py-2 border-t">
          <button
            onClick={logout}
            className="flex w-full items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all duration-150"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>

        {/* Brand footer */}
        <div className="px-4 pb-3 pt-1">
          <p className="text-[10px] text-center text-muted-foreground/40 leading-tight">
            Powered by{" "}
            <span className="font-semibold text-muted-foreground/60">Neuroqaa.ai</span>
          </p>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
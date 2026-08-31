import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Clock,
  Settings,
  LogOut,
  Zap,
  Receipt,
  Users,
  RotateCcw,
  ShieldCheck,
  FileBarChart,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useLanguageStore } from "@/store/languageStore";
import { useTranslation } from "@/lib/useTranslation";
import { catalogApi } from "@/lib/catalog";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  {
    labelKey: "nav.sectionOperations",
    items: [
      { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
      { to: "/products",  labelKey: "nav.products",  icon: Package, badgeKey: "lowStock" },
      { to: "/checkout",  labelKey: "nav.checkout",  icon: ShoppingCart },
      { to: "/bills",     labelKey: "nav.bills",     icon: Receipt },
      { to: "/returns",   labelKey: "nav.returns",   icon: RotateCcw },
    ],
  },
  {
    labelKey: "nav.sectionManagement",
    items: [
      { to: "/customers", labelKey: "nav.customers",   icon: Users },
      { to: "/audit",     labelKey: "nav.audit",       icon: FileBarChart },
      { to: "/shifts",    labelKey: "nav.shifts",      icon: Clock },
      { to: "/activity",  labelKey: "nav.activityLog", icon: ShieldCheck },
      { to: "/settings",  labelKey: "nav.settings",    icon: Settings },
    ],
  },
];

function LanguageToggle() {
  const language = useLanguageStore((s) => s.language);
  const setLanguage = useLanguageStore((s) => s.setLanguage);
  return (
    <div className="flex items-center rounded-full bg-white/10 border border-white/15 p-0.5 shrink-0">
      <button
        type="button"
        onClick={() => setLanguage("en")}
        className={cn(
          "px-2 py-0.5 rounded-full text-[10px] font-bold transition-colors",
          language === "en" ? "bg-white text-slate-900" : "text-white/60 hover:text-white"
        )}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => setLanguage("ur")}
        className={cn(
          "px-2 py-0.5 rounded-full text-[10px] font-bold transition-colors",
          language === "ur" ? "bg-white text-slate-900" : "text-white/60 hover:text-white"
        )}
      >
        اردو
      </button>
    </div>
  );
}

export default function ProtectedLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const location = useLocation();
  const { t } = useTranslation();

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
      <aside className="w-56 flex flex-col shrink-0 border-r bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 shadow-[1px_0_0_0_hsl(var(--border))]">

        {/* Brand header — Dark sidebar with Neuroqaa.ai */}
        <div className="sidebar-brand-header relative overflow-hidden px-4 py-5">
          <div className="relative z-10 space-y-3">
            {/* Neuroqaa.ai branding */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-lg font-black text-orange-400">◆</span>
                <p className="text-xs font-bold text-gray-300 uppercase tracking-wider">Neuroqaa.ai</p>
              </div>
              <p className="text-[10px] text-gray-400 italic">Modern POS for Modern Businesses</p>
            </div>

            {/* Language toggle */}
            <LanguageToggle />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
          {NAV_SECTIONS.map(({ labelKey, items }) => (
            <div key={labelKey}>
              <p className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/50">
                {t(labelKey)}
              </p>
              <div className="space-y-0.5">
                {items.map(({ to, labelKey: itemLabelKey, icon: Icon, badgeKey }) => (
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
                    <span className="flex-1">{t(itemLabelKey)}</span>
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
            {t("nav.signOut")}
          </button>
        </div>

        {/* Brand footer */}
        <div className="px-4 pb-3 pt-1">
          <p className="text-[10px] text-center text-muted-foreground/40 leading-tight">
            {t("nav.poweredBy")}{" "}
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
import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Clock,
  Settings,
  LogOut,
  Receipt,
  Users,
  RotateCcw,
  ShieldCheck,
  FileBarChart,
  Wallet,
  UserCog,
  FileText,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useTranslation } from "@/lib/useTranslation";
import { catalogApi } from "@/lib/catalog";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { LanguageToggle } from "@/components/LanguageToggle";
import { can } from "@/lib/permissions";
import { logoutApi } from "@/lib/users";
import type { User } from "@/types/auth";

interface NavItem {
  to: string;
  labelKey: string;
  icon: React.FC<{ className?: string }>;
  badgeKey?: string;
  /** Omitted means everyone signed in may see it. */
  allow?: (user: User | null) => boolean;
}

const NAV_SECTIONS: { labelKey: string; items: NavItem[] }[] = [
  {
    labelKey: "nav.sectionOperations",
    items: [
      { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
      { to: "/products", labelKey: "nav.products", icon: Package, badgeKey: "lowStock" },
      { to: "/checkout", labelKey: "nav.checkout", icon: ShoppingCart },
      { to: "/bills", labelKey: "nav.bills", icon: Receipt },
      { to: "/returns", labelKey: "nav.returns", icon: RotateCcw },
      { to: "/quotations", labelKey: "nav.quotations", icon: FileText },
    ],
  },
  {
    labelKey: "nav.sectionManagement",
    items: [
      { to: "/customers", labelKey: "nav.customers", icon: Users },
      { to: "/khata", labelKey: "nav.khata", icon: Wallet },
      { to: "/audit", labelKey: "nav.audit", icon: FileBarChart, allow: can.viewReports },
      { to: "/shifts", labelKey: "nav.shifts", icon: Clock },
      { to: "/activity", labelKey: "nav.activityLog", icon: ShieldCheck, allow: can.viewActivityLog },
      { to: "/settings", labelKey: "nav.settings", icon: Settings, allow: can.editSettings },
      { to: "/users", labelKey: "nav.users", icon: UserCog, allow: can.manageUsers },
    ],
  },
];

/**
 * Drop the pages this role cannot open.
 *
 * A cashier staring all day at Audit and Settings links that answer 403 is bad
 * product, not security — the server is what refuses them.
 */
function visibleSections(user: User | null) {
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.allow || item.allow(user)),
  })).filter((section) => section.items.length > 0);
}

interface AppSidebarProps {
  isCollapsed?: boolean;
}

export function AppSidebar({ isCollapsed = false }: AppSidebarProps) {
  const clearAuth = useAuthStore((s) => s.logout);

  // Blacklists the refresh-token cookie server-side (so it can't be replayed
  // even if it had leaked) before clearing local state. Best-effort — if the
  // request fails (offline, server already gone), signing out locally still
  // must happen, since the alternative is a "sign out" button that doesn't.
  async function handleSignOut() {
    try {
      await logoutApi();
    } catch {
      // Ignore — clearing local auth state below is what actually signs
      // this device out; the server call is a courtesy, not a dependency.
    } finally {
      clearAuth();
    }
  }
  const user = useAuthStore((s) => s.user);
  const { t } = useTranslation();

  const { data: lowStockProducts = [] } = useQuery({
    queryKey: ["low-stock"],
    queryFn: catalogApi.products.lowStock,
    staleTime: 60_000,
  });

  const badges: Record<string, number> = {
    lowStock: lowStockProducts.length,
  };

  return (
    <aside
      className={cn(
        "flex flex-col shrink-0 bg-chrome border-r border-chrome-border shadow-sm transition-all duration-200",
        isCollapsed ? "w-16" : "w-60"
      )}
    >
      {/* Brand header */}
      <div className="px-4 py-5 border-b border-chrome-border">
        <div className="space-y-3">
          {/* Logo + Brand name */}
          <div className="flex items-center gap-2.5">
            <img src="/brand/logo-mark-mono-light.svg" alt="Speed Tech" className="h-7 w-7 shrink-0" />
            {!isCollapsed && (
              <div className="min-w-0">
                <p className="text-sm font-semibold text-chrome-foreground uppercase tracking-wider leading-tight">
                  Speed Tech
                </p>
                <p className="text-[9px] font-bold text-teal-400 uppercase tracking-wider leading-none">
                  Solutions
                </p>
              </div>
            )}
          </div>

          {/* Language toggle */}
          {!isCollapsed && <LanguageToggle />}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        {visibleSections(user).map(({ labelKey, items }) => (
          <div key={labelKey}>
            {!isCollapsed && (
              <p className="px-3 mb-1.5 text-2xs font-semibold uppercase tracking-[0.14em] text-chrome-muted/70">
                {t(labelKey)}
              </p>
            )}
            <div className="space-y-0.5">
              {items.map(({ to, labelKey: itemLabelKey, icon: Icon, badgeKey }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "group relative flex items-center gap-2.5 px-3 py-2 rounded-md h-9 text-sm transition-all duration-150",
                      isActive
                        ? "bg-teal-600/15 text-chrome-foreground font-medium"
                        : "text-chrome-muted hover:bg-chrome-hover hover:text-chrome-foreground"
                    )
                  }
                  title={isCollapsed ? t(itemLabelKey) : undefined}
                >
                  {({ isActive }) => (
                    <>
                      {/* Active indicator bar */}
                      {isActive && (
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-teal-400" />
                      )}
                      <Icon className="h-4 w-4 shrink-0" />
                      {!isCollapsed && (
                        <>
                          <span className="flex-1">{t(itemLabelKey)}</span>
                          {badgeKey && badges[badgeKey] > 0 && (
                            <Badge
                              variant="warning"
                              className="text-[10px] px-1.5 h-4 leading-none"
                            >
                              {badges[badgeKey]}
                            </Badge>
                          )}
                        </>
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Logout button */}
      <div className="px-2 py-2 border-t border-chrome-border">
        <button
          onClick={handleSignOut}
          className="flex w-full items-center gap-2.5 px-3 py-2 rounded-md h-9 text-sm text-chrome-muted hover:bg-chrome-hover hover:text-chrome-foreground transition-all duration-150"
          title={isCollapsed ? t("nav.signOut") : undefined}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!isCollapsed && t("nav.signOut")}
        </button>
      </div>

      {/* Footer */}
      {!isCollapsed && (
        <div className="px-4 pb-3 pt-2 border-t border-chrome-border">
          <div className="space-y-2">
            {user && (
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-teal-600/20 text-teal-300 flex items-center justify-center text-xs font-bold shrink-0">
                  {user.first_name?.[0]?.toUpperCase() || user.username?.[0]?.toUpperCase() || "?"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-chrome-foreground truncate">
                    {user.first_name || user.username}
                  </p>
                  <p className="text-2xs text-chrome-muted capitalize truncate">
                    {user.role}
                  </p>
                </div>
              </div>
            )}
            <p className="text-2xs text-center text-chrome-muted/60 leading-tight">
              {t("nav.poweredBy")}{" "}
              <span className="font-semibold text-chrome-muted/80">Neuroqaa.ai</span>
            </p>
          </div>
        </div>
      )}
    </aside>
  );
}
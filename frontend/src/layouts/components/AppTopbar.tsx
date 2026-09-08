import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/store/authStore";
import { useTranslation } from "@/lib/useTranslation";
import { shiftsApi } from "@/lib/shifts";
import { Link } from "react-router-dom";
import { DarkModeToggle } from "@/components/dark-mode-toggle";

export function AppTopbar() {
  const user = useAuthStore((s) => s.user);
  const { t, language } = useTranslation();

  // Get current shift status
  const { data: currentShift } = useQuery({
    queryKey: ["shift-current"],
    queryFn: shiftsApi.current,
    retry: false,
    staleTime: 30_000,
  });

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return t("dashboard.greetingMorning");
    if (h < 17) return t("dashboard.greetingAfternoon");
    return t("dashboard.greetingEvening");
  };

  const dateLabel = new Date().toLocaleDateString(
    language === "ur" ? "ur-PK" : "en-PK",
    { weekday: "short", month: "short", day: "numeric" }
  );

  const timeLabel = new Date().toLocaleTimeString(
    language === "ur" ? "ur-PK" : "en-PK",
    { hour: "2-digit", minute: "2-digit" }
  );

  return (
    <header className="h-14 sticky top-0 z-30 bg-card/85 backdrop-blur border-b border-border flex items-center px-6 gap-4">
      {/* Left: Breadcrumb or app title */}
      <div className="flex-1 min-w-0">
        <div className="text-sm">
          <span className="text-muted-foreground">
            {greeting()} <span className="font-semibold text-foreground">{user?.first_name}</span>
          </span>
        </div>
      </div>

      {/* Right: Status pills and info */}
      <div className="flex items-center gap-4">
        {/* Shift status pill */}
        <Link
          to="/shifts"
          className={cn(
            "text-xs font-medium px-3 py-1.5 rounded-full flex items-center gap-2 transition-colors",
            currentShift
              ? "bg-accent-soft text-accent border border-teal-200"
              : "bg-warning-bg text-warning border border-warning/30"
          )}
        >
          <span className={cn("h-2 w-2 rounded-full", currentShift ? "bg-teal-500 animate-pulse" : "bg-warning")}>

          </span>
          {currentShift
            ? `Shift #${currentShift.id} · Open`
            : "No shift open"}
        </Link>

        {/* Dark Mode Toggle */}
        <DarkModeToggle />

        {/* Divider */}
        <div className="h-6 w-px bg-border" />

        {/* Date & Time */}
        <div className="text-right text-xs">
          <p className="font-medium text-foreground">{dateLabel}</p>
          <p className="text-muted-foreground">{timeLabel}</p>
        </div>

        {/* Divider */}
        <div className="h-6 w-px bg-border" />

        {/* User info (compact) */}
        <div className="text-right text-xs">
          <p className="font-medium text-foreground capitalize">{user?.role}</p>
          <p className="text-muted-foreground">{user?.username}</p>
        </div>
      </div>
    </header>
  );
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
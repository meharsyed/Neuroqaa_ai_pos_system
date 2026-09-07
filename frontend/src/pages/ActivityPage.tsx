import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/axios";
import { useAuthStore } from "@/store/authStore";

type ActivityEntry = {
  id: number;
  action: string;
  user: number | null;
  user_email: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
};

type ActivityResponse = {
  count: number;
  page: number;
  page_size: number;
  results: ActivityEntry[];
};

const ACTION_LABELS: Record<string, string> = {
  login:            "Login",
  logout:           "Logout",
  sale_created:     "Sale Created",
  sale_voided:      "Sale Voided",
  return_created:   "Return Processed",
  stock_in:         "Stock Added",
  setting_changed:  "Setting Changed",
  shift_opened:     "Shift Opened",
  shift_closed:     "Shift Closed",
  customer_created: "Customer Created",
};

const ACTION_COLORS: Record<string, string> = {
  login:            "bg-info-bg text-info",
  sale_created:     "bg-success-bg text-success",
  sale_voided:      "bg-destructive-bg text-destructive",
  return_created:   "bg-warning-bg text-warning",
  stock_in:         "bg-info-bg text-info",
  setting_changed:  "bg-warning-bg text-warning",
  shift_opened:     "bg-accent-soft text-accent",
  shift_closed:     "bg-n-100 text-n-600",
  customer_created: "bg-accent-soft text-accent",
};

function formatDt(iso: string) {
  return new Date(iso).toLocaleString("en-PK", {
    dateStyle: "medium",
    timeStyle: "medium",
  });
}

function DetailChips({ details }: { details: Record<string, unknown> }) {
  const entries = Object.entries(details).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {entries.map(([k, v]) => (
        <span key={k} className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-mono">
          {k}: {String(v)}
        </span>
      ))}
    </div>
  );
}

export default function ActivityPage() {
  const user = useAuthStore((s) => s.user);
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");

  const { data, isLoading } = useQuery<ActivityResponse>({
    queryKey: ["activity", { page, actionFilter }],
    queryFn: () =>
      apiClient
        .get("/auth/activity/", { params: { page, ...(actionFilter && { action: actionFilter }) } })
        .then((r) => r.data),
    staleTime: 30_000,
    enabled: user?.role === "owner" || user?.role === "manager",
  });

  if (user?.role !== "owner" && user?.role !== "manager") {
    return (
      <div className="min-h-full flex items-center justify-center p-8">
        <div className="text-center">
          <ShieldCheck className="h-12 w-12 mx-auto mb-3 text-muted-foreground opacity-30" />
          <p className="font-semibold text-muted-foreground">Access restricted</p>
          <p className="text-sm text-muted-foreground/60 mt-1">Only owners and managers can view the activity log.</p>
        </div>
      </div>
    );
  }

  const entries = data?.results ?? [];
  const totalPages = data ? Math.ceil(data.count / (data.page_size || 50)) : 1;

  return (
    <PageContainer>
      <PageHeader
        title="Activity Log"
        subtitle={`Security and operational audit trail — ${data?.count ?? "…"} total events`}
      />

      <div className="space-y-4">

        {/* Action filter */}
        <div className="flex flex-wrap gap-1.5">
          {(["", ...Object.keys(ACTION_LABELS)] as string[]).map((action) => (
            <button
              key={action}
              onClick={() => { setActionFilter(action); setPage(1); }}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                actionFilter === action
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background text-muted-foreground border-border hover:border-primary/40"
              }`}
            >
              {action === "" ? "All Events" : ACTION_LABELS[action] ?? action}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="rounded-xl border p-12 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading activity log…
          </div>
        ) : entries.length === 0 ? (
          <div className="rounded-xl border p-12 text-center">
            <ShieldCheck className="h-8 w-8 mx-auto mb-3 opacity-15" />
            <p className="text-sm text-muted-foreground">No activity recorded yet.</p>
          </div>
        ) : (
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 border-b">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Event</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">User</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Details</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">IP</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                          ACTION_COLORS[entry.action] ?? "bg-muted text-muted-foreground"
                        }`}
                      >
                        {ACTION_LABELS[entry.action] ?? entry.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono">{entry.user_email}</td>
                    <td className="px-4 py-3">
                      <DetailChips details={entry.details} />
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground font-mono">
                      {entry.ip_address || "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                      {formatDt(entry.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="px-4 py-3 border-t bg-muted/20 flex items-center justify-between">
                <Button
                  variant="outline" size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="gap-1"
                >
                  <ChevronLeft className="h-4 w-4" /> Prev
                </Button>
                <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
                <Button
                  variant="outline" size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="gap-1"
                >
                  Next <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </PageContainer>
  );
}
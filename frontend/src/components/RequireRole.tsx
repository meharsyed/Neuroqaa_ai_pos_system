import { Navigate, useLocation } from "react-router-dom";
import { ShieldAlert } from "lucide-react";

import { mayOpen } from "@/lib/permissions";
import { useAuthStore } from "@/store/authStore";

/**
 * Keeps a role off a page it has no business on.
 *
 * The server refuses these endpoints regardless — this exists so a cashier who
 * types /audit gets a straight answer instead of a page full of failed
 * requests. Never the security boundary; the manners.
 */
export function RequireRole({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const { pathname } = useLocation();

  if (mayOpen(pathname, user)) return <>{children}</>;

  // Send them somewhere useful rather than showing a dead end.
  return (
    <Navigate
      to="/dashboard"
      replace
      state={{ deniedFrom: pathname }}
    />
  );
}

export function NotAllowed({ what }: { what: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <ShieldAlert className="h-8 w-8 text-muted-foreground" />
      <p className="font-medium">{what} is not available to your role</p>
      <p className="text-sm text-muted-foreground">
        Ask the shop owner if you need access.
      </p>
    </div>
  );
}

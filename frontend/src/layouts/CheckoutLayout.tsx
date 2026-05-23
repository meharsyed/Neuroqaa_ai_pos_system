import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

/** Full-screen layout for the checkout page — no sidebar, just an auth guard. */
export default function CheckoutLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Outlet />
    </div>
  );
}
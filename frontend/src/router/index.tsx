import { createBrowserRouter } from "react-router-dom";
import ProtectedLayout from "@/layouts/ProtectedLayout";
import CheckoutLayout from "@/layouts/CheckoutLayout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import ProductsPage from "@/pages/ProductsPage";
import CheckoutPage from "@/pages/CheckoutPage";
import BillsPage from "@/pages/BillsPage";
import ShiftsPage from "@/pages/ShiftsPage";
import CustomersPage from "@/pages/CustomersPage";
import SuppliersPage from "@/pages/SuppliersPage";
import KhataPage from "@/pages/KhataPage";
import ReturnsPage from "@/pages/ReturnsPage";
import ActivityPage from "@/pages/ActivityPage";
import AuditPage from "@/pages/AuditPage";
import SettingsPage from "@/pages/SettingsPage";
import UsersPage from "@/pages/UsersPage";
import QuotationsPage from "@/pages/QuotationsPage";
export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    // Full-screen checkout — no sidebar
    element: <CheckoutLayout />,
    children: [
      { path: "/checkout", element: <CheckoutPage /> },
    ],
  },
  {
    // Standard layout with sidebar
    element: <ProtectedLayout />,
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/products", element: <ProductsPage /> },
      { path: "/bills",     element: <BillsPage /> },
      { path: "/returns",   element: <ReturnsPage /> },
      { path: "/quotations", element: <QuotationsPage /> },
      { path: "/customers", element: <CustomersPage /> },
      { path: "/suppliers", element: <SuppliersPage /> },
      { path: "/khata",     element: <KhataPage /> },
      { path: "/shifts",    element: <ShiftsPage /> },
      { path: "/activity",  element: <ActivityPage /> },
      { path: "/audit",     element: <AuditPage /> },
      { path: "/settings",  element: <SettingsPage /> },
      { path: "/users",     element: <UsersPage /> },
    ],
  },
]);
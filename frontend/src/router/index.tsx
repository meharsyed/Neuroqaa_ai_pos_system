import { createBrowserRouter } from "react-router-dom";
import ProtectedLayout from "@/layouts/ProtectedLayout";
import CheckoutLayout from "@/layouts/CheckoutLayout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import ProductsPage from "@/pages/ProductsPage";
import CheckoutPage from "@/pages/CheckoutPage";

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
    ],
  },
]);
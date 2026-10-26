import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import AdminPage from "./pages/AdminPage";
import ForbiddenPage from "./pages/ForbiddenPage";
import GuardLabPage from "./pages/GuardLabPage";
import LoginPage from "./pages/LoginPage";
import OrdersPage from "./pages/OrdersPage";
import RestaurantsPage from "./pages/RestaurantsPage";

function Loading() {
  return <p className="muted">Loading…</p>;
}

function RequireAuth() {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (user) return <Navigate to="/restaurants" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <ForbiddenPage />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route
              path="/login"
              element={
                <PublicOnly>
                  <LoginPage />
                </PublicOnly>
              }
            />
            <Route element={<RequireAuth />}>
              <Route path="/restaurants" element={<RestaurantsPage />} />
              <Route path="/orders" element={<OrdersPage />} />
              <Route path="/guard-lab" element={<GuardLabPage />} />
              <Route
                path="/admin"
                element={
                  <RequireAdmin>
                    <AdminPage />
                  </RequireAdmin>
                }
              />
            </Route>
            <Route path="/" element={<Navigate to="/restaurants" replace />} />
            <Route path="*" element={<Navigate to="/restaurants" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

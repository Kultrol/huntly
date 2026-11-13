import { Route, Routes } from "react-router";
import { GuestOnly, RequireAuth } from "@/features/auth/AuthRouteGuards";
import { AuthLayout } from "@/features/auth/components/AuthLayout";
import LoginPage from "@/features/auth/pages/LoginPage";
import RegisterPage from "@/features/auth/pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import RolesPage from "./pages/RolesPage";
import NotFoundPage from "./pages/NotFoundPage";

/** Groups routes by who can visit them once the session check settles. */
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route element={<GuestOnly />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/roles" element={<RolesPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

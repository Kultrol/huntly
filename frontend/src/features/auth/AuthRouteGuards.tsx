import { Navigate, Outlet, useLocation } from "react-router";
import { Button } from "@/components/ui/button";
import { getAuthRedirect } from "./redirect";
import { useAuth } from "./session/useAuth";

function SessionStatus() {
  const { status, error, refreshSession } = useAuth();
  if (status === "loading") return <p role="status">Loading user information...</p>;
  return (
    <main>
      <p role="alert">{error}</p>
      <Button onClick={() => void refreshSession()}>Retry</Button>
    </main>
  );
}

/** Waits for the session check before opening a protected route or redirecting to login. */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading" || status === "error") return <SessionStatus />;
  if (status === "unauthenticated") {
    // Keep the query and fragment so sign-in can return the user to the exact destination.
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search + location.hash }} />;
  }
  return <Outlet />;
}

/** Allows signed-out users to see the forms and sends signed-in users to their destination. */
export function GuestOnly() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading" || status === "error") return <SessionStatus />;
  if (status === "authenticated") return <Navigate to={getAuthRedirect(location.state)} replace />;
  return <Outlet />;
}

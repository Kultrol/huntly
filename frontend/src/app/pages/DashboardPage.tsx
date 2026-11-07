import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/session/useAuth";

export default function DashboardPage() {
  const { user, signOut, isPending, error: sessionError } = useAuth();
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    setError(null);
    try {
      await signOut();
    } catch (error) {
      setError(getErrorMessage(error));
    }
  }

  // The route guard redirects when a session ends.
  if (!user) return null;

  return (
    <main>
      <h1>Welcome {user.name} to the dashboard</h1>
      {(error || sessionError) && <p role="alert">{error || sessionError}</p>}
      <Button disabled={isPending} onClick={handleLogout}>Logout</Button>
    </main>
  );
}

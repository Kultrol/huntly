import { useState } from "react";
import { getErrorMessage } from "@/api/client";
import { SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useAuth } from "@/features/auth/session/useAuth";
import { SideBar } from "@/components/sidebar/SideBar";
import PageHeader from "../../components/PageHeader";
import SessionErrorAlert from "../../components/SessionErrorAlert";
import PageContainer from "../../components/PageContainer";

export default function RolesPage() {
  const { user, signOut, isPending, error: sessionError } = useAuth();
  const [logoutError, setLogoutError] = useState<string | null>(null);

  async function handleLogout() {
    setLogoutError(null);
    try {
      await signOut();
    } catch (error) {
      setLogoutError(getErrorMessage(error));
    }
  }

  // The route guard redirects when a session ends.
  if (!user) return null;

  return (
    <TooltipProvider>
      <SidebarProvider className="[--sidebar-width:14rem]! lg:[--sidebar-width:15rem]!">
        <SideBar
          user={user}
          onLogout={handleLogout}
          isLoggingOut={isPending}
          pageName={"roles"}
        />
        <main className="min-w-0 flex-1 bg-background">
          <PageHeader pageName={"Roles"} />
          <PageContainer>
            <SessionErrorAlert
              sessionError={sessionError}
              logoutError={logoutError}
            />
          </PageContainer>
        </main>
      </SidebarProvider>
    </TooltipProvider>
  );
}

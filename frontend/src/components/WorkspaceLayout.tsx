import { useState, type CSSProperties, type ReactNode } from "react";
import { getErrorMessage } from "@/api/client";
import { useAuth } from "@/features/auth/session/useAuth";
import { SideBar } from "./sidebar/SideBar";
import type { WorkspacePageName } from "./sidebar/components/HuntlySideBarContent";
import { SidebarProvider } from "./ui/sidebar";
import { TooltipProvider } from "./ui/tooltip";
import PageContainer from "./PageContainer";
import PageHeader from "./PageHeader";
import SessionErrorAlert from "./SessionErrorAlert";

type WorkspaceLayoutProps = {
  page: WorkspacePageName;
  title: string;
  children: ReactNode;
};

export function WorkspaceLayout({ page, title, children }: WorkspaceLayoutProps) {
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

  if (!user) return null;

  return (
    <TooltipProvider>
      <SidebarProvider
        className="workspace-shell"
        style={{ "--sidebar-width": "var(--workspace-sidebar-width)" } as CSSProperties}
      >
        <SideBar user={user} onLogout={handleLogout} isLoggingOut={isPending} pageName={page} />
        <main className="min-w-0 flex-1 bg-background">
          <PageHeader pageName={title} />
          <PageContainer>
            <SessionErrorAlert sessionError={sessionError} logoutError={logoutError} />
            {children}
          </PageContainer>
        </main>
      </SidebarProvider>
    </TooltipProvider>
  );
}

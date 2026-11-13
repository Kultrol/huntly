import { Sidebar } from "@/components/ui/sidebar";
import type { AuthUser } from "@/features/auth/api/types";
import HuntlySideBarHeader from "./components/HuntlySideBarHeader";
import HuntlySideBarContent, {
  type WorkspacePageName,
} from "./components/HuntlySideBarContent";
import HuntlySideBarFooter from "./components/HuntlySideBarFooter";

type SidebarProps = {
  user: AuthUser;
  onLogout: () => void;
  isLoggingOut: boolean;
  pageName: WorkspacePageName;
};

export function SideBar({
  user,
  onLogout,
  isLoggingOut,
  pageName,
}: SidebarProps) {
  return (
    <Sidebar>
      <HuntlySideBarHeader />
      <HuntlySideBarContent pageName={pageName} />
      <HuntlySideBarFooter
        user={user}
        isLoggingOut={isLoggingOut}
        onLogout={onLogout}
      />
    </Sidebar>
  );
}

import { LogOut, Settings as SettingsIcon, UserRound } from "lucide-react";
import {
  SidebarFooter,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import UnavailableSidebarItem from "./UnavailableSideBarItem";
import type { AuthUser } from "@/features/auth/api/types";

interface HuntlySideBarFooterProps {
  user: AuthUser;
  onLogout: () => void;
  isLoggingOut: boolean;
}

export default function HuntlySideBarFooter({
  user,
  isLoggingOut,
  onLogout,
}: HuntlySideBarFooterProps) {
  const { setOpenMobile } = useSidebar();

  function handleLogout() {
    // Close the mobile drawer before the route guard leaves this page.
    setOpenMobile(false);
    onLogout();
  }

  return (
    <SidebarFooter className="px-4 pb-4">
      <div className="flex min-w-0 items-center gap-2.5 border-t border-sidebar-border px-1.5 pt-3 pb-1">
        <div className="grid size-9 shrink-0 place-items-center rounded-full bg-sidebar-accent text-sidebar-accent-foreground">
          <UserRound aria-hidden="true" className="size-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{user.name}</p>
          {user.email && (
            <p className="truncate text-xs text-muted-foreground">
              {user.email}
            </p>
          )}
        </div>
      </div>

      <SidebarMenu>
        <UnavailableSidebarItem label="Settings" icon={SettingsIcon} />
        <SidebarMenuItem>
          <SidebarMenuButton
            type="button"
            disabled={isLoggingOut}
            aria-busy={isLoggingOut}
            className="h-11 px-3"
            onClick={handleLogout}
          >
            <LogOut aria-hidden="true" />
            <span>Logout</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
  );
}

import {
  BriefcaseBusiness,
  Building2,
  ContactRound,
  LayoutDashboard,
  LogOut,
  Settings as SettingsIcon,
  Target,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import type { AuthUser } from "@/features/auth/api/types";
import { UnavailableAction } from "./UnavailableAction";

const unbuiltWorkspacePages = [
  { label: "Roles", icon: BriefcaseBusiness },
  { label: "Companies", icon: Building2 },
  { label: "Contacts", icon: ContactRound },
];

type DashboardSidebarProps = {
  user: AuthUser;
  onLogout: () => void;
  isLoggingOut: boolean;
};

function UnavailableSidebarItem({ label, icon: Icon }: { label: string; icon: LucideIcon }) {
  const { isMobile } = useSidebar();

  return (
    <SidebarMenuItem>
      {/* SidebarMenuButton clears pointer events and fades aria-disabled items.
          These overrides keep the item readable and able to show the message. */}
      <UnavailableAction
        render={<SidebarMenuButton className="h-11 cursor-not-allowed px-3 text-muted-foreground aria-disabled:pointer-events-auto aria-disabled:opacity-100" />}
        side={isMobile ? "top" : "right"}
      >
        <Icon aria-hidden="true" />
        <span>{label}</span>
      </UnavailableAction>
    </SidebarMenuItem>
  );
}

export function DashboardSidebar({ user, onLogout, isLoggingOut }: DashboardSidebarProps) {
  const { setOpenMobile } = useSidebar();

  function handleLogout() {
    // Close the mobile drawer before the route guard leaves this page.
    setOpenMobile(false);
    onLogout();
  }

  return (
    <Sidebar>
      <SidebarHeader className="flex-row items-center gap-2.5 px-4 pt-5 pb-4">
        <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
          <Target aria-hidden="true" className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="text-lg leading-tight font-semibold tracking-tight">Huntly</p>
          <p className="text-xs text-muted-foreground">Job search workspace</p>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2">
        <nav aria-label="Workspace">
          <SidebarGroup>
            <SidebarGroupLabel className="px-3 text-[0.65rem] font-semibold tracking-widest text-muted-foreground uppercase">
              Workspace
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={<span />}
                    aria-current="page"
                    isActive
                    className="h-11 rounded-lg bg-sidebar-accent px-3 font-semibold text-sidebar-accent-foreground"
                  >
                    <LayoutDashboard aria-hidden="true" />
                    <span>Dashboard</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                {unbuiltWorkspacePages.map(({ label, icon }) => (
                  <UnavailableSidebarItem key={label} label={label} icon={icon} />
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </nav>
      </SidebarContent>

      <SidebarFooter className="px-4 pb-4">
        <div className="flex min-w-0 items-center gap-2.5 border-t border-sidebar-border px-1.5 pt-3 pb-1">
          <div className="grid size-9 shrink-0 place-items-center rounded-full bg-sidebar-accent text-sidebar-accent-foreground">
            <UserRound aria-hidden="true" className="size-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{user.name}</p>
            {user.email && <p className="truncate text-xs text-muted-foreground">{user.email}</p>}
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
    </Sidebar>
  );
}

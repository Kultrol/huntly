import {
  BriefcaseBusiness,
  Building2,
  ContactRound,
  LayoutDashboard,
  type LucideIcon,
} from "lucide-react";
import {
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
} from "@/components/ui/sidebar";
import AvailableSideBarItem from "./AvailableSideBarItem";
import UnavailableSidebarItem from "./UnavailableSideBarItem";

export type WorkspacePageName = "dashboard" | "roles";

type WorkspaceNavItem =
  | {
      id: WorkspacePageName;
      label: string;
      icon: LucideIcon;
      available: true;
      route: string;
    }
  | {
      label: string;
      icon: LucideIcon;
      available: false;
    };

const pages: WorkspaceNavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    available: true,
    route: "/dashboard",
  },
  {
    id: "roles",
    label: "Roles",
    icon: BriefcaseBusiness,
    available: true,
    route: "/roles",
  },
  { label: "Companies", icon: Building2, available: false },
  { label: "Contacts", icon: ContactRound, available: false },
];

export default function HuntlySideBarContent({
  pageName,
}: {
  pageName: WorkspacePageName;
}) {
  return (
    <SidebarContent className="px-2">
      <nav aria-label="Workspace">
        <SidebarGroup>
          <SidebarGroupLabel className="px-3 text-[0.65rem] font-semibold tracking-widest text-muted-foreground uppercase">
            Workspace
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {pages.map((page) =>
                page.available ? (
                  <AvailableSideBarItem
                    key={page.id}
                    label={page.label}
                    icon={page.icon}
                    route={page.route}
                    current={pageName === page.id}
                  />
                ) : (
                  <UnavailableSidebarItem
                    key={page.label}
                    label={page.label}
                    icon={page.icon}
                  />
                ),
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </nav>
    </SidebarContent>
  );
}

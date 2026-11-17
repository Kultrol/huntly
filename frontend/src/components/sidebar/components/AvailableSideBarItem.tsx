import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";
import { SidebarMenuButton, SidebarMenuItem, useSidebar } from "@/components/ui/sidebar";

type AvailableSideBarItemProps = {
  label: string;
  icon: LucideIcon;
  route: string;
  current: boolean;
};

export default function AvailableSideBarItem({
  label,
  icon: Icon,
  route,
  current,
}: AvailableSideBarItemProps) {
  const { setOpenMobile } = useSidebar();
  return (
    <SidebarMenuItem>
      {current ? (
        <SidebarMenuButton
          render={<span />}
          aria-current="page"
          isActive
          className="h-11 rounded-lg bg-sidebar-accent px-3 font-semibold text-sidebar-accent-foreground"
        >
          <Icon aria-hidden="true" />
          <span>{label}</span>
        </SidebarMenuButton>
      ) : (
        <SidebarMenuButton
          render={<Link to={route} onClick={() => setOpenMobile(false)} />}
          className="h-11 rounded-lg px-3 font-semibold text-muted-foreground hover:cursor-pointer"
        >
          <Icon aria-hidden="true" />
          <span>{label}</span>
        </SidebarMenuButton>
      )}
    </SidebarMenuItem>
  );
}

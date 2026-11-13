import { SidebarMenuItem, SidebarMenuButton } from "@/components/ui/sidebar";
import { UnavailableAction } from "@/features/dashboard/UnavailableAction";
import { type LucideIcon } from "lucide-react";
import { useSidebar } from "@/components/ui/sidebar";

export default function UnavailableSidebarItem({
  label,
  icon: Icon,
}: {
  label: string;
  icon: LucideIcon;
}) {
  const { isMobile } = useSidebar();

  return (
    <SidebarMenuItem>
      {/* SidebarMenuButton clears pointer events and fades aria-disabled items.
          These overrides keep the item readable and able to show the message. */}
      <UnavailableAction
        render={
          <SidebarMenuButton className="h-11 cursor-not-allowed px-3 text-muted-foreground aria-disabled:pointer-events-auto aria-disabled:opacity-100" />
        }
        side={isMobile ? "top" : "right"}
      >
        <Icon aria-hidden="true" />
        <span>{label}</span>
      </UnavailableAction>
    </SidebarMenuItem>
  );
}

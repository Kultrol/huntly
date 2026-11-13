import { Target } from "lucide-react";
import { SidebarHeader } from "@/components/ui/sidebar";

export default function HuntlySideBarHeader() {
  return (
    <SidebarHeader className="flex-row items-center gap-2.5 px-4 pt-5 pb-4">
      <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
        <Target aria-hidden="true" className="size-5" />
      </div>
      <div className="min-w-0">
        <p className="text-lg leading-tight font-semibold tracking-tight">
          Huntly
        </p>
        <p className="text-xs text-muted-foreground">Job search workspace</p>
      </div>
    </SidebarHeader>
  );
}

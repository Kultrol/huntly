import { SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeToggleButton } from "@/theme/ThemeToggleButton";

export default function PageHeader({ pageName }) {
  return (
    <header className="flex h-14 items-center gap-3 border-b bg-card/70 px-4 md:px-6">
      <SidebarTrigger className="size-8" />
      <span className="h-4 border-l" aria-hidden="true" />
      <span className="text-sm font-medium">{pageName}</span>
      <ThemeToggleButton className="ml-auto" />
    </header>
  );
}

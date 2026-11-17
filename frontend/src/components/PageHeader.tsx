import { SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeToggleButton } from "@/theme/ThemeToggleButton";

interface PageHeaderProps {
  pageName: string;
}

export default function PageHeader({ pageName }: PageHeaderProps) {
  return (
    <header className="page-gutters flex min-h-14 items-center gap-3 border-b bg-card/70">
      <SidebarTrigger />
      <span className="h-4 border-l" aria-hidden="true" />
      <span className="text-sm font-medium">{pageName}</span>
      <ThemeToggleButton className="ml-auto" />
    </header>
  );
}

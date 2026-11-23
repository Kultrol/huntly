import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageContainerProps {
  children: ReactNode;
  fitToViewport?: boolean;
}

export default function PageContainer({ children, fitToViewport = false }: PageContainerProps) {
  return (
    <div className={cn("page-gutters py-6", fitToViewport && "flex min-h-0 flex-1 flex-col")}>
      <div className={cn("@container/workspace space-y-6", fitToViewport && "flex min-h-0 flex-1 flex-col")}>
        {children}
      </div>
    </div>
  );
}

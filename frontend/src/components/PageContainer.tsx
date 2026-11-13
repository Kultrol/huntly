import type { ReactNode } from "react";

interface PageContainerProps {
  children: ReactNode;
}

export default function PageContainer({ children }: PageContainerProps) {
  return (
    <div className="@container space-y-6 px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
      {children}
    </div>
  );
}

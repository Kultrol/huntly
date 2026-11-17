import type { ReactNode } from "react";

interface PageContainerProps {
  children: ReactNode;
}

export default function PageContainer({ children }: PageContainerProps) {
  return (
    <div className="page-gutters py-6">
      <div className="@container/workspace space-y-6">
        {children}
      </div>
    </div>
  );
}

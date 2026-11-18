import { lazy, Suspense } from "react";
import { WorkspaceLayout } from "@/components/WorkspaceLayout";
import { LoadingState } from "@/components/feedback/LoadState";
import { useAuth } from "@/features/auth/session/useAuth";

const CompaniesWorkspace = lazy(() => import("@/features/companies/CompaniesWorkspace"));

export default function CompaniesPage() {
  const { user, csrfToken } = useAuth();
  if (!user) return null;
  return (
    <WorkspaceLayout page="companies" title="Companies">
      <Suspense fallback={<LoadingState message="Loading companies…" />}>
        <CompaniesWorkspace key={`${user.id}:${csrfToken}`} />
      </Suspense>
    </WorkspaceLayout>
  );
}

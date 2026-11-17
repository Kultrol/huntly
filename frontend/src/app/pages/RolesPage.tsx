import { lazy, Suspense } from "react";
import { useAuth } from "@/features/auth/session/useAuth";
import { WorkspaceLayout } from "@/components/WorkspaceLayout";
import { LoadingState } from "@/components/feedback/LoadState";

const RolesWorkspace = lazy(() => import("@/features/roles/RolesWorkspace"));

export default function RolesPage() {
  const { user, csrfToken } = useAuth();
  if (!user) return null;

  return (
    <WorkspaceLayout page="roles" title="Roles">
      <Suspense fallback={<LoadingState message="Loading roles…" />}>
        <RolesWorkspace key={`${user.id}:${csrfToken}`} userId={user.id} />
      </Suspense>
    </WorkspaceLayout>
  );
}

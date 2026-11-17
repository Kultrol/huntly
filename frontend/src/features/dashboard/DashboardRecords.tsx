import { lazy, Suspense, useRef, useState } from "react";
import { ChevronDown, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, LoadError, LoadingState } from "@/components/feedback/LoadState";
import { UnavailableAction } from "@/components/feedback/UnavailableAction";
import { useAuth } from "@/features/auth/session/useAuth";
import { deleteRole, saveRole } from "@/features/roles/api";
import type { RoleEditor } from "@/features/roles/RoleDialog";
import { cn } from "@/lib/utils";
import type {
  DashboardCompany,
  DashboardContact,
  DashboardDataset,
  DashboardRole,
  DashboardRoleStatus,
  useDashboardRecords,
} from "./useDashboardRecords";

const RoleDialog = lazy(() => import("@/features/roles/RoleDialog").then((module) => ({
  default: module.RoleDialog,
})));

type RoleStatusFilter = DashboardRoleStatus | "all";

const roleStatusFilters: Record<RoleStatusFilter, string> = {
  all: "All statuses",
  saved: "Saved",
  applied: "Applied",
  screening: "Screening",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  accepted: "Accepted",
  withdrawn: "Withdrawn",
};

// Applied dates are instants, so the viewer's local day is intentional.
// Event days in Next up are calendar dates and use UTC instead.
const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

type RecordColumn<RecordType> = {
  heading: string;
  value: (record: RecordType) => string | null;
};

type RecordsPanelProps<RecordType> = {
  label: "roles" | "companies" | "contacts";
  addLabel: string;
  columns: RecordColumn<RecordType>[];
  dataset: DashboardDataset<RecordType>;
  getRoleStatus?: (record: RecordType) => DashboardRoleStatus;
  onRetry: () => void;
  onOpen?: (record: RecordType, trigger: HTMLButtonElement) => void;
  onCreate?: (trigger: HTMLButtonElement) => void;
};

function RecordsPanel<RecordType extends { id: string }>({
  label, addLabel, columns, dataset, getRoleStatus, onRetry, onOpen, onCreate,
}: RecordsPanelProps<RecordType>) {
  const [query, setQuery] = useState("");
  const [roleStatus, setRoleStatus] = useState<RoleStatusFilter>("all");
  const statusLabel = roleStatusFilters[roleStatus];
  const search = query.trim().toLowerCase();
  const rows = dataset.records.map((record) => ({
    record,
    cells: columns.map(({ heading, value }) => ({ heading, value: value(record) })),
  }));
  const filteredRows = rows.filter(({ record, cells }) =>
    (roleStatus === "all" || getRoleStatus?.(record) === roleStatus) &&
    cells.some(({ value }) => value?.toLowerCase().includes(search)),
  );

  return (
    <>
      <div className="flex flex-wrap items-center gap-2.5 border-y px-4 py-3 sm:px-5">
        <label className="relative min-w-0 grow basis-40 @lg/workspace:max-w-72">
          <span className="sr-only">Filter {label}</span>
          <Search aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            className="bg-background pl-9"
            placeholder={`Filter ${label}…`}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        {getRoleStatus && (
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger
              aria-label={`Role status: ${statusLabel}`}
              render={<Button variant="outline" className="min-w-32 justify-between" />}
            >
              {statusLabel}
              <ChevronDown aria-hidden="true" className="text-muted-foreground" />
            </DropdownMenuTrigger>
            <DropdownMenuContent aria-label="Role status" className="min-w-40">
              <DropdownMenuRadioGroup value={roleStatus} onValueChange={setRoleStatus}>
                {Object.entries(roleStatusFilters).map(([value, name]) => (
                  <DropdownMenuRadioItem key={value} value={value} closeOnClick className="min-h-8">
                    {name}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
        {onCreate ? (
          <Button variant="outline" aria-haspopup="dialog" onClick={(event) => onCreate(event.currentTarget)}>
            <Plus aria-hidden="true" />
            {addLabel}
          </Button>
        ) : (
          <UnavailableAction
            render={<Button variant="outline" className="cursor-not-allowed opacity-60" />}
          >
            <Plus aria-hidden="true" />
            {addLabel}
          </UnavailableAction>
        )}
      </div>

      <Table aria-label={label.charAt(0).toUpperCase() + label.slice(1)} className="min-w-max">
        <TableHeader className="bg-muted/50">
          <TableRow>
            {columns.map(({ heading }) => (
              <TableHead key={heading} scope="col" className="px-4 text-xs text-muted-foreground sm:px-5">
                {heading}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredRows.map(({ record, cells }) => (
            <TableRow
              key={record.id}
              className={cn(onOpen && "cursor-pointer hover:bg-accent/50")}
              onClick={onOpen ? (event) => {
                // The title button also provides native Enter/Space activation.
                const trigger = event.currentTarget.querySelector<HTMLButtonElement>("[data-record-trigger]");
                if (trigger) onOpen(record, trigger);
              } : undefined}
            >
              {cells.map(({ heading, value }, index) => (
                <TableCell
                  key={heading}
                  className="max-w-56 px-4 py-3 wrap-anywhere whitespace-normal first:font-medium sm:px-5"
                >
                  {index === 0 && onOpen ? (
                    <button
                      id={`tracker-${label}-${record.id}`}
                      data-record-trigger
                      type="button"
                      aria-haspopup="dialog"
                      aria-label={`View ${value}`}
                      className="touch-target cursor-pointer rounded-sm text-left underline decoration-transparent underline-offset-4 hover:decoration-current focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      {value ?? "—"}
                    </button>
                  ) : (value ?? "—")}
                </TableCell>
              ))}
            </TableRow>
          ))}
          {filteredRows.length === 0 && (
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={columns.length} className="h-24 px-4 whitespace-normal sm:px-5">
                <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
                  {dataset.status === "loading" && <LoadingState message={`Loading ${label}…`} />}
                  {dataset.status === "error" && (
                    <LoadError message={dataset.error} onRetry={onRetry} />
                  )}
                  {dataset.status === "ready" && (
                    <EmptyState message={rows.length ? "No records match your filters." : `No ${label} yet.`} />
                  )}
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {dataset.status === "ready" && (
        <p role="status" className="border-t px-4 py-3 text-xs text-muted-foreground tabular-nums sm:px-5">
          Showing {filteredRows.length} of {rows.length}
        </p>
      )}
    </>
  );
}

type DashboardRecordsProps = Pick<ReturnType<typeof useDashboardRecords>, "roles" | "companies" | "contacts" | "retry">;

export function DashboardRecords({ roles, companies, contacts, retry }: DashboardRecordsProps) {
  const { user, request } = useAuth();
  const [roleEditor, setRoleEditor] = useState<RoleEditor | null>(null);
  const selectedRole = roleEditor && roleEditor.mode !== "create" ? roleEditor.role : null;
  const tracker = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const companyNames = new Map(companies.records.map((company) => [company.id, company.name]));

  function openRole(role: DashboardRole, trigger: HTMLButtonElement) {
    opener.current = trigger;
    setRoleEditor({ mode: "view", role });
  }

  function createRole(trigger: HTMLButtonElement) {
    opener.current = trigger;
    setRoleEditor({ mode: "create" });
  }

  function refreshRoleData() {
    retry("roles");
    retry("upcomingEvents");
  }

  function handleRoleSaved(role: DashboardRole) {
    setRoleEditor({ mode: "view", role });
    refreshRoleData();
  }

  async function handleRoleDeleted(id: string) {
    await deleteRole(request, id);
    // The deleted row disappears during refresh; the filter remains mounted.
    opener.current = tracker.current?.querySelector<HTMLInputElement>('input[type="search"]') ?? null;
    setRoleEditor(null);
    refreshRoleData();
  }

  function restoreRoleFocus() {
    if (opener.current?.isConnected) return opener.current;
    // A refresh replaces the row; deletion or a changed filter can remove it.
    return document.getElementById(`tracker-roles-${selectedRole?.id}`)
      ?? tracker.current?.querySelector<HTMLInputElement>('input[type="search"]')
      ?? null;
  }

  function companyName(companyId: string | null) {
    // The link is set, but that company is not in the list that loaded.
    return companyId === null ? null : companyNames.get(companyId) ?? "Unavailable";
  }

  if (!user) return null;

  return (
    <Card ref={tracker} className="gap-3">
      <CardHeader className="px-4 sm:px-5">
        <CardTitle><h2 className="text-lg font-semibold">Tracker</h2></CardTitle>
        <CardDescription>Browse and filter the records in your job search.</CardDescription>
      </CardHeader>
      {/* Panels stay mounted so filter text and the status choice survive a tab change. */}
      <Tabs defaultValue="roles" className="gap-3">
        <TabsList aria-label="Tracker records" className="mx-4 sm:mx-5">
          <TabsTrigger value="roles" className="px-3">Roles</TabsTrigger>
          <TabsTrigger value="companies" className="px-3">Companies</TabsTrigger>
          <TabsTrigger value="contacts" className="px-3">Contacts</TabsTrigger>
        </TabsList>
        <TabsContent value="roles" keepMounted>
          <RecordsPanel<DashboardRole>
            label="roles"
            addLabel="Add role"
            columns={[
              { heading: "Role", value: (role) => role.title },
              { heading: "Company", value: (role) => companyName(role.company_id) },
              { heading: "Status", value: (role) => roleStatusFilters[role.status] },
              { heading: "Type", value: (role) => role.role_type?.replaceAll("_", " ") ?? null },
              { heading: "Location", value: (role) => role.location },
              {
                heading: "Applied",
                value: (role) => role.applied_at ? dateFormat.format(new Date(role.applied_at)) : null,
              },
            ]}
            dataset={roles}
            getRoleStatus={(role) => role.status}
            onRetry={() => retry("roles")}
            onOpen={openRole}
            onCreate={createRole}
          />
        </TabsContent>
        <TabsContent value="companies" keepMounted>
          <RecordsPanel<DashboardCompany>
            label="companies"
            addLabel="Add company"
            columns={[
              { heading: "Company", value: (company) => company.name },
              { heading: "Location", value: (company) => company.location },
              { heading: "Website", value: (company) => company.website },
            ]}
            dataset={companies}
            onRetry={() => retry("companies")}
          />
        </TabsContent>
        <TabsContent value="contacts" keepMounted>
          <RecordsPanel<DashboardContact>
            label="contacts"
            addLabel="Add contact"
            columns={[
              { heading: "Contact", value: (contact) => contact.name },
              { heading: "Company", value: (contact) => companyName(contact.company_id) },
              { heading: "Title", value: (contact) => contact.role },
              { heading: "Email", value: (contact) => contact.email },
              { heading: "Phone", value: (contact) => contact.phone_number },
            ]}
            dataset={contacts}
            onRetry={() => retry("contacts")}
          />
        </TabsContent>
      </Tabs>
      {roleEditor && (
        <Suspense fallback={<div className="px-4"><LoadingState message="Loading role details…" /></div>}>
          <RoleDialog
            editor={roleEditor}
            companyName={selectedRole?.company_id ? companyNames.get(selectedRole.company_id) : undefined}
            onClose={() => setRoleEditor(null)}
            onSave={(change) => saveRole(request, user.id, change)}
            onSaved={handleRoleSaved}
            onDelete={handleRoleDeleted}
            restoreFocus={restoreRoleFocus}
          />
        </Suspense>
      )}
    </Card>
  );
}

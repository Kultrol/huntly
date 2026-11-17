import { Fragment, useEffect, useRef, type ReactNode } from "react";
import { ChevronDownIcon, ChevronRightIcon, PlusIcon, SearchIcon } from "lucide-react";
import { ChoiceField } from "@/components/ChoiceField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatApplicationDate } from "./formValues";
import { rolePriorities, roleStatuses, type TrackedRole } from "./types";

type RolesTableProps = {
  roles: TrackedRole[];
  companies: ReadonlyMap<string, string>;
  search: string;
  status: string;
  selectedId: string | null;
  focusRequest: number;
  onSearch: (search: string) => void;
  onStatus: (status: string) => void;
  onSelect: (id: string | null) => void;
  onCreate: (trigger: HTMLButtonElement) => void;
  renderDetails: (role: TrackedRole) => ReactNode;
};

export function RolesTable({
  roles,
  companies,
  search,
  status,
  selectedId,
  focusRequest,
  onSearch,
  onStatus,
  onSelect,
  onCreate,
  renderDetails,
}: RolesTableProps) {
  const selectedButton = useRef<HTMLButtonElement>(null);
  const query = search.trim().toLowerCase();
  const visibleRoles = roles
    .filter((role) => {
      const companyName = role.company_id ? companies.get(role.company_id) : "";
      const matchesStatus = !status || role.status === status;
      const matchesSearch = role.title.toLowerCase().includes(query)
        || companyName?.toLowerCase().includes(query);
      return matchesStatus && matchesSearch;
    })
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at) || a.id.localeCompare(b.id));

  useEffect(() => {
    if (!focusRequest) return;
    selectedButton.current?.scrollIntoView?.({ block: "nearest" });
    selectedButton.current?.focus({ preventScroll: true });
  }, [focusRequest]);

  return (
    <Card className="gap-0 overflow-hidden pb-0">
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-center gap-3">
          <CardTitle><h2>All roles</h2></CardTitle>
          <Button onClick={(event) => onCreate(event.currentTarget)}>
            <PlusIcon aria-hidden="true" />
            Add role
          </Button>
          {roles.length > 0 && (
            <span className="text-xs text-muted-foreground">{visibleRoles.length} of {roles.length}</span>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-wrap items-end gap-3 pb-4">
        <label className="grid min-w-40 flex-1 gap-1.5 text-sm font-medium @lg/workspace:max-w-sm">
          Search roles
          <div className="relative">
            <SearchIcon aria-hidden="true" className="absolute top-3 left-3 size-4 text-muted-foreground" />
            <Input
              type="search"
              value={search}
              onChange={(event) => onSearch(event.target.value)}
              placeholder="Title or company"
              className="pl-9 font-normal"
            />
          </div>
        </label>
        <div className="w-full @lg/workspace:w-44">
          <ChoiceField
            label="Filter by status"
            options={roleStatuses}
            value={status}
            onValueChange={onStatus}
            optionalLabel="All statuses"
          />
        </div>
      </CardContent>
      <Table aria-label="Tracked roles" className="table-fixed">
        <TableHeader className="border-t bg-muted/40">
          <TableRow>
            <TableHead className="px-4">Role</TableHead>
            <TableHead className="w-28">Status</TableHead>
            <TableHead className="hidden w-24 @2xl/workspace:table-cell">Priority</TableHead>
            <TableHead className="hidden w-32 @2xl/workspace:table-cell">Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {visibleRoles.map((role) => {
            const selected = selectedId === role.id;
            const Chevron = selected ? ChevronDownIcon : ChevronRightIcon;
            return (
              <Fragment key={role.id}>
                <TableRow data-state={selected ? "selected" : undefined}>
                  <TableCell className="min-w-36 px-4 py-3 whitespace-normal">
                    <button
                      ref={selected ? selectedButton : undefined}
                      type="button"
                      aria-expanded={selected}
                      aria-controls={selected ? `role-details-${role.id}` : undefined}
                      aria-label={role.title}
                      onClick={() => onSelect(selected ? null : role.id)}
                      className="touch-target flex w-full cursor-pointer items-center gap-2 rounded-md text-left focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <Chevron className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      <span className="min-w-0">
                        <span className="block font-medium wrap-anywhere">{role.title}</span>
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          {role.company_id ? companies.get(role.company_id) ?? "Company unavailable" : role.location ?? "Company unassigned"}
                        </span>
                      </span>
                    </button>
                  </TableCell>
                  <TableCell><Badge variant="secondary">{roleStatuses[role.status]}</Badge></TableCell>
                  <TableCell className="hidden text-muted-foreground @2xl/workspace:table-cell">{role.priority ? rolePriorities[role.priority] : "—"}</TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground @2xl/workspace:table-cell">{formatApplicationDate(role.updated_at)}</TableCell>
                </TableRow>
                {selected && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={4} className="whitespace-normal bg-muted/20 p-0">
                      <section
                        id={`role-details-${role.id}`}
                        aria-label={`${role.title} details`}
                        className="@container/role border-l-2 border-l-primary p-4 sm:p-5"
                      >
                        {renderDetails(role)}
                      </section>
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
          {visibleRoles.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="px-4 py-10 text-center whitespace-normal text-muted-foreground">
                {roles.length ? "No roles match your search or filters." : "No roles yet. Add a role to start tracking it."}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  );
}

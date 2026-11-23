import { useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { ArrowLeft, Plus, Search } from "lucide-react";
import { readOwnedRecords } from "@/api/ownedRecords";
import { useDataset } from "@/api/useDataset";
import { EmptyState, LoadError, LoadingState } from "@/components/feedback/LoadState";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/features/auth/session/useAuth";
import type { TrackedRole } from "@/features/roles/types";
import { cn } from "@/lib/utils";
import type { Company } from "./api";
import { CompanyDetails } from "./CompanyDetails";
import { CompanyDialog, type CompanyEditor } from "./CompanyDialog";
import { useCompanies } from "./useCompanies";

const columns = "grid grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_3rem] items-center gap-2 px-4";

function matchesSearch(company: Company, term: string) {
  return company.name.toLowerCase().includes(term) || !!company.location?.toLowerCase().includes(term);
}

export default function CompaniesWorkspace() {
  const [companies, reload, updateCompanies] = useCompanies();
  const [roles, retryRoles] = useDataset<TrackedRole>("/tracked-roles/", useAuth(), readOwnedRecords);
  const [editor, setEditor] = useState<CompanyEditor | null>(null);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const opener = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const back = useRef<HTMLButtonElement>(null);
  const profile = useRef<HTMLElement>(null);
  const selectedRow = useRef<HTMLButtonElement>(null);
  const term = query.trim().toLowerCase();
  const filtered = companies.records.filter((company) => matchesSearch(company, term));
  const selected = filtered.find((company) => company.id === selectedId) ?? filtered[0];
  const detailOpen = showDetails && !!selected;

  const rolesByCompany = useMemo(() => {
    const grouped = new Map<string, TrackedRole[]>();
    for (const role of roles.records) {
      if (!role.company_id) continue;
      const group = grouped.get(role.company_id);
      if (group) group.push(role);
      else grouped.set(role.company_id, [role]);
    }
    return grouped;
  }, [roles.records]);

  function selectCompany(id: string, fromKeyboard: boolean) {
    // Focus the destination after the responsive panes have switched.
    flushSync(() => {
      setSelectedId(id);
      setShowDetails(true);
    });
    if (back.current?.getClientRects().length) back.current.focus({ preventScroll: true });
    else if (fromKeyboard) profile.current?.focus({ preventScroll: true });
  }

  function backToList() {
    flushSync(() => setShowDetails(false));
    selectedRow.current?.scrollIntoView?.({ block: "nearest" });
    selectedRow.current?.focus({ preventScroll: true });
  }

  function open(next: CompanyEditor, trigger: HTMLButtonElement) {
    opener.current = trigger;
    setEditor(next);
  }

  function showSaved(company: Company) {
    if (!matchesSearch(company, term)) setQuery("");
    setSelectedId(company.id);
    setShowDetails(true);
    setEditor(null);
    updateCompanies((records) => {
      if (records.some((record) => record.id === company.id && record.name === company.name)) {
        return records.map((record) => record.id === company.id ? company : record);
      }
      const updated = [...records.filter((record) => record.id !== company.id), company];
      return updated.sort((a, b) => a.name.localeCompare(b.name) || a.id.localeCompare(b.id));
    });
  }

  function removeSelected() {
    if (!selected) return;
    const index = filtered.findIndex((company) => company.id === selected.id);
    setSelectedId((filtered[index + 1] ?? filtered[index - 1])?.id ?? null);
    setShowDetails(false);
    updateCompanies((records) => records.filter((company) => company.id !== selected.id));
  }

  return (
    <Card className="min-h-0 gap-0 py-0">
      <header className="flex shrink-0 flex-wrap items-center gap-3 border-b px-4 py-3">
        <h1 className="page-title mr-auto">Companies</h1>
        <label className={cn("relative order-last w-full @xl/workspace:order-none @xl/workspace:w-60", detailOpen && "hidden @xl/workspace:block")}>
          <Search aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input ref={search} type="search" aria-label="Search companies" placeholder="Find by name or location"
            className="pl-9" value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <Button aria-haspopup="dialog" onClick={(event) => open({ mode: "create" }, event.currentTarget)}>
          <Plus aria-hidden="true" /> Add company
        </Button>
      </header>

      {companies.status === "loading" && <div className="px-4"><LoadingState message="Loading companies…" /></div>}
      {companies.status === "error" && <div className="p-4"><LoadError message={companies.error} onRetry={reload} retryLabel="Retry companies" /></div>}
      {companies.status === "ready" && !selected && (
        <div className="p-4"><EmptyState message={companies.records.length ? "No companies match your search." : "No companies yet."} /></div>
      )}
      {selected && (
        <div className="grid min-h-0 grid-rows-[minmax(0,1fr)] @xl/workspace:grid-cols-[minmax(0,1fr)_minmax(13rem,30%)]">
          <section aria-label="Company list" tabIndex={0} className={cn(
            "min-h-0 min-w-0 overflow-y-auto overscroll-contain scroll-pt-9 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring",
            detailOpen && "hidden @xl/workspace:block",
          )}>
            <div aria-hidden="true" className={cn(columns, "sticky top-0 z-1 min-h-9 border-b bg-card text-xs font-semibold tracking-wider text-muted-foreground uppercase")}>
              <span>Company</span><span>Location</span><span className="text-right">Roles</span>
            </div>
            <ul>
              {filtered.map((company) => {
                const active = company.id === selected.id;
                const count = rolesByCompany.get(company.id)?.length ?? 0;
                return (
                  <li key={company.id}>
                    <button type="button" ref={active ? selectedRow : undefined}
                      aria-label={`View ${company.name}`} aria-current={active || undefined}
                      aria-controls="company-details" aria-describedby={`company-summary-${company.id}`}
                      className={cn(columns, "touch-target min-h-10 w-full border-b py-1 text-left hover:bg-muted focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring",
                        active && "bg-accent shadow-[inset_3px_0_var(--primary)] hover:bg-accent")}
                      onClick={(event) => selectCompany(company.id, event.detail === 0)}>
                      <span className="text-[0.9375rem] font-semibold tracking-tight wrap-anywhere">{company.name}</span>
                      <span className="text-sm text-muted-foreground wrap-anywhere">{company.location || "—"}</span>
                      <span className="text-right font-mono text-sm tabular-nums">{roles.status === "ready" ? count : "—"}</span>
                      <span id={`company-summary-${company.id}`} className="sr-only">
                        {company.location && `${company.location}. `}{roles.status === "ready" ? `${count} tracked roles` : "Role count unavailable"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
          <aside ref={profile} key={selected.id} id="company-details" aria-label="Company details" tabIndex={0}
            className={cn("min-h-0 min-w-0 overflow-y-auto overscroll-contain bg-muted/50 p-4 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring @xl/workspace:block @xl/workspace:border-l", !detailOpen && "hidden")}>
            <Button ref={back} variant="ghost" size="sm" className="mb-3 @xl/workspace:hidden"
              onClick={backToList}>
              <ArrowLeft aria-hidden="true" /> Back to companies
            </Button>
            <CompanyDetails company={selected} roles={rolesByCompany.get(selected.id) ?? []}
              rolesStatus={roles.status} rolesError={roles.error ?? undefined} onRetryRoles={retryRoles}
              onEdit={(trigger) => open({ mode: "edit", company: selected }, trigger)}
              onDelete={(trigger) => open({ mode: "delete", company: selected }, trigger)} />
          </aside>
        </div>
      )}
      {editor && (
        <CompanyDialog editor={editor} onClose={() => setEditor(null)} onSaved={showSaved}
          onDeleted={removeSelected}
          restoreFocus={() => opener.current?.isConnected ? opener.current : search.current} />
      )}
    </Card>
  );
}

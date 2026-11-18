import { useRef, useState } from "react";
import { Building2, ChevronRight, Plus } from "lucide-react";
import { EmptyState, LoadError, LoadingState } from "@/components/feedback/LoadState";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { CompanyDialog, type CompanyEditor } from "./CompanyDialog";
import { useCompanies } from "./useCompanies";

export default function CompaniesWorkspace() {
  const [companies, reload] = useCompanies();
  const [editor, setEditor] = useState<CompanyEditor | null>(null);
  const [query, setQuery] = useState("");
  const opener = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const term = query.trim().toLowerCase();
  const filtered = companies.records.filter(({ name, location }) =>
    name.toLowerCase().includes(term) || location?.toLowerCase().includes(term),
  );

  function open(next: CompanyEditor, trigger: HTMLButtonElement) {
    opener.current = trigger;
    setEditor(next);
  }

  return (
    <Card className="gap-0 overflow-hidden">
      <CardHeader className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title">Companies</h1>
        <Button aria-haspopup="dialog" onClick={(event) => open({ mode: "create" }, event.currentTarget)}>
          <Plus aria-hidden="true" /> Add company
        </Button>
      </CardHeader>
      <div className="mt-4 space-y-4 border-t px-4 pt-4 sm:px-6">
        <Input ref={search} type="search" aria-label="Search companies" placeholder="Search by name or location"
          className="max-w-md" value={query} onChange={(event) => setQuery(event.target.value)} />
        {companies.status === "loading" && <LoadingState message="Loading companies…" />}
        {companies.status === "error" && <LoadError message={companies.error} onRetry={reload} retryLabel="Retry companies" />}
        {companies.status === "ready" && (filtered.length ? (
          <ul className="grid gap-2 @3xl/workspace:grid-cols-2 @6xl/workspace:grid-cols-3">
            {filtered.map((company) => (
              <li key={company.id} className="min-w-0">
                <button type="button" aria-haspopup="dialog" aria-label={`View ${company.name}`}
                  className="flex w-full items-center gap-3 rounded-lg border p-3 text-left hover:bg-accent focus-visible:outline-ring"
                  onClick={(event) => open({ mode: "view", company }, event.currentTarget)}>
                  <Building2 aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium wrap-anywhere">{company.name}</span>
                    {company.location && <span className="block text-sm text-muted-foreground wrap-anywhere">{company.location}</span>}
                  </span>
                  <ChevronRight aria-hidden="true" className="size-4 shrink-0" />
                </button>
              </li>
            ))}
          </ul>
        ) : <EmptyState message={companies.records.length ? "No companies match your search." : "No companies yet."} />)}
      </div>
      {editor && (
        <CompanyDialog
          editor={editor}
          onClose={() => setEditor(null)}
          onDeleted={reload}
          onSaved={(company) => {
            reload();
            setEditor({ mode: "view", company });
          }}
          restoreFocus={() => opener.current?.isConnected ? opener.current : search.current}
        />
      )}
    </Card>
  );
}

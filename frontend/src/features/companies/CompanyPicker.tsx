import { useRef, useState } from "react";
import type { Dataset } from "@/api/useDataset";
import { ChoiceField } from "@/components/ChoiceField";
import { Button } from "@/components/ui/button";
import { CompanyDialog } from "./CompanyDialog";
import type { Company } from "./api";

type Props = {
  companies: Dataset<Company>;
  value: string;
  onChange: (id: string) => void;
  onReload: () => void;
};

export function CompanyPicker({ companies, value, onChange, onReload }: Props) {
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<Company | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const options = Object.fromEntries(companies.records.map(({ id, name }) => [id, name]));
  // Keep the selected label visible during the refresh after an inline create.
  if (created && !options[created.id]) options[created.id] = created.name;
  if (value && !options[value]) options[value] = "Assigned company";

  function selectNewCompany(company: Company) {
    setCreated(company);
    onChange(company.id);
    setCreating(false);
    onReload();
  }

  return (
    <div className="grid min-w-0 content-start gap-1">
      <ChoiceField label="Company" options={options} value={value} onValueChange={onChange} />
      <div className="flex flex-wrap items-center gap-2">
        <Button ref={trigger} type="button" variant="link" size="sm" className="px-0"
          aria-haspopup="dialog" onClick={() => setCreating(true)}>
          New company
        </Button>
        {companies.status === "loading" && <span role="status" className="text-xs">Loading companies…</span>}
        {companies.status === "error" && (
          <Button type="button" variant="outline" size="sm" onClick={onReload}>Retry companies</Button>
        )}
      </div>
      {creating && (
        <CompanyDialog
          editor={{ mode: "create" }}
          onClose={() => setCreating(false)}
          restoreFocus={() => trigger.current}
          onSaved={selectNewCompany}
        />
      )}
    </div>
  );
}

import { readOwnedRecords } from "@/api/ownedRecords";
import { useDataset } from "@/api/useDataset";
import { useAuth } from "@/features/auth/session/useAuth";
import type { Company } from "./api";

export function useCompanies() {
  return useDataset<Company>("/companies/", useAuth(), readOwnedRecords);
}

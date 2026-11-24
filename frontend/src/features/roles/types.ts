export const roleStatuses = {
  saved: "Saved",
  applied: "Applied",
  screening: "Screening",
  interview: "Interview",
  offer: "Offer",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export const roleTypes = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  internship: "Internship",
  temporary: "Temporary",
  other: "Other",
};

export const rolePriorities = { low: "Low", medium: "Medium", high: "High" };

export type RoleStatus = keyof typeof roleStatuses;
export type RoleType = keyof typeof roleTypes;
export type RolePriority = keyof typeof rolePriorities;

export type RoleInput = {
  company_id?: string | null;
  title: string;
  status: RoleStatus;
  location: string | null;
  role_type: RoleType | null;
  priority: RolePriority | null;
  listing_url: string | null;
  salary_min: string | null;
  salary_max: string | null;
  salary_currency: string | null;
  applied_at: string | null;
  description: string | null;
  notes: string | null;
};

export type RoleChange =
  | { data: RoleInput }
  | { id: string; data: Partial<RoleInput> };

export type TrackedRole = RoleInput & {
  id: string;
  user_id: string;
  company_id: string | null;
  updated_at: string;
};

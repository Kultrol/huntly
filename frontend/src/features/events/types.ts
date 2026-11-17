export const eventTypes = {
  interview: "Interview",
  recruiter_screen: "Recruiter screen",
  assessment: "Assessment",
  follow_up: "Follow-up",
  application_deadline: "Application deadline",
  offer_deadline: "Offer deadline",
  networking: "Networking",
  custom: "Custom",
};

export const eventStatuses = {
  pending: "Pending",
  scheduled: "Scheduled",
  completed: "Completed",
  cancelled: "Cancelled",
  missed: "Missed",
};

export type EventInput = {
  title: string;
  event_type: keyof typeof eventTypes;
  custom_type_name: string | null;
  event_date: string;
  event_time: string | null;
  status: keyof typeof eventStatuses;
  notes: string | null;
  url: string | null;
  location: string | null;
};

export type RoleEvent = EventInput & { id: string; tracked_role_id: string };

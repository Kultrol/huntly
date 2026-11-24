export function verifyOwner(value: unknown, userId: string) {
  // A different tab can replace the session cookie before this tab refreshes auth.
  if (typeof value !== "object" || value === null || !("user_id" in value) || value.user_id !== userId) {
    throw new Error("Could not verify the account for these records. Try again.");
  }
}

export function readOwnedRecords<T>(body: unknown, userId: string): T[] {
  if (!Array.isArray(body)) throw new Error("The server returned an invalid records list.");
  for (const record of body) verifyOwner(record, userId);
  return body as T[];
}

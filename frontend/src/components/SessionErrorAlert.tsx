interface SessionErrorAlertProps {
  logoutError: string;
  sessionError: string;
}

export default function SessionErrorAlert({
  logoutError,
  sessionError,
}: SessionErrorAlertProps) {
  return (
    <>
      {(logoutError || sessionError) && (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
        >
          {logoutError || sessionError}
        </p>
      )}
    </>
  );
}

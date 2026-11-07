import { useState } from "react";
import { AuthField, AuthForm } from "../components/AuthForm";
import { registrationPasswordMinLength, useAuthForm } from "../useAuthForm";

export default function RegisterPage() {
  const [displayName, setDisplayName] = useState("");
  const [emailAddress, setEmailAddress] = useState("");
  const [password, setPassword] = useState("");
  const {
    formErrorMessage,
    fieldErrors,
    isPending,
    onSubmit,
    clearSubmissionErrorOnEdit,
  } = useAuthForm({
    mode: "register",
    formValues: { name: displayName, email: emailAddress, password },
  });

  return (
    <AuthForm
      title="Create your account"
      pageTitle="Create your account | Huntly"
      description="Set up your Huntly workspace to start tracking your job search."
      error={formErrorMessage}
      isPending={isPending}
      onSubmit={onSubmit}
      submitLabel="Create account"
      alternate={{ prompt: "Already have an account?", label: "Sign in", to: "/login" }}
    >
      <AuthField
        label="Name"
        name="name"
        autoComplete="name"
        required
        disabled={isPending}
        error={fieldErrors.name}
        value={displayName}
        onChange={(event) => {
          setDisplayName(event.target.value);
          clearSubmissionErrorOnEdit("name");
        }}
      />
      <AuthField
        label="Email"
        type="email"
        name="email"
        autoComplete="username"
        placeholder="you@example.com"
        required
        disabled={isPending}
        error={fieldErrors.email}
        value={emailAddress}
        onChange={(event) => {
          setEmailAddress(event.target.value);
          clearSubmissionErrorOnEdit("email");
        }}
      />
      <AuthField
        label="Password"
        type="password"
        name="password"
        autoComplete="new-password"
        hint={`Use at least ${registrationPasswordMinLength} characters.`}
        required
        disabled={isPending}
        error={fieldErrors.password}
        value={password}
        onChange={(event) => {
          setPassword(event.target.value);
          clearSubmissionErrorOnEdit("password");
        }}
      />
    </AuthForm>
  );
}

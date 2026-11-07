import { useState } from "react";
import { AuthField, AuthForm } from "../components/AuthForm";
import { useAuthForm } from "../useAuthForm";

export default function LoginPage() {
  const [emailAddress, setEmailAddress] = useState("");
  const [password, setPassword] = useState("");
  const {
    formErrorMessage,
    fieldErrors,
    isPending,
    onSubmit,
    clearSubmissionErrorOnEdit,
  } = useAuthForm({
    mode: "login",
    formValues: { email: emailAddress, password },
  });

  return (
    <AuthForm
      title="Sign in to Huntly"
      pageTitle="Sign in | Huntly"
      description="Enter your email and password to open your workspace."
      error={formErrorMessage}
      isPending={isPending}
      onSubmit={onSubmit}
      submitLabel="Login"
      alternate={{ prompt: "New to Huntly?", label: "Create an account", to: "/register" }}
    >
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
        autoComplete="current-password"
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

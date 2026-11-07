import { useRef, useState, type SubmitEvent } from "react";
import { getErrorMessage } from "@/api/client";
import { AuthApiError } from "./api/request";
import type { LoginInput, RegisterInput } from "./api/types";
import { useAuth } from "./session/useAuth";

type AuthFormOptions =
  | { mode: "login"; formValues: LoginInput }
  | { mode: "register"; formValues: RegisterInput };

type AuthFieldName = keyof RegisterInput;
type AuthFieldErrors = Partial<Record<AuthFieldName, string>>;
type SubmissionErrors = { fieldErrors?: AuthFieldErrors; formErrorMessage?: string };

export const registrationPasswordMinLength = 12;
const registrationNameMaxLength = 255;
const passwordMaxLength = 128;
const emailFormat = /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/u;
const unicodeDomainSeparators = /[\u3002\uFF0E\uFF61]/gu;

function normalizeAuthForm({ mode, formValues }: AuthFormOptions): AuthFormOptions {
  const normalizedEmail = formValues.email.trim();
  // Preserve password whitespace because it is part of the credential.
  if (mode === "register") {
    return {
      mode,
      formValues: { ...formValues, email: normalizedEmail, name: formValues.name.trim() },
    };
  }
  return { mode, formValues: { ...formValues, email: normalizedEmail } };
}

function validateAuthForm({ mode, formValues }: AuthFormOptions): AuthFieldErrors {
  const fieldErrors: AuthFieldErrors = {};
  // Accept Unicode domain dots in the format check and let the API normalize the address.
  const emailAddressForValidation = formValues.email.replace(unicodeDomainSeparators, ".");
  if (mode === "register") {
    const nameLength = [...formValues.name].length;
    if (nameLength === 0) {
      fieldErrors.name = "Enter your name.";
    } else if (nameLength > registrationNameMaxLength) {
      fieldErrors.name = `Name must be at most ${registrationNameMaxLength} characters.`;
    }
  }
  if (!formValues.email) {
    fieldErrors.email = "Enter your email address.";
  } else if (formValues.email.length > 254 || !emailFormat.test(emailAddressForValidation)) {
    fieldErrors.email = "Enter a valid email address.";
  }

  // The API counts Unicode code points and accepts shorter passwords for existing accounts.
  const passwordLength = [...formValues.password].length;
  if (mode === "register" && passwordLength < registrationPasswordMinLength) {
    fieldErrors.password = `Password must be at least ${registrationPasswordMinLength} characters.`;
  } else if (passwordLength === 0) {
    fieldErrors.password = "Enter your password.";
  } else if (passwordLength > passwordMaxLength) {
    fieldErrors.password = `Password must be at most ${passwordMaxLength} characters.`;
  }

  return fieldErrors;
}

/** Shares validation and submission behavior while each page owns its field values. */
export function useAuthForm(authForm: AuthFormOptions) {
  const { signIn, signUp, isPending, error: sessionError } = useAuth();
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [submissionErrors, setSubmissionErrors] = useState<SubmissionErrors>({});
  // A second submit can arrive before the disabled state renders.
  const isSubmissionInProgress = useRef(false);
  const normalizedAuthForm = normalizeAuthForm(authForm);
  const { mode, formValues: normalizedFormValues } = normalizedAuthForm;
  const clientValidationErrors = validateAuthForm(normalizedAuthForm);

  /** Clears the form-wide submission error and feedback for the edited field. */
  function clearSubmissionErrorOnEdit(editedField: AuthFieldName) {
    setSubmissionErrors((previousErrors) => {
      if (!previousErrors.formErrorMessage && !previousErrors.fieldErrors?.[editedField]) {
        return previousErrors;
      }
      return { fieldErrors: { ...previousErrors.fieldErrors, [editedField]: undefined } };
    });
  }

  async function onSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmissionInProgress.current || isPending) return;
    setHasAttemptedSubmit(true);
    setSubmissionErrors({});

    // Show local validation after the first submit attempt and focus the first field to fix.
    const firstInvalidField = Object.keys(clientValidationErrors)[0];
    if (firstInvalidField) {
      event.currentTarget.querySelector<HTMLInputElement>(`input[name="${firstInvalidField}"]`)?.focus();
      return;
    }

    isSubmissionInProgress.current = true;
    try {
      if (mode === "register") await signUp(normalizedFormValues);
      else await signIn(normalizedFormValues);
    } catch (error) {
      // Use inline feedback for errors tied to a visible field and a banner for the rest.
      const serverFieldErrors = error instanceof AuthApiError ? error.fieldErrors : undefined;
      if (
        serverFieldErrors?.email ||
        serverFieldErrors?.password ||
        (mode === "register" && serverFieldErrors?.name)
      ) {
        setSubmissionErrors({ fieldErrors: serverFieldErrors });
      } else {
        setSubmissionErrors({ formErrorMessage: getErrorMessage(error) });
      }
    } finally {
      isSubmissionInProgress.current = false;
    }
  }

  return {
    formErrorMessage: submissionErrors.formErrorMessage ?? sessionError,
    fieldErrors: hasAttemptedSubmit ? { ...submissionErrors.fieldErrors, ...clientValidationErrors } : {},
    isPending,
    onSubmit,
    clearSubmissionErrorOnEdit,
  };
}

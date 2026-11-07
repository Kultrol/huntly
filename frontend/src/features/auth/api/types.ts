export type AuthUser = {
  id: string;
  name: string;
  email: string | null;
};

/** The API returns these values together for the session identified by the HttpOnly cookie. */
export type AuthSession = {
  user: AuthUser;
  csrf_token: string;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type RegisterInput = LoginInput & {
  name: string;
};

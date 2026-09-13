export const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error(
    "API URL could not be reached or found. Check to see if API_URL has been configured.",
  );
}

import { API_URL } from "./client";

type HealthResponse = {
  status: "ok";
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`);
  if (response.ok) {
    const healthResponse = await response.json();
    return healthResponse;
  } else {
    throw Error("Backend API Connection Failure.");
  }
}

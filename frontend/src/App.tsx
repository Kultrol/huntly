import { useState, useEffect } from "react";
import { getHealth } from "./api/health";

function App() {
  type BackendStatus = "loading" | "success" | "error";

  const [backendStatus, setBackendStatus] = useState<BackendStatus>("loading");

  async function backendHealthStatusUpdater() {
    try {
      await getHealth();
      setBackendStatus("success");
    } catch {
      setBackendStatus("error");
    }
  }

  useEffect(() => {
    backendHealthStatusUpdater();
  }, []);

  if (backendStatus === "loading") {
    return (
      <div>
        <p>Backend Status: Checking...</p>
      </div>
    );
  } else if (backendStatus === "success") {
    return (
      <div>
        <p>Backend Status: Online</p>
      </div>
    );
  } else {
    return (
      <div>
        <p>Backend Status: Offline</p>
      </div>
    );
  }
}

export default App;

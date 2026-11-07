import { useState, useEffect } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { getHealth } from "@/api/health";

function HomePage() {
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
      <div className="m-2">
        <p className="mb-2">Backend Status: Online</p>
        <Button>
          <Link to="/login">Login In</Link>
        </Button>
        <Button>
          <Link to="/register">Register</Link>
        </Button>
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

export default HomePage;

import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./App.css";
import App from "./App.jsx";
import LandingPage from "./LandingPage.jsx";
import AuthPage from "./AuthPage.jsx";
import api from "./lib/api";

function ProtectedDashboard() {
  const [authorized, setAuthorized] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;

    async function verifySession() {
      if (!localStorage.getItem("trademind_access_token")) {
        window.location.replace("/login");
        return;
      }

      try {
        await api.get("/api/auth/me");
        if (active) setAuthorized(true);
      } catch {
        localStorage.removeItem("trademind_access_token");
        if (active) window.location.replace("/login");
      } finally {
        if (active) setChecking(false);
      }
    }

    const handleUnauthorized = () => {
      localStorage.removeItem("trademind_access_token");
      window.location.replace("/login");
    };

    window.addEventListener("trademind:unauthorized", handleUnauthorized);
    verifySession();

    return () => {
      active = false;
      window.removeEventListener(
        "trademind:unauthorized",
        handleUnauthorized
      );
    };
  }, []);

  if (checking || !authorized) {
    return <div className="route-loading" aria-label="Checking session" />;
  }

  return <App />;
}

function Router() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";

  if (path === "/") return <LandingPage />;
  if (path === "/login") return <AuthPage mode="login" />;
  if (path === "/signup") return <AuthPage mode="signup" />;

  if (path === "/dashboard" || path === "/app") {
    return <ProtectedDashboard />;
  }

  return <LandingPage />;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Router />
  </StrictMode>
);

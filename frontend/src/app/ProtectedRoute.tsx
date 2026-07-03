import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./auth";
import { ROUTES } from "../routes/paths";

export function ProtectedRoute() {
  const { session } = useAuth();
  const location = useLocation();

  if (!session) {
    return (
      <Navigate
        to={ROUTES.login}
        replace
        state={{ from: location, reason: "Sessao expirada" }}
      />
    );
  }

  return <Outlet />;
}

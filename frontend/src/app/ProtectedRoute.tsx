import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./auth";
import { ROUTES } from "../routes/paths";

export function ProtectedRoute() {
  const { session, sessionExpired } = useAuth();
  const location = useLocation();

  if (!session) {
    return (
      <Navigate
        to={ROUTES.login}
        replace
        state={{
          from: location,
          reason: sessionExpired ? "Sessao expirada" : undefined,
        }}
      />
    );
  }

  return <Outlet />;
}

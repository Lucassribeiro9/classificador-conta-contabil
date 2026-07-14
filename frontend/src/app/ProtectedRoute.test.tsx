import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ROUTES } from "../routes/paths";
import { renderWithProviders } from "../test/testUtils";
import { ProtectedRoute } from "./ProtectedRoute";

function renderProtectedRoute(session: { accessToken: string } | null) {
  renderWithProviders(
    <Routes>
      <Route path={ROUTES.login} element={<h1>Login</h1>} />
      <Route element={<ProtectedRoute />}>
        <Route path={ROUTES.empresas} element={<h1>Empresas</h1>} />
      </Route>
    </Routes>,
    {
      initialEntries: [ROUTES.empresas],
      initialSession: session
        ? {
            accessToken: session.accessToken,
            userEmail: "teste@interno.local",
          }
        : null,
    },
  );
}

describe("ProtectedRoute", () => {
  it("redireciona usuario sem sessao para login", () => {
    renderProtectedRoute(null);

    expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
  });

  it("renderiza rota interna quando existe sessao", () => {
    renderProtectedRoute({ accessToken: "token-de-teste" });

    expect(
      screen.getByRole("heading", { name: "Empresas" }),
    ).toBeInTheDocument();
  });
});

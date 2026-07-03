import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "./auth";
import { ProtectedRoute } from "./ProtectedRoute";
import { ROUTES } from "../routes/paths";

function renderProtectedRoute(session: { accessToken: string } | null) {
  render(
    <AuthProvider initialSession={session}>
      <MemoryRouter initialEntries={[ROUTES.empresas]}>
        <Routes>
          <Route path={ROUTES.login} element={<h1>Login</h1>} />
          <Route element={<ProtectedRoute />}>
            <Route path={ROUTES.empresas} element={<h1>Empresas</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
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

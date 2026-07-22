import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { ROUTES } from "../routes/paths";
import { renderWithProviders } from "../test/testUtils";
import { AuthProvider } from "./auth";
import { ProtectedRoute } from "./ProtectedRoute";

const SESSION_STORAGE_KEY = "classificador.auth.session";

function createJwt(exp: number) {
  const payload = btoa(JSON.stringify({ exp }))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
  return `header.${payload}.signature`;
}

function LoginProbe() {
  const location = useLocation();
  return (
    <>
      <h1>Login</h1>
      <span>{location.state?.reason ?? "autenticacao necessaria"}</span>
    </>
  );
}

function renderProtectedRoute(session: { accessToken: string } | null) {
  renderWithProviders(
    <Routes>
      <Route path={ROUTES.login} element={<LoginProbe />} />
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
  afterEach(() => {
    sessionStorage.clear();
  });

  it("redireciona usuario sem sessao para login", () => {
    renderProtectedRoute(null);

    expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
    expect(screen.getByText("autenticacao necessaria")).toBeInTheDocument();
  });

  it("renderiza rota interna quando existe sessao", () => {
    renderProtectedRoute({ accessToken: "token-de-teste" });

    expect(
      screen.getByRole("heading", { name: "Empresas" }),
    ).toBeInTheDocument();
  });

  it("informa quando uma sessao persistida expirou", () => {
    sessionStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        accessToken: createJwt(Math.floor(Date.now() / 1000) - 60),
        userEmail: "teste@interno.local",
      }),
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={[ROUTES.empresas]}>
          <Routes>
            <Route path={ROUTES.login} element={<LoginProbe />} />
            <Route element={<ProtectedRoute />}>
              <Route path={ROUTES.empresas} element={<h1>Empresas</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );

    expect(screen.getByText("Sessao expirada")).toBeInTheDocument();
  });
});

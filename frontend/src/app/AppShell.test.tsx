import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "./auth";
import { AppShell } from "./AppShell";
import { ProtectedRoute } from "./ProtectedRoute";
import { ROUTES } from "../routes/paths";

const TEST_SESSION = {
  accessToken: "token-de-teste",
  userEmail: "operador.hml",
};

describe("AppShell", () => {
  it("mantem a empresa selecionada visivel no contexto operacional", () => {
    render(
      <AuthProvider initialSession={TEST_SESSION}>
        <MemoryRouter initialEntries={["/empresas/42"]}>
          <Routes>
            <Route path={ROUTES.empresa.operacaoPath} element={<AppShell />}>
              <Route index element={<h1>Operacao da Empresa</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );

    expect(screen.getByText("Empresa selecionada: 42")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Operacao da Empresa" }),
    ).toBeInTheDocument();
  });

  it("encerra a sessao e retorna ao login", () => {
    render(
      <AuthProvider initialSession={TEST_SESSION}>
        <MemoryRouter initialEntries={[ROUTES.empresas]}>
          <Routes>
            <Route path={ROUTES.login} element={<h1>Login</h1>} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path={ROUTES.empresas} element={<h1>Empresas</h1>} />
              </Route>
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Sair" }));

    expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
  });
});

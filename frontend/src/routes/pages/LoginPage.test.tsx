import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import { ROUTES } from "../paths";
import { LoginPage } from "./LoginPage";
import { authClient } from "../../lib/api/authClient";

vi.mock("../../lib/api/authClient", () => ({
  InvalidCredentialsError: class InvalidCredentialsError extends Error {},
  NetworkAuthError: class NetworkAuthError extends Error {},
  authClient: {
    login: vi.fn(),
  },
}));

const loginMock = vi.mocked(authClient.login);

type LoginInitialEntry =
  | string
  | { pathname: string; state?: { reason: string } };

function renderLogin(initialEntry: LoginInitialEntry = ROUTES.login) {
  render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path={ROUTES.login} element={<LoginPage />} />
          <Route path={ROUTES.empresas} element={<h1>Empresas</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it("envia credenciais, armazena sessao e redireciona para empresas", async () => {
    loginMock.mockResolvedValueOnce({
      accessToken: "jwt-de-teste",
      userEmail: "operador@interno.test",
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "operador@interno.test" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-segura" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() =>
      expect(loginMock).toHaveBeenCalledWith({
        email: "operador@interno.test",
        password: "senha-segura",
      }),
    );
    expect(
      await screen.findByRole("heading", { name: "Empresas" }),
    ).toBeInTheDocument();
  });

  it("exibe mensagem curta para credenciais invalidas", async () => {
    loginMock.mockRejectedValueOnce(new Error("invalid"));

    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "operador@interno.test" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-incorreta" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText(/Credenciais invalidas/)).toBeInTheDocument();
  });

  it("exibe orientacao para erro de rede", async () => {
    loginMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "operador@interno.test" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-segura" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByText(/Nao foi possivel conectar/),
    ).toBeInTheDocument();
  });

  it("mostra aviso de sessao expirada quando a rota protegida redireciona", () => {
    renderLogin({
      pathname: ROUTES.login,
      state: { reason: "Sessao expirada" },
    });

    expect(screen.getByText(/Sessao expirada/)).toBeInTheDocument();
  });
});

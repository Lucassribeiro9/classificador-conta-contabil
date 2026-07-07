import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import {
  EmpresasAccessDeniedError,
  EmpresasNetworkError,
  empresasClient,
} from "../../lib/api/empresasClient";
import { ROUTES } from "../paths";
import { EmpresasPage } from "./EmpresasPage";

vi.mock("../../lib/api/empresasClient", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../lib/api/empresasClient")>();

  return {
    ...actual,
    empresasClient: {
      list: vi.fn(),
    },
  };
});

const listEmpresasMock = vi.mocked(empresasClient.list);

function renderEmpresasPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider
        initialSession={{
          accessToken: "jwt-de-teste",
          userEmail: "operador@interno.test",
        }}
      >
        <MemoryRouter initialEntries={[ROUTES.empresas]}>
          <Routes>
            <Route path={ROUTES.empresas} element={<EmpresasPage />} />
            <Route
              path={ROUTES.empresa.operacaoPath}
              element={<h1>Operacao da Empresa</h1>}
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("EmpresasPage", () => {
  beforeEach(() => {
    listEmpresasMock.mockReset();
  });

  it("lista empresas autorizadas pela API e abre a operacao da empresa escolhida", async () => {
    listEmpresasMock.mockResolvedValueOnce([
      {
        id: 7,
        nome: "Comercial Alfa LTDA",
        documento: "12.345.678/0001-90",
        papel: "operador",
      },
      {
        id: 11,
        nome: "Industria Beta SA",
        documento: "98.765.432/0001-10",
        papel: "admin",
      },
    ]);

    renderEmpresasPage();

    expect(
      await screen.findByRole("heading", { name: "Escolha a empresa" }),
    ).toBeInTheDocument();
    expect(listEmpresasMock).toHaveBeenCalledWith("jwt-de-teste");
    expect(screen.getByText("Comercial Alfa LTDA")).toBeInTheDocument();
    expect(screen.getByText("Industria Beta SA")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /Abrir Comercial Alfa LTDA/ }),
    );

    expect(
      await screen.findByRole("heading", { name: "Operacao da Empresa" }),
    ).toBeInTheDocument();
  });

  it("orienta contato com administrador quando nao ha empresas vinculadas", async () => {
    listEmpresasMock.mockResolvedValueOnce([]);

    renderEmpresasPage();

    expect(
      await screen.findByRole("heading", { name: "Sem empresas vinculadas" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Contate o administrador/)).toBeInTheDocument();
  });

  it("exibe acesso negado sem mostrar empresas locais", async () => {
    listEmpresasMock.mockRejectedValueOnce(new EmpresasAccessDeniedError());

    renderEmpresasPage();

    expect(
      await screen.findByRole("heading", { name: "Acesso negado" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Comercial Alfa LTDA")).not.toBeInTheDocument();
  });

  it("exibe mensagem operacional para erro de rede", async () => {
    listEmpresasMock.mockRejectedValueOnce(new EmpresasNetworkError());

    renderEmpresasPage();

    expect(
      await screen.findByRole("heading", {
        name: "Nao foi possivel carregar empresas",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Verifique a API interna e tente novamente."),
    ).toBeInTheDocument();
  });
});

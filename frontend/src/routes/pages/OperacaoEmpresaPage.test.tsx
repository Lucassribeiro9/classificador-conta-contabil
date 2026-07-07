import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import {
  OperacaoEmpresaAccessDeniedError,
  OperacaoEmpresaNetworkError,
  operacaoEmpresaClient,
} from "../../lib/api/operacaoEmpresaClient";
import { ROUTES } from "../paths";
import { ImportarMovimentosPage } from "./ImportarMovimentosPage";
import { LoteMovimentosPage } from "./LoteMovimentosPage";
import { OperacaoEmpresaPage } from "./OperacaoEmpresaPage";
import { RazaoContasPage } from "./RazaoContasPage";

vi.mock("../../lib/api/operacaoEmpresaClient", async (importOriginal) => {
  const actual =
    await importOriginal<
      typeof import("../../lib/api/operacaoEmpresaClient")
    >();

  return {
    ...actual,
    operacaoEmpresaClient: {
      getHub: vi.fn(),
    },
  };
});

const getHubMock = vi.mocked(operacaoEmpresaClient.getHub);

function renderOperacaoEmpresaPage() {
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
        <MemoryRouter initialEntries={[ROUTES.empresa.operacao("7")]}>
          <Routes>
            <Route
              path={ROUTES.empresa.operacaoPath}
              element={<OperacaoEmpresaPage />}
            />
            <Route
              path={ROUTES.empresa.importarMovimentosPath}
              element={<ImportarMovimentosPage />}
            />
            <Route
              path={ROUTES.empresa.loteMovimentosPath}
              element={<LoteMovimentosPage />}
            />
            <Route
              path={ROUTES.empresa.razaoContasPath}
              element={<RazaoContasPage />}
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("OperacaoEmpresaPage", () => {
  beforeEach(() => {
    getHubMock.mockReset();
  });

  it("exibe o resumo operacional da empresa e atalhos principais", async () => {
    getHubMock.mockResolvedValueOnce({
      empresa: {
        id: 7,
        nome: "Comercial Alfa LTDA",
        documento: "12345678000190",
        papel: "operador",
      },
      ml: {
        status: "modelo_pronto",
        treinavel: true,
        modeloExistente: true,
        podeClassificarMovimentos: true,
        datasetTotalLinhas: 42,
      },
      razao: {
        totalLotes: 2,
        totalLinhas: 180,
        ultimoStatus: "completed",
      },
      movimentos: {
        totalLotes: 3,
        totalLinhas: 28,
        ultimoLoteId: 15,
        ultimoStatus: "completed_with_warnings",
      },
      contasVinculadas: null,
    });

    renderOperacaoEmpresaPage();

    expect(
      await screen.findByRole("heading", { name: "Comercial Alfa LTDA" }),
    ).toBeInTheDocument();
    expect(getHubMock).toHaveBeenCalledWith("jwt-de-teste", "7");
    expect(screen.getByText("Modelo pronto")).toBeInTheDocument();
    expect(screen.getByText("2 lotes")).toBeInTheDocument();
    expect(screen.getByText("28 movimentos")).toBeInTheDocument();
    expect(screen.getByText("Nao informado pela API")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Importar movimentos" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Abrir ultimo lote" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Consultar razao" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Classificar pendentes")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("link", { name: "Importar movimentos" }),
    );
    expect(
      await screen.findByRole("heading", { name: "Importar Movimentos" }),
    ).toBeInTheDocument();
  });

  it("alerta quando nao ha razao ou base suficiente para classificacao", async () => {
    getHubMock.mockResolvedValueOnce({
      empresa: {
        id: 7,
        nome: "Comercial Alfa LTDA",
        papel: "operador",
      },
      ml: {
        status: "sem_razao",
        treinavel: false,
        modeloExistente: false,
        podeClassificarMovimentos: false,
        datasetTotalLinhas: 0,
      },
      razao: {
        totalLotes: 0,
        totalLinhas: 0,
      },
      movimentos: {
        totalLotes: 0,
        totalLinhas: 0,
      },
      contasVinculadas: null,
    });

    renderOperacaoEmpresaPage();

    expect(
      await screen.findByText("Importe o razao antes de validar classificacao."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Base insuficiente para classificacao automatica."),
    ).toBeInTheDocument();
    expect(screen.getByText("Sem lote operacional")).toBeInTheDocument();
  });

  it("exibe acesso negado para empresa sem permissao", async () => {
    getHubMock.mockRejectedValueOnce(new OperacaoEmpresaAccessDeniedError());

    renderOperacaoEmpresaPage();

    expect(
      await screen.findByRole("heading", { name: "Acesso negado" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Comercial Alfa LTDA")).not.toBeInTheDocument();
  });

  it("exibe mensagem operacional para erro de rede", async () => {
    getHubMock.mockRejectedValueOnce(new OperacaoEmpresaNetworkError());

    renderOperacaoEmpresaPage();

    expect(
      await screen.findByRole("heading", {
        name: "Nao foi possivel carregar a operacao",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Verifique a API interna e tente novamente."),
    ).toBeInTheDocument();
  });
});

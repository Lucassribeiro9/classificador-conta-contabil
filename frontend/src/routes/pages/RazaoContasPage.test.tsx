import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import {
  RazaoContasAccessDeniedError,
  RazaoContasNetworkError,
  razaoContasClient,
} from "../../lib/api/razaoContasClient";
import type {
  LancamentoRazaoResumo,
  LoteRazaoResumo,
  PaginatedResult,
} from "../../lib/api/razaoContasClient";
import { ROUTES } from "../paths";
import { RazaoContasPage } from "./RazaoContasPage";

vi.mock("../../lib/api/razaoContasClient", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../lib/api/razaoContasClient")>();

  return {
    ...actual,
    razaoContasClient: {
      listLotes: vi.fn(),
      listLancamentos: vi.fn(),
    },
  };
});

const listLotesMock = vi.mocked(razaoContasClient.listLotes);
const listLancamentosMock = vi.mocked(razaoContasClient.listLancamentos);

const lotes: PaginatedResult<LoteRazaoResumo> = {
  items: [
    {
      id: 15,
      empresaId: 7,
      originalFilename: "razao-consulta.xlsx",
      status: "completed",
      totalLinhas: 12,
      totalImportadas: 11,
      totalInvalidas: 1,
      createdAt: "2026-01-04T10:00:00",
    },
  ],
  total: 1,
  page: 1,
  limit: 10,
  hasNext: false,
};

const lancamentos: PaginatedResult<LancamentoRazaoResumo> = {
  items: [
    {
      id: 101,
      loteId: 15,
      empresaId: 7,
      numeroLancamento: "42",
      data: "2026-01-02",
      contaOrigem: 10046,
      contaContrapartida: 20001,
      contaDebito: 10046,
      contaCredito: 20001,
      direcao: "debito",
      historicoNormalizado: "pagamento fornecedor",
      valor: "250.75",
    },
    {
      id: 102,
      loteId: 15,
      empresaId: 7,
      numeroLancamento: "43",
      data: "2026-01-03",
      contaOrigem: 10046,
      contaContrapartida: 30001,
      contaDebito: 30001,
      contaCredito: 10046,
      direcao: "credito",
      historicoNormalizado: "recebimento cliente",
      valor: "900.00",
    },
  ],
  total: 2,
  page: 1,
  limit: 10,
  hasNext: false,
};

function renderRazaoContasPage(accessToken = "jwt-de-teste") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider
        initialSession={{
          accessToken,
          userEmail: "contador@interno.test",
        }}
      >
        <MemoryRouter initialEntries={[ROUTES.empresa.razaoContas("7")]}>
          <Routes>
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

describe("RazaoContasPage", () => {
  beforeEach(() => {
    listLotesMock.mockReset();
    listLancamentosMock.mockReset();
  });

  it("lista lotes, seleciona lote e filtra lancamentos por codigo ou historico", async () => {
    listLotesMock.mockResolvedValueOnce(lotes);
    listLancamentosMock.mockResolvedValue(lancamentos);

    renderRazaoContasPage();

    expect(
      await screen.findByRole("heading", { name: "Razao e Contas Vinculadas" }),
    ).toBeInTheDocument();
    expect(listLotesMock).toHaveBeenCalledWith("jwt-de-teste", "7", 1);
    expect(await screen.findByText("razao-consulta.xlsx")).toBeInTheDocument();
    expect(screen.getByText("11 importadas")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Abrir lote 15" }));

    expect(listLancamentosMock).toHaveBeenCalledWith("jwt-de-teste", "7", "15", 1);
    expect(await screen.findByText("pagamento fornecedor")).toBeInTheDocument();
    expect(screen.getByText("recebimento cliente")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Buscar por codigo ou historico"), {
      target: { value: "30001" },
    });

    expect(screen.queryByText("pagamento fornecedor")).not.toBeInTheDocument();
    expect(screen.getByText("recebimento cliente")).toBeInTheDocument();
  });

  it("exibe painel de contas vinculadas como contrato ausente sem inventar dados", async () => {
    listLotesMock.mockResolvedValueOnce(lotes);
    listLancamentosMock.mockResolvedValue(lancamentos);

    renderRazaoContasPage();

    await screen.findByText("razao-consulta.xlsx");
    const painel = screen.getByRole("region", { name: "Contas vinculadas" });

    expect(within(painel).getByText("Contrato ainda nao disponivel")).toBeInTheDocument();
    expect(
      within(painel).getByText(
        "A API ainda nao expoe busca paginada de contas vinculadas por empresa.",
      ),
    ).toBeInTheDocument();
  });

  it("trata vazio, acesso negado e erro de rede", async () => {
    listLotesMock.mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
      hasNext: false,
    });

    renderRazaoContasPage();

    expect(
      await screen.findByRole("heading", { name: "Sem razao importado" }),
    ).toBeInTheDocument();

    listLotesMock.mockRejectedValueOnce(new RazaoContasAccessDeniedError());
    renderRazaoContasPage();

    expect(
      await screen.findByRole("heading", { name: "Acesso negado" }),
    ).toBeInTheDocument();

    listLotesMock.mockRejectedValueOnce(new RazaoContasNetworkError());
    renderRazaoContasPage();

    expect(
      await screen.findByRole("heading", { name: "Nao foi possivel carregar o razao" }),
    ).toBeInTheDocument();
  });
});

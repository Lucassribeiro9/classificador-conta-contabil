import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import {
  RevisarMovimentoAccessDeniedError,
  RevisarMovimentoNetworkError,
  revisarMovimentoClient,
} from "../../lib/api/revisarMovimentoClient";
import type {
  ContaContabilResumo,
  MovimentoRevisao,
} from "../../lib/api/revisarMovimentoClient";
import { ROUTES } from "../paths";
import { RevisarMovimentoPage } from "./RevisarMovimentoPage";

vi.mock("../../lib/api/revisarMovimentoClient", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../lib/api/revisarMovimentoClient")>();

  return {
    ...actual,
    revisarMovimentoClient: {
      getMovimento: vi.fn(),
      reviewMovimento: vi.fn(),
      searchContas: vi.fn(),
    },
  };
});

const getMovimentoMock = vi.mocked(revisarMovimentoClient.getMovimento);
const searchContasMock = vi.mocked(revisarMovimentoClient.searchContas);
const reviewMovimentoMock = vi.mocked(revisarMovimentoClient.reviewMovimento);

const movimento: MovimentoRevisao = {
  id: 91,
  loteId: 15,
  empresaId: 7,
  data: "2026-01-03",
  contaFinanceira: 10046,
  historicoNormalizado: "pagamento fornecedor",
  valorAbsoluto: "250.75",
  direcao: "credito",
  tipoMovimento: "saida",
  contrapartidaInformada: null,
  contrapartidaSugerida: 20001,
  contrapartidaFinal: null,
  confidenceSugerida: 0.91,
  status: "pre_classificado",
  elegivelTreino: false,
  mensagensValidacao: ["Conferencia humana obrigatoria."],
};

const contas: ContaContabilResumo[] = [
  {
    id: 3,
    codigo: 20001,
    classificacao: "2.0.0",
    nome: "Fornecedores nacionais",
    tipo: "A",
    isActive: true,
    isFinancialOrigin: false,
  },
  {
    id: 4,
    codigo: 30001,
    classificacao: "3.0.0",
    nome: "Servicos tomados",
    tipo: "A",
    isActive: true,
    isFinancialOrigin: false,
  },
];

function renderRevisarMovimentoPage(entry = `${ROUTES.empresa.revisarMovimento("7", "91")}?loteId=15`) {
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
        <MemoryRouter initialEntries={[entry]}>
          <Routes>
            <Route
              path={ROUTES.empresa.revisarMovimentoPath}
              element={<RevisarMovimentoPage />}
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("RevisarMovimentoPage", () => {
  beforeEach(() => {
    getMovimentoMock.mockReset();
    searchContasMock.mockReset();
    reviewMovimentoMock.mockReset();
  });

  it("exibe dados, sugestao, confianca, warnings e busca vinculada primeiro", async () => {
    getMovimentoMock.mockResolvedValueOnce(movimento);
    searchContasMock.mockResolvedValueOnce(contas);

    renderRevisarMovimentoPage();

    expect(
      await screen.findByRole("heading", { name: "Revisar Movimento" }),
    ).toBeInTheDocument();
    expect(getMovimentoMock).toHaveBeenCalledWith("jwt-de-teste", "7", "15", "91");
    expect(screen.getByText("pagamento fornecedor")).toBeInTheDocument();
    expect(screen.getByText("91% de confianca")).toBeInTheDocument();
    expect(screen.getByText("Conferencia humana obrigatoria.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Usar 20001/ })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Buscar conta"), {
      target: { value: "fornecedor" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Buscar no plano completo" }));

    expect(await screen.findByRole("button", { name: /Usar 30001/ })).toBeInTheDocument();
    expect(searchContasMock).toHaveBeenCalledWith("jwt-de-teste", "fornecedor");
  });

  it("avisa quando a conta global escolhida ainda nao esta vinculada e corrige", async () => {
    getMovimentoMock.mockResolvedValueOnce(movimento);
    searchContasMock.mockResolvedValueOnce(contas);
    reviewMovimentoMock.mockResolvedValueOnce({
      ...movimento,
      contrapartidaFinal: 30001,
      status: "corrigido",
    });

    renderRevisarMovimentoPage();

    await screen.findByText("pagamento fornecedor");
    fireEvent.change(screen.getByLabelText("Buscar conta"), {
      target: { value: "servicos" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Buscar no plano completo" }));
    fireEvent.click(await screen.findByRole("button", { name: /Usar 30001/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "O vinculo desta conta sera criado pelo backend ao salvar a revisao.",
    );

    fireEvent.click(screen.getByRole("button", { name: "Corrigir com conta selecionada" }));

    await waitFor(() => {
      expect(reviewMovimentoMock).toHaveBeenCalledWith("jwt-de-teste", "7", "15", "91", {
        action: "correct",
        contaFinal: 30001,
      });
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Movimento corrigido.",
    );
  });

  it("aprova sugestao explicitamente e rejeita sem motivo", async () => {
    getMovimentoMock.mockResolvedValueOnce(movimento);
    reviewMovimentoMock.mockResolvedValueOnce({
      ...movimento,
      contrapartidaFinal: 20001,
      status: "aprovado",
    });
    reviewMovimentoMock.mockResolvedValueOnce({
      ...movimento,
      status: "rejeitado",
    });

    renderRevisarMovimentoPage();

    await screen.findByText("pagamento fornecedor");
    fireEvent.click(screen.getByRole("button", { name: "Aprovar sugestao" }));

    await waitFor(() => {
      expect(reviewMovimentoMock).toHaveBeenCalledWith("jwt-de-teste", "7", "15", "91", {
        action: "approve",
        contaFinal: 20001,
      });
    });

    fireEvent.change(screen.getByLabelText("Motivo de rejeicao"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rejeitar movimento" }));

    await waitFor(() => {
      expect(reviewMovimentoMock).toHaveBeenLastCalledWith(
        "jwt-de-teste",
        "7",
        "15",
        "91",
        { action: "reject" },
      );
    });
  });

  it("exibe acesso negado, erro de rede e lote ausente", async () => {
    getMovimentoMock.mockRejectedValueOnce(new RevisarMovimentoAccessDeniedError());
    renderRevisarMovimentoPage();

    expect(
      await screen.findByRole("heading", { name: "Acesso negado" }),
    ).toBeInTheDocument();

    getMovimentoMock.mockReset();
    getMovimentoMock.mockRejectedValueOnce(new RevisarMovimentoNetworkError());
    renderRevisarMovimentoPage();

    expect(
      await screen.findByRole("heading", {
        name: "Nao foi possivel carregar o movimento",
      }),
    ).toBeInTheDocument();

    renderRevisarMovimentoPage(ROUTES.empresa.revisarMovimento("7", "91"));
    expect(
      await screen.findByRole("heading", { name: "Lote nao informado" }),
    ).toBeInTheDocument();
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import {
  LoteMovimentosNetworkError,
  loteMovimentosClient,
} from "../../lib/api/loteMovimentosClient";
import type { MovimentoOperacional } from "../../lib/api/loteMovimentosClient";
import { ROUTES } from "../paths";
import { LoteMovimentosPage } from "./LoteMovimentosPage";
import { RevisarMovimentoPage } from "./RevisarMovimentoPage";

vi.mock("../../lib/api/loteMovimentosClient", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../lib/api/loteMovimentosClient")>();

  return {
    ...actual,
    loteMovimentosClient: {
      listMovimentos: vi.fn(),
      reviewMovimentos: vi.fn(),
      classificarPendentes: vi.fn(),
    },
  };
});

const listMovimentosMock = vi.mocked(loteMovimentosClient.listMovimentos);
const reviewMovimentosMock = vi.mocked(loteMovimentosClient.reviewMovimentos);
const classificarPendentesMock = vi.mocked(
  loteMovimentosClient.classificarPendentes,
);

const movimentos: MovimentoOperacional[] = [
  {
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
    mensagensValidacao: [],
  },
  {
    id: 92,
    loteId: 15,
    empresaId: 7,
    data: "2026-01-04",
    contaFinanceira: 10046,
    historicoNormalizado: "transferencia sem contrapartida",
    valorAbsoluto: "100.00",
    direcao: "credito",
    tipoMovimento: "transferencia",
    contrapartidaInformada: null,
    contrapartidaSugerida: null,
    contrapartidaFinal: null,
    confidenceSugerida: null,
    status: "revisao",
    elegivelTreino: false,
    mensagensValidacao: ["Tipo transferencia exige contrapartida."],
  },
  {
    id: 93,
    loteId: 15,
    empresaId: 7,
    data: "2026-01-05",
    contaFinanceira: 10046,
    historicoNormalizado: "tarifa bancaria",
    valorAbsoluto: "32.10",
    direcao: "credito",
    tipoMovimento: "saida",
    contrapartidaInformada: 30001,
    contrapartidaSugerida: null,
    contrapartidaFinal: null,
    confidenceSugerida: null,
    status: "pendente",
    elegivelTreino: false,
    mensagensValidacao: [],
  },
];

function renderLoteMovimentosPage() {
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
        <MemoryRouter initialEntries={[ROUTES.empresa.loteMovimentos("7", "15")]}>
          <Routes>
            <Route
              path={ROUTES.empresa.loteMovimentosPath}
              element={<LoteMovimentosPage />}
            />
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

describe("LoteMovimentosPage", () => {
  beforeEach(() => {
    listMovimentosMock.mockReset();
    reviewMovimentosMock.mockReset();
    classificarPendentesMock.mockReset();
  });

  it("lista movimentos do lote e filtra por status", async () => {
    listMovimentosMock.mockResolvedValueOnce({
      items: movimentos,
      total: 3,
      page: 1,
      limit: 100,
      hasNext: false,
    });
    listMovimentosMock.mockResolvedValueOnce({
      items: [movimentos[1]],
      total: 1,
      page: 1,
      limit: 100,
      hasNext: false,
    });

    renderLoteMovimentosPage();

    expect(
      await screen.findByRole("heading", { name: "Lote de Movimentos" }),
    ).toBeInTheDocument();
    expect(screen.getByText("pagamento fornecedor")).toBeInTheDocument();
    expect(screen.getByText("transferencia sem contrapartida")).toBeInTheDocument();
    expect(listMovimentosMock).toHaveBeenCalledWith("jwt-de-teste", "7", "15", "todos");

    fireEvent.click(screen.getByRole("button", { name: "Revisao" }));

    expect(
      await screen.findByText("transferencia sem contrapartida"),
    ).toBeInTheDocument();
    expect(screen.queryByText("pagamento fornecedor")).not.toBeInTheDocument();
    expect(listMovimentosMock).toHaveBeenLastCalledWith(
      "jwt-de-teste",
      "7",
      "15",
      "revisao",
    );
  });

  it("seleciona movimentos, aprova elegiveis e navega para revisao individual", async () => {
    listMovimentosMock.mockResolvedValue({
      items: movimentos,
      total: 3,
      page: 1,
      limit: 100,
      hasNext: false,
    });
    reviewMovimentosMock.mockResolvedValueOnce({
      successCount: 1,
      failureCount: 0,
      failures: [],
    });

    renderLoteMovimentosPage();

    const fornecedorRow = await screen.findByRole("row", {
      name: /pagamento fornecedor/,
    });
    fireEvent.click(within(fornecedorRow).getByRole("checkbox"));
    expect(screen.getByText("1 selecionado")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Aprovar selecionados" }));

    await waitFor(() => {
      expect(reviewMovimentosMock).toHaveBeenCalledWith(
        "jwt-de-teste",
        "7",
        "15",
        [{ movimentoId: 91, action: "approve", contaFinal: 20001 }],
      );
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "1 movimento atualizado.",
    );

    fireEvent.click(within(fornecedorRow).getByRole("link", { name: "Abrir revisao" }));
    expect(
      await screen.findByRole("heading", { name: "Revisar Movimento" }),
    ).toBeInTheDocument();
  });

  it("rejeita selecionados e exibe falha parcial", async () => {
    listMovimentosMock.mockResolvedValue({
      items: movimentos,
      total: 3,
      page: 1,
      limit: 100,
      hasNext: false,
    });
    reviewMovimentosMock.mockResolvedValueOnce({
      successCount: 1,
      failureCount: 1,
      failures: [{ movimentoId: 92, message: "Movimento nao encontrado" }],
    });

    renderLoteMovimentosPage();

    fireEvent.click(
      within(await screen.findByRole("row", { name: /pagamento fornecedor/ }))
        .getByRole("checkbox"),
    );
    fireEvent.click(
      within(screen.getByRole("row", { name: /transferencia sem contrapartida/ }))
        .getByRole("checkbox"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Rejeitar selecionados" }));

    await waitFor(() => {
      expect(reviewMovimentosMock).toHaveBeenCalledWith(
        "jwt-de-teste",
        "7",
        "15",
        [
          { movimentoId: 91, action: "reject" },
          { movimentoId: 92, action: "reject" },
        ],
      );
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "1 falha ao atualizar selecionados.",
    );
  });

  it("bloqueia envio para revisao sem contrato e classifica pendentes da empresa", async () => {
    listMovimentosMock.mockResolvedValue({
      items: movimentos,
      total: 3,
      page: 1,
      limit: 100,
      hasNext: false,
    });
    classificarPendentesMock.mockResolvedValueOnce({
      empresaId: 7,
      quantidadeProcessada: 2,
      totalSugerido: 1,
      totalRevisao: 1,
    });

    renderLoteMovimentosPage();

    expect(
      await screen.findByText("Classificar pendentes atua em todos os pendentes da empresa."),
    ).toBeInTheDocument();
    fireEvent.click(
      within(screen.getByRole("row", { name: /tarifa bancaria/ })).getByRole(
        "checkbox",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Enviar para revisao" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Envio para revisao aguarda contrato da API.",
    );

    fireEvent.click(screen.getByRole("button", { name: "Classificar pendentes da empresa" }));

    await waitFor(() => {
      expect(classificarPendentesMock).toHaveBeenCalledWith("jwt-de-teste", "7");
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "2 pendentes classificados.",
    );
  });

  it("mostra estado de erro de rede", async () => {
    listMovimentosMock.mockRejectedValueOnce(new LoteMovimentosNetworkError());

    renderLoteMovimentosPage();

    expect(
      await screen.findByRole("heading", {
        name: "Nao foi possivel carregar o lote",
      }),
    ).toBeInTheDocument();
  });
});

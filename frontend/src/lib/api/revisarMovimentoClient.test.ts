import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RevisarMovimentoAccessDeniedError,
  RevisarMovimentoNetworkError,
  revisarMovimentoClient,
} from "./revisarMovimentoClient";

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status });
}

const movimentoApi = {
  id: 91,
  lote_id: 15,
  empresa_id: 7,
  data: "2026-01-03",
  conta_financeira: 10046,
  historico_normalizado: "pagamento fornecedor",
  valor_absoluto: "250.75",
  direcao: "credito",
  tipo_movimento: "saida",
  contrapartida_informada: null,
  contrapartida_sugerida: 20001,
  contrapartida_final: null,
  confidence_sugerida: 0.91,
  status: "pre_classificado",
  elegivel_treino: false,
  mensagens_validacao: ["Conferencia humana obrigatoria."],
  conta_debito: null,
  conta_credito: null,
};

describe("revisarMovimentoClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("localiza movimento dentro do lote e busca contas no catalogo", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          items: [movimentoApi],
          total: 1,
          page: 1,
          limit: 100,
          has_next: false,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse([
          {
            id: 3,
            codigo: 20001,
            classificacao: "2.0.0",
            nome: "Fornecedores nacionais",
            tipo: "A",
            grau: 3,
            is_active: true,
            is_financial_origin: false,
            created_at: "2026-01-01T00:00:00",
            updated_at: "2026-01-01T00:00:00",
          },
        ]),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      revisarMovimentoClient.getMovimento("jwt-de-teste", "7", "15", "91"),
    ).resolves.toMatchObject({
      id: 91,
      historicoNormalizado: "pagamento fornecedor",
      contrapartidaSugerida: 20001,
      mensagensValidacao: ["Conferencia humana obrigatoria."],
    });
    await expect(
      revisarMovimentoClient.searchContas("jwt-de-teste", "fornecedor"),
    ).resolves.toEqual([
      {
        codigo: 20001,
        classificacao: "2.0.0",
        id: 3,
        isActive: true,
        isFinancialOrigin: false,
        nome: "Fornecedores nacionais",
        tipo: "A",
      },
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/movimentos-operacionais/lotes/15/movimentos?limit=100",
      { headers: { Authorization: "Bearer jwt-de-teste" } },
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/plano-contas?nome=fornecedor",
      {
        headers: { Authorization: "Bearer jwt-de-teste" },
      },
    );
  });

  it("envia aprovar, corrigir e rejeitar para o endpoint de review", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() => jsonResponse(movimentoApi));
    vi.stubGlobal("fetch", fetchMock);

    await revisarMovimentoClient.reviewMovimento(
      "jwt-de-teste",
      "7",
      "15",
      "91",
      {
        action: "approve",
        contaFinal: 20001,
      },
    );
    await revisarMovimentoClient.reviewMovimento(
      "jwt-de-teste",
      "7",
      "15",
      "91",
      {
        action: "correct",
        contaFinal: 30001,
      },
    );
    await revisarMovimentoClient.reviewMovimento(
      "jwt-de-teste",
      "7",
      "15",
      "91",
      {
        action: "reject",
      },
    );

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/companies/7/movimentos-operacionais/lotes/15/movimentos/91/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ action: "approve", conta_final: 20001 }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/companies/7/movimentos-operacionais/lotes/15/movimentos/91/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ action: "correct", conta_final: 30001 }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/companies/7/movimentos-operacionais/lotes/15/movimentos/91/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ action: "reject" }),
      }),
    );
  });

  it("normaliza acesso negado e erro de rede", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 403 })),
    );

    await expect(
      revisarMovimentoClient.getMovimento("jwt-de-teste", "7", "15", "91"),
    ).rejects.toBeInstanceOf(RevisarMovimentoAccessDeniedError);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError()));

    await expect(
      revisarMovimentoClient.searchContas("jwt-de-teste", "fornecedor"),
    ).rejects.toBeInstanceOf(RevisarMovimentoNetworkError);
  });

  it("retorna dados demo sem chamar fetch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      revisarMovimentoClient.getMovimento(
        "demo-preview-token",
        "7",
        "15",
        "91",
      ),
    ).resolves.toMatchObject({
      id: 91,
      contrapartidaSugerida: 20001,
    });
    await expect(
      revisarMovimentoClient.searchContas("demo-preview-token", "fornecedor"),
    ).resolves.toEqual(
      expect.arrayContaining([expect.objectContaining({ codigo: 20001 })]),
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

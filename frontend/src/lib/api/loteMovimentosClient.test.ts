import { afterEach, describe, expect, it, vi } from "vitest";

import {
  LoteMovimentosAccessDeniedError,
  LoteMovimentosNetworkError,
  loteMovimentosClient,
} from "./loteMovimentosClient";

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status });
}

describe("loteMovimentosClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lista movimentos do lote com filtro de status", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        items: [
          {
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
            mensagens_validacao: [],
            conta_debito: null,
            conta_credito: null,
          },
        ],
        total: 1,
        page: 1,
        limit: 100,
        has_next: false,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      loteMovimentosClient.listMovimentos(
        "jwt-de-teste",
        "7",
        "15",
        "pre_classificado",
      ),
    ).resolves.toMatchObject({
      total: 1,
      items: [
        {
          id: 91,
          loteId: 15,
          historicoNormalizado: "pagamento fornecedor",
          contrapartidaSugerida: 20001,
          status: "pre_classificado",
        },
      ],
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/movimentos-operacionais/lotes/15/movimentos?limit=100&status=pre_classificado",
      { headers: { Authorization: "Bearer jwt-de-teste" } },
    );
  });

  it("chama review individual para aprovar e rejeitar selecionados", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 91, status: "aprovado" }))
      .mockResolvedValueOnce(jsonResponse({ id: 92, status: "rejeitado" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      loteMovimentosClient.reviewMovimentos("jwt-de-teste", "7", "15", [
        { movimentoId: 91, action: "approve", contaFinal: 20001 },
        { movimentoId: 92, action: "reject" },
      ]),
    ).resolves.toEqual({
      successCount: 2,
      failureCount: 0,
      failures: [],
    });
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
      "/api/v1/companies/7/movimentos-operacionais/lotes/15/movimentos/92/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ action: "reject" }),
      }),
    );
  });

  it("retorna falhas parciais das acoes em lote", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ id: 91, status: "aprovado" }))
        .mockResolvedValueOnce(
          jsonResponse({ detail: "Conta final invalida" }, 400),
        ),
    );

    await expect(
      loteMovimentosClient.reviewMovimentos("jwt-de-teste", "7", "15", [
        { movimentoId: 91, action: "approve", contaFinal: 20001 },
        { movimentoId: 92, action: "approve", contaFinal: 99999 },
      ]),
    ).resolves.toEqual({
      successCount: 1,
      failureCount: 1,
      failures: [{ movimentoId: 92, message: "Conta final invalida" }],
    });
  });

  it("classifica pendentes da empresa e normaliza erros", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        empresa_id: 7,
        quantidade_processada: 2,
        total_sugerido: 1,
        total_revisao: 1,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      loteMovimentosClient.classificarPendentes("jwt-de-teste", "7"),
    ).resolves.toEqual({
      empresaId: 7,
      quantidadeProcessada: 2,
      totalSugerido: 1,
      totalRevisao: 1,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/movimentos-operacionais/classificar",
      expect.objectContaining({ method: "POST" }),
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 403 })),
    );
    await expect(
      loteMovimentosClient.classificarPendentes("jwt-de-teste", "7"),
    ).rejects.toBeInstanceOf(LoteMovimentosAccessDeniedError);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError()));
    await expect(
      loteMovimentosClient.classificarPendentes("jwt-de-teste", "7"),
    ).rejects.toBeInstanceOf(LoteMovimentosNetworkError);
  });

  it("retorna movimentos demo em desenvolvimento sem chamar fetch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const result = await loteMovimentosClient.listMovimentos(
      "demo-preview-token",
      "7",
      "15",
    );
    expect(result.total).toBe(5);
    expect(result.items.map((item) => item.status)).toEqual(
      expect.arrayContaining(["pendente", "pre_classificado", "revisao"]),
    );
    await expect(
      loteMovimentosClient.classificarPendentes("demo-preview-token", "7"),
    ).resolves.toMatchObject({ quantidadeProcessada: 2 });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

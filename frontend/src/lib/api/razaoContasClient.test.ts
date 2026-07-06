import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RazaoContasAccessDeniedError,
  RazaoContasNetworkError,
  razaoContasClient,
} from "./razaoContasClient";

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status });
}

const loteApi = {
  id: 15,
  empresa_id: 7,
  original_filename: "razao-consulta.xlsx",
  status: "completed",
  total_linhas: 12,
  total_importadas: 11,
  total_invalidas: 1,
  created_at: "2026-01-04T10:00:00",
};

const lancamentoApi = {
  id: 101,
  lote_id: 15,
  empresa_id: 7,
  numero_lancamento: "42",
  data: "2026-01-02",
  conta_origem: 10046,
  conta_contrapartida: 20001,
  conta_debito: 10046,
  conta_credito: 20001,
  direcao: "debito",
  historico_normalizado: "pagamento fornecedor",
  valor: "250.75",
};

describe("razaoContasClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lista lotes e lancamentos normalizados com paginacao", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          items: [loteApi],
          total: 1,
          page: 1,
          limit: 10,
          has_next: false,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [lancamentoApi],
          total: 1,
          page: 1,
          limit: 10,
          has_next: false,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      razaoContasClient.listLotes("jwt-de-teste", "7", 1),
    ).resolves.toMatchObject({
      total: 1,
      items: [
        {
          id: 15,
          originalFilename: "razao-consulta.xlsx",
          totalImportadas: 11,
        },
      ],
    });
    await expect(
      razaoContasClient.listLancamentos("jwt-de-teste", "7", "15", 1),
    ).resolves.toMatchObject({
      items: [
        {
          id: 101,
          contaOrigem: 10046,
          contaContrapartida: 20001,
          historicoNormalizado: "pagamento fornecedor",
        },
      ],
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/razao/lotes?page=1&limit=10",
      { headers: { Authorization: "Bearer jwt-de-teste" } },
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/razao/lotes/15/lancamentos?page=1&limit=10",
      { headers: { Authorization: "Bearer jwt-de-teste" } },
    );
  });

  it("normaliza acesso negado e erro de rede", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));

    await expect(
      razaoContasClient.listLotes("jwt-de-teste", "7", 1),
    ).rejects.toBeInstanceOf(RazaoContasAccessDeniedError);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError()));

    await expect(
      razaoContasClient.listLancamentos("jwt-de-teste", "7", "15", 1),
    ).rejects.toBeInstanceOf(RazaoContasNetworkError);
  });

  it("retorna dados demo sem chamar fetch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      razaoContasClient.listLotes("demo-preview-token", "7", 1),
    ).resolves.toMatchObject({
      total: 2,
      items: expect.arrayContaining([
        expect.objectContaining({ originalFilename: "razao-demo.xlsx" }),
      ]),
    });
    await expect(
      razaoContasClient.listLancamentos("demo-preview-token", "7", "15", 1),
    ).resolves.toMatchObject({
      items: expect.arrayContaining([
        expect.objectContaining({
          historicoNormalizado: "pagamento fornecedor",
        }),
      ]),
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

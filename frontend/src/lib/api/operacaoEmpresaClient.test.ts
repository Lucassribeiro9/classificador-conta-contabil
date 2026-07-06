import { afterEach, describe, expect, it, vi } from "vitest";

import {
  OperacaoEmpresaAccessDeniedError,
  OperacaoEmpresaNetworkError,
  operacaoEmpresaClient,
} from "./operacaoEmpresaClient";

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status });
}

describe("operacaoEmpresaClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("compoe o hub operacional com endpoints reais da API", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          id: 7,
          nome_empresa: "Comercial Alfa LTDA",
          cnpj_cpf: "12345678000190",
          papel: "operador",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: "modelo_pronto",
          treinavel: true,
          modelo_existente: true,
          pode_classificar_movimentos: true,
          dataset_total_linhas: 42,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            { id: 1, status: "completed", total_importadas: 80 },
            { id: 2, status: "completed", total_importadas: 100 },
          ],
          total: 2,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            { id: 15, status: "completed_with_warnings", total_importadas: 28 },
          ],
          total: 1,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      operacaoEmpresaClient.getHub("jwt-de-teste", "7"),
    ).resolves.toMatchObject({
      empresa: {
        id: 7,
        nome: "Comercial Alfa LTDA",
        documento: "12345678000190",
      },
      ml: {
        status: "modelo_pronto",
        datasetTotalLinhas: 42,
      },
      razao: {
        totalLotes: 2,
        totalLinhas: 180,
      },
      movimentos: {
        totalLotes: 1,
        totalLinhas: 28,
        ultimoLoteId: 15,
      },
      contasVinculadas: null,
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/companies/7", {
      headers: { Authorization: "Bearer jwt-de-teste" },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/ml/status",
      { headers: { Authorization: "Bearer jwt-de-teste" } },
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/razao/lotes?limit=5",
      { headers: { Authorization: "Bearer jwt-de-teste" } },
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/movimentos-operacionais/lotes?limit=5",
      { headers: { Authorization: "Bearer jwt-de-teste" } },
    );
  });

  it("normaliza acesso negado e falha de rede", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));

    await expect(
      operacaoEmpresaClient.getHub("jwt-de-teste", "7"),
    ).rejects.toBeInstanceOf(OperacaoEmpresaAccessDeniedError);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError()));

    await expect(
      operacaoEmpresaClient.getHub("jwt-de-teste", "7"),
    ).rejects.toBeInstanceOf(OperacaoEmpresaNetworkError);
  });

  it("retorna hub demo em desenvolvimento sem chamar a API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      operacaoEmpresaClient.getHub("demo-preview-token", "7"),
    ).resolves.toMatchObject({
      empresa: {
        id: 7,
        nome: "Comercial Alfa LTDA",
      },
      ml: {
        status: "modelo_pronto",
        treinavel: true,
      },
      razao: {
        totalLotes: 2,
      },
      movimentos: {
        ultimoLoteId: 15,
      },
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

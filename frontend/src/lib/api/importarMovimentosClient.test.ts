import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ImportarMovimentosAccessDeniedError,
  ImportarMovimentosBlockedError,
  ImportarMovimentosNetworkError,
  importarMovimentosClient,
} from "./importarMovimentosClient";

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status });
}

describe("importarMovimentosClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("envia o arquivo xlsx para a API usando multipart autenticado", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        lote_id: 31,
        status: "completed",
        total_linhas: 12,
        total_importadas: 12,
        total_invalidas: 0,
        warnings: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["xlsx"], "movimentos.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    await expect(
      importarMovimentosClient.importar("jwt-de-teste", "7", file),
    ).resolves.toEqual({
      loteId: 31,
      status: "completed",
      totalLinhas: 12,
      totalImportadas: 12,
      totalInvalidas: 0,
      warnings: [],
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/companies/7/movimentos-operacionais/import",
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer jwt-de-teste" },
        body: expect.any(FormData),
      }),
    );
    const body = fetchMock.mock.calls[0][1].body as FormData;
    expect(body.get("file")).toBe(file);
  });

  it("normaliza bloqueio da importacao, acesso negado e erro de rede", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(jsonResponse({ detail: "Arquivo deve ser .xlsx" }, 400)),
    );

    await expect(
      importarMovimentosClient.importar(
        "jwt-de-teste",
        "7",
        new File(["csv"], "movimentos.csv", { type: "text/csv" }),
      ),
    ).rejects.toMatchObject(new ImportarMovimentosBlockedError("Arquivo deve ser .xlsx"));

    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(null, { status: 403 })));

    await expect(
      importarMovimentosClient.importar(
        "jwt-de-teste",
        "7",
        new File(["xlsx"], "movimentos.xlsx"),
      ),
    ).rejects.toBeInstanceOf(ImportarMovimentosAccessDeniedError);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError()));

    await expect(
      importarMovimentosClient.importar(
        "jwt-de-teste",
        "7",
        new File(["xlsx"], "movimentos.xlsx"),
      ),
    ).rejects.toBeInstanceOf(ImportarMovimentosNetworkError);
  });

  it("retorna resumo demo em desenvolvimento sem chamar a API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      importarMovimentosClient.importar(
        "demo-preview-token",
        "7",
        new File(["xlsx"], "movimentos.xlsx"),
      ),
    ).resolves.toMatchObject({
      loteId: 15,
      status: "completed_with_warnings",
      totalLinhas: 28,
      totalImportadas: 26,
      totalInvalidas: 2,
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

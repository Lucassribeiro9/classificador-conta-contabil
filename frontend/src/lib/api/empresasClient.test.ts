import { afterEach, describe, expect, it, vi } from "vitest";

import {
  EmpresasAccessDeniedError,
  EmpresasNetworkError,
  empresasClient,
} from "./empresasClient";

describe("empresasClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lista empresas autorizadas usando o token da sessao", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 7,
            nome_empresa: "Comercial Alfa LTDA",
            cnpj_cpf: "12345678000190",
            papel: "operador",
          },
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(empresasClient.list("jwt-de-teste")).resolves.toEqual([
      {
        id: 7,
        nome: "Comercial Alfa LTDA",
        documento: "12345678000190",
        papel: "operador",
      },
    ]);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/companies", {
      headers: { Authorization: "Bearer jwt-de-teste" },
    });
  });

  it("normaliza acesso negado e falha de rede", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(new Response(null, { status: 403 })),
    );

    await expect(empresasClient.list("jwt-de-teste")).rejects.toBeInstanceOf(
      EmpresasAccessDeniedError,
    );

    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError()));

    await expect(empresasClient.list("jwt-de-teste")).rejects.toBeInstanceOf(
      EmpresasNetworkError,
    );
  });
});

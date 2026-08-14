import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("apiClient", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("VITE_API_BASE_URL", "https://api.interna.test");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("usa base URL por env var e anexa token quando autenticado", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 7, nome: "Comercial Alfa LTDA" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { apiClient } = await import("./apiClient");

    await expect(
      apiClient.get("/api/v1/companies/7", { accessToken: "jwt-de-teste" }),
    ).resolves.toEqual({ id: 7, nome: "Comercial Alfa LTDA" });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.interna.test/api/v1/companies/7",
      {
        headers: { Authorization: "Bearer jwt-de-teste" },
        method: "GET",
      },
    );
  });

  it("nao envia Authorization quando nao existe token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { apiClient } = await import("./apiClient");

    await apiClient.get("/api/v1/health");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.interna.test/api/v1/health",
      {
        headers: {},
        method: "GET",
      },
    );
  });

  it("normaliza 401, 403 e erro de rede", async () => {
    const {
      ApiAccessDeniedError,
      ApiNetworkError,
      ApiSessionExpiredError,
      apiClient,
    } = await import("./apiClient");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 401 })),
    );
    await expect(apiClient.get("/api/v1/companies")).rejects.toBeInstanceOf(
      ApiSessionExpiredError,
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 403 })),
    );
    await expect(apiClient.get("/api/v1/companies")).rejects.toBeInstanceOf(
      ApiAccessDeniedError,
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(apiClient.get("/api/v1/companies")).rejects.toBeInstanceOf(
      ApiNetworkError,
    );
  });

  it("preserva mensagem segura de validacao enviada pelo backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: "Arquivo precisa estar em formato XLSX." }),
          {
            status: 422,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );
    const { ApiValidationError, apiClient } = await import("./apiClient");

    await expect(
      apiClient.post("/api/v1/import", { body: {} }),
    ).rejects.toMatchObject({
      name: "ApiValidationError",
      message: "Arquivo precisa estar em formato XLSX.",
    });
    await expect(
      apiClient.post("/api/v1/import", { body: {} }),
    ).rejects.toBeInstanceOf(ApiValidationError);
  });

  it("prioriza mensagem do envelope canonico e tolera detail legado", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "validation_error",
            message: "Mensagem segura do envelope.",
            details: {},
            request_id: "req-frontend-1",
            detail: "Mensagem legada.",
          }),
          {
            status: 400,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );
    const { apiClient } = await import("./apiClient");

    await expect(
      apiClient.post("/api/v1/import", { body: {} }),
    ).rejects.toMatchObject({
      name: "ApiValidationError",
      message: "Mensagem segura do envelope.",
    });
  });
});

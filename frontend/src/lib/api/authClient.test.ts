import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("authClient", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("VITE_API_BASE_URL", "/api");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("envia o login para a rota versionada da API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "jwt-de-teste",
          token_type: "bearer",
          expires_in: 43_200,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { authClient } = await import("./authClient");

    await expect(
      authClient.login({
        email: "operador.hml",
        password: "senha-segura",
      }),
    ).resolves.toEqual({
      accessToken: "jwt-de-teste",
      userEmail: "operador.hml",
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        login: "operador.hml",
        senha: "senha-segura",
      }),
    });
  });
});

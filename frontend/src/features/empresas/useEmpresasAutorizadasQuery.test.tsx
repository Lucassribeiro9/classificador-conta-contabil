import { waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { empresasClient } from "../../lib/api/empresasClient";
import { queryKeys } from "../../lib/queryKeys";
import { renderHookWithProviders } from "../../test/testUtils";
import { useEmpresasAutorizadasQuery } from "./useEmpresasAutorizadasQuery";

vi.mock("../../lib/api/empresasClient", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../lib/api/empresasClient")>();

  return {
    ...actual,
    empresasClient: {
      list: vi.fn(),
    },
  };
});

const listEmpresasMock = vi.mocked(empresasClient.list);

describe("useEmpresasAutorizadasQuery", () => {
  beforeEach(() => {
    listEmpresasMock.mockReset();
  });

  it("usa query key padronizada e expoe loading antes do sucesso", async () => {
    listEmpresasMock.mockResolvedValueOnce([
      {
        id: 7,
        nome: "Comercial Alfa LTDA",
        documento: "12.345.678/0001-90",
        papel: "operador",
      },
    ]);

    const { result } = renderHookWithProviders(() =>
      useEmpresasAutorizadasQuery("jwt-de-teste"),
    );

    expect(result.current.queryKey).toEqual(queryKeys.empresas.autorizadas());
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(listEmpresasMock).toHaveBeenCalledWith("jwt-de-teste");
    expect(result.current.data).toEqual([
      {
        id: 7,
        nome: "Comercial Alfa LTDA",
        documento: "12.345.678/0001-90",
        papel: "operador",
      },
    ]);
  });

  it("mantem query desabilitada sem token de sessao", () => {
    const { result } = renderHookWithProviders(() =>
      useEmpresasAutorizadasQuery(""),
    );

    expect(result.current.queryKey).toEqual(queryKeys.empresas.autorizadas());
    expect(result.current.fetchStatus).toBe("idle");
    expect(listEmpresasMock).not.toHaveBeenCalled();
  });

  it("expoe erro normalizado pelo service", async () => {
    const error = new Error("Falha operacional");
    listEmpresasMock.mockRejectedValueOnce(error);

    const { result } = renderHookWithProviders(() =>
      useEmpresasAutorizadasQuery("jwt-de-teste"),
    );

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });
});

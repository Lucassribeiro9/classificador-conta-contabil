import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../app/auth";
import {
  ImportarMovimentosBlockedError,
  ImportarMovimentosNetworkError,
  importarMovimentosClient,
} from "../../lib/api/importarMovimentosClient";
import { ROUTES } from "../paths";
import { ImportarMovimentosPage } from "./ImportarMovimentosPage";
import { LoteMovimentosPage } from "./LoteMovimentosPage";

vi.mock("../../lib/api/importarMovimentosClient", async (importOriginal) => {
  const actual =
    await importOriginal<
      typeof import("../../lib/api/importarMovimentosClient")
    >();

  return {
    ...actual,
    importarMovimentosClient: {
      importar: vi.fn(),
    },
  };
});

const importarMock = vi.mocked(importarMovimentosClient.importar);

function renderImportarMovimentosPage(accessToken = "jwt-de-teste") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider
        initialSession={{
          accessToken,
          userEmail: "operador@interno.test",
        }}
      >
        <MemoryRouter initialEntries={[ROUTES.empresa.importarMovimentos("7")]}>
          <Routes>
            <Route
              path={ROUTES.empresa.importarMovimentosPath}
              element={<ImportarMovimentosPage />}
            />
            <Route
              path={ROUTES.empresa.loteMovimentosPath}
              element={<LoteMovimentosPage />}
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("ImportarMovimentosPage", () => {
  beforeEach(() => {
    importarMock.mockReset();
  });

  it("bloqueia arquivo que nao seja xlsx antes de chamar a API", async () => {
    renderImportarMovimentosPage();

    fireEvent.change(screen.getByLabelText("Arquivo .xlsx"), {
      target: {
        files: [new File(["csv"], "movimentos.csv", { type: "text/csv" })],
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Importar arquivo" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Selecione um arquivo .xlsx.",
    );
    expect(importarMock).not.toHaveBeenCalled();
  });

  it("envia xlsx, mostra resumo do lote e permite abrir o lote", async () => {
    importarMock.mockResolvedValueOnce({
      loteId: 31,
      status: "completed",
      totalLinhas: 12,
      totalImportadas: 12,
      totalInvalidas: 0,
      warnings: [],
    });
    const file = new File(["xlsx"], "movimentos.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    renderImportarMovimentosPage();

    fireEvent.change(screen.getByLabelText("Arquivo .xlsx"), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Importar arquivo" }));

    expect(
      await screen.findByRole("heading", { name: "Importacao concluida" }),
    ).toBeInTheDocument();
    expect(importarMock).toHaveBeenCalledWith("jwt-de-teste", "7", file);
    expect(screen.getByText("12 linhas lidas")).toBeInTheDocument();
    expect(screen.getByText("12 movimentos importados")).toBeInTheDocument();
    expect(screen.getByText("0 bloqueios")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Abrir lote" }));
    expect(
      await screen.findByRole("heading", { name: "Lote de Movimentos" }),
    ).toBeInTheDocument();
  });

  it("exibe warnings e bloqueios retornados pela importacao", async () => {
    importarMock.mockResolvedValueOnce({
      loteId: 32,
      status: "completed_with_warnings",
      totalLinhas: 28,
      totalImportadas: 26,
      totalInvalidas: 2,
      warnings: ["Linha 8 sem contrapartida.", "Linha 13 ignorada."],
    });

    renderImportarMovimentosPage();

    fireEvent.change(screen.getByLabelText("Arquivo .xlsx"), {
      target: { files: [new File(["xlsx"], "movimentos.xlsx")] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Importar arquivo" }));

    expect(
      await screen.findByRole("heading", { name: "Importacao com warnings" }),
    ).toBeInTheDocument();
    expect(screen.getByText("26 movimentos importados")).toBeInTheDocument();
    expect(screen.getByText("2 bloqueios")).toBeInTheDocument();
    expect(screen.getByText("Linha 8 sem contrapartida.")).toBeInTheDocument();
  });

  it("trata importacao bloqueada e erro de rede com mensagens operacionais", async () => {
    importarMock.mockRejectedValueOnce(
      new ImportarMovimentosBlockedError("Arquivo deve ser .xlsx"),
    );

    renderImportarMovimentosPage();

    fireEvent.change(screen.getByLabelText("Arquivo .xlsx"), {
      target: { files: [new File(["xlsx"], "movimentos.xlsx")] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Importar arquivo" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Arquivo deve ser .xlsx",
    );

    importarMock.mockRejectedValueOnce(new ImportarMovimentosNetworkError());
    fireEvent.click(screen.getByRole("button", { name: "Importar arquivo" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Nao foi possivel conectar a API interna.",
    );
  });
});

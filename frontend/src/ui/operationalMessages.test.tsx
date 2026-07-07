import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  PageState,
  getImportStatusMessage,
  operationalMessages,
} from "./operationalMessages";

describe("operationalMessages", () => {
  it("cobre estados obrigatorios da spec 09 com mensagens curtas e acionaveis", () => {
    expect(operationalMessages.loading.empresas).toEqual({
      title: "Carregando empresas",
      description: "Buscando empresas liberadas para o seu usuario.",
    });
    expect(operationalMessages.empty.semEmpresas).toEqual({
      title: "Sem empresas vinculadas",
      description: "Contate o administrador para liberar seu acesso.",
    });
    expect(operationalMessages.error.network).toEqual({
      title: "Conexao indisponivel",
      description: "Verifique a API interna e tente novamente.",
    });
    expect(operationalMessages.accessDenied.default).toEqual({
      title: "Acesso negado",
      description: "Seu usuario nao tem permissao para esta acao.",
    });
    expect(operationalMessages.sessionExpired.login).toEqual({
      title: "Sessao expirada",
      description: "Entre novamente para continuar.",
    });
  });

  it("distingue importacao concluida, com warnings e bloqueada", () => {
    expect(getImportStatusMessage({ status: "completed", warnings: [] })).toEqual({
      title: "Importacao concluida",
      description: "Abra o lote ou importe outro arquivo.",
    });
    expect(
      getImportStatusMessage({
        status: "completed_with_warnings",
        warnings: ["Linha ignorada."],
      }),
    ).toEqual({
      title: "Importacao com warnings",
      description: "Revise os avisos antes de abrir o lote.",
    });
    expect(
      getImportStatusMessage({ status: "blocked", warnings: [] }),
    ).toEqual({
      title: "Importacao bloqueada",
      description: "Corrija o arquivo e tente novamente.",
    });
  });
});

describe("PageState", () => {
  it("renderiza estado reutilizavel com semantica operacional", () => {
    render(
      <PageState
        message={operationalMessages.accessDenied.default}
        titleAs="h2"
      />,
    );

    expect(
      screen.getByRole("heading", { level: 2, name: "Acesso negado" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Seu usuario nao tem permissao para esta acao."),
    ).toBeInTheDocument();
  });
});

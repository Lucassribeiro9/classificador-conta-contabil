import type { ElementType } from "react";

export type OperationalMessage = {
  title: string;
  description: string;
};

export const operationalMessages = {
  loading: {
    empresas: {
      title: "Carregando empresas",
      description: "Buscando empresas liberadas para o seu usuario.",
    },
    operacao: {
      title: "Carregando operacao",
      description: "Buscando resumo da empresa e dados do modelo.",
    },
    lote: {
      title: "Carregando lote",
      description: "Buscando movimentos e status de revisao.",
    },
    movimento: {
      title: "Carregando movimento",
      description: "Buscando dados, sugestao e historico.",
    },
    razao: {
      title: "Carregando razao",
      description: "Buscando lotes importados e dados de apoio.",
    },
  },
  empty: {
    semEmpresas: {
      title: "Sem empresas vinculadas",
      description: "Contate o administrador para liberar seu acesso.",
    },
    empresaNaoEncontrada: {
      title: "Empresa nao encontrada",
      description: "Volte para Empresas e selecione um cliente disponivel.",
    },
    semRazao: {
      title: "Sem razao importado",
      description: "Importe um lote de razao para consultar lancamentos.",
    },
    semMovimentosFiltro: {
      title: "Sem movimentos neste filtro",
      description: "Altere o status para consultar outros movimentos.",
    },
    semLancamentosFiltro: {
      title: "Sem lancamentos neste filtro",
      description: "Ajuste a busca para consultar o lote.",
    },
  },
  error: {
    network: {
      title: "Conexao indisponivel",
      description: "Verifique a API interna e tente novamente.",
    },
    empresas: {
      title: "Nao foi possivel carregar empresas",
      description: "Verifique a API interna e tente novamente.",
    },
    operacao: {
      title: "Nao foi possivel carregar a operacao",
      description: "Verifique a API interna e tente novamente.",
    },
    lote: {
      title: "Nao foi possivel carregar o lote",
      description: "Verifique a API interna e tente novamente.",
    },
    movimento: {
      title: "Nao foi possivel carregar o movimento",
      description: "Verifique a API interna e tente novamente.",
    },
    razao: {
      title: "Nao foi possivel carregar o razao",
      description: "Verifique a API interna e tente novamente.",
    },
    lancamentos: {
      title: "Nao foi possivel carregar os lancamentos",
      description: "Verifique a API interna e tente novamente.",
    },
  },
  accessDenied: {
    default: {
      title: "Acesso negado",
      description: "Seu usuario nao tem permissao para esta acao.",
    },
    empresas: {
      title: "Acesso negado",
      description: "Seu usuario nao pode consultar empresas.",
    },
    empresa: {
      title: "Acesso negado",
      description: "Seu usuario nao pode consultar esta empresa.",
    },
    lote: {
      title: "Acesso negado",
      description: "Seu usuario nao pode consultar este lote.",
    },
    movimento: {
      title: "Acesso negado",
      description: "Seu usuario nao pode revisar este movimento.",
    },
    razao: {
      title: "Acesso negado",
      description: "Seu usuario nao pode consultar o razao desta empresa.",
    },
    lancamentos: {
      title: "Acesso negado",
      description: "Seu usuario nao pode consultar os lancamentos deste lote.",
    },
  },
  sessionExpired: {
    login: {
      title: "Sessao expirada",
      description: "Entre novamente para continuar.",
    },
    unavailable: {
      title: "Sessao indisponivel",
      description: "Entre novamente para continuar.",
    },
  },
  importacao: {
    completed: {
      title: "Importacao concluida",
      description: "Abra o lote ou importe outro arquivo.",
    },
    completedWithWarnings: {
      title: "Importacao com warnings",
      description: "Revise os avisos antes de abrir o lote.",
    },
    blocked: {
      title: "Importacao bloqueada",
      description: "Corrija o arquivo e tente novamente.",
    },
  },
} as const;

type ImportStatusInput = {
  status: string;
  warnings: string[];
};

export function getImportStatusMessage({
  status,
  warnings,
}: ImportStatusInput): OperationalMessage {
  if (status === "blocked" || status === "failed") {
    return operationalMessages.importacao.blocked;
  }

  if (status === "completed_with_warnings" || warnings.length) {
    return operationalMessages.importacao.completedWithWarnings;
  }

  return operationalMessages.importacao.completed;
}

export function PageState({
  message,
  titleAs: Title = "h1",
}: {
  message: OperationalMessage;
  titleAs?: ElementType;
}) {
  return (
    <section className="border border-slate-200 bg-white p-6 shadow-sm">
      <Title className="text-lg font-semibold text-slate-950">
        {message.title}
      </Title>
      <p className="mt-2 max-w-2xl text-sm text-slate-600">
        {message.description}
      </p>
    </section>
  );
}

import { isDemoPreviewToken } from "../demoPreview";

export type StatusMovimentoFiltro =
  | "todos"
  | "pendente"
  | "pre_classificado"
  | "sugerido"
  | "revisao"
  | "aprovado"
  | "rejeitado";

export type MovimentoOperacional = {
  id: number;
  loteId: number;
  empresaId: number;
  data: string;
  contaFinanceira: number;
  historicoNormalizado: string;
  valorAbsoluto: string;
  direcao: string;
  tipoMovimento: string | null;
  contrapartidaInformada: number | null;
  contrapartidaSugerida: number | null;
  contrapartidaFinal: number | null;
  confidenceSugerida: number | null;
  status: string;
  elegivelTreino: boolean;
  mensagensValidacao: string[];
};

export type MovimentoOperacionalList = {
  items: MovimentoOperacional[];
  total: number;
  page: number;
  limit: number;
  hasNext: boolean;
};

export type ReviewMovimentoRequest = {
  movimentoId: number;
  action: "approve" | "reject";
  contaFinal?: number;
};

export type ReviewBatchResult = {
  successCount: number;
  failureCount: number;
  failures: Array<{ movimentoId: number; message: string }>;
};

export type ClassificacaoPendentesResult = {
  empresaId: number;
  quantidadeProcessada: number;
  totalSugerido: number;
  totalRevisao: number;
};

type MovimentoOperacionalApi = {
  id: number;
  lote_id: number;
  empresa_id: number;
  data: string;
  conta_financeira: number;
  historico_normalizado: string;
  valor_absoluto: string;
  direcao: string;
  tipo_movimento: string | null;
  contrapartida_informada: number | null;
  contrapartida_sugerida: number | null;
  contrapartida_final: number | null;
  confidence_sugerida: number | null;
  status: string;
  elegivel_treino: boolean;
  mensagens_validacao: string[];
};

type MovimentoOperacionalListApi = {
  items: MovimentoOperacionalApi[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
};

type ClassificacaoPendentesApi = {
  empresa_id: number;
  quantidade_processada: number;
  total_sugerido: number;
  total_revisao: number;
};

type ErrorResponse = {
  detail?: string;
};

export class LoteMovimentosAccessDeniedError extends Error {
  constructor() {
    super("Acesso negado");
    this.name = "LoteMovimentosAccessDeniedError";
  }
}

export class LoteMovimentosNetworkError extends Error {
  constructor() {
    super("Nao foi possivel carregar os movimentos.");
    this.name = "LoteMovimentosNetworkError";
  }
}

export class LoteMovimentosSessionExpiredError extends Error {
  constructor() {
    super("Sessao expirada");
    this.name = "LoteMovimentosSessionExpiredError";
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function authHeaders(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}` };
}

function jsonHeaders(accessToken: string) {
  return {
    ...authHeaders(accessToken),
    "Content-Type": "application/json",
  };
}

async function parseErrorDetail(response: Response) {
  try {
    const data = (await response.json()) as ErrorResponse;
    return data.detail ?? "Acao nao concluida.";
  } catch {
    return "Acao nao concluida.";
  }
}

async function fetchJson<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: init?.headers ?? authHeaders(accessToken),
    });
  } catch {
    throw new LoteMovimentosNetworkError();
  }

  if (response.status === 401) {
    throw new LoteMovimentosSessionExpiredError();
  }

  if (response.status === 403) {
    throw new LoteMovimentosAccessDeniedError();
  }

  if (!response.ok) {
    throw new LoteMovimentosNetworkError();
  }

  return (await response.json()) as T;
}

function mapMovimento(data: MovimentoOperacionalApi): MovimentoOperacional {
  return {
    id: data.id,
    loteId: data.lote_id,
    empresaId: data.empresa_id,
    data: data.data,
    contaFinanceira: data.conta_financeira,
    historicoNormalizado: data.historico_normalizado,
    valorAbsoluto: data.valor_absoluto,
    direcao: data.direcao,
    tipoMovimento: data.tipo_movimento,
    contrapartidaInformada: data.contrapartida_informada,
    contrapartidaSugerida: data.contrapartida_sugerida,
    contrapartidaFinal: data.contrapartida_final,
    confidenceSugerida: data.confidence_sugerida,
    status: data.status,
    elegivelTreino: data.elegivel_treino,
    mensagensValidacao: data.mensagens_validacao,
  };
}

function mapList(data: MovimentoOperacionalListApi): MovimentoOperacionalList {
  return {
    items: data.items.map(mapMovimento),
    total: data.total,
    page: data.page,
    limit: data.limit,
    hasNext: data.has_next,
  };
}

function mapClassificacao(
  data: ClassificacaoPendentesApi,
): ClassificacaoPendentesResult {
  return {
    empresaId: data.empresa_id,
    quantidadeProcessada: data.quantidade_processada,
    totalSugerido: data.total_sugerido,
    totalRevisao: data.total_revisao,
  };
}

function demoMovimentos(): MovimentoOperacionalList {
  return {
    total: 5,
    page: 1,
    limit: 100,
    hasNext: false,
    items: [
      {
        id: 93,
        loteId: 15,
        empresaId: 7,
        data: "2026-01-05",
        contaFinanceira: 10046,
        historicoNormalizado: "tarifa bancaria",
        valorAbsoluto: "32.10",
        direcao: "credito",
        tipoMovimento: "saida",
        contrapartidaInformada: 30001,
        contrapartidaSugerida: null,
        contrapartidaFinal: null,
        confidenceSugerida: null,
        status: "pendente",
        elegivelTreino: false,
        mensagensValidacao: [],
      },
      {
        id: 91,
        loteId: 15,
        empresaId: 7,
        data: "2026-01-03",
        contaFinanceira: 10046,
        historicoNormalizado: "pagamento fornecedor",
        valorAbsoluto: "250.75",
        direcao: "credito",
        tipoMovimento: "saida",
        contrapartidaInformada: null,
        contrapartidaSugerida: 20001,
        contrapartidaFinal: null,
        confidenceSugerida: 0.91,
        status: "pre_classificado",
        elegivelTreino: false,
        mensagensValidacao: [],
      },
      {
        id: 92,
        loteId: 15,
        empresaId: 7,
        data: "2026-01-04",
        contaFinanceira: 10046,
        historicoNormalizado: "transferencia sem contrapartida",
        valorAbsoluto: "100.00",
        direcao: "credito",
        tipoMovimento: "transferencia",
        contrapartidaInformada: null,
        contrapartidaSugerida: null,
        contrapartidaFinal: null,
        confidenceSugerida: null,
        status: "revisao",
        elegivelTreino: false,
        mensagensValidacao: ["Tipo transferencia exige contrapartida."],
      },
      {
        id: 94,
        loteId: 15,
        empresaId: 7,
        data: "2026-01-06",
        contaFinanceira: 10046,
        historicoNormalizado: "recebimento cliente",
        valorAbsoluto: "900.00",
        direcao: "debito",
        tipoMovimento: "entrada",
        contrapartidaInformada: null,
        contrapartidaSugerida: null,
        contrapartidaFinal: 40001,
        confidenceSugerida: null,
        status: "aprovado",
        elegivelTreino: true,
        mensagensValidacao: [],
      },
      {
        id: 95,
        loteId: 15,
        empresaId: 7,
        data: "2026-01-07",
        contaFinanceira: 10046,
        historicoNormalizado: "movimento duplicado",
        valorAbsoluto: "10.00",
        direcao: "credito",
        tipoMovimento: "saida",
        contrapartidaInformada: null,
        contrapartidaSugerida: null,
        contrapartidaFinal: null,
        confidenceSugerida: null,
        status: "rejeitado",
        elegivelTreino: false,
        mensagensValidacao: [],
      },
    ],
  };
}

async function listMovimentos(
  accessToken: string,
  empresaId: string,
  loteId: string,
  status: StatusMovimentoFiltro = "todos",
): Promise<MovimentoOperacionalList> {
  if (isDemoPreviewToken(accessToken)) {
    const list = demoMovimentos();
    if (status === "todos") return list;
    return {
      ...list,
      items: list.items.filter((item) => item.status === status),
      total: list.items.filter((item) => item.status === status).length,
    };
  }

  const params = new URLSearchParams({ limit: "100" });
  if (status !== "todos") {
    params.set("status", status);
  }

  const data = await fetchJson<MovimentoOperacionalListApi>(
    `/api/v1/companies/${empresaId}/movimentos-operacionais/lotes/${loteId}/movimentos?${params.toString()}`,
    accessToken,
  );
  return mapList(data);
}

async function reviewMovimentos(
  accessToken: string,
  empresaId: string,
  loteId: string,
  requests: ReviewMovimentoRequest[],
): Promise<ReviewBatchResult> {
  if (isDemoPreviewToken(accessToken)) {
    return { successCount: requests.length, failureCount: 0, failures: [] };
  }

  const failures: ReviewBatchResult["failures"] = [];
  let successCount = 0;

  for (const request of requests) {
    const body =
      request.action === "approve"
        ? { action: request.action, conta_final: request.contaFinal }
        : { action: request.action };

    let response: Response;
    try {
      response = await fetch(
        `${API_BASE_URL}/api/v1/companies/${empresaId}/movimentos-operacionais/lotes/${loteId}/movimentos/${request.movimentoId}/review`,
        {
          method: "POST",
          headers: jsonHeaders(accessToken),
          body: JSON.stringify(body),
        },
      );
    } catch {
      failures.push({
        movimentoId: request.movimentoId,
        message: "Nao foi possivel conectar a API interna.",
      });
      continue;
    }

    if (response.ok) {
      successCount += 1;
    } else {
      failures.push({
        movimentoId: request.movimentoId,
        message: await parseErrorDetail(response),
      });
    }
  }

  return {
    successCount,
    failureCount: failures.length,
    failures,
  };
}

async function classificarPendentes(
  accessToken: string,
  empresaId: string,
): Promise<ClassificacaoPendentesResult> {
  if (isDemoPreviewToken(accessToken)) {
    return {
      empresaId: Number(empresaId) || 7,
      quantidadeProcessada: 2,
      totalSugerido: 1,
      totalRevisao: 1,
    };
  }

  const data = await fetchJson<ClassificacaoPendentesApi>(
    `/api/v1/companies/${empresaId}/movimentos-operacionais/classificar`,
    accessToken,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  return mapClassificacao(data);
}

export const loteMovimentosClient = {
  classificarPendentes,
  listMovimentos,
  reviewMovimentos,
};

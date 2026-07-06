import { isDemoPreviewToken } from "../demoPreview";

export type MovimentoRevisao = {
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

export type ContaContabilResumo = {
  id: number;
  codigo: number;
  classificacao: string;
  nome: string;
  tipo: string;
  isActive: boolean;
  isFinancialOrigin: boolean;
};

export type RevisaoMovimentoRequest = {
  action: "approve" | "correct" | "reject";
  contaFinal?: number;
};

type MovimentoRevisaoApi = {
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

type MovimentoRevisaoListApi = {
  items: MovimentoRevisaoApi[];
};

type ContaContabilApi = {
  id: number;
  codigo: number;
  classificacao: string;
  nome: string;
  tipo: string;
  is_active: boolean;
  is_financial_origin: boolean;
};

export class RevisarMovimentoAccessDeniedError extends Error {
  constructor() {
    super("Acesso negado");
    this.name = "RevisarMovimentoAccessDeniedError";
  }
}

export class RevisarMovimentoNetworkError extends Error {
  constructor() {
    super("Nao foi possivel carregar o movimento.");
    this.name = "RevisarMovimentoNetworkError";
  }
}

export class RevisarMovimentoSessionExpiredError extends Error {
  constructor() {
    super("Sessao expirada");
    this.name = "RevisarMovimentoSessionExpiredError";
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
    throw new RevisarMovimentoNetworkError();
  }

  if (response.status === 401) {
    throw new RevisarMovimentoSessionExpiredError();
  }

  if (response.status === 403) {
    throw new RevisarMovimentoAccessDeniedError();
  }

  if (!response.ok) {
    throw new RevisarMovimentoNetworkError();
  }

  return (await response.json()) as T;
}

function mapMovimento(data: MovimentoRevisaoApi): MovimentoRevisao {
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

function mapConta(data: ContaContabilApi): ContaContabilResumo {
  return {
    id: data.id,
    codigo: data.codigo,
    classificacao: data.classificacao,
    nome: data.nome,
    tipo: data.tipo,
    isActive: data.is_active,
    isFinancialOrigin: data.is_financial_origin,
  };
}

function demoMovimento(): MovimentoRevisao {
  return {
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
    mensagensValidacao: ["Conferencia humana obrigatoria."],
  };
}

function demoContas(): ContaContabilResumo[] {
  return [
    {
      id: 3,
      codigo: 20001,
      classificacao: "2.0.0",
      nome: "Fornecedores nacionais",
      tipo: "A",
      isActive: true,
      isFinancialOrigin: false,
    },
    {
      id: 4,
      codigo: 30001,
      classificacao: "3.0.0",
      nome: "Servicos tomados",
      tipo: "A",
      isActive: true,
      isFinancialOrigin: false,
    },
  ];
}

async function getMovimento(
  accessToken: string,
  empresaId: string,
  loteId: string,
  movimentoId: string,
): Promise<MovimentoRevisao> {
  if (isDemoPreviewToken(accessToken)) {
    return demoMovimento();
  }

  const data = await fetchJson<MovimentoRevisaoListApi>(
    `/api/v1/companies/${empresaId}/movimentos-operacionais/lotes/${loteId}/movimentos?limit=100`,
    accessToken,
  );
  const movimento = data.items.find((item) => String(item.id) === movimentoId);

  if (!movimento) {
    throw new RevisarMovimentoNetworkError();
  }

  return mapMovimento(movimento);
}

async function searchContas(
  accessToken: string,
  query: string,
): Promise<ContaContabilResumo[]> {
  if (isDemoPreviewToken(accessToken)) {
    const normalized = query.trim().toLowerCase();
    return demoContas().filter(
      (conta) =>
        String(conta.codigo).includes(normalized) ||
        conta.nome.toLowerCase().includes(normalized),
    );
  }

  const params = new URLSearchParams();
  const trimmedQuery = query.trim();
  if (/^\d+$/.test(trimmedQuery)) {
    params.set("codigo", trimmedQuery);
  } else {
    params.set("nome", trimmedQuery);
  }

  const data = await fetchJson<ContaContabilApi[]>(
    `/api/v1/plano-contas?${params.toString()}`,
    accessToken,
  );
  return data.map(mapConta);
}

async function reviewMovimento(
  accessToken: string,
  empresaId: string,
  loteId: string,
  movimentoId: string,
  request: RevisaoMovimentoRequest,
): Promise<MovimentoRevisao> {
  if (isDemoPreviewToken(accessToken)) {
    return {
      ...demoMovimento(),
      contrapartidaFinal: request.contaFinal ?? null,
      status: request.action === "reject" ? "rejeitado" : "aprovado",
    };
  }

  const body =
    request.action === "reject"
      ? { action: request.action }
      : { action: request.action, conta_final: request.contaFinal };

  const data = await fetchJson<MovimentoRevisaoApi>(
    `/api/v1/companies/${empresaId}/movimentos-operacionais/lotes/${loteId}/movimentos/${movimentoId}/review`,
    accessToken,
    {
      method: "POST",
      headers: jsonHeaders(accessToken),
      body: JSON.stringify(body),
    },
  );
  return mapMovimento(data);
}

export const revisarMovimentoClient = {
  getMovimento,
  reviewMovimento,
  searchContas,
};

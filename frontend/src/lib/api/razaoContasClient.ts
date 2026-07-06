import { isDemoPreviewToken } from "../demoPreview";

export type PaginatedResult<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasNext: boolean;
};

export type LoteRazaoResumo = {
  id: number;
  empresaId: number;
  originalFilename: string;
  status: string;
  totalLinhas: number;
  totalImportadas: number;
  totalInvalidas: number;
  createdAt: string;
};

export type LancamentoRazaoResumo = {
  id: number;
  loteId: number;
  empresaId: number;
  numeroLancamento: string;
  data: string;
  contaOrigem: number;
  contaContrapartida: number;
  contaDebito: number;
  contaCredito: number;
  direcao: string;
  historicoNormalizado: string;
  valor: string;
};

type PaginatedApi<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
};

type LoteRazaoApi = {
  id: number;
  empresa_id: number;
  original_filename: string;
  status: string;
  total_linhas: number;
  total_importadas: number;
  total_invalidas: number;
  created_at: string;
};

type LancamentoRazaoApi = {
  id: number;
  lote_id: number;
  empresa_id: number;
  numero_lancamento: string;
  data: string;
  conta_origem: number;
  conta_contrapartida: number;
  conta_debito: number;
  conta_credito: number;
  direcao: string;
  historico_normalizado: string;
  valor: string;
};

export class RazaoContasAccessDeniedError extends Error {
  constructor() {
    super("Acesso negado");
    this.name = "RazaoContasAccessDeniedError";
  }
}

export class RazaoContasNetworkError extends Error {
  constructor() {
    super("Nao foi possivel carregar o razao.");
    this.name = "RazaoContasNetworkError";
  }
}

export class RazaoContasSessionExpiredError extends Error {
  constructor() {
    super("Sessao expirada");
    this.name = "RazaoContasSessionExpiredError";
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const PAGE_LIMIT = 10;

function authHeaders(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}` };
}

async function fetchJson<T>(path: string, accessToken: string): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: authHeaders(accessToken),
    });
  } catch {
    throw new RazaoContasNetworkError();
  }

  if (response.status === 401) {
    throw new RazaoContasSessionExpiredError();
  }

  if (response.status === 403) {
    throw new RazaoContasAccessDeniedError();
  }

  if (!response.ok) {
    throw new RazaoContasNetworkError();
  }

  return (await response.json()) as T;
}

function mapPaginated<TApi, TModel>(
  data: PaginatedApi<TApi>,
  mapper: (item: TApi) => TModel,
): PaginatedResult<TModel> {
  return {
    items: data.items.map(mapper),
    total: data.total,
    page: data.page,
    limit: data.limit,
    hasNext: data.has_next,
  };
}

function mapLote(data: LoteRazaoApi): LoteRazaoResumo {
  return {
    id: data.id,
    empresaId: data.empresa_id,
    originalFilename: data.original_filename,
    status: data.status,
    totalLinhas: data.total_linhas,
    totalImportadas: data.total_importadas,
    totalInvalidas: data.total_invalidas,
    createdAt: data.created_at,
  };
}

function mapLancamento(data: LancamentoRazaoApi): LancamentoRazaoResumo {
  return {
    id: data.id,
    loteId: data.lote_id,
    empresaId: data.empresa_id,
    numeroLancamento: data.numero_lancamento,
    data: data.data,
    contaOrigem: data.conta_origem,
    contaContrapartida: data.conta_contrapartida,
    contaDebito: data.conta_debito,
    contaCredito: data.conta_credito,
    direcao: data.direcao,
    historicoNormalizado: data.historico_normalizado,
    valor: data.valor,
  };
}

function demoLotes(): PaginatedResult<LoteRazaoResumo> {
  return {
    items: [
      {
        id: 15,
        empresaId: 7,
        originalFilename: "razao-demo.xlsx",
        status: "completed",
        totalLinhas: 12,
        totalImportadas: 11,
        totalInvalidas: 1,
        createdAt: "2026-01-04T10:00:00",
      },
      {
        id: 14,
        empresaId: 7,
        originalFilename: "razao-demo-warnings.xlsx",
        status: "completed_with_warnings",
        totalLinhas: 8,
        totalImportadas: 7,
        totalInvalidas: 1,
        createdAt: "2026-01-03T10:00:00",
      },
    ],
    total: 2,
    page: 1,
    limit: PAGE_LIMIT,
    hasNext: false,
  };
}

function demoLancamentos(): PaginatedResult<LancamentoRazaoResumo> {
  return {
    items: [
      {
        id: 101,
        loteId: 15,
        empresaId: 7,
        numeroLancamento: "42",
        data: "2026-01-02",
        contaOrigem: 10046,
        contaContrapartida: 20001,
        contaDebito: 10046,
        contaCredito: 20001,
        direcao: "debito",
        historicoNormalizado: "pagamento fornecedor",
        valor: "250.75",
      },
      {
        id: 102,
        loteId: 15,
        empresaId: 7,
        numeroLancamento: "43",
        data: "2026-01-03",
        contaOrigem: 10046,
        contaContrapartida: 30001,
        contaDebito: 30001,
        contaCredito: 10046,
        direcao: "credito",
        historicoNormalizado: "recebimento cliente",
        valor: "900.00",
      },
    ],
    total: 2,
    page: 1,
    limit: PAGE_LIMIT,
    hasNext: false,
  };
}

async function listLotes(
  accessToken: string,
  empresaId: string,
  page: number,
): Promise<PaginatedResult<LoteRazaoResumo>> {
  if (isDemoPreviewToken(accessToken)) {
    return demoLotes();
  }

  const params = new URLSearchParams({
    page: String(page),
    limit: String(PAGE_LIMIT),
  });
  const data = await fetchJson<PaginatedApi<LoteRazaoApi>>(
    `/api/v1/companies/${empresaId}/razao/lotes?${params.toString()}`,
    accessToken,
  );
  return mapPaginated(data, mapLote);
}

async function listLancamentos(
  accessToken: string,
  empresaId: string,
  loteId: string,
  page: number,
): Promise<PaginatedResult<LancamentoRazaoResumo>> {
  if (isDemoPreviewToken(accessToken)) {
    return demoLancamentos();
  }

  const params = new URLSearchParams({
    page: String(page),
    limit: String(PAGE_LIMIT),
  });
  const data = await fetchJson<PaginatedApi<LancamentoRazaoApi>>(
    `/api/v1/companies/${empresaId}/razao/lotes/${loteId}/lancamentos?${params.toString()}`,
    accessToken,
  );
  return mapPaginated(data, mapLancamento);
}

export const razaoContasClient = {
  listLancamentos,
  listLotes,
};

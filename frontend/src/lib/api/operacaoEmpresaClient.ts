import { isDemoPreviewToken } from "../demoPreview";

export type EmpresaHubResumo = {
  id: number;
  nome: string;
  documento?: string;
  papel?: string;
};

export type ModeloHubResumo = {
  status: string;
  treinavel: boolean;
  modeloExistente: boolean;
  podeClassificarMovimentos: boolean;
  datasetTotalLinhas: number;
};

export type LotesHubResumo = {
  totalLotes: number;
  totalLinhas: number;
  ultimoStatus?: string;
};

export type MovimentosHubResumo = LotesHubResumo & {
  ultimoLoteId?: number;
};

export type OperacaoEmpresaHub = {
  empresa: EmpresaHubResumo;
  ml: ModeloHubResumo;
  razao: LotesHubResumo;
  movimentos: MovimentosHubResumo;
  contasVinculadas: number | null;
};

type EmpresaApiResponse = {
  id: number;
  nome?: string;
  nome_empresa?: string;
  documento?: string;
  cnpj_cpf?: string;
  papel?: string;
  role?: string;
};

type MLStatusApiResponse = {
  status: string;
  treinavel: boolean;
  modelo_existente: boolean;
  pode_classificar_movimentos: boolean;
  dataset_total_linhas: number;
};

type LoteApiResponse = {
  id: number;
  status: string;
  total_linhas?: number;
  total_importadas?: number;
};

type LoteListApiResponse = {
  items: LoteApiResponse[];
  total: number;
};

export class OperacaoEmpresaAccessDeniedError extends Error {
  constructor() {
    super("Acesso negado");
    this.name = "OperacaoEmpresaAccessDeniedError";
  }
}

export class OperacaoEmpresaNetworkError extends Error {
  constructor() {
    super("Nao foi possivel carregar a operacao da empresa");
    this.name = "OperacaoEmpresaNetworkError";
  }
}

export class OperacaoEmpresaSessionExpiredError extends Error {
  constructor() {
    super("Sessao expirada");
    this.name = "OperacaoEmpresaSessionExpiredError";
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

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
    throw new OperacaoEmpresaNetworkError();
  }

  if (response.status === 401) {
    throw new OperacaoEmpresaSessionExpiredError();
  }

  if (response.status === 403) {
    throw new OperacaoEmpresaAccessDeniedError();
  }

  if (!response.ok) {
    throw new OperacaoEmpresaNetworkError();
  }

  return (await response.json()) as T;
}

function mapEmpresa(data: EmpresaApiResponse): EmpresaHubResumo {
  return {
    id: data.id,
    nome: data.nome ?? data.nome_empresa ?? `Empresa ${data.id}`,
    documento: data.documento ?? data.cnpj_cpf,
    papel: data.papel ?? data.role,
  };
}

function mapModelo(data: MLStatusApiResponse): ModeloHubResumo {
  return {
    status: data.status,
    treinavel: data.treinavel,
    modeloExistente: data.modelo_existente,
    podeClassificarMovimentos: data.pode_classificar_movimentos,
    datasetTotalLinhas: data.dataset_total_linhas,
  };
}

function mapLotes(data: LoteListApiResponse): LotesHubResumo {
  const ultimo = data.items[data.items.length - 1];
  return {
    totalLotes: data.total,
    totalLinhas: data.items.reduce(
      (total, lote) =>
        total + (lote.total_importadas ?? lote.total_linhas ?? 0),
      0,
    ),
    ultimoStatus: ultimo?.status,
  };
}

function mapMovimentos(data: LoteListApiResponse): MovimentosHubResumo {
  const lotes = mapLotes(data);
  return {
    ...lotes,
    ultimoLoteId: data.items[data.items.length - 1]?.id,
  };
}

async function getHub(
  accessToken: string,
  empresaId: string,
): Promise<OperacaoEmpresaHub> {
  if (isDemoPreviewToken(accessToken)) {
    return {
      empresa: {
        id: Number(empresaId) || 7,
        nome: "Comercial Alfa LTDA",
        documento: "12.345.678/0001-90",
        papel: "operador",
      },
      ml: {
        status: "modelo_pronto",
        treinavel: true,
        modeloExistente: true,
        podeClassificarMovimentos: true,
        datasetTotalLinhas: 42,
      },
      razao: {
        totalLotes: 2,
        totalLinhas: 180,
        ultimoStatus: "completed",
      },
      movimentos: {
        totalLotes: 1,
        totalLinhas: 28,
        ultimoLoteId: 15,
        ultimoStatus: "completed_with_warnings",
      },
      contasVinculadas: null,
    };
  }

  const [empresa, ml, razao, movimentos] = await Promise.all([
    fetchJson<EmpresaApiResponse>(
      `/api/v1/companies/${empresaId}`,
      accessToken,
    ),
    fetchJson<MLStatusApiResponse>(
      `/api/v1/companies/${empresaId}/ml/status`,
      accessToken,
    ),
    fetchJson<LoteListApiResponse>(
      `/api/v1/companies/${empresaId}/razao/lotes?limit=5`,
      accessToken,
    ),
    fetchJson<LoteListApiResponse>(
      `/api/v1/companies/${empresaId}/movimentos-operacionais/lotes?limit=5`,
      accessToken,
    ),
  ]);

  return {
    empresa: mapEmpresa(empresa),
    ml: mapModelo(ml),
    razao: mapLotes(razao),
    movimentos: mapMovimentos(movimentos),
    contasVinculadas: null,
  };
}

export const operacaoEmpresaClient = {
  getHub,
};

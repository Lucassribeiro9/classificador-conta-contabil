import { isDemoPreviewToken } from "../demoPreview";

export type EmpresaResumo = {
  id: number;
  nome: string;
  documento?: string;
  papel?: string;
  permissao?: string;
};

type EmpresaApiResponse = {
  id: number;
  nome?: string;
  nome_empresa?: string;
  documento?: string;
  cnpj_cpf?: string;
  papel?: string;
  permissao?: string;
  role?: string;
};

export class EmpresasAccessDeniedError extends Error {
  constructor() {
    super("Acesso negado");
    this.name = "EmpresasAccessDeniedError";
  }
}

export class EmpresasNetworkError extends Error {
  constructor() {
    super("Nao foi possivel carregar empresas");
    this.name = "EmpresasNetworkError";
  }
}

export class EmpresasSessionExpiredError extends Error {
  constructor() {
    super("Sessao expirada");
    this.name = "EmpresasSessionExpiredError";
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const EMPRESAS_PATH = "/api/v1/companies/authorized";
const DEMO_EMPRESAS: EmpresaResumo[] = [
  {
    id: 7,
    nome: "Comercial Alfa LTDA",
    documento: "12.345.678/0001-90",
    papel: "operador",
  },
];

function mapEmpresa(data: EmpresaApiResponse): EmpresaResumo {
  return {
    id: data.id,
    nome: data.nome ?? data.nome_empresa ?? `Empresa ${data.id}`,
    documento: data.documento ?? data.cnpj_cpf,
    papel: data.papel ?? data.role,
    permissao: data.permissao,
  };
}

async function list(accessToken: string): Promise<EmpresaResumo[]> {
  if (isDemoPreviewToken(accessToken)) {
    return DEMO_EMPRESAS;
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${EMPRESAS_PATH}`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  } catch {
    throw new EmpresasNetworkError();
  }

  if (response.status === 401) {
    throw new EmpresasSessionExpiredError();
  }

  if (response.status === 403) {
    throw new EmpresasAccessDeniedError();
  }

  if (!response.ok) {
    throw new EmpresasNetworkError();
  }

  const data = (await response.json()) as EmpresaApiResponse[];
  return data.map(mapEmpresa);
}

export const empresasClient = {
  list,
};

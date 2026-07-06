import { isDemoPreviewToken } from "../demoPreview";

export type ImportarMovimentosResumo = {
  loteId: number;
  status: string;
  totalLinhas: number;
  totalImportadas: number;
  totalInvalidas: number;
  warnings: string[];
};

type ImportarMovimentosApiResponse = {
  lote_id: number;
  status: string;
  total_linhas: number;
  total_importadas: number;
  total_invalidas: number;
  warnings: string[];
};

type ErrorResponse = {
  detail?: string;
};

export class ImportarMovimentosAccessDeniedError extends Error {
  constructor() {
    super("Acesso negado");
    this.name = "ImportarMovimentosAccessDeniedError";
  }
}

export class ImportarMovimentosBlockedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ImportarMovimentosBlockedError";
  }
}

export class ImportarMovimentosNetworkError extends Error {
  constructor() {
    super("Nao foi possivel conectar a API interna.");
    this.name = "ImportarMovimentosNetworkError";
  }
}

export class ImportarMovimentosSessionExpiredError extends Error {
  constructor() {
    super("Sessao expirada");
    this.name = "ImportarMovimentosSessionExpiredError";
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function mapResumo(data: ImportarMovimentosApiResponse): ImportarMovimentosResumo {
  return {
    loteId: data.lote_id,
    status: data.status,
    totalLinhas: data.total_linhas,
    totalImportadas: data.total_importadas,
    totalInvalidas: data.total_invalidas,
    warnings: data.warnings,
  };
}

async function parseErrorDetail(response: Response) {
  try {
    const data = (await response.json()) as ErrorResponse;
    return data.detail ?? "Importacao bloqueada pela API.";
  } catch {
    return "Importacao bloqueada pela API.";
  }
}

async function importar(
  accessToken: string,
  empresaId: string,
  file: File,
): Promise<ImportarMovimentosResumo> {
  if (isDemoPreviewToken(accessToken)) {
    return {
      loteId: 15,
      status: "completed_with_warnings",
      totalLinhas: 28,
      totalImportadas: 26,
      totalInvalidas: 2,
      warnings: [
        "Linha 8 sem contrapartida.",
        "Linha 13 ignorada por dados incompletos.",
      ],
    };
  }

  const formData = new FormData();
  formData.append("file", file);

  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/companies/${empresaId}/movimentos-operacionais/import`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData,
      },
    );
  } catch {
    throw new ImportarMovimentosNetworkError();
  }

  if (response.status === 401) {
    throw new ImportarMovimentosSessionExpiredError();
  }

  if (response.status === 403) {
    throw new ImportarMovimentosAccessDeniedError();
  }

  if (response.status === 400) {
    throw new ImportarMovimentosBlockedError(await parseErrorDetail(response));
  }

  if (!response.ok) {
    throw new ImportarMovimentosNetworkError();
  }

  return mapResumo((await response.json()) as ImportarMovimentosApiResponse);
}

export const importarMovimentosClient = {
  importar,
};

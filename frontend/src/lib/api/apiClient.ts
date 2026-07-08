type ApiRequestOptions = {
  accessToken?: string;
  body?: BodyInit | Record<string, unknown>;
  headers?: Record<string, string>;
};

type ApiErrorResponse = {
  detail?: unknown;
  message?: unknown;
};

export class ApiNetworkError extends Error {
  constructor() {
    super("Nao foi possivel conectar a API interna.");
    this.name = "ApiNetworkError";
  }
}

export class ApiSessionExpiredError extends Error {
  constructor() {
    super("Sessao expirada");
    this.name = "ApiSessionExpiredError";
  }
}

export class ApiAccessDeniedError extends Error {
  constructor() {
    super("Acesso negado");
    this.name = "ApiAccessDeniedError";
  }
}

export class ApiValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiValidationError";
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const DEFAULT_VALIDATION_MESSAGE = "Dados invalidos enviados para a API.";

function buildHeaders(options: ApiRequestOptions) {
  const headers: Record<string, string> = { ...options.headers };

  if (options.accessToken) {
    headers.Authorization = `Bearer ${options.accessToken}`;
  }

  return headers;
}

function buildBody(body: ApiRequestOptions["body"]) {
  if (!body) return undefined;
  if (body instanceof FormData) return body;
  if (body instanceof Blob) return body;
  if (typeof body === "string") return body;
  return JSON.stringify(body);
}

function buildRequestInit(method: string, options: ApiRequestOptions): RequestInit {
  const headers = buildHeaders(options);
  const body = buildBody(options.body);

  if (body && typeof body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  return {
    headers,
    method,
    ...(body ? { body } : {}),
  };
}

async function parseSafeValidationMessage(response: Response) {
  try {
    const data = (await response.json()) as ApiErrorResponse;
    const message = data.detail ?? data.message;
    return typeof message === "string" && message.trim()
      ? message
      : DEFAULT_VALIDATION_MESSAGE;
  } catch {
    return DEFAULT_VALIDATION_MESSAGE;
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function request<T>(
  method: string,
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, buildRequestInit(method, options));
  } catch {
    throw new ApiNetworkError();
  }

  if (response.status === 401) {
    throw new ApiSessionExpiredError();
  }

  if (response.status === 403) {
    throw new ApiAccessDeniedError();
  }

  if (response.status === 400 || response.status === 422) {
    throw new ApiValidationError(await parseSafeValidationMessage(response));
  }

  if (!response.ok) {
    throw new ApiNetworkError();
  }

  return parseJson<T>(response);
}

export const apiClient = {
  get: <T>(path: string, options?: ApiRequestOptions) =>
    request<T>("GET", path, options),
  post: <T>(path: string, options?: ApiRequestOptions) =>
    request<T>("POST", path, options),
  put: <T>(path: string, options?: ApiRequestOptions) =>
    request<T>("PUT", path, options),
  patch: <T>(path: string, options?: ApiRequestOptions) =>
    request<T>("PATCH", path, options),
  delete: <T>(path: string, options?: ApiRequestOptions) =>
    request<T>("DELETE", path, options),
};

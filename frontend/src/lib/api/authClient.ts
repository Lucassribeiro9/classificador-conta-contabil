export type LoginCredentials = {
  email: string;
  password: string;
};

export type LoginSession = {
  accessToken: string;
  userEmail: string;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export class InvalidCredentialsError extends Error {
  constructor() {
    super("Credenciais invalidas");
    this.name = "InvalidCredentialsError";
  }
}

export class NetworkAuthError extends Error {
  constructor() {
    super("Nao foi possivel conectar");
    this.name = "NetworkAuthError";
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const LOGIN_PATH = "/auth/login";

async function login(credentials: LoginCredentials): Promise<LoginSession> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${LOGIN_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        login: credentials.email,
        senha: credentials.password,
      }),
    });
  } catch {
    throw new NetworkAuthError();
  }

  if (response.status === 401 || response.status === 403) {
    throw new InvalidCredentialsError();
  }

  if (!response.ok) {
    throw new NetworkAuthError();
  }

  const data = (await response.json()) as TokenResponse;
  return {
    accessToken: data.access_token,
    userEmail: credentials.email,
  };
}

export const authClient = {
  login,
};

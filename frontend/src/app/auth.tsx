import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

export type AuthSession = {
  accessToken: string;
  userEmail: string;
};

type AuthContextValue = {
  session: AuthSession | null;
  sessionExpired: boolean;
  setSession: (session: AuthSession | null) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const SESSION_STORAGE_KEY = "classificador.auth.session";

type AuthState = {
  session: AuthSession | null;
  sessionExpired: boolean;
};

function readStoredSession(): AuthState {
  const storedSession = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (!storedSession) {
    return { session: null, sessionExpired: false };
  }

  try {
    const session = JSON.parse(storedSession) as Partial<AuthSession>;
    if (
      typeof session.accessToken !== "string" ||
      typeof session.userEmail !== "string"
    ) {
      throw new Error("Sessao armazenada invalida");
    }

    const payloadPart = session.accessToken.split(".")[1];
    if (!payloadPart) {
      throw new Error("JWT armazenado invalido");
    }

    const normalizedPayload = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const paddedPayload = normalizedPayload.padEnd(
      normalizedPayload.length + ((4 - (normalizedPayload.length % 4)) % 4),
      "=",
    );
    const payload = JSON.parse(atob(paddedPayload)) as { exp?: number };

    if (typeof payload.exp !== "number") {
      throw new Error("JWT armazenado sem expiracao");
    }
    if (payload.exp <= Date.now() / 1000) {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
      return { session: null, sessionExpired: true };
    }

    return {
      session: session as AuthSession,
      sessionExpired: false,
    };
  } catch {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    return { session: null, sessionExpired: false };
  }
}

type AuthProviderProps = {
  children: ReactNode;
  initialSession?: AuthSession | null;
};

export function AuthProvider({ children, initialSession }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>(() => {
    if (initialSession !== undefined) {
      return { session: initialSession, sessionExpired: false };
    }

    return readStoredSession();
  });
  const setSession = useCallback((nextSession: AuthSession | null) => {
    if (nextSession) {
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(nextSession));
    } else {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    }
    setAuthState({ session: nextSession, sessionExpired: false });
  }, []);
  const value = useMemo(
    () => ({ ...authState, setSession }),
    [authState, setSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider");
  }
  return context;
}

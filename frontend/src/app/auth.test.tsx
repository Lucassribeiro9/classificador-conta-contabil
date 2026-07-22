import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { AuthProvider, useAuth } from "./auth";

function createJwt(exp: number) {
  const encode = (value: object) =>
    btoa(JSON.stringify(value))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=/g, "");

  return `${encode({ alg: "HS256", typ: "JWT" })}.${encode({ exp })}.signature`;
}

function SessionProbe({ accessToken }: { accessToken: string }) {
  const { session, setSession } = useAuth();

  return (
    <>
      <span>{session?.userEmail ?? "sem sessao"}</span>
      <button
        onClick={() =>
          setSession({
            accessToken,
            userEmail: "operador.hml",
          })
        }
        type="button"
      >
        Entrar
      </button>
      <button onClick={() => setSession(null)} type="button">
        Sair
      </button>
    </>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it("restaura uma sessao JWT valida na mesma aba", () => {
    const accessToken = createJwt(Math.floor(Date.now() / 1000) + 3_600);
    const firstRender = render(
      <AuthProvider>
        <SessionProbe accessToken={accessToken} />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(screen.getByText("operador.hml")).toBeInTheDocument();
    firstRender.unmount();

    render(
      <AuthProvider>
        <SessionProbe accessToken={accessToken} />
      </AuthProvider>,
    );

    expect(screen.getByText("operador.hml")).toBeInTheDocument();
  });

  it("descarta uma sessao com JWT expirado", () => {
    const accessToken = createJwt(Math.floor(Date.now() / 1000) - 60);
    const firstRender = render(
      <AuthProvider>
        <SessionProbe accessToken={accessToken} />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
    firstRender.unmount();

    render(
      <AuthProvider>
        <SessionProbe accessToken={accessToken} />
      </AuthProvider>,
    );

    expect(screen.getByText("sem sessao")).toBeInTheDocument();
    expect(sessionStorage).toHaveLength(0);
  });

  it("descarta dados de sessao corrompidos sem interromper a aplicacao", () => {
    sessionStorage.setItem("classificador.auth.session", "{json-invalido");

    expect(() =>
      render(
        <AuthProvider>
          <SessionProbe accessToken={createJwt(0)} />
        </AuthProvider>,
      ),
    ).not.toThrow();

    expect(screen.getByText("sem sessao")).toBeInTheDocument();
    expect(sessionStorage).toHaveLength(0);
  });

  it("remove a sessao do estado e do navegador no logout", () => {
    const accessToken = createJwt(Math.floor(Date.now() / 1000) + 3_600);
    render(
      <AuthProvider>
        <SessionProbe accessToken={accessToken} />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));

    expect(screen.getByText("sem sessao")).toBeInTheDocument();
    expect(sessionStorage).toHaveLength(0);
  });
});

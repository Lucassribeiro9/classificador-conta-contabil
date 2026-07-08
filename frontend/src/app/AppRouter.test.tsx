import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppRouter } from "./AppRouter";
import { AuthProvider } from "./auth";

function renderRouterAt(path: string) {
  window.history.pushState({}, "", path);

  render(
    <AuthProvider>
      <AppRouter />
    </AuthProvider>,
  );
}

describe("AppRouter", () => {
  it("trata navegacao invalida retornando usuario sem sessao ao login", async () => {
    renderRouterAt("/rota-inexistente");

    expect(
      await screen.findByRole("heading", { name: "Entrar" }),
    ).toBeInTheDocument();
  });
});

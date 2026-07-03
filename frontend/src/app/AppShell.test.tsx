import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";
import { ROUTES } from "../routes/paths";

describe("AppShell", () => {
  it("mantem a empresa selecionada visivel no contexto operacional", () => {
    render(
      <MemoryRouter initialEntries={["/empresas/42"]}>
        <Routes>
          <Route path={ROUTES.empresa.operacaoPath} element={<AppShell />}>
            <Route index element={<h1>Operacao da Empresa</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Empresa selecionada: 42")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Operacao da Empresa" }),
    ).toBeInTheDocument();
  });
});

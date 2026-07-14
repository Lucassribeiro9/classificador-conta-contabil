import { expect, test } from "@playwright/test";

async function enterDemo(page: Parameters<typeof test>[0]["page"]) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Entrar em modo demo" }).click();
  await expect(page).toHaveURL("/empresas");
}

test("smoke de rotas MVP abre SPA e navegacao principal sem dados reais", async ({
  page,
}) => {
  await page.goto("/login");
  await expect(
    page.getByRole("button", { name: "Entrar", exact: true }),
  ).toBeVisible();

  await enterDemo(page);
  await page.getByRole("button", { name: "Abrir Comercial Alfa LTDA" }).click();
  await expect(page).toHaveURL("/empresas/7");
  await expect(page.getByText("Empresa selecionada: 7")).toBeVisible();

  await page.getByRole("link", { name: "Importar movimentos" }).click();
  await expect(page).toHaveURL("/empresas/7/movimentos/importar");

  await page.getByRole("link", { name: "Operacao" }).click();
  await page.getByRole("link", { name: "Abrir ultimo lote" }).click();
  await expect(page).toHaveURL("/empresas/7/movimentos/lotes/15");

  await page
    .getByRole("row", { name: /pagamento fornecedor/ })
    .getByRole("link", { name: "Abrir revisao" })
    .click();
  await expect(page).toHaveURL(/\/empresas\/7\/movimentos\/91/);

  await page.getByRole("link", { name: "Operacao" }).click();
  await page.getByRole("link", { name: "Consultar razao" }).click();
  await expect(page).toHaveURL("/empresas/7/razao");
});

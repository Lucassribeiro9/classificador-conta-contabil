import { expect, test } from "@playwright/test";

async function enterDemo(page: Parameters<typeof test>[0]["page"]) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Entrar em modo demo" }).click();
  await expect(
    page.getByRole("heading", { name: "Escolha a empresa" }),
  ).toBeVisible();
}

test("login demo abre empresas e hub operacional", async ({ page }) => {
  await enterDemo(page);

  await page
    .getByRole("button", { name: "Abrir Comercial Alfa LTDA" })
    .click();

  await expect(
    page.getByRole("heading", { name: "Comercial Alfa LTDA" }),
  ).toBeVisible();
  await expect(page.getByText("Modelo pronto")).toBeVisible();
  await expect(page.getByRole("link", { name: "Importar movimentos" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Consultar razao" })).toBeVisible();
});

test("importa movimentos em demo e abre o lote", async ({ page }) => {
  await enterDemo(page);
  await page
    .getByRole("button", { name: "Abrir Comercial Alfa LTDA" })
    .click();
  await page.getByRole("link", { name: "Importar movimentos" }).click();

  await page.getByLabel("Arquivo .xlsx").setInputFiles({
    name: "movimentos-demo.xlsx",
    mimeType:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("demo"),
  });
  await page.getByRole("button", { name: "Importar arquivo" }).click();

  await expect(
    page.getByRole("heading", { name: "Importacao com warnings" }),
  ).toBeVisible();
  await expect(page.getByText("26 movimentos importados")).toBeVisible();
  await expect(page.getByText("Linha 8 sem contrapartida.")).toBeVisible();

  await page.getByRole("link", { name: "Abrir lote" }).click();
  await expect(
    page.getByRole("heading", { name: "Lote de Movimentos" }),
  ).toBeVisible();
  await expect(page.getByText("pagamento fornecedor")).toBeVisible();
});

test("revisa movimento com aprovacao, correcao e rejeicao explicitas", async ({
  page,
}) => {
  await enterDemo(page);
  await page
    .getByRole("button", { name: "Abrir Comercial Alfa LTDA" })
    .click();
  await page.getByRole("link", { name: "Abrir ultimo lote" }).click();

  const fornecedorRow = page.getByRole("row", { name: /pagamento fornecedor/ });
  await fornecedorRow.getByRole("link", { name: "Abrir revisao" }).click();

  await expect(
    page.getByRole("heading", { name: "Revisar Movimento" }),
  ).toBeVisible();
  await expect(page.getByText("pagamento fornecedor")).toBeVisible();
  await expect(page.getByText("91% de confianca")).toBeVisible();

  await page.getByRole("button", { name: "Aprovar sugestao" }).click();
  await expect(page.getByRole("status")).toHaveText("Movimento aprovado.");

  await page.getByLabel("Buscar conta").fill("servicos");
  await page.getByRole("button", { name: "Buscar no plano completo" }).click();
  await page.getByRole("button", { name: "Usar 30001" }).click();
  await expect(
    page.getByText(
      "O vinculo desta conta sera criado pelo backend ao salvar a revisao.",
    ),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Corrigir com conta selecionada" })
    .click();
  await expect(page.getByRole("status")).toHaveText("Movimento corrigido.");

  await page.getByRole("button", { name: "Rejeitar movimento" }).click();
  await expect(page.getByRole("status")).toHaveText("Movimento rejeitado.");
});

test("consulta razao e filtra lancamentos normalizados", async ({ page }) => {
  await enterDemo(page);
  await page
    .getByRole("button", { name: "Abrir Comercial Alfa LTDA" })
    .click();
  await page.getByRole("link", { name: "Consultar razao" }).click();

  await expect(
    page.getByRole("heading", { name: "Razao e Contas Vinculadas" }),
  ).toBeVisible();
  await expect(page.getByText("razao-demo.xlsx")).toBeVisible();
  await expect(page.getByText("pagamento fornecedor")).toBeVisible();
  await expect(page.getByText("recebimento cliente")).toBeVisible();
  await expect(page.getByText("Contrato ainda nao disponivel")).toBeVisible();

  await page.getByLabel("Buscar por codigo ou historico").fill("30001");

  await expect(page.getByText("recebimento cliente")).toBeVisible();
  await expect(page.getByText("pagamento fornecedor")).toBeHidden();
});

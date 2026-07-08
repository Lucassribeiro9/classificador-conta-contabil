const empresasKeys = {
  all: ["empresas"] as const,
  autorizadas: () => [...empresasKeys.all, "autorizadas"] as const,
  detalhe: (empresaId: string) => [...empresasKeys.all, empresaId] as const,
};

const movimentosKeys = {
  all: (empresaId: string) =>
    [...empresasKeys.detalhe(empresaId), "movimentos"] as const,
  lotes: (empresaId: string) =>
    [...movimentosKeys.all(empresaId), "lotes"] as const,
  lote: (empresaId: string, loteId: string) =>
    [...movimentosKeys.lotes(empresaId), loteId] as const,
  lista: (empresaId: string, loteId: string, status?: string) =>
    [...movimentosKeys.lote(empresaId, loteId), "lista", status ?? "todos"] as const,
  detalhe: (empresaId: string, loteId: string, movimentoId: string) =>
    [...movimentosKeys.lote(empresaId, loteId), "movimentos", movimentoId] as const,
};

const razaoKeys = {
  all: (empresaId: string) =>
    [...empresasKeys.detalhe(empresaId), "razao"] as const,
  lotes: (empresaId: string, page?: number) =>
    [...razaoKeys.all(empresaId), "lotes", page ?? 1] as const,
  lancamentos: (empresaId: string, loteId: string, page?: number, search?: string) =>
    [
      ...razaoKeys.all(empresaId),
      "lotes",
      loteId,
      "lancamentos",
      page ?? 1,
      search ?? "",
    ] as const,
};

export const queryKeys = {
  empresas: empresasKeys,
  movimentos: movimentosKeys,
  razao: razaoKeys,
} as const;

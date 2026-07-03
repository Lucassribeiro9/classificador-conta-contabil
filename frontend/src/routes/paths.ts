export const ROUTES = {
  login: "/login",
  empresas: "/empresas",
  empresa: {
    operacaoPath: "/empresas/:empresaId",
    importarMovimentosPath: "/empresas/:empresaId/movimentos/importar",
    loteMovimentosPath: "/empresas/:empresaId/movimentos/lotes/:loteId",
    revisarMovimentoPath: "/empresas/:empresaId/movimentos/:movimentoId",
    razaoContasPath: "/empresas/:empresaId/razao",
    operacao: (empresaId: string) => `/empresas/${empresaId}`,
    importarMovimentos: (empresaId: string) =>
      `/empresas/${empresaId}/movimentos/importar`,
    loteMovimentos: (empresaId: string, loteId: string) =>
      `/empresas/${empresaId}/movimentos/lotes/${loteId}`,
    revisarMovimento: (empresaId: string, movimentoId: string) =>
      `/empresas/${empresaId}/movimentos/${movimentoId}`,
    razaoContas: (empresaId: string) => `/empresas/${empresaId}/razao`,
  },
} as const;

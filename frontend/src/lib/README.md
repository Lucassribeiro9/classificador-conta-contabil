# Dados Remotos no Frontend

Use TanStack Query para todo dado remoto consumido pela SPA.

Padrao minimo:

- defina a chave em `queryKeys.ts`, agrupada por dominio;
- mantenha chamadas HTTP em `src/lib/api`;
- exponha hooks em `src/features/<dominio>`;
- use `isLoading` para estado de carregamento;
- use `isError` e erros normalizados do service para mensagens operacionais;
- use `isSuccess` ou `data` somente para renderizar dados confirmados;
- em mutations futuras, invalide o menor prefixo afetado da query key.

Exemplo inicial:

- `queryKeys.empresas.autorizadas()`
- `useEmpresasAutorizadasQuery(accessToken)`
- `empresasClient.list(accessToken)`

O frontend nao deve acessar banco, arquivos do servidor ou duplicar regra
contabil pesada.

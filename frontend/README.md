# Frontend

SPA interna em React, TypeScript, Vite, Tailwind CSS, React Router e TanStack
Query. O frontend consome somente a API FastAPI.

## Comandos

Execute a partir de `frontend/`:

| Comando                | Uso                                           |
| ---------------------- | --------------------------------------------- |
| `npm run dev`          | Sobe o Vite em modo desenvolvimento.          |
| `npm run build`        | Gera o build estatico da SPA.                 |
| `npm run preview`      | Serve o build localmente para validacao.      |
| `npm run typecheck`    | Executa `tsc --noEmit`.                       |
| `npm run lint`         | Executa ESLint.                               |
| `npm run format`       | Formata os arquivos do frontend com Prettier. |
| `npm run format:check` | Verifica a formatacao sem alterar arquivos.   |
| `npm test`             | Executa Vitest.                               |
| `npm run test:e2e`     | Executa Playwright.                           |

## Estrutura

```text
src/app        inicializacao, providers, router e layout base
src/components componentes reutilizaveis sem regra de dominio pesada
src/features   hooks e fluxos por dominio
src/lib        cliente API, helpers, query keys e tipos compartilhados
src/routes     rotas e paginas
src/styles     Tailwind, CSS global e tokens visuais
src/test       setup/utilitarios de teste
src/ui         componentes operacionais compartilhados
```

## Variaveis De Ambiente

- `VITE_API_BASE_URL`: URL base da API FastAPI consumida pelo frontend. Nao
  coloque token, usuario, senha ou segredo nesta variavel.
- `VITE_ENABLE_DEMO_LOGIN`: usado apenas em validacoes locais/e2e para expor o
  login demo. Nao habilite em producao.

## Fronteiras Tecnicas

- Sempre consuma dados pela API FastAPI.
- Sempre mantenha contratos TypeScript no frontend.
- Sempre use `sessionStorage` para a persistencia MVP do JWT quando a sessao for
  persistida na aba.
- Nunca acesse banco, arquivos locais do servidor ou servicos internos direto do
  frontend.
- Nunca duplique regra contabil pesada no frontend.
- Nunca versionar segredos, credenciais, tokens ou dados reais em fixtures,
  testes, screenshots ou Playwright traces.
- Pergunte antes de adicionar dependencia grande de UI, estado global ou
  biblioteca de formularios.

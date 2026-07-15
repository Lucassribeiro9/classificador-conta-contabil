# Frontend

SPA interna em React, TypeScript, Vite, Tailwind CSS, React Router e TanStack
Query. O frontend consome somente a API FastAPI.

## Referencias

- [PRD da evolucao do produto](../docs/prd/evolucao-plano-contas-importacao-ml.md)
- [Spec de padroes de codigo e documentacao](../docs/specs/12-frontend-padroes-codigo-documentacao.md)

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

## Convencoes De Codigo

- Componentes React e seus arquivos usam `PascalCase`.
- Hooks comecam com `use` e descrevem o fluxo, como
  `useEmpresasAutorizadasQuery`.
- Clientes da API recebem nomes por dominio, como `empresasClient`.
- Tipos representam contratos ou conceitos do dominio com nomes claros.
- Rotas usam nomes alinhados ao vocabulario operacional do usuario.
- Testes unitarios e de componentes ficam proximos ao codigo, com sufixo
  `.test.ts` ou `.test.tsx`.

Use comentarios curtos somente para regras contabeis, operacionais, de acesso ou
tratamentos de erro que nao sejam obvios pelo codigo. Nao repita em comentarios o
nome de funcoes ou informacoes que pertencem ao PRD, a uma spec ou a este README.

## Testes

Use `renderWithProviders` e `renderHookWithProviders`, de `src/test/testUtils`,
para testes que dependam de TanStack Query, autenticacao ou React Router. Passe
apenas a sessao, as entradas de rota ou um Query Client especifico exigidos pelo
cenario. Mantenha rotas de apoio e mocks de API no proprio teste.

## Validacoes Por Tipo De Mudanca

| Mudanca         | Validacoes minimas                                                           |
| --------------- | ---------------------------------------------------------------------------- |
| Docs ou spec    | Revisar o diff, a formatacao e a consistencia com PRD e specs.               |
| Setup frontend  | `npm run build`, `npm run typecheck` e `npm run lint`.                       |
| Tela simples    | `npm run build`, typecheck, lint e `npm test -- <arquivo>` quando aplicavel. |
| Fluxo com API   | Build, typecheck, lint, teste de service/hook e `npm run test:e2e`.          |
| Docker/ambiente | Build da imagem, subida controlada e smoke test.                             |

Antes de abrir o PR, execute tambem `npm run format:check`. Restrinja cada PR ao
escopo da issue e registre no corpo do PR os comandos executados e seus
resultados.

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

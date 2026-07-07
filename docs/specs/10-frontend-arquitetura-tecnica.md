# Spec: Arquitetura Tecnica do Frontend

## Objetivo

Definir a arquitetura tecnica do frontend separado em `frontend/`.

O frontend deve ser uma SPA interna que consome a API FastAPI existente. Ele nao deve acessar banco, arquivos locais do servidor ou regras de dominio diretamente.

## Tech Stack

- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- React Router.
- TanStack Query.
- Fetch API ou cliente HTTP leve definido na implementacao.
- Vitest e React Testing Library quando aplicavel.
- Playwright para fluxos principais quando houver ambiente integrado.

## Comandos Esperados

Os comandos finais devem ser confirmados quando o projeto `frontend/` for criado.

- Dev: `npm run dev`
- Build: `npm run build`
- Typecheck: `npm run typecheck`
- Lint: `npm run lint`
- Testes: `npm test`
- E2E: `npm run test:e2e`

## Project Structure

Estrutura esperada:

```text
frontend/
  src/
    app/
    components/
    features/
    lib/
    routes/
    styles/
    test/
  public/
  package.json
  vite.config.ts
  tsconfig.json
  tailwind.config.ts
```

Responsabilidades:

- `app/`: inicializacao, providers, router e layout base.
- `components/`: componentes reutilizaveis e sem regra de dominio pesada.
- `features/`: fluxos por dominio, como auth, empresas, movimentos e razao.
- `lib/`: cliente API, helpers, formatadores e tipos compartilhados do frontend.
- `routes/`: definicao de rotas e telas.
- `styles/`: Tailwind e tokens visuais.
- `test/`: utilitarios de teste.

## Rotas Esperadas

- `/login`
- `/empresas`
- `/empresas/:empresaId`
- `/empresas/:empresaId/movimentos/importar`
- `/empresas/:empresaId/movimentos/lotes/:loteId`
- `/empresas/:empresaId/movimentos/:movimentoId`
- `/empresas/:empresaId/razao`

## Estado e Dados

- Autenticacao deve manter token e usuario atual em fronteira clara.
- No MVP, o access token JWT deve ser persistido em `sessionStorage`, nao em
  `localStorage`.
- O estado React pode refletir a sessao ativa e ser reidratado a partir do
  `sessionStorage` ao recarregar a aba.
- Sessao expirada ou resposta `401` da API deve limpar estado, limpar
  `sessionStorage` e retornar o usuario ao login.
- Dados remotos devem ser carregados com TanStack Query.
- Mutations devem invalidar queries afetadas.
- Erros da API devem ser normalizados para mensagens operacionais.
- Empresa selecionada deve vir da rota, nao de estado global oculto.

## Cliente API

O cliente API deve:

- usar URL base via variavel de ambiente;
- anexar token quando autenticado;
- tratar 401 como sessao expirada;
- tratar 403 como acesso negado;
- preservar mensagens de validacao do backend quando seguras para usuario;
- separar tipos de request/response por dominio.

## Code Style

Exemplo de direcao esperada:

```tsx
export function EmpresasPage() {
  const empresas = useEmpresasQuery();

  if (empresas.isLoading) return <PageState tone="loading" title="Carregando empresas" />;
  if (empresas.isError) return <PageState tone="error" title="Nao foi possivel carregar empresas" />;

  return <EmpresasList empresas={empresas.data} />;
}
```

Componentes devem expressar estados de usuario. Hooks e services devem concentrar integracao com API.

Formularios iniciais devem ser controlados simples em React. Bibliotecas de
formularios ou validacao externa ficam fora do MVP e exigem issue propria se a
complexidade crescer.

## Testing Strategy

- Testar hooks/services quando houver mapeamento relevante de API.
- Testar componentes quando houver regra visual ou estado operacional importante.
- Testar rotas principais com Playwright quando o fluxo envolver navegacao, login ou mutation.
- Nao testar detalhes internos de componentes simples.
- Validar build, typecheck e lint antes de PR.

## Boundaries

- Sempre: consumir a API FastAPI.
- Sempre: manter `frontend/` separado do backend.
- Sempre: usar TypeScript para contratos do frontend.
- Sempre: manter comentarios curtos em regras nao obvias.
- Perguntar antes: adicionar dependencia grande de UI, estado global ou formularios.
- Perguntar antes: mudar contrato de endpoint.
- Nunca: acessar banco diretamente.
- Nunca: duplicar regra contabil complexa no frontend.
- Nunca: colocar dados reais ou sensiveis em fixtures do frontend.

## Success Criteria

- Estrutura tecnica do frontend esta definida.
- Rotas do MVP estao mapeadas.
- Estrategia de API, estado, erro e autenticacao esta definida.
- Validacoes esperadas para issues futuras estao claras.
- A spec permite gerar issues tecnicas pequenas.

## Proximas Issues Recomendadas

1. `chore(frontend): criar projeto React Vite em frontend`
2. `chore(frontend): configurar Tailwind e tokens visuais`
3. `chore(frontend): configurar router e providers`
4. `chore(frontend): criar cliente API autenticado`
5. `chore(frontend): configurar testes e lint`
6. `test(frontend): criar smoke test de roteamento`

## Decisoes Aprovadas Apos Task Review #283

- O token JWT sera persistido em `sessionStorage` no MVP para preservar a
  sessao durante refresh da aba sem usar persistencia longa em `localStorage`.
- O timeout da sessao continua definido pelo `exp` do JWT emitido pela API. A
  primeira versao usa access token de 12 horas e nao implementa refresh token.
- `401` da API representa sessao expirada para a UI: limpar sessao e retornar
  ao login.
- Formularios iniciais usam formularios controlados simples em React, sem
  biblioteca dedicada.
- Refresh token, troca de estrategia de storage ou biblioteca de formularios
  exigem issue propria.

## Open Questions

- Nenhuma em aberto para persistencia JWT e estrategia inicial de formularios.

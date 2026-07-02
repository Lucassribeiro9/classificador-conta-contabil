# Spec: Padroes de Codigo, Comentarios e Documentacao do Frontend

## Objetivo

Definir padroes minimos para manter o frontend legivel, testavel e consistente com o fluxo SDD/TDD do projeto.

Esta spec tambem registra a decisao de usar comentarios e docstrings de forma curta e util, sem poluir codigo simples.

## Principios

- Codigo deve expressar comportamento operacional.
- Componentes simples devem permanecer simples.
- Regras de dominio, permissoes, status e mapeamentos de API merecem nomes claros e comentarios curtos quando nao forem obvios.
- Cada issue deve manter escopo pequeno e validavel.
- PRs devem seguir o template do repositorio.

## Comentarios e Docstrings

Usar comentarios quando:

- houver regra contabil ou operacional nao obvia;
- houver mapeamento entre status da API e estado visual;
- houver permissao por empresa;
- houver tratamento especial de erro da API;
- houver decisao temporaria ou limitacao intencional.

Evitar comentarios quando:

- o codigo ja e autoexplicativo;
- o comentario apenas repete o nome da funcao;
- a informacao pertence a spec, PRD ou README.

Exemplo:

```ts
// Movimentos finais nao podem ser alterados em lote no MVP.
const FINAL_STATUSES = ["aprovado", "corrigido", "rejeitado", "convertido"] as const;
```

## Nomenclatura

- Componentes React: `PascalCase`.
- Hooks: `useNomeDoFluxo`.
- Services/API: nomes por dominio, como `movimentosApi`.
- Tipos: nomes claros baseados no contrato de resposta.
- Rotas: nomes alinhados ao dominio do usuario.

## Organizacao de Issues

Cada issue deve conter:

- spec de origem;
- escopo exato;
- criterios de aceite;
- validacoes esperadas;
- riscos;
- branch sugerida seguindo `.github/BRANCHING.md`.

Antes de implementar, o agente deve sugerir a branch. Para esta fase, branches provaveis usam `spec/frontend-*`, `chore/frontend-*`, `feat/frontend-*`, `test/frontend-*` ou `docs/frontend-*`.

## Pull Requests

Cada PR deve seguir `.github/pull_request_template.md`.

Quando o corpo do PR for gerado em chat, deve ser entregue em um unico bloco de codigo Markdown para preservar formatacao.

Quando houver acesso ao GitHub e o usuario pedir publicacao, o PR deve ser criado como draft ate revisao humana.

## Validacoes por Tipo de Mudanca

- Docs/spec: revisao do diff e consistencia com PRD.
- Setup frontend: build, typecheck e lint.
- Tela simples: build, typecheck, lint e teste de componente quando houver estado relevante.
- Fluxo com API: build, typecheck, lint, teste de service/hook e Playwright quando possivel.
- Docker/ambiente: build de imagem, subida controlada e smoke test.

## Boundaries

- Sempre: manter portugues tecnico em docs do projeto.
- Sempre: usar ASCII nos documentos, salvo necessidade explicita.
- Sempre: atualizar specs quando decisao aprovada mudar.
- Sempre: usar comentarios curtos para regras nao obvias.
- Perguntar antes: adicionar dependencia que mude padrao de arquitetura.
- Perguntar antes: mudar template de issue ou PR.
- Nunca: misturar refatoracao ampla com entrega de tela.
- Nunca: deixar markdown de PR quebrado em multiplos blocos quando o usuario pedir corpo pronto.

## Success Criteria

- Padroes de comentarios e documentacao estao definidos.
- Regras para branch e PR estao registradas.
- Validacoes por tipo de mudanca estao claras.
- A spec reduz ambiguidade para implementacoes futuras.

## Proximas Issues Recomendadas

1. `docs(frontend): revisar guia de prompts com casos de uso da fase 2`
2. `chore(frontend): configurar lint e formatacao`
3. `docs(frontend): criar README inicial do frontend`
4. `test(frontend): definir helpers de teste`

## Open Questions

- O frontend usara formatter automatico dedicado ou apenas regras de lint no primeiro momento?

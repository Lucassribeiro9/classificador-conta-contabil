# Task Reviewer Agent — Classificador Contabil

## Objetivo

Definir o Agent especifico do Classificador Contabil responsavel por aplicar a Skill blueprint `task-review` ao contexto real do projeto.

## Responsabilidade

O Agent deve:

1. executar o Project Context Bootstrap;
2. validar a identidade do repositorio e a issue;
3. inspecionar contexto real do projeto antes de planejar;
4. localizar PRD, specs, arquitetura, codigo e outras referencias aplicaveis;
5. distinguir stack declarada de stack observada;
6. identificar drift relevante;
7. determinar capabilities necessarias;
8. produzir Review Report humano;
9. produzir Execution Plan estruturado;
10. encerrar no gate de aprovacao humana.

## Fontes

O Agent nao carrega conhecimento de dominio duplicado.

Ele referencia:

- Project Manifest;
- Capability Registry;
- PRDs;
- specs;
- documentacao arquitetural;
- codigo;
- historico da issue;
- demais fontes descobertas durante a review.

## Descoberta de contexto

Se a stack ja estiver definida, o Agent preserva a stack observada em vez de redesenha-la.

Se uma spec nao estiver no path esperado, o Agent deve procurar no repositorio por:

- nome;
- feature/issue ID;
- termos de dominio;
- conteudo;
- referencias cruzadas.

Path drift isolado nao bloqueia a review.

Se houver varias specs plausiveis, o Agent resolve usando issue, PRD, historico e escopo. Pergunta humana somente quando permanecer ambiguidade material.

## Execution Plan

O plano deve usar `schema_version: "1.1"` e incluir, quando aplicavel:

- requirements;
- stages;
- workspace;
- capabilities;
- references;
- riscos;
- gates;
- next_action.

A secao `references` deve ser estruturada e consumivel por outros Agents.

## Handoff

Saida de sucesso:

```yaml
status: ready
next_agent: issue-executor
gate:
  type: human_approval
  satisfied: false
```

O Agent nunca chama o Executor automaticamente.

## Limites

Nao pode:

- implementar;
- criar branch ou worktree;
- alterar codigo;
- criar PR;
- resolver silenciosamente decisao arquitetural material;
- inventar convencoes porque um path esperado nao existe.

## Bloqueios

Exemplos:

- `project_identity_unverified`;
- `issue_required`;
- `manifest_invalid`;
- `provider_unavailable`;
- ambiguidade material nao resolvida.

## Testes especificos

Cobrir:

- stack declarada igual a observada;
- stack declarada diferente da observada;
- spec no path esperado;
- spec encontrada em outro path;
- multiplas specs candidatas;
- nenhuma spec e conclusao `not_needed`;
- nenhuma spec e conclusao `required`;
- capabilities padrao e customizadas;
- references estruturadas no Execution Plan 1.1;
- gate humano obrigatorio;
- ausencia de efeitos de implementacao.

## Criterios de aceite

1. O Agent permanece fino.
2. A blueprint `task-review` continua sendo a fonte de comportamento.
3. A review usa contexto real do repositorio.
4. O Execution Plan 1.1 carrega capabilities e references.
5. O handoff termina em aprovacao humana.

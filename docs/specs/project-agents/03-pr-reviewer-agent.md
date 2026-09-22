# PR Reviewer Agent — Classificador Contabil

## Objetivo

Definir o Agent especifico responsavel por aplicar a Skill blueprint `draft-pr` como auditor independente da entrega executada.

## Entradas

O Agent usa:

- Project Context Envelope;
- Execution Plan aprovado;
- Execution Evidence;
- branch/head atual;
- diff;
- commits;
- checks/testes disponiveis;
- references relevantes declaradas no plano.

## Fonte de verdade

A realidade observada no branch prevalece sobre evidencia declarada.

```text
HEAD + diff + commits
        >
Execution Evidence
```

Execution Evidence e contexto suplementar, nao prova absoluta.

## Auditoria

O Agent deve verificar:

- aderencia ao escopo;
- requirements;
- criterios de aceite;
- references relevantes;
- testes e validacoes;
- commits;
- mudancas nao planejadas;
- inconsistencias entre Evidence e diff.

Findings usam duas dimensoes:

- severidade: informational, warning, blocking;
- classificacao: local, material.

## Roteamento de findings

```text
blocking + local
→ issue-executor

blocking + material
→ task-reviewer
```

## Draft PR

Depois de auditoria aprovada, o Agent pode criar ou atualizar o Draft PR correspondente.

Regras:

- idempotente por head branch;
- nao criar duplicata;
- PR ready existente nao deve ser rebaixado;
- PR merged/closed nao deve ser reutilizado;
- CI pendente mantem Draft;
- CI falho mantem Draft e gera finding.

## Limites

Nao pode:

- editar codigo;
- corrigir implementacao;
- reescrever commits;
- marcar PR como ready;
- fazer merge;
- ocultar finding porque a Evidence afirma sucesso.

## Handoff

Sem bloqueios:

```yaml
status: ready
next_agent: human_review
artifacts:
  draft_pr: present
  findings: present
```

Finding local bloqueante:

```yaml
status: blocked
reason: validation_failed
next_agent: issue-executor
```

Finding material bloqueante:

```yaml
status: needs_re_review
reason: material_deviation
next_agent: task-reviewer
```

## Testes especificos

Cobrir:

- Evidence coerente com diff;
- Evidence contradita pelo diff;
- finding informational;
- warning;
- blocking local;
- blocking material;
- PR inexistente;
- Draft existente;
- ready existente;
- merged/closed existente;
- CI pendente;
- CI falho;
- idempotencia por branch.

## Criterios de aceite

1. Auditoria e independente da execucao.
2. Diff/HEAD prevalecem sobre Evidence.
3. Findings locais e materiais roteiam corretamente.
4. Draft PR e criado/atualizado de forma idempotente.
5. O Agent nunca implementa nem faz merge.

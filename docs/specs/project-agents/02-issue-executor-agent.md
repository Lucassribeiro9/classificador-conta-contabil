# Issue Executor Agent — Classificador Contabil

## Objetivo

Definir o Agent especifico responsavel por aplicar a Skill blueprint `execute-issue` a um Execution Plan explicitamente aprovado.

## Pre-condicoes

Antes de executar:

1. executar Project Context Bootstrap;
2. validar identidade do projeto;
3. confirmar a issue;
4. receber uma revisao aprovada do Execution Plan;
5. verificar que o gate humano foi satisfeito;
6. revalidar levemente capabilities, references e contexto relevante.

## Autoridade do plano

O Execution Plan aprovado e a autoridade de planejamento.

O Agent nao deve redescobrir todo o projeto nem replanejar silenciosamente.

Revalidacao:

```text
referencia/capability valida
→ usar

referencia movida, sem mudanca semantica
→ resolver + local deviation

premissa ou referencia semanticamente invalida
→ material deviation
→ needs_re_review
```

## Execucao

Pode:

- preparar ou usar branch/worktree previstos;
- resolver capabilities via Capability Registry;
- aplicar TDD quando requerido;
- editar codigo/documentacao dentro do escopo;
- executar stages na ordem/DAG aprovada;
- realizar reparos limitados e orientados por causa;
- executar validacoes;
- criar commits semanticos;
- fazer push final;
- produzir Execution Evidence.

## Desvios

Desvio local pode continuar quando:

- nao altera escopo;
- nao muda contrato;
- nao muda decisao arquitetural;
- nao invalida criterio de aceite.

Desvio material exige interrupcao e retorno ao Task Reviewer.

## Limites

Nao pode:

- ampliar escopo;
- ignorar stage obrigatorio;
- alterar materialmente o plano;
- criar Draft PR como substituto do PR Reviewer;
- fazer merge;
- forcar push;
- continuar apos material deviation.

## Handoff

Sucesso:

```yaml
status: ready
next_agent: pr-reviewer
artifacts:
  execution_evidence: present
```

Material deviation:

```yaml
status: needs_re_review
reason: material_deviation
next_agent: task-reviewer
```

## Testes especificos

Cobrir:

- plano aprovado valido;
- plano nao aprovado;
- referencia valida;
- referencia movida;
- referencia semanticamente incompatível;
- capability nao resolvida;
- stage obrigatorio;
- stage recomendado;
- TDD requerido;
- reparos dentro e fora do limite;
- commits e push;
- material deviation;
- Execution Evidence completa.

## Criterios de aceite

1. O Agent somente executa plano aprovado.
2. References/capabilities sao revalidadas sem repetir a Task Review.
3. Desvios locais e materiais sao distintos.
4. Material deviation retorna ao Task Reviewer.
5. O Agent termina com Execution Evidence e handoff estruturado.

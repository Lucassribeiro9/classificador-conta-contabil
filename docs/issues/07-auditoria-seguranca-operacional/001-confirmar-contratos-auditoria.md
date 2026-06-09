# Issue 001: chore(audit): confirmar contratos de auditoria

## Contexto

A spec define uma tabela unica de eventos, mas ainda deixa em aberto alguns nomes e detalhes operacionais.

## Escopo

- Confirmar o nome final da tabela, preferencialmente `audit_events`.
- Confirmar se login falho pode armazenar email/login tentado de forma mascarada.
- Confirmar comportamento de falha de auditoria em login falho: best-effort ou bloqueante.
- Confirmar lista inicial de `event_type`.
- Nao implementar modelo nesta issue.

## Criterios de Aceite

- Decisoes abertas ficam registradas.
- Se houver mudanca, a spec e atualizada antes da implementacao.
- Eventos iniciais ficam padronizados para as proximas issues.

## Testes Esperados

- Nao se aplica, issue de alinhamento.

## TDD

Nao obrigatorio.

## Riscos

- Implementar nomes diferentes em fluxos distintos.
- Gravar identificadores sensiveis de login sem decisao explicita.

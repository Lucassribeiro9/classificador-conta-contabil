# Issue 016: backlog(audit): avaliar retencao e limpeza de auditoria

## Contexto

A decisao atual e manter auditoria por tempo indeterminado na primeira versao. Politica de retencao pode ser revista depois com volume real.

## Escopo

- Registrar avaliacao futura de retencao.
- Considerar volume, backup, requisitos legais e necessidade operacional.
- Nao criar rotina automatica de limpeza nesta fase.

## Criterios de Aceite

- Backlog preserva retencao indefinida inicial.
- Qualquer limpeza futura exige decisao explicita.

## Testes Esperados

- A definir quando implementada.

## TDD

Obrigatorio quando implementada.

## Riscos

- Apagar trilha auditavel cedo demais.
- Crescimento de tabela sem monitoramento futuro.

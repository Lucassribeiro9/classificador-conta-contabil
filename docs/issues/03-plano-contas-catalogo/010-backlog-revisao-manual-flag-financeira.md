# Issue 010: backlog(contas): permitir revisao manual da flag financeira

## Contexto

A primeira fase usa heuristica para marcar contas candidatas a origem financeira. Revisao manual da flag pode ser necessaria para corrigir falsos positivos ou negativos.

## Escopo

- Definir fluxo futuro para revisar flag financeira.
- Avaliar permissao necessaria para alterar a flag.
- Avaliar auditoria da alteracao.
- Nao implementar nesta fase sem nova aprovacao.

## Criterios de Aceite

- Necessidade futura esta registrada.
- Escopo nao altera campos oficiais do plano.
- Regras de permissao e auditoria serao consideradas quando implementada.

## Testes Esperados

- A definir quando a issue sair do backlog.

## TDD

Obrigatorio quando implementada.

## Riscos

- Alterar flag sem auditoria.
- Confundir revisao de flag com edicao oficial do plano.

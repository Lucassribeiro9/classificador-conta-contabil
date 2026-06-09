# Issue 014: backlog(ml): avaliar cache de modelo por empresa

## Contexto

A arquitetura deve permitir cache futuro, mas a primeira versao treina por request.

## Escopo

- Registrar necessidade futura de cache quando houver volume ou latencia medidos.
- Avaliar invalidacao por feedback, nova importacao e alteracao de vinculos.
- Nao implementar nesta fase.

## Criterios de Aceite

- Backlog deixa claro que cache esta fora da primeira versao.
- Criterios de invalidacao futura ficam listados.

## Testes Esperados

- A definir quando implementada.

## TDD

Obrigatorio quando implementada.

## Riscos

- Servir modelo desatualizado apos feedback ou importacao.
- Otimizar antes de medir latencia real.

# Issue 001: chore(dataset): confirmar contratos e campos base

## Contexto

O builder de dataset depende de estruturas entregues pelas specs anteriores: catalogo unico, flag financeira, lancamentos normalizados e vinculo por empresa. Antes de codificar, os nomes finais precisam estar alinhados para evitar retrabalho.

## Escopo

- Confirmar o nome final da flag financeira no catalogo, preferencialmente `is_financial_origin`.
- Confirmar que `historico_normalizado` esta persistido no lancamento normalizado ou indicar origem calculada.
- Confirmar os campos minimos do lancamento normalizado usados pelo dataset: `empresa_id`, `conta_origem`, `conta_contrapartida`, `direcao`, `historico_normalizado`.
- Confirmar como identificar conta analitica no catalogo, preferencialmente `tipo = A`.
- Nao implementar builder nesta issue.

## Criterios de Aceite

- Campos base ficam documentados na propria issue ou na spec se houver mudanca.
- Nenhum nome de campo fica ambiguo antes das issues funcionais.
- Decisoes novas, se existirem, sao refletidas na spec antes da implementacao.

## Testes Esperados

- Nao se aplica, issue de alinhamento.

## TDD

Nao obrigatorio.

## Riscos

- Implementar builder com nomes provisoriamente diferentes dos modelos reais.
- Duplicar normalizacao de historico se ela ja vier da importacao do razao.

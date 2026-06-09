# Issues: 03 Catalogo Unico do Plano de Contas

Issues derivadas da spec `docs/specs/03-plano-contas-catalogo.md`.

## Ordem Recomendada

1. `001-definir-nome-flag-financeira.md`
2. `002-criar-modelo-conta-contabil.md`
3. `003-criar-parser-plano-contas.md`
4. `004-criar-servico-importacao-idempotente.md`
5. `005-inferir-contas-financeiras.md`
6. `006-criar-endpoint-admin-importacao-plano.md`
7. `007-criar-endpoint-consulta-catalogo.md`
8. `008-bloquear-contas-sinteticas-como-classificaveis.md`
9. `009-documentar-regra-contas-ausentes.md`
10. `010-backlog-revisao-manual-flag-financeira.md`
11. `011-backlog-historico-versoes-plano.md`

## TDD Obrigatorio

- `003-criar-parser-plano-contas.md`
- `004-criar-servico-importacao-idempotente.md`
- `005-inferir-contas-financeiras.md`
- `006-criar-endpoint-admin-importacao-plano.md`
- `007-criar-endpoint-consulta-catalogo.md`
- `008-bloquear-contas-sinteticas-como-classificaveis.md`

## Observacao

Estas issues nao devem implementar importacao do razao, dataset de treino ou ML. Elas entregam apenas o catalogo unico do escritorio e a base para que outras specs usem as contas.

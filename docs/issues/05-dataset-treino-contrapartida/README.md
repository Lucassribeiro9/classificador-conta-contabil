# Issues: 05 Dataset de Treino para Contrapartida

Issues derivadas da spec `docs/specs/05-dataset-treino-contrapartida.md`.

## Ordem Recomendada

1. `001-confirmar-contratos-campos-base.md`
2. `002-criar-contrato-builder-dataset.md`
3. `003-filtrar-lancamentos-por-empresa.md`
4. `004-filtrar-origem-financeira-por-flag.md`
5. `005-validar-target-contrapartida-analitica.md`
6. `006-montar-features-iniciais.md`
7. `007-retornar-metadados-dataset.md`
8. `008-sinalizar-dataset-insuficiente.md`
9. `009-integrar-builder-ao-ml-sem-treinar-nesta-issue.md`
10. `010-criar-testes-unitarios-builder-dataset.md`
11. `011-documentar-contrato-dataset.md`
12. `012-backlog-features-com-valor-normalizado.md`
13. `013-backlog-dataset-multiplas-origens.md`

## TDD Obrigatorio

- `002-criar-contrato-builder-dataset.md`
- `003-filtrar-lancamentos-por-empresa.md`
- `004-filtrar-origem-financeira-por-flag.md`
- `005-validar-target-contrapartida-analitica.md`
- `006-montar-features-iniciais.md`
- `007-retornar-metadados-dataset.md`
- `008-sinalizar-dataset-insuficiente.md`
- `009-integrar-builder-ao-ml-sem-treinar-nesta-issue.md`
- `010-criar-testes-unitarios-builder-dataset.md`

## Observacao

Estas issues assumem que o catalogo unico, a flag financeira persistida e os lancamentos normalizados do razao ja existem. Elas nao devem implementar o novo comportamento completo de predicao; isso pertence a spec de ML.

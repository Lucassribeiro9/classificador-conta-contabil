# Issues: 06 ML de Contrapartida e Feedback Humano

Issues derivadas da spec `docs/specs/06-ml-classificacao-feedback.md`.

## Ordem Recomendada

1. `001-confirmar-contratos-endpoints-campos.md`
2. `002-adaptar-ml-engine-para-dataset-contrapartida.md`
3. `003-tratar-dataset-insuficiente-com-erro-dominio.md`
4. `004-treinar-modelo-por-request-sem-cache.md`
5. `005-limitar-predicoes-a-contas-validas-da-empresa.md`
6. `006-criar-schemas-contrapartida-predict-classification.md`
7. `007-adaptar-endpoint-predict-contrapartida.md`
8. `008-adaptar-endpoint-classification-pendentes.md`
9. `009-persistir-predicao-confianca-revisao.md`
10. `010-adaptar-feedback-para-corrigir-contrapartida.md`
11. `011-registrar-evento-auditavel-feedback.md`
12. `012-criar-testes-comportamento-ml-feedback.md`
13. `013-documentar-fluxo-predicao-feedback.md`
14. `014-backlog-cache-modelo-por-empresa.md`
15. `015-backlog-avaliacao-novo-algoritmo.md`

## TDD Obrigatorio

- `002-adaptar-ml-engine-para-dataset-contrapartida.md`
- `003-tratar-dataset-insuficiente-com-erro-dominio.md`
- `004-treinar-modelo-por-request-sem-cache.md`
- `005-limitar-predicoes-a-contas-validas-da-empresa.md`
- `006-criar-schemas-contrapartida-predict-classification.md`
- `007-adaptar-endpoint-predict-contrapartida.md`
- `008-adaptar-endpoint-classification-pendentes.md`
- `009-persistir-predicao-confianca-revisao.md`
- `010-adaptar-feedback-para-corrigir-contrapartida.md`
- `011-registrar-evento-auditavel-feedback.md`
- `012-criar-testes-comportamento-ml-feedback.md`

## Observacao

Estas issues assumem que o dataset da spec 05 ja existe e que autenticacao, permissoes por empresa e auditoria basica foram ou serao entregues pelas specs correspondentes. Elas nao devem trocar o algoritmo principal nesta fase.

# Issues: 01 PostgreSQL e Migracao

Issues derivadas da spec `docs/specs/01-postgresql-migracao.md`.

## Ordem Recomendada

1. `001-adicionar-driver-psycopg.md`
2. `002-ajustar-config-database-url.md`
3. `003-adicionar-env-example-postgres.md`
4. `004-adicionar-postgres-docker-compose.md`
5. `005-validar-migrations-postgresql.md`
6. `006-criar-script-migracao-empresas.md`
7. `007-testar-migracao-empresas-idempotente.md`
8. `008-documentar-decisao-transacoes-legadas.md`
9. `009-documentar-backup-postgresql.md`
10. `010-backlog-testes-integracao-postgresql.md`
11. `011-backlog-declarative-base-sqlalchemy2.md`

## TDD Obrigatorio

- `002-ajustar-config-database-url.md`
- `006-criar-script-migracao-empresas.md`
- `007-testar-migracao-empresas-idempotente.md`

## Observacao

Nenhuma issue deve implementar autenticacao, plano de contas, importacao do razao ou ML. Esta pasta cobre apenas a base PostgreSQL e migracao obrigatoria das empresas existentes.

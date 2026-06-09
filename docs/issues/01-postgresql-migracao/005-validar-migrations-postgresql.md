# Issue 005: chore(alembic): validar migrations atuais em PostgreSQL

## Contexto

As migrations existentes foram usadas com SQLite. A spec exige que Alembic aplique migrations no PostgreSQL sem erro antes de evoluir o dominio.

## Escopo

- Rodar migrations Alembic em um banco PostgreSQL limpo.
- Ajustar migrations somente se houver incompatibilidade real com PostgreSQL.
- Registrar evidencias de validacao.
- Nao criar novos modelos de dominio nesta issue.

## Criterios de Aceite

- `alembic upgrade head` executa com sucesso no PostgreSQL.
- `alembic current` mostra a revisao esperada.
- Tabelas atuais sao criadas no PostgreSQL.
- Qualquer ajuste em migration e justificado.

## Testes Esperados

- `.\venv\Scripts\python.exe -m alembic upgrade head` contra PostgreSQL.
- `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Nao obrigatorio. Validacao de migration e principalmente integracao/infra.

## Riscos

- Ajustar migration antiga de forma incompativel com bancos existentes.
- Confundir problema de schema com problema de conexao/configuracao.

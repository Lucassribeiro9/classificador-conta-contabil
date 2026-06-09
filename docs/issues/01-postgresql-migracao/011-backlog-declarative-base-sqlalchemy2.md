# Issue 011: chore(sqlalchemy): migrar declarative_base para DeclarativeBase

## Contexto

O projeto usa API depreciada de SQLAlchemy para base declarativa. A migracao para PostgreSQL nao depende diretamente disso, mas a evolucao para SQLAlchemy 2 fica mais limpa usando `DeclarativeBase`.

## Escopo

- Migrar base ORM para API atual do SQLAlchemy 2.
- Preservar modelos existentes.
- Garantir que Alembic continua reconhecendo metadata.
- Nao alterar schema funcional nesta issue.

## Criterios de Aceite

- Warning de API depreciada deixa de aparecer.
- Modelos atuais continuam funcionando.
- Alembic continua acessando metadata.
- Testes existentes passam.

## Testes Esperados

- `.\venv\Scripts\python.exe -m pytest -q tests`
- Checagem de Alembic quando aplicavel.

## TDD

Nao obrigatorio, mas testes existentes devem cobrir regressao.

## Riscos

- Quebrar importacao de `Base` usada por modelos e Alembic.
- Misturar refactor tecnico com mudanca de schema.

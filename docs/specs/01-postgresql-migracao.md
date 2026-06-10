# Spec: PostgreSQL e Migracao de Persistencia

## Objetivo

Substituir SQLite como banco-alvo por PostgreSQL em Docker, mantendo a API preparada para ambiente interno com usuarios simultaneos, importacoes, auditoria e backups.

Sucesso significa que a aplicacao consegue rodar com PostgreSQL via variavel de ambiente, aplicar migrations Alembic e manter testes de dominio isolados.

## Tech Stack

- PostgreSQL em container Docker.
- SQLAlchemy como ORM.
- Alembic para migrations.
- Pydantic settings para configuracao.
- Driver PostgreSQL `psycopg` v3 com URL `postgresql+psycopg://...`.
- Pytest para validacao.

## Comandos

- Subir stack: `docker compose up -d --build`
- Aplicar migrations: `.\venv\Scripts\python.exe -m alembic upgrade head`
- Revisao atual: `.\venv\Scripts\python.exe -m alembic current`
- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- Testes de integracao PostgreSQL: `make test-postgres`

## Project Structure

- `core/config.py`: leitura de `DATABASE_URL` e configuracoes futuras.
- `core/database.py`: engine, session e base ORM.
- `docker-compose.yml`: servico PostgreSQL e variaveis da API.
- `alembic/`: migrations compativeis com PostgreSQL.
- `tests/`: cobertura de configuracao, modelos e API.

## Code Style

Configuracao deve ser explicita por ambiente e manter defaults seguros para desenvolvimento local.

Exemplo de decisao de formato:

```python
DATABASE_URL = "postgresql+psycopg://user:password@postgres:5432/classificador"
```

## Testing Strategy

- Testar que a API continua respondendo `/health` com banco online.
- Testar que modelos atuais continuam persistindo em sessao de teste.
- Validar migrations em ambiente controlado.
- Manter testes existentes com banco isolado quando apropriado.
- Manter testes de integracao PostgreSQL em comando dedicado para nao exigir Docker na suite unitaria.
- Adicionar checagem de configuracao para evitar `check_same_thread` em PostgreSQL.

## Boundaries

- Sempre: usar `DATABASE_URL` para selecionar banco.
- Sempre: manter migrations versionadas.
- Sempre: documentar variaveis de ambiente.
- Sempre: preservar as empresas ja cadastradas no SQLite atual durante a migracao para PostgreSQL.
- Sempre: usar script controlado e idempotente para migrar empresas de SQLite para PostgreSQL.
- Sempre: validar duplicidade por `cnpj_cpf`, `cod_dominio` e `api_key` durante a migracao de empresas.
- Sempre: aplicar `connect_args={"check_same_thread": False}` apenas quando o banco for SQLite.
- Sempre: manter PostgreSQL privado na rede Docker, sem exposicao publica.
- Perguntar antes: migrar transacoes/classificacoes antigas.
- Perguntar antes: mudar estrutura de tabelas existentes fora do escopo da spec.
- Nunca: expor porta do PostgreSQL publicamente.
- Nunca: versionar senha real de banco.

## Success Criteria

- Docker Compose inclui PostgreSQL para a aplicacao contabil.
- API roda com PostgreSQL.
- Alembic aplica migrations no PostgreSQL.
- Testes existentes continuam passando.
- Configuracao SQLite legada nao impede uso de PostgreSQL.
- Empresas existentes no SQLite atual sao migradas para PostgreSQL.
- Reexecutar a migracao de empresas nao duplica registros.
- `.env.example` documenta credenciais locais ficticias e variaveis necessarias.
- Riscos de backup e migracao estao documentados.
- Comando dedicado valida migrations e `/health` contra PostgreSQL real sem interferir nos testes unitarios.

## Decisoes Aprovadas

- PostgreSQL sera o banco operacional alvo.
- SQLite fica como legado e/ou banco de teste quando util.
- A migracao de dados existentes sera obrigatoria apenas para empresas.
- Transacoes e classificacoes antigas ficam fora da migracao inicial e podem virar backlog conforme `docs/postgresql-operacao.md`.
- A migracao de empresas sera feita por script SQLite -> PostgreSQL, controlado e idempotente.
- O driver PostgreSQL sera `psycopg` v3.
- A API usara `DATABASE_URL` como fonte unica da conexao.
- PostgreSQL nao tera porta publica exposta.
- Credenciais de desenvolvimento serao documentadas em `.env.example` com valores ficticios/locais.
- A estrategia inicial de backup sera manual via `pg_dump`/`pg_restore`, documentada em `docs/postgresql-operacao.md`; automacao, retencao, criptografia, armazenamento externo e teste recorrente de restore ficam como backlog operacional.
- Testes de integracao com PostgreSQL serao executados por `make test-postgres`, em fluxo separado da suite unitaria.

## Open Questions

- A migracao para `sqlalchemy.orm.DeclarativeBase` sera feita junto desta spec ou como issue tecnica separada?

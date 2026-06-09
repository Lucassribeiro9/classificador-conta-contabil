# Issue 002: chore(config): ajustar DATABASE_URL para SQLite e PostgreSQL

## Contexto

O projeto usa `DATABASE_URL` para configurar SQLAlchemy, mas a configuracao atual aplica `connect_args={"check_same_thread": False}` diretamente na engine. Essa opcao e especifica de SQLite e nao deve ser aplicada ao PostgreSQL.

## Escopo

- Ajustar a criacao da engine para detectar o tipo de banco a partir da `DATABASE_URL`.
- Aplicar `check_same_thread=False` apenas quando o banco for SQLite.
- Manter `DATABASE_URL` como fonte unica da conexao.
- Preservar compatibilidade com SQLite em testes/legado.

## Criterios de Aceite

- SQLite continua funcionando com `check_same_thread=False`.
- PostgreSQL nao recebe `check_same_thread`.
- Configuracao continua lendo `DATABASE_URL` via settings.
- Testes existentes continuam passando.

## Testes Esperados

- Teste unitario ou de configuracao cobrindo montagem de argumentos da engine para SQLite.
- Teste unitario ou de configuracao cobrindo montagem de argumentos da engine para PostgreSQL.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio. Criar teste falhando antes de ajustar a configuracao.

## Riscos

- Quebrar testes que usam SQLite em memoria.
- Acoplar teste demais ao detalhe interno da engine. Preferir testar funcao/adapter de configuracao se ela for criada.

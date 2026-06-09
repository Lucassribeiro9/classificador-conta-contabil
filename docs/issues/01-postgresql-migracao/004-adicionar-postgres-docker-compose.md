# Issue 004: chore(docker): adicionar PostgreSQL ao docker-compose

## Contexto

O sistema rodara no servidor Ubuntu com Docker. PostgreSQL sera o banco operacional alvo e nao deve ter porta publica exposta.

## Escopo

- Adicionar servico PostgreSQL ao `docker-compose.yml`.
- Configurar volume persistente para dados do banco.
- Configurar a API para usar `DATABASE_URL` apontando para o servico PostgreSQL.
- Manter PostgreSQL privado na rede Docker, sem publicar porta para fora.
- Nao alterar n8n nesta issue.

## Criterios de Aceite

- `docker compose up -d --build` sobe API e PostgreSQL.
- API consegue resolver o host do banco na rede Docker.
- PostgreSQL nao expoe porta publica no compose.
- Volume de dados do PostgreSQL esta definido.

## Testes Esperados

- Checagem manual com `docker compose up -d --build`.
- Checagem manual de `/health` com API usando PostgreSQL, quando ambiente estiver disponivel.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests` para garantir que nada local quebrou.

## TDD

Nao obrigatorio. Esta issue e infraestrutura.

## Riscos

- Derrubar configuracao atual de n8n/ngrok no compose.
- Expor porta do banco por engano.
- Usar credenciais reais em arquivo versionado.

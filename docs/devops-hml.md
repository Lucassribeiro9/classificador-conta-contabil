# Homologacao com Docker Compose

O arquivo `docker-compose.hml.yml` sobe API, frontend e PostgreSQL exclusivos de
homologacao. O Nginx de borda compartilhado e externo a esta stack: ele deve
estar conectado a rede `classificador-hml-edge`, servir o frontend em `/` e
encaminhar `/api` para a API removendo esse prefixo.

Use somente dados ficticios ou sanitizados. O arquivo `.env.hml` deve existir
apenas no servidor e nunca ser versionado.

## Preparacao

Crie a rede exclusiva que conecta a stack ao proxy compartilhado:

```bash
docker network create classificador-hml-edge
```

Crie `.env.hml` a partir de `.env.hml.example` e substitua todos os valores
`CHANGE_ME` por segredos de homologacao. O banco, usuario e segredos nao devem
ser reutilizados em producao.

Valide a configuracao resolvida antes de subir os servicos:

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml config
```

## Subida

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml up -d --build
docker compose --env-file .env.hml -f docker-compose.hml.yml ps
```

O PostgreSQL nao publica porta no host. API e frontend tambem permanecem sem
portas publicadas e recebem trafego apenas pela rede do proxy.

## Gate e Seed Sanitizado

Preencha os gates aplicaveis de `docs/homologacao-checklist-tecnico.md`. Confirme
no resultado de `docker compose ... ps` que esta e a stack
`classificador-hml`, sem portas publicadas e com o volume
`classificador-hml-postgres-data`.

Execute o seed somente depois que `postgres`, `api` e `frontend` estiverem
`healthy`. Forneca os segredos apenas no ambiente do terminal:

```bash
export HML_ADMIN_PASSWORD='<senha-temporaria>'
export HML_OPERATOR_PASSWORD='<senha-temporaria>'
export HML_COMPANY_API_KEY='<chave-temporaria>'

docker compose --env-file .env.hml -f docker-compose.hml.yml exec \
  -e HML_ADMIN_PASSWORD \
  -e HML_OPERATOR_PASSWORD \
  -e HML_COMPANY_API_KEY \
  api python -m scripts.seed_homologacao

unset HML_ADMIN_PASSWORD HML_OPERATOR_PASSWORD HML_COMPANY_API_KEY
```

O seed exige `APP_ENV=hml`, usa o `DATABASE_URL` da API e pode ser reexecutado
sem duplicar a massa sanitizada. Nao adicione esses tres segredos ao arquivo
`.env.hml`.

## Validacao

Depois que os healthchecks estiverem saudaveis e o proxy estiver configurado,
valide a API e a rota de login usando uma estacao que confie na CA interna:

```bash
curl --fail --show-error --silent https://classificador-hml.interno/api/health
curl --fail --show-error --silent https://classificador-hml.interno/login
```

O primeiro comando deve informar API e banco online. O segundo deve retornar o
HTML da SPA. Revise os logs caso algum servico nao fique saudavel:

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml logs api frontend postgres
```

## Rollback operacional

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml down
```

O comando preserva o volume `classificador-hml-postgres-data`. Remova ou
restaure esse volume somente por procedimento operacional aprovado.

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

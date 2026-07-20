# Homologacao com Docker Compose

O arquivo `docker-compose.hml.yml` sobe API, frontend e PostgreSQL exclusivos de
homologacao. O arquivo `docker-compose.edge.yml` sobe separadamente o Nginx de
borda interno, conectado a rede `classificador-hml-edge`. Ele publica somente
as portas 80 e 443, termina o TLS, serve o frontend em `/` e encaminha
`/api/` para a API removendo esse prefixo.

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

Solicite um certificado emitido pela CA interna para
`classificador-hml.interno`. Instale o certificado e a chave no host nos
caminhos definidos por `HML_TLS_CERT_PATH` e `HML_TLS_KEY_PATH`. Os arquivos
devem ser legiveis pelo Docker, permanecer fora do repositorio e nunca ser
incluidos em imagens. Configure o DNS interno para apontar
`classificador-hml.interno` para o host; para um teste local temporario, use
uma entrada equivalente em `/etc/hosts`.

Valide a configuracao resolvida antes de subir os servicos:

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml config
docker compose --env-file .env.hml -f docker-compose.edge.yml config
```

## Subida

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml up -d --build
docker compose --env-file .env.hml -f docker-compose.hml.yml ps
```

O PostgreSQL nao publica porta no host. API e frontend tambem permanecem sem
portas publicadas e recebem trafego apenas pela rede do proxy. Suba a borda
somente depois que `api` e `frontend` estiverem `healthy`:

```bash
docker compose --env-file .env.hml -f docker-compose.edge.yml up -d
docker compose --env-file .env.hml -f docker-compose.edge.yml ps
```

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

Valide a sintaxe carregada pelo processo em execucao e confirme que Nginx, API
e frontend aparecem conectados a rede, enquanto o PostgreSQL nao aparece:

```bash
docker compose --env-file .env.hml -f docker-compose.edge.yml exec nginx nginx -t
docker network inspect classificador-hml-edge
```

Execute o gate completo definido em `docs/homologacao-smoke-aplicacao.md`:

```bash
python -m scripts.smoke_homologacao --base-url https://classificador-hml.interno
```

Depois que os healthchecks estiverem saudaveis e o proxy estiver configurado,
use os comandos abaixo quando precisar diagnosticar cada rota separadamente em
uma estacao que confie na CA interna:

```bash
curl --fail --show-error --silent https://classificador-hml.interno/api/health
curl --fail --show-error --silent https://classificador-hml.interno/login
```

O primeiro comando deve informar API e banco online. O segundo deve retornar o
HTML da SPA. Revise os logs caso algum servico nao fique saudavel:

```bash
docker compose --env-file .env.hml -f docker-compose.edge.yml logs nginx
docker compose --env-file .env.hml -f docker-compose.hml.yml logs api frontend postgres
```

## Rollback operacional

```bash
docker compose --env-file .env.hml -f docker-compose.edge.yml down
docker compose --env-file .env.hml -f docker-compose.hml.yml down
```

Desligue primeiro a borda para interromper novas requisicoes. O segundo comando
preserva o volume `classificador-hml-postgres-data`. Remova ou
restaure esse volume somente por procedimento operacional aprovado.

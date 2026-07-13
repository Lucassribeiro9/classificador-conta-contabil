# Variaveis de Ambiente

Este documento registra os nomes e exemplos sanitizados de variaveis para
desenvolvimento, homologacao e producao, conforme
`docs/specs/11-frontend-docker-ambientes.md`.

Arquivos `.env` reais nao devem ser versionados. Use `.env.example` e
`frontend/.env.example` apenas como referencia de nomes, sem copiar segredos
reais para o repositorio.

## Variaveis

| Variavel | Uso | Exemplo sanitizado |
| --- | --- | --- |
| `APP_ENV` | Identifica o ambiente da API/stack. | `dev`, `hml`, `prod` |
| `FRONTEND_PUBLIC_URL` | URL publica/interna usada pelos usuarios para acessar a SPA. | `https://classificador-hml.interno` |
| `API_PUBLIC_URL` | URL publica/interna da API quando documentada fora do proxy. | `https://classificador-hml.interno/api` |
| `VITE_APP_ENV` | Identifica o ambiente exposto ao build Vite. | `dev`, `hml`, `prod` |
| `VITE_FRONTEND_PUBLIC_URL` | URL publica/interna da SPA exposta ao frontend. | `https://classificador.interno` |
| `VITE_API_BASE_URL` | Base usada pelo frontend para chamar a API. | `VITE_API_BASE_URL=/api` em hml/prod |
| `DATABASE_URL` | String de conexao da API com PostgreSQL privado. | `postgresql+psycopg://classificador_hml:CHANGE_ME@postgres-hml:5432/classificador_hml` |
| `JWT_SECRET_KEY` | Segredo usado para assinar tokens JWT da API. | `CHANGE_ME_JWT_SECRET_KEY_32_CHARS_MIN` |
| `JWT_ALGORITHM` | Algoritmo JWT configurado na API. | `HS256` |
| `CORS_ALLOWED_ORIGINS` | Origens permitidas para chamadas cross-origin quando necessarias. | `https://classificador-hml.interno` |
| `POSTGRES_DB` | Banco PostgreSQL do ambiente. | `classificador_hml` |
| `POSTGRES_USER` | Usuario PostgreSQL do ambiente. | `classificador_hml` |
| `POSTGRES_PASSWORD` | Senha PostgreSQL do ambiente. | `CHANGE_ME_POSTGRES_PASSWORD_HML` |

## Ambientes

### Desenvolvimento

- `APP_ENV=dev`
- `FRONTEND_PUBLIC_URL=http://localhost:5173`
- `API_PUBLIC_URL=http://localhost:8000`
- `VITE_APP_ENV=dev`
- `VITE_FRONTEND_PUBLIC_URL=http://localhost:5173`
- `VITE_API_BASE_URL=http://localhost:8000`
- `DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}`
- `CORS_ALLOWED_ORIGINS=http://localhost:5173`

### Homologacao

- `APP_ENV=hml`
- `FRONTEND_PUBLIC_URL=https://classificador-hml.interno`
- `API_PUBLIC_URL=https://classificador-hml.interno/api`
- `VITE_APP_ENV=hml`
- `VITE_FRONTEND_PUBLIC_URL=https://classificador-hml.interno`
- `VITE_API_BASE_URL=/api`
- `DATABASE_URL=postgresql+psycopg://classificador_hml:CHANGE_ME@postgres-hml:5432/classificador_hml`
- `JWT_SECRET_KEY=CHANGE_ME_JWT_SECRET_KEY_HML_32_CHARS_MIN`
- `CORS_ALLOWED_ORIGINS=https://classificador-hml.interno`

### Producao

- `APP_ENV=prod`
- `FRONTEND_PUBLIC_URL=https://classificador.interno`
- `API_PUBLIC_URL=https://classificador.interno/api`
- `VITE_APP_ENV=prod`
- `VITE_FRONTEND_PUBLIC_URL=https://classificador.interno`
- `VITE_API_BASE_URL=/api`
- `DATABASE_URL=postgresql+psycopg://classificador_prod:CHANGE_ME@postgres-prod:5432/classificador_prod`
- `JWT_SECRET_KEY=CHANGE_ME_JWT_SECRET_KEY_PROD_32_CHARS_MIN`
- `CORS_ALLOWED_ORIGINS=https://classificador.interno`

## Proxy e CORS

Em homologacao e producao, frontend e API devem ficar na mesma origem. O Nginx
recebe chamadas em `/api` e remove esse prefixo antes de encaminhar para a
FastAPI. Por isso, o build do frontend nesses ambientes deve usar
`VITE_API_BASE_URL=/api`.

CORS nao deve ser usado como controle principal de acesso. Mantenha CORS
restrito aos hosts internos esperados e preserve autenticacao JWT nos endpoints
internos.

## Checklist de Revisao

- `.env`, `.env.hml`, `.env.prod` e variantes reais nao foram versionados.
- `.env.example` e `frontend/.env.example` contem apenas placeholders.
- Segredos reais foram definidos fora do repositorio.
- Homologacao e producao usam bancos, hosts e segredos separados.
- `DATABASE_URL` aponta para PostgreSQL privado, sem porta publica do banco.

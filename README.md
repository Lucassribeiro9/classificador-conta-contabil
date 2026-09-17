# Classificador de Conta Contabil

Aplicacao interna para importar dados contabilizados, consultar informacoes por empresa e apoiar a classificacao com revisao humana. A arquitetura atual e API-first: API FastAPI, SPA React, PostgreSQL e worker assincrono de Razao.

O produto e voltado a operacao interna. Nao envie planilhas reais, credenciais ou tokens para issues, pull requests, exemplos ou logs versionados.

## Visao geral

Fontes de produto e contrato: [PRD](docs/prd/evolucao-plano-contas-importacao-ml.md), [specs](docs/specs/) e [OpenAPI](docs/api-openapi-consumo.md).

## Requisitos locais

- Git;
- Docker Engine com o plugin `docker compose`;
- Python 3 e ambiente virtual para testes ou comandos locais;
- Node.js e npm para executar a SPA fora dos containers.

Comece a partir de um clone novo:

```bash
git clone https://github.com/Lucassribeiro9/classificador-conta-contabil.git
cd classificador-conta-contabil
cp .env.example .env
```

Edite `.env` antes de subir qualquer servico e substitua todos os valores `CHANGE_ME` por valores locais exclusivos. Arquivos `.env` reais nunca devem ser versionados; veja [variaveis de ambiente](docs/devops-env-variaveis.md).

## Containers e stacks disponiveis

O Compose de desenvolvimento (`docker-compose.yml`) define:

| Servico | Finalidade |
| --- | --- |
| `postgres` | Banco PostgreSQL local. |
| `api-contabil` | API FastAPI; aplica migrations ao iniciar. |
| `razao-worker` | Worker da fila assincrona de importacao de Razao. |
| `n8n-test` | Apoio a workflows locais, quando configurado. |
| `cloudflared` | Tunel de borda, quando configurado. |

Homologacao e producao usam stacks separadas em `docker-compose.hml.yml` e `docker-compose.prod.yml`, com proxy de borda e variaveis exclusivas. Nao use arquivos `.env` de homologacao ou producao para desenvolvimento local.

## Matriz de ambientes

| Ambiente | Uso | Fonte atual | Limite |
| --- | --- | --- | --- |
| `dev` | Desenvolvimento local | `docker-compose.yml` e `.env` | Pode recriar apenas recursos locais explicitamente identificados. |
| `hml` | Homologacao interna | `docker-compose.hml.yml` e `.env.hml` no servidor | Preserva dados e evidencias; use somente massa sanitizada. |
| `prod` | Producao interna | `docker-compose.prod.yml` e `.env.prod` no servidor | Requer homologacao aprovada e autorizacao operacional explicita. |
| `all` | Orquestracao padronizada | Futuro — issue [#397](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/397) | Nao esta disponivel como comando unico. |

Os comandos comuns preservam volumes por padrao. Nao remova volumes, banco ou evidencias de homologacao como tentativa de correcao ou rollback.

## Comandos principais

Para subir o nucleo local sem depender dos servicos auxiliares de workflow ou tunel:

```bash
docker compose up -d --build postgres api-contabil razao-worker
docker compose ps
```

A API local fica em `http://localhost:8000`. Consulte logs com `docker compose logs -f api-contabil` e pare os containers com `docker compose down`; isso preserva volumes.

Os alvos atuais do `Makefile` incluem `make build`, `make up-api`, `make test`, `make test-postgres` e `make logs`. Revise o alvo antes de executa-lo, em especial os que removem recursos. `make clean-razao-temp` remove explicitamente o volume temporario do Razao e nao e um comando rotineiro.

`make check` e `make check-full` sao contratos planejados da [#398](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/398); eles ainda nao existem e nao devem ser apresentados como comandos executaveis.

## Subir, testar, limpar cache e consultar logs

Crie um ambiente virtual quando for executar testes locais:

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
make test
```

Para a matriz de integracao PostgreSQL isolada, use `make test-postgres`. Ela cria recursos de teste e faz limpeza ao final; nao a aponte para um ambiente de homologacao ou producao.

O frontend pode ser executado separadamente:

```bash
cd frontend
npm install
npm run dev
```

Os comandos de build, typecheck, lint, testes e Playwright da SPA estao em [frontend/README.md](frontend/README.md). Para limpar somente recursos locais, consulte os alvos `clean-project` e `clean-razao-temp` no `Makefile` e confirme o alvo antes da execucao.

## Notebooks e artefatos auxiliares

Notebooks e arquivos de apoio nao sao o caminho operacional principal. Use apenas artefatos ficticios ou sanitizados nos ambientes de desenvolvimento e homologacao. Planilhas, dumps, tokens, logs brutos e qualquer dado contabil real devem permanecer fora do repositorio.

Os contratos de entrada e os exemplos sanitizados estao em documentos do dominio, como [modelo de Razao](docs/razao-planilha-modelo.md) e [movimentos operacionais](docs/movimentos-operacionais-planilha-modelo.md).

O Streamlit permanece como apoio legado best-effort e nao e o caminho critico da Release 1. A arquitetura-alvo usa a API FastAPI e a SPA; o legado nao deve acessar o banco diretamente nem bloquear a homologacao do frontend interno.

## Workflows operacionais e esteira supervisionada

Os workflows n8n e os servicos de tunel exigem configuracao propria; nao os considere prontos apenas por executar `docker compose up`. Ha uma divergencia conhecida entre referencias legadas a `ngrok` no `Makefile` e o servico `cloudflared` definido no Compose. Ela esta fora deste README e deve ser resolvida em issue propria antes de ser documentada como fluxo confirmado.

A esteira de agentes supervisionada tem estado oficial no GitHub e contrato em [Spec 14](docs/specs/14-esteira-agentes-supervisionada.md) e no [protocolo operacional](docs/agent-protocol.md). Cada issue requer Task Review, aprovacao humana e evidencias proprias; a esteira nao substitui o fluxo manual.

## API, OpenAPI e autenticacao

Com a API local em execucao, os pontos de consulta sao:

- Swagger UI: `http://localhost:8000/docs`;
- ReDoc: `http://localhost:8000/redoc`;
- schema: `http://localhost:8000/openapi.json`;
- health: `http://localhost:8000/health`.

O OpenAPI e a fonte canonica de endpoints e payloads. O guia de consumo traz exemplos sanitizados e a estrategia de autenticacao: [docs/api-openapi-consumo.md](docs/api-openapi-consumo.md). Usuarios humanos usam login e JWT; nunca inclua tokens, senhas ou chaves de servico em comandos salvos, screenshots ou evidencias.

## Homologacao manual e evidencias

Homologacao ocorre em ambiente interno separado e com massa sanitizada. O roteiro formal do Ciclo 0 registra ambiente, commit, responsaveis, cenarios, evidencias tratadas, divergencias e decisao final: [docs/homologacao/roteiro-ciclo-0.md](docs/homologacao/roteiro-ciclo-0.md).

Use tambem o [checklist tecnico](docs/homologacao-checklist-tecnico.md), o [roteiro de operador/contador](docs/homologacao-roteiro-operador-contador.md) e o [smoke da aplicacao](docs/homologacao-smoke-aplicacao.md). O deploy manual de HML e producao esta em [docs/deploy-interno-manual.md](docs/deploy-interno-manual.md).

## Troubleshooting

- Execute `docker compose ps` e `docker compose logs -f api-contabil` antes de reiniciar servicos locais.
- Confirme que `.env` existe e que seus placeholders foram substituidos antes de diagnosticar falhas de configuracao.
- Para contratos de API, consulte o OpenAPI em vez de inferir payloads por exemplos antigos.
- Para HML ou producao, siga os runbooks correspondentes; nao reutilize Compose, volumes ou segredos locais.
- Nao use `make up-infra` como caminho confirmado enquanto a divergencia `ngrok`/`cloudflared` permanecer aberta.

## Seguranca, dados sensiveis e producao

Nunca versione `.env` reais, senhas, tokens, chaves privadas, planilhas de clientes, dumps de banco, logs brutos ou telemetria privada. Mantenha bancos, volumes, hosts e segredos separados entre dev, HML e producao.

Operacoes mutaveis em producao — inclusive subida de containers, migrations, carga de dados, limpeza e rollback — exigem autorizacao humana explicita e o procedimento documentado. A producao interna so pode avancar depois da homologacao aprovada; detalhes estao em [docs/devops-prod.md](docs/devops-prod.md).

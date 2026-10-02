# Comandos facilitadores
# Usa o plugin moderno do Docker Compose (`docker compose`)
DOCKER_COMPOSE := docker compose
PYTHON ?= ./venv/bin/python
CHECK_PYTHON ?= $(PYTHON)
CHECK_BASE_REF ?= origin/main
CHECK_FULL_GATES := security backend postgres frontend playwright compose docs
DOCKER ?= docker
DEV_ENV_FILE := .env
HML_ENV_FILE := .env.hml
PROD_ENV_FILE := .env.prod
LOG_TAIL := 200
DEV_COMPOSE := $(DOCKER_COMPOSE) --env-file $(DEV_ENV_FILE) -f docker-compose.yml
HML_COMPOSE := $(DOCKER_COMPOSE) --env-file $(HML_ENV_FILE) -f docker-compose.hml.yml
HML_EDGE_COMPOSE := $(DOCKER_COMPOSE) --env-file $(HML_ENV_FILE) -f docker-compose.edge.yml
PROD_COMPOSE := $(DOCKER_COMPOSE) --env-file $(PROD_ENV_FILE) -f docker-compose.prod.yml
# Volume temporário removido somente pelo alvo explícito clean-razao-temp.
export RAZAO_TEMP_VOLUME_NAME ?= classificador-dev-razao-temp
# Projeto Docker Compose isolado para testes de integracao PostgreSQL
DOCKER_COMPOSE_TEST := RAZAO_TEMP_VOLUME_NAME=classificador-conta-contabil-test-razao-temp docker compose -p classificador-conta-contabil-test
# Nome do serviço principal da API no `docker-compose.yml`
SERVICE_API := api-contabil
# Serviços auxiliares de infraestrutura (orquestração e túnel)
SERVICES_INFRA := n8n-test ngrok
# Agrupa todos os serviços para comandos de build/rebuild completos
SERVICES_ALL := $(SERVICE_API) $(SERVICES_INFRA)
# Serviço do banco de dados PostgreSQL (usado para logs e testes)
SERVICE_DB := postgres
# Declara targets "falsos" para evitar conflito com arquivos de mesmo nome
.PHONY: build rebuild build-all rebuild-all up up-with-test up-api up-infra up-build down logs shell clean-project clean-razao-temp test test-postgres migrate-create migrate-up migrate-down migrate-current dev-build dev-test dev-clean-cache dev-logs dev-up dev-down hml-build hml-test hml-clean-cache hml-logs hml-up hml-down edge-up edge-down prod-test prod-logs prod-build prod-clean-cache prod-up prod-down registry-login all-build all-test all-clean-cache all-logs check check-full check-security check-backend check-postgres check-frontend check-playwright check-compose check-docs

.NOTPARALLEL: check check-full

ifneq ($(filter check,$(MAKECMDGOALS)),)
CHECK_GATES := $(shell $(CHECK_PYTHON) scripts/check_scope.py --base-ref "$(CHECK_BASE_REF)")
ifneq ($(.SHELLSTATUS),0)
$(error make check nao conseguiu determinar o escopo; consulte a mensagem check-scope acima)
endif
endif

# Constroi somente a stack local de desenvolvimento.
dev-build:
	$(DEV_COMPOSE) build

# A suite local canonica nao depende de nenhuma stack Compose.
dev-test: test

# Limpeza escopada da stack local; volumes nao sao removidos.
dev-clean-cache:
	$(DEV_COMPOSE) down --rmi local

dev-logs:
	$(DEV_COMPOSE) logs -f --tail $(LOG_TAIL)

# Sobe e para a stack local, preservando os volumes por padrao.
dev-up:
	$(DEV_COMPOSE) up -d --wait

dev-down:
	$(DEV_COMPOSE) down

# HML inclui o proxy de borda, que usa a mesma rede externa da stack principal.
hml-build:
	$(HML_COMPOSE) build
	$(HML_EDGE_COMPOSE) pull

hml-test: test

hml-clean-cache:
	$(HML_COMPOSE) down --rmi local
	$(HML_EDGE_COMPOSE) down --rmi local

hml-logs:
	$(HML_COMPOSE) logs -f --tail $(LOG_TAIL)
	$(HML_EDGE_COMPOSE) logs -f --tail $(LOG_TAIL)

# HML deve estar saudavel antes de iniciar a borda; a rede externa e gerida fora do Compose.
hml-up:
	$(HML_COMPOSE) config --quiet
	$(DOCKER) network inspect classificador-hml-edge
	$(HML_COMPOSE) up -d --wait

edge-up: hml-up
	$(HML_EDGE_COMPOSE) config --quiet
	$(HML_EDGE_COMPOSE) up -d --wait

# Pare a borda antes da stack HML para interromper novas requisicoes com seguranca.
edge-down:
	$(HML_EDGE_COMPOSE) down

hml-down: edge-down
	$(HML_COMPOSE) down

# Testes locais sao a validacao segura para producao: nao iniciam recursos da stack.
prod-test: test

prod-logs:
	$(PROD_COMPOSE) logs -f --tail $(LOG_TAIL)


# Acoes que modificam recursos de producao exigem a confirmacao do alvo exato.
prod-build:
	@if [ "$(CONFIRM_PROD)" != "prod-build" ]; then echo "Defina CONFIRM_PROD=prod-build para continuar." >&2; exit 2; fi
	$(PROD_COMPOSE) build

prod-clean-cache:
	@if [ "$(CONFIRM_PROD)" != "prod-clean-cache" ]; then echo "Defina CONFIRM_PROD=prod-clean-cache para continuar." >&2; exit 2; fi
	$(PROD_COMPOSE) down --rmi local

# Acoes de producao validam configuracao e rede externa antes de alterar containers.
prod-up:
	@if [ "$(CONFIRM_PROD)" != "prod-up" ]; then echo "Defina CONFIRM_PROD=prod-up para continuar." >&2; exit 2; fi
	$(PROD_COMPOSE) config --quiet
	@if ! $(DOCKER) network inspect classificador-prod-edge >/dev/null 2>&1; then echo "Criando rede externa classificador-prod-edge."; $(DOCKER) network create classificador-prod-edge >/dev/null; fi
	$(PROD_COMPOSE) up -d --wait

prod-down:
	@if [ "$(CONFIRM_PROD)" != "prod-down" ]; then echo "Defina CONFIRM_PROD=prod-down para continuar." >&2; exit 2; fi
	$(PROD_COMPOSE) config --quiet
	$(PROD_COMPOSE) down

# Credenciais devem ser fornecidas pelo ambiente ou secret manager e nunca persistidas.
registry-login:
	@if [ -z "$$REGISTRY_HOST" ] || [ -z "$$REGISTRY_USERNAME" ] || [ -z "$$REGISTRY_TOKEN" ]; then echo "Defina REGISTRY_HOST, REGISTRY_USERNAME e REGISTRY_TOKEN no ambiente." >&2; exit 2; fi
	@printf '%s' "$$REGISTRY_TOKEN" | $(DOCKER) login "$$REGISTRY_HOST" --username "$$REGISTRY_USERNAME" --password-stdin

# Agregadores seguros: operacoes mutaveis em producao nunca sao encadeadas.
all-build: dev-build hml-build
all-test: test
all-clean-cache: dev-clean-cache hml-clean-cache
all-logs: dev-logs hml-logs prod-logs

# Build da imagem da API usando cache (mais rápido no dia a dia)
build:
	$(DOCKER_COMPOSE) build $(SERVICE_API)

# Rebuild da API sem cache (útil quando cache está inconsistente)
rebuild:
	$(DOCKER_COMPOSE) build --no-cache $(SERVICE_API)

# Build de todos os serviços definidos neste projeto
build-all:
	$(DOCKER_COMPOSE) build $(SERVICES_ALL)

# Rebuild de todos os serviços sem cache
rebuild-all:
	$(DOCKER_COMPOSE) build --no-cache $(SERVICES_ALL)

# Sobe todos os serviços em background sem forçar rebuild
up:
	$(DOCKER_COMPOSE) up -d
# Subir fazendo teste
up-with-test: test
	$(DOCKER_COMPOSE) up -d

# Sobe apenas a API (fluxo mais rápido para desenvolvimento da aplicação)
up-api:
	$(DOCKER_COMPOSE) up -d $(SERVICE_API)

# Sobe apenas serviços auxiliares (n8n e ngrok)
up-infra:
	$(DOCKER_COMPOSE) up -d $(SERVICES_INFRA)

# Sobe a API e o banco de dados (útil para testes e logs)
up-api-db:
	$(DOCKER_COMPOSE) up -d $(SERVICE_API) $(SERVICE_DB)
# Sobe todos os serviços forçando build das imagens
up-build:
	$(DOCKER_COMPOSE) up -d --build

# Para e remove containers, rede e recursos criados pelo compose
down:
	$(DOCKER_COMPOSE) down

# Acompanha logs em tempo real apenas da API
logs:
	$(DOCKER_COMPOSE) logs -f $(SERVICE_API)

# Abre shell interativo dentro do container da API
shell:
	$(DOCKER_COMPOSE) exec $(SERVICE_API) bash

# Remove somente containers, rede e imagens locais deste Compose; preserva volumes.
clean-project:
	$(DOCKER_COMPOSE) down --rmi local

# Remove explicitamente apenas o volume temporário do Razão em desenvolvimento.
# O PostgreSQL permanece preservado; pare o projeto antes de remover o volume.
clean-razao-temp:
	$(DOCKER_COMPOSE) down
	docker volume rm $(RAZAO_TEMP_VOLUME_NAME)

# Executa os testes do projeto no ambiente virtual local
test:
	$(PYTHON) -m pytest -q tests

# Executa testes de integracao reais contra PostgreSQL na rede Docker
test-postgres:
	$(DOCKER_COMPOSE_TEST) up -d --build $(SERVICE_DB)
	$(DOCKER_COMPOSE_TEST) run --build --rm $(SERVICE_API) sh -c "python -m alembic upgrade head && python -m pytest -q -m integration_postgres tests/integration"
	$(DOCKER_COMPOSE_TEST) down -v

# Gate proporcional ao diff. A classificacao e avaliada antes de qualquer gate.
check: check-security $(addprefix check-,$(CHECK_GATES))
	@echo "[check] escopo detectado por scripts/check_scope.py: $(CHECK_GATES)"
	@echo "[check] validacao proporcional concluida"

# Gate ampliado e deterministico para pre-merge, release e homologacao tecnica.
check-full: $(addprefix check-,$(CHECK_FULL_GATES))
	@echo "[check-full] matriz completa concluida"

check-security:
	@echo "[check] security"
	$(CHECK_PYTHON) scripts/check_diff_security.py --base-ref "$(CHECK_BASE_REF)"

check-backend:
	@echo "[check] backend"
	$(PYTHON) -m pytest -q tests

check-postgres:
	@echo "[check] postgres"
	@set -eu; \
		cleanup() { $(DOCKER_COMPOSE_TEST) down -v; }; \
		trap cleanup EXIT INT TERM; \
		$(DOCKER_COMPOSE_TEST) up -d --build $(SERVICE_DB); \
		$(DOCKER_COMPOSE_TEST) run --build --rm $(SERVICE_API) sh -c \
			"python -m alembic upgrade head && python -m pytest -q -m integration_postgres tests/integration"

check-frontend:
	@echo "[check] frontend"
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm test
	cd frontend && npm run build

check-playwright:
	@echo "[check] playwright"
	cd frontend && npm run test:e2e

check-compose:
	@echo "[check] compose"
	$(DOCKER_COMPOSE) --env-file .env.example -f docker-compose.yml config --quiet
	$(DOCKER_COMPOSE) --env-file .env.hml.example -f docker-compose.hml.yml config --quiet
	$(DOCKER_COMPOSE) --env-file .env.hml.example -f docker-compose.edge.yml config --quiet
	$(DOCKER_COMPOSE) --env-file .env.prod.example -f docker-compose.prod.yml config --quiet

check-docs:
	@echo "[check] docs"
	$(PYTHON) -m pytest -q tests/test_*docs.py

# Executa testes no ambiente Windows
test-win:
	.\venv\Scripts\python -m pytest -q tests
# Cria migration nova (uso: make migrate-create MSG="add is_active")
migrate-create:
	./venv/bin/python -m alembic revision --autogenerate -m "$(MSG)"

# Aplica todas as migrations pendentes
migrate-up:
	./venv/bin/python -m alembic upgrade head

# Volta 1 migration (ou defina REV=-1 / <revision_id>)
migrate-down:
	./venv/bin/python -m alembic downgrade $(or $(REV),-1)

# Mostra revisão atual aplicada no banco
migrate-current:
	./venv/bin/python -m alembic current

# Comandos facilitadores
# Usa o plugin moderno do Docker Compose (`docker compose`)
DOCKER_COMPOSE := docker compose
# Nome do serviço principal da API no `docker-compose.yml`
SERVICE_API := api-contabil
# Serviços auxiliares de infraestrutura (orquestração e túnel)
SERVICES_INFRA := n8n-test ngrok
# Agrupa todos os serviços para comandos de build/rebuild completos
SERVICES_ALL := $(SERVICE_API) $(SERVICES_INFRA)

# Declara targets "falsos" para evitar conflito com arquivos de mesmo nome
.PHONY: build rebuild build-all rebuild-all up up-api up-infra up-build down logs shell clean-cache test

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

# Remove cache de build do Docker para liberar espaço e limpar estado
clean-cache:
	docker builder prune -f

# Executa os testes do projeto no ambiente virtual local
test:
	./venv/bin/python -m pytest -q tests

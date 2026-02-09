# Comandos facilitadores
up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f api-contabil

shell:
	docker exec -it api-contabil bash

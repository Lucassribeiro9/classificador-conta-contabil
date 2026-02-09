# Comandos facilitadores
deploy:
	docker-compose down -v && \
	docker compose up -d --build && \
	echo "Deploy concluído! Acesse: http://localhost:8000/docs"

logs:
	docker-compose logs -f api-contabil

shell:
	docker exec -it api-contabil bash

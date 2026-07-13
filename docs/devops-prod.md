# Producao interna com Docker Compose

O arquivo `docker-compose.prod.yml` sobe API, frontend e PostgreSQL exclusivos
de producao. O proxy compartilhado deve estar conectado apenas a rede
`classificador-prod-edge` dessa stack, servir a SPA em `/` e encaminhar `/api`
para a API removendo o prefixo.

O arquivo `.env.prod` e os dados reais devem permanecer fora do repositorio.
DNS interno, certificados da CA interna e firewall restrito as sub-redes
autorizadas sao pre-requisitos operacionais.

## Gate de liberacao

Nao execute a subida enquanto todos os itens abaixo nao estiverem confirmados:

- [ ] Homologacao aprovada pelo responsavel da operacao.
- [ ] Falhas conhecidas e testes backend revisados.
- [ ] Frontend com typecheck, lint e build verdes.
- [ ] Banco, volume, usuarios e segredos exclusivos de producao.
- [ ] Autorizacao explicita para carregar dados reais.
- [ ] Estrategia de backup testada antes da carga inicial.
- [ ] Versao anterior e procedimento de rollback registrados.
- [ ] Proxy, HTTPS, DNS interno e firewall validados.

## Preparacao

Crie a rede exclusiva que conecta a stack ao proxy compartilhado:

```bash
docker network create classificador-prod-edge
```

Crie `.env.prod` a partir de `.env.prod.example` e substitua todos os valores
`CHANGE_ME` por segredos de producao. Nao reutilize valores de desenvolvimento
ou homologacao.

Revise a configuracao resolvida antes de qualquer alteracao nos containers:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config
```

Confirme na saida que nao existem portas publicadas para frontend, API ou
PostgreSQL e que nenhum host, volume ou rede pertence a outro ambiente.

## Subida manual

Depois da aprovacao do gate:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

## Validacao

Em uma estacao autorizada e com a CA interna confiavel:

```bash
curl --fail --show-error --silent https://classificador.interno/api/health
curl --fail --show-error --silent https://classificador.interno/login
```

O healthcheck deve informar API e banco online. A rota de login deve retornar o
HTML da SPA. Registre as evidencias e revise os logs antes de liberar usuarios:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs api frontend postgres
```

## Rollback operacional

Interrompa a stack se a validacao falhar:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

O volume `classificador-prod-postgres-data` e preservado por padrao. Restaure a
versao anterior das imagens e, quando necessario, o backup validado seguindo o
procedimento operacional aprovado. Nunca remova o volume como tentativa de
rollback sem autorizacao explicita.

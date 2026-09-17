# Operacao e recuperacao da fila assincrona de Razao

Este guia complementa a [Spec 04](specs/04-importacao-razao-normalizacao.md) e o [OpenAPI](api-openapi-consumo.md). A spec permanece o contrato canonico; este documento nao redefine endpoints, schemas ou runbooks.

Use somente arquivos ficticios ou sanitizados. Nao publique tokens, planilhas, payloads ou logs brutos, caminhos internos nem dados contabeis reais.

## Componentes e configuracao

A API recebe o upload, persiste o lote no PostgreSQL e responde sem aguardar processamento. `razao-worker`, na mesma imagem, consome a fila e compartilha somente o volume temporario privado.

| Configuracao | Padrao | Uso |
| --- | ---: | --- |
| `RAZAO_UPLOAD_MAX_BYTES` | 50.000.000 | `413` acima do limite. |
| `RAZAO_STORAGE_MIN_FREE_BYTES` | 5.000.000.000 | Reserva absoluta. |
| `RAZAO_STORAGE_MIN_FREE_RATIO` | 0,15 | Reserva proporcional. |
| `RAZAO_FAILED_RETENTION_SECONDS` | 86.400 | Retencao de arquivo `failed`. |
| `RAZAO_IMPORT_BLOCK_SIZE` | 1.000 | Bloco interno. |
| `RAZAO_WORKER_CONCURRENCY` | 1 | Consumidores. |
| `RAZAO_HEARTBEAT_SECONDS` | 30 | Renovacao do heartbeat. |
| `RAZAO_LEASE_SECONDS` | 600 | Lease exclusiva renovavel. |
| `RAZAO_POLL_INTERVAL_SECONDS` | 3 | Espera ociosa e polling. |

Os valores efetivos pertencem ao ambiente. Nao reutilize segredos entre dev, HML e producao. O armazenamento temporario e diferente do arquivamento permanente futuro da [#96](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/96).

## Iniciar, parar e inspecionar

### Desenvolvimento

Com `.env` local completo:

```bash
docker compose up -d --build postgres api-contabil razao-worker
docker compose ps
docker compose logs -f api-contabil razao-worker
docker compose down
```

`docker compose down` preserva volumes. O temporario usa `RAZAO_TEMP_VOLUME_NAME` (padrao `classificador-dev-razao-temp`). Nao execute `make clean-razao-temp` durante upload, processamento, retry ou investigacao: ele remove explicitamente esse volume.

### Homologacao

No servidor autorizado, siga [docs/devops-hml.md](devops-hml.md). Com `.env.hml` fora do repositorio e borda preparada:

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml up -d --build
docker compose --env-file .env.hml -f docker-compose.hml.yml ps
docker compose --env-file .env.hml -f docker-compose.hml.yml logs api razao-worker
docker compose --env-file .env.hml -f docker-compose.edge.yml down
docker compose --env-file .env.hml -f docker-compose.hml.yml down
```

Preserve `classificador-hml-razao-temp` e `classificador-hml-postgres-data`.

### Producao

Execute somente depois da homologacao aprovada, do gate e da autorizacao operacional em [docs/devops-prod.md](devops-prod.md):

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs api razao-worker
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

Nunca remova `classificador-prod-razao-temp` ou `classificador-prod-postgres-data` para recuperar lote. Rollback, restauracao e dados reais seguem o procedimento aprovado, nao este guia.

## Upload, polling e estados

O endpoint e `POST /api/v1/companies/{company_id}/razao/import`. Exemplo local sanitizado:

```bash
curl --show-error --silent --include -X POST \
  "http://localhost:8000/api/v1/companies/123/razao/import" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>" \
  -F "file=@razao-sanitizado.xlsx"
```

Arquivo novo retorna `202 Accepted`, `Retry-After: 3`, `lote_id`, `status: "queued"` e `status_url`. Consulte o `status_url`, sem reenviar o arquivo:

```bash
curl --show-error --silent \
  "http://localhost:8000/api/v1/companies/123/razao/lotes/123" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

| Estado | Acao segura |
| --- | --- |
| `queued` | Confirmar worker saudavel e continuar polling. |
| `processing` | Aguardar; nao iniciar outro consumidor nem apagar arquivo. |
| `completed` | Registrar resultado sanitizado. |
| `completed_with_warnings` | Consultar resumo/paginacao; saldos pertencem a [#413](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/413). |
| `failed` | Usar `retry_url` se o arquivo temporario ainda existir. |

`total_linhas` pode ser `null` antes do parser conhecer o total. Erros publicos incluem mensagem segura e `request_id`, nunca traceback ou caminho local; confira o schema no OpenAPI.

## Idempotencia, falhas e retry

Mesmo hash para a mesma empresa reutiliza o lote: `queued` ou `processing` retorna `202`; `completed` ou `completed_with_warnings`, `200`; `failed`, `409 Conflict` com `retry_url`. Nao crie outro lote para contornar falha.

```bash
curl --show-error --silent --include -X POST \
  "http://localhost:8000/api/v1/companies/123/razao/lotes/123/retry" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

O retry manual aceita apenas lote `failed`, permissao operacional e arquivo retido; retorna `202`, conserva a identidade e volta a `queued`. Se expirou, a API devolve erro seguro: envie arquivo corrigido como novo upload. O worker faz no maximo uma repeticao automatica para falha tecnica transitoria; ela nao substitui o retry manual.

Upload acima do limite recebe `413`; capacidade temporaria insuficiente, `507`. Em ambos nao existe lote incompleto. Registre somente `lote_id`, `request_id`, codigo publico, estado e ambiente.

## Recuperacao, limpeza e rollback

A lease dura 10 minutos e o heartbeat a renova a cada 30 segundos. Depois de reiniciar API ou worker, confirme `postgres`, API e `razao-worker` saudaveis e consulte os lotes afetados. Lease expirada pode ser recuperada por outro worker; falha transitoria pode voltar a `queued` dentro do limite de tentativas.

Nao altere manualmente lease, heartbeat, contadores ou estado no banco. Com heartbeat estagnado, inspecione logs sanitizados e ambiente antes de qualquer mudanca de lease.

O worker executa `cleanup()` quando esta ocioso e apos processamentos. Ela remove apenas falhas expiradas e orfaos; preserva `queued`, `processing`, arquivos sob trava e leases validas. Arquivos de sucesso saem depois do commit. Nao apague `.storage.lock`, diretorios ou arquivos temporarios enquanto houver consumidores ativos.

Para rollback, suspenda consumidores e limpeza, preserve jobs ativos e vinculos privados, e siga o runbook do ambiente. A fila nao arquiva arquivo original permanentemente. Logs tecnicos pertencem a [#404](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/404).

## Evidencias, referencias e limites

No PR, registre commit, ambiente, comando de subida, `ps` resumido, upload sanitizado, polling ate estado terminal e retry ou expiracao quando aplicavel. Inclua rollback planejado e TDD nao aplicavel. Use o [benchmark assincrono](../benchmarks/README-razao-async.md) apenas com dados sinteticos; ele nao prova responsividade HTTP sem sonda real nem substitui homologacao.

- [Armazenamento temporario](razao-armazenamento-temporario.md): admissao, vinculo privado, locks e volume.
- [#95](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/95) foi superada pela fila duravel da [#473](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/473) e Spec 04 aprovada na [#475](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/475).

Nao implemente nesta entrega armazenamento permanente, logs tecnicos, saldos, API, worker, Compose, Makefile ou infraestrutura.

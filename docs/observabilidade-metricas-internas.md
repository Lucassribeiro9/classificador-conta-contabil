# Métricas operacionais internas

## Superfície de coleta

A API atende tráfego de aplicação na porta 8000. API e workers abrem um
listener Prometheus próprio na porta 9000 somente quando `METRICS_NETWORK_PEER`
está configurado. Em HML e produção, o valor é `postgres`: o listener descobre o
endereço local usado para alcançar o PostgreSQL e se vincula apenas à interface
da rede `hml-db` ou `prod-db`, ambas `internal: true`. Não há publicação de
porta no host nem rota no proxy. O frontend e o proxy não participam dessas
redes. Fora desses perfis, o exporter fica desativado por padrão.

Um coletor aprovado deve ingressar **somente** na rede interna do perfil e
consultar `http://api:9000/metrics`, `http://ml-worker:9000/metrics` e
`http://razao-worker:9000/metrics` com intervalo inicial de 60 segundos. A API
expõe métricas de processo, HTTP e banco; cada worker expõe apenas métricas do
próprio processo. Use nomes de job distintos no coletor. O acesso à rede do
coletor, suas credenciais e a retenção do TSDB são responsabilidade da operação
interna; não publique Grafana ou Prometheus na internet. A porta
9000 não deve ser encaminhada pelo proxy. Antes da ativação, confirme o
endereço de bind no contêiner e o bloqueio pela URL pública do ambiente.

As séries usam apenas método HTTP conhecido, template de rota, classe de status,
tipo/estado de job e estados fechados do domínio. Nunca incluem empresa, usuário,
job, request ID, caminho efetivo, query string, histórico, conta, filename,
payload, segredo ou telemetria do `agent_runner`. Logs JSON da #404 e
`audit_events` mantêm suas finalidades e retenções próprias.

## Séries e painéis mínimos

| Painel | Série ou consulta PromQL | Leitura |
| --- | --- | --- |
| Disponibilidade do scrape | `up{job="classificador-api"}` e `classificador_operational_db_up` | Exporter e consulta agregada ao banco |
| Recursos dos serviços | `rate(process_cpu_seconds_total[5m])`, `process_resident_memory_bytes` por job do coletor | CPU e memória da API e dos workers |
| Tráfego e erros | `sum by (status) (rate(classificador_http_requests_total[5m]))` | Classes 2xx a 5xx |
| Latência p95 | `histogram_quantile(0.95, sum by (le, route) (rate(classificador_http_request_duration_seconds_bucket[5m])))` | Templates de rota, sem URLs reais |
| Fila ML | `sum by (kind, status) (classificador_ml_jobs)` | Jobs duráveis por tipo e estado |
| Espera ML | `classificador_ml_job_queue_oldest_seconds` | Idade do job mais antigo em fila por tipo |
| Progresso ML | `classificador_ml_job_progress_percent` | Média dos jobs em execução por tipo |
| Qualidade do Razão | `classificador_razao_batches`, `classificador_razao_invalid_lines`, `classificador_razao_warnings` | Estados e totais históricos agregados |
| Revisões e sugestões | `classificador_review_items`, `classificador_ml_movements` | Estados atuais, inclusive `sugerido` e `revisao` |
| Modelos | `classificador_ml_models` | Versões `candidate`, `active` e `retired` |

As séries de banco são **gauges de estado atual ou totais históricos**, não
contadores de eventos. Totais podem diminuir após limpeza legítima. Uma série
ausente para um estado significa zero registros desse estado; o painel deve
tratar ausência como zero onde fizer sentido. `classificador_operational_db_up=0`
invalida a leitura dos demais gauges do scrape. A métrica HTTP mede o tempo do
handler até o início da resposta.

## Alertas iniciais

Os limiares abaixo são ponto de partida para HML e precisam de calibração com
histórico sintético ou autorizado antes de produção:

- `up{job=~"classificador-(api|ml-worker|razao-worker)"} == 0` por 2 minutos: verificar processo e rede interna.
- `classificador_operational_db_up == 0` por 2 minutos: verificar PostgreSQL e migrations.
- `classificador_ml_job_queue_oldest_seconds > 900` por 10 minutos: verificar worker, leases e capacidade do pool `ml/cpu`.
- `classificador_ml_jobs{status="failed"} > 0` ou aumento de `classificador_razao_batches{status="failed"}`: investigar códigos técnicos sanitizados e retry permitido.
- `sum(rate(classificador_http_requests_total{status="5xx"}[5m])) / clamp_min(sum(rate(classificador_http_requests_total[5m])), 1) > 0.05` por 10 minutos: investigar erros de API.
- Crescimento inesperado de `classificador_razao_invalid_lines`, `classificador_razao_warnings` ou `classificador_ml_movements{status="revisao"}`: conferir qualidade de dados e fila de revisão, sem inspecionar conteúdo em painéis.

Nenhum alerta deve incluir labels livres, payloads, IDs de cliente ou exemplos
contábeis. Configure entrega e retenção de alertas somente no ambiente interno.

## Runbook de degradação

1. Anote ambiente, commit implantado, janela do incidente, série afetada e
   status do scrape, sem copiar amostras sensíveis para relatórios.
2. Se o scrape falhar, confira saúde da API e do contêiner, a rede interna e o
   bind da porta 9000. Confirme que a URL pública do proxy não chega ao
   exporter. Não publique a porta para depurar.
3. Se `classificador_operational_db_up=0`, confira saúde do PostgreSQL e
   migrations antes de interpretar filas ou qualidade. Os gauges podem estar
   incompletos nesse estado.
4. Se a fila ML crescer, compare `queued`, `running`, idade e progresso;
   verifique worker, lease vencida e retry conforme
   [operação dos jobs](ml-jobs-operacao.md). Não altere linhas diretamente.
5. Se crescerem erros ou revisões, confira logs técnicos sanitizados e os
   estados funcionais pela interface autorizada. Auditoria é consultada só
   pelo fluxo próprio.
6. Para rollback, reimplante a imagem e o arquivo Compose anteriores em
   janela controlada, seguindo o procedimento do perfil. A instrumentação de
   requisições é best effort e não altera os estados de negócio. Revalide
   `/api/health` e confirme que a porta 9000 não está publicada.

## Roteiro de homologação

Use dados sintéticos e registre commit, perfil, ambiente, horário, roteiro,
evidências sanitizadas, divergências e resultado `APROVADO`, `REPROVADO` ou
`BLOQUEADO`.

1. Suba o perfil isolado após migrations e confirme `/api/health` pelo proxy.
2. Do contêiner coletor na rede `hml-db`, consulte os três alvos na porta 9000.
   Confira séries HTTP e `classificador_operational_db_up=1` na API, além de
   CPU e memória de cada processo.
3. Gere um job ML sintético e uma importação sintética; compare estados, idade
   de fila, progresso e qualidade com a operação autorizada. Não anexe
   payloads, IDs ou planilhas à evidência.
4. Pelo proxy público de HML, tente `/metrics` e `/api/metrics` e confirme que
   não retornam as séries. Confira também que não há porta 9000 publicada no
   host nem encaminhamento no proxy.
5. Revise a captura sanitizada para ausência de valores contábeis, nomes,
   identificadores, caminhos reais, queries, segredos e telemetria agentic.

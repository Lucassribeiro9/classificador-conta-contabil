# Benchmark da importação assíncrona do Razão

Este harness produz somente dados sintéticos determinísticos. Ele não lê nem
publica arquivos contábeis reais.

## Execução reproduzível

```bash
./venv/bin/python -m benchmarks.razao_async \
  --rows 20000 --seed 484 --block-size 1000 \
  --output /tmp/razao-async-benchmark.json
```

O JSON registra versão do Python, plataforma, tamanho, seed, quantidade de
blocos, tempo e pico de memória das fases de geração/parsing sintético,
validação, persistência simulada por blocos e serialização. Tempo absoluto não
é gate: serve apenas para comparação quando as duas execuções usam o mesmo
ambiente.

Os gates do comando são estruturais. Sem uma sonda injetada pela suíte, o gate
`api_responsive_during_job` permanece falso; a responsividade HTTP real deve
ser validada e registrada separadamente. O harness não substitui PostgreSQL
nem afirma latência de produção.

## Gates e testes responsáveis

| Contrato | Evidência |
| --- | --- |
| Fixture determinística, meses, inválidos e warnings | `tests/test_razao_async_benchmark.py` |
| Consultas proporcionais aos blocos | `tests/integration/test_razao_importer_blocks_postgresql.py` |
| Posse concorrente e lease perdida sem commit | `tests/integration/test_razao_worker_postgresql.py` |
| Interrupção, reinício e limite de tentativas | `tests/test_razao_worker.py` |
| Upload/retry concorrente | `tests/test_razao_async_upload_api.py` e `tests/test_razao_status_retry_api.py` |
| Warnings normalizados e compatibilidade legada | `tests/test_razao_warnings_api.py` e `tests/integration/test_razao_warnings_postgresql.py` |

Validação focada:

```bash
./venv/bin/pytest -q \
  tests/test_razao_async_benchmark.py \
  tests/test_razao_worker.py \
  tests/test_razao_async_upload_api.py \
  tests/test_razao_status_retry_api.py \
  tests/test_razao_warnings_api.py
make test-postgres
```

## Comparação e limitações

Guarde os dois JSONs obtidos no mesmo host e compare cada fase. Registre no PR
o commit, o comando e as condições do ambiente. Este repositório não contém
uma medição histórica equivalente anterior ao contrato assíncrono; portanto o
primeiro resultado deste harness é a baseline reproduzível para comparações
futuras, não um “antes” retroativo inventado.

O pico de memória vem de `tracemalloc` e cobre alocações Python do processo,
não RSS total, buffers do PostgreSQL nem memória de containers. Para aprovação
em ambiente, complemente o relatório com métricas do processo e com a sonda
HTTP real executada enquanto o worker consome o arquivo sintético.

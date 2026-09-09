# Armazenamento temporário do Razão

O serviço `core.razao_storage.RazaoStorage` implementa a parte de armazenamento
da [Spec 04](specs/04-importacao-razao-normalizacao.md), na issue #478.
Consome chunks, reserva disco, mantém associação privada entre arquivo e lote
e oferece limpeza e acesso protegido. Não cria lotes, endpoints, worker ou
agendamento. A integração desses consumidores pertence às próximas entregas.

## Configuração

| Variável | Padrão | Unidade/condição |
| --- | --- | --- |
| `RAZAO_STORAGE_DIR` | `./data/razao-temporario` | Diretório dedicado, privado, compartilhado por API e worker |
| `RAZAO_UPLOAD_MAX_BYTES` | `50000000` | Bytes; maior que zero |
| `RAZAO_STORAGE_MIN_FREE_BYTES` | `5000000000` | Bytes; não negativo |
| `RAZAO_STORAGE_MIN_FREE_RATIO` | `0.15` | Fração da capacidade total; de zero até menos que um |
| `RAZAO_FAILED_RETENTION_SECONDS` | `86400` | Segundos desde `failed_at`; maior que zero |

MB e GB usam unidades decimais: 50 MB = 50.000.000 bytes. A retenção padrão
é 24 horas. Construa o serviço com `RazaoStorage.from_settings(settings,
sessions=SessionLocal)`, usando a mesma base PostgreSQL dos lotes.

O volume deve ser local Linux/POSIX, suportar `flock`, `posix_fallocate`,
rename atômico e `fsync`. API e worker precisam acessar o mesmo volume e
operar com o mesmo UID. Diretórios usam modo `0700` e arquivos `0600`.
O serviço aplica `0700` ao diretório configurado; por isso ele deve ser
exclusivo para uploads temporários. Não use uma pasta de documentos existente.
Volumes sem suporte à reserva física são recusados com erro seguro de
capacidade. Não há fallback para reserva apenas em memória.

## Admissão e vínculo

A ordem de integração é:

1. Validar autorização e extensão no consumidor HTTP.
2. Entrar em `storage.admit(chunks)`. O iterável deve fornecer blocos limitados
   de bytes; o serviço não materializa o upload completo em memória.
3. Após a gravação completa e durável, usar `upload.file_hash` (SHA-256 em
   hexadecimal), `upload.size` e, se necessário, `upload.read(tamanho)`.
4. Dentro do contexto de admissão, abrir a transação que cria o lote canônico,
   adicionar o lote e chamar `upload.bind(session, lote)` antes do commit.
5. Confirmar o commit **antes de sair** do contexto de admissão.

`bind` faz flush, verifica o hash e persiste a associação privada. Não faz
commit. O serviço precisa receber a fábrica de sessões para aceitar vínculos.
Os metadados privados contêm somente o ID do lote, sem usar `warnings_metadata`
ou alterar o schema. Eles não devem ser serializados pela API ou auditoria.

Reenvio idempotente que reutiliza um lote existente deve sair do contexto
**sem chamar bind**. Assim, a cópia adicional é descartada e o arquivo canônico
permanece intacto. Um segundo vínculo para o mesmo lote é recusado.

Falha, excesso de tamanho ou saída sem vínculo remove arquivo e reserva.
Se houver rollback depois de persistir o vínculo, a próxima limpeza reconhece
a ausência do lote e recolhe o arquivo. Interrupções de processo liberam a
trava pelo sistema operacional; o conteúdo incompleto é recolhido na limpeza.

O handle é interno e válido apenas dentro do contexto. Seu identificador e o
nome `.xlsx` são UUIDs aleatórios, independentes de empresa, CNPJ e nome original.
Não exponha handles, nomes internos, streams ou exceções de infraestrutura nos
contratos HTTP. Extensão, conteúdo XLSX, permissões e CNPJ continuam sendo
responsabilidade das integrações especificadas para API/parser.

## Capacidade e concorrência

Uma trava de volume serializa a checagem e a pré-alocação do máximo permitido.
O piso é o maior entre a reserva absoluta e a fração do volume, arredondada
para cima. O serviço verifica o espaço livre antes e depois da pré-alocação,
incluindo o arredondamento real do filesystem para blocos.

A reserva já ocupa disco: não se soma outra reserva lógica aos bytes gravados.
Ao finalizar o streaming, o arquivo é truncado ao tamanho recebido. A trava
por arquivo permanece até terminar a admissão, protegendo também o intervalo
entre gravar os bytes e confirmar a criação do lote.

As garantias coordenam os consumidores deste serviço. Escritores externos ao
serviço podem consumir o mesmo volume; falhas de I/O são recusadas sem aceitar
upload incompleto. O volume privado não deve receber cargas não relacionadas.

## Consumo, retry e limpeza

- `open_for_job(lote_id)` entrega um stream seekable sob trava do arquivo.
  Posse/renovação de lease e transação contábil pertencem ao worker.
- `retry_guard(lote_id)` entrega `(session, lote, stream)` com trava do arquivo
  e `FOR UPDATE SKIP LOCKED`. Exige `failed`, `failed_at`, prazo não expirado
  e ausência de lease válida. O consumidor aplica a transição e reinicia os
  contadores conforme a spec. A saída normal confirma a transação; uma exceção
  faz rollback. Não faça commit antecipado dentro desse contexto.
- `cleanup()` retorna a quantidade de diretórios recolhidos. O consumidor deve
  chamá-lo imediatamente após confirmar sucesso e liberar o contexto de leitura,
  e periodicamente para falhas expiradas e órfãos. O agendamento pertence à
  integração operacional futura.

A limpeza consulta o banco em transações próprias e curtas. Não confunde linha
ocupada com linha inexistente, não espera por row lock e revalida o estado antes
de remover. Preserva `queued`, `processing`, arquivo sob trava e qualquer lease
válida. `processing` com lease expirada fica para recuperação do worker; não é
considerado órfão. `failed` sem `failed_at` é preservado conservadoramente.

Ordem de travas: arquivo antes da linha do lote. Consumidores não devem adquirir
row lock e depois esperar pelo arquivo. Não apague `.storage.lock`, diretórios
ou arquivos manualmente enquanto houver consumidores ativos.

Erros seguros disponíveis para tradução nas próximas integrações:

| Exceção | Código | Uso |
| --- | --- | --- |
| `UploadTooLarge` | `upload_too_large` | HTTP 413 |
| `InsufficientCapacity` | `temporary_capacity_unavailable` | HTTP 507 |
| `TemporaryFileUnavailable` | `temporary_file_unavailable` | Ausente, ocupado ou não elegível para retry |

## Validação e rollback

Execute os contratos focados com:

```bash
./venv/bin/python -m pytest -q tests/test_razao_storage.py
make test-postgres
./venv/bin/python -m pytest -q tests
git diff --check
```

Os testes PostgreSQL estão em
`tests/integration/test_razao_storage_postgresql.py`. Use somente banco
sintético descartável. O alvo `make test-postgres` permite sobrescrever
`DOCKER_COMPOSE_TEST` para um projeto isolado; a validação desta entrega usa
PostgreSQL efêmero, sem portas publicadas ou volumes de ambientes existentes.

Para rollback, suspenda os consumidores e a limpeza antes de reverter o código.
Preserve arquivos de jobs ativos e os vínculos privados. Esta entrega não muda
schema e não exige downgrade da migration entregue pela #477.

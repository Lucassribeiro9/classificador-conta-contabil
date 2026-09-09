# Spec: Importacao do Razao e Normalizacao Debito/Credito

## Objetivo

Importar o livro-razao de uma empresa, interpretar blocos de conta e normalizar cada linha em conta de origem, contrapartida, conta de debito, conta de credito, historico, valor, data, numero, saldos observados e lote de importacao.

Sucesso significa que o sistema transforma relatorios de razao em dados estruturados e auditaveis, sem confundir debito/credito com regras globais incorretas e preservando saldos suficientes para derivar fechamentos mensais por conta.

## Tech Stack

- openpyxl para leitura de `.xlsx`.
- SQLAlchemy para persistencia.
- Alembic para schema.
- FastAPI para endpoint de upload/importacao.
- PostgreSQL para fila duravel, posse do job e estado consultavel.
- Volume privado compartilhado para armazenamento temporario do `.xlsx`.
- Worker separado, executado com a mesma imagem da aplicacao.
- Pytest para parser, normalizacao e persistencia.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`
- Migrations: `.\venv\Scripts\python.exe -m alembic upgrade head`

## Project Structure

- `core/`: parser do razao e servico de importacao.
- `core/models.py`: lote de importacao, lancamento normalizado e vinculo empresa-conta.
- `api/routes/`: endpoint de importacao do razao.
- `api/schemas.py`: resposta de importacao, erros e resumo.
- worker do Razao: consumo da fila, heartbeat, processamento e recuperacao.
- volume temporario: arquivos pendentes identificados apenas por nome interno.
- `tests/`: testes de parser, importacao e autorizacao.

## Code Style

O parser deve ser deterministico e explicito sobre a regra contabil:

```python
if debito is not None:
    conta_debito = conta_bloco
    conta_credito = conta_contrapartida
elif credito is not None:
    conta_debito = conta_contrapartida
    conta_credito = conta_bloco
```

## Contrato de Layout

O arquivo padrao de importacao do Razao deve ser `.xlsx` e pode seguir o
modelo higienizado `modelo-razao-importacao.xlsx`, documentado em
`docs/razao-planilha-modelo.md`. Arquivos `.xls` ficam fora desta fase.

Relatorios em formato de Razao por blocos devem usar linhas iniciadas por
`Conta:` para definir a conta de origem das linhas seguintes. A conta do bloco
permanece ativa ate que outro bloco `Conta:` seja encontrado.

Campos obrigatorios do cabecalho:

- `Empresa`: nome da empresa exibida no arquivo.
- `CNPJ`: documento da empresa. A importacao normaliza para digitos e usa o
  valor como validacao forte contra a empresa alvo da importacao.
- `Periodo inicio`: data inicial do Razao.
- `Periodo fim`: data final do Razao.

Campos obrigatorios dos lancamentos:

- `data`
- `conta_origem`
- `historico`
- `contrapartida`
- `debito` ou `credito`: exatamente um dos dois deve estar preenchido em cada
  linha valida.

Campos opcionais dos lancamentos:

- `numero`: numero externo do lancamento quando o relatorio de origem trouxer
  esta informacao.
- `conta_origem_classificacao`
- `conta_origem_nome`
- `saldo_anterior`
- `saldo`
- `saldo_exercicio`
- `saldo_exercicio_original`: alias legado de `saldo_exercicio`.

O campo persistido `numero_lancamento` representa o numero externo do
lancamento vindo da planilha. Ele pode ser nulo quando o layout de origem nao
fornecer numero de lancamento. O `id` interno do banco identifica o registro
persistido e nao substitui nem deve ser usado como numero externo do
lancamento.

## Semantica dos Saldos

O Razao anual pode trazer tres informacoes de saldo:

- `saldo_anterior`: saldo observado que abre a sequencia de um bloco de conta;
- `saldo`: saldo observado da sequencia exibida no bloco ou relatorio;
- `saldo_exercicio`: saldo acumulado do exercicio informado pelo relatorio.

`saldo_exercicio_original` permanece como alias legado de `saldo_exercicio`
quando o arquivo antigo ou a documentacao anterior usar esse nome.

`Saldo` e `Saldo-Exercicio` devem ser preservados separadamente como saldos
observados do Dominio. Eles nao devem ser fundidos: cada campo segue sua
propria sequencia de validacao e calculo conforme definido nesta spec.

Cada saldo preservado deve manter:

- `valor_original`, como apareceu no arquivo;
- `valor_decimal`, como numero normalizado com precisao decimal;
- `natureza`, com valor `D` ou `C`, quando informada.

Quando o saldo vier como texto, o sufixo `D` ou `C` tem prioridade. Quando a
celula contiver valor numerico, a natureza so pode ser derivada de um formato
contabil explicitamente suportado, com secoes equivalentes a positivo `D`,
negativo `C` e zero neutro. Para essas celulas, `valor_original` preserva a
exibicao normalizada em formato brasileiro, `valor_decimal` armazena a
magnitude positiva e `natureza` preserva o sinal contabil. Saldo numerico zero
e valido com `natureza` ausente e nao gera `saldo_invalido`.

A natureza `D` ou `C` pertence ao saldo e nao substitui a regra principal de
debito/credito do lancamento. Saldos nao definem `valor`, `direcao`,
`conta_debito` ou `conta_credito` do lancamento.

`saldo_exercicio` sera a referencia principal para conciliacao futura. `saldo`
fica preservado como diagnostico secundario e como apoio para entender a
sequencia exibida no relatorio.

Se o CNPJ informado no arquivo divergir da empresa alvo da importacao, a
importacao deve ser bloqueada antes de persistir lote ou lancamentos. Se o
CNPJ corresponder a uma empresa inativa, a importacao tambem deve ser
bloqueada antes de persistir dados.

Linhas invalidas nao devem ser persistidas como lancamento valido. A importacao
pode ser parcial: linhas validas entram, linhas invalidas geram warnings no
lote. Quando houver ao menos uma linha valida e warnings, o status aprovado e
`completed_with_warnings`.

## Sequencia de Saldos e Fechamentos Mensais

A sequencia de saldos deve ser avaliada por empresa, lote e bloco de conta.
Cada bloco possui sua propria sequencia independente.

Regras alvo:

- `saldo_anterior` abre somente a sequencia acumulada do exercicio;
- `saldo` representa a movimentacao acumulada da competencia mensal e sua
  sequencia calculada inicia em zero a cada empresa, lote, bloco, ano e mes;
- `saldo_exercicio` representa o acumulado do exercicio e sua sequencia
  calculada inicia em `saldo_anterior`, sem reinicio mensal;
- lancamentos validos atualizam as duas sequencias conforme debito/credito;
- a validacao de `saldo` usa a sequencia mensal, enquanto o fechamento que
  possui `saldo_exercicio` compara e preserva a sequencia do exercicio;
- divergencia recuperavel entre saldo calculado e saldo observado gera warning
  e nao bloqueia linhas validas;
- erro bloqueante de sequencia deve ficar restrito a casos em que a conta do
  bloco, a empresa ou a estrutura minima do Razao nao possam ser identificadas
  com seguranca;
- valor ou natureza de saldo em formato invalido deve gerar warning quando as
  demais informacoes do lancamento forem suficientes para continuar;
- ausencia de colunas de saldo em arquivo antigo mantem a importacao possivel,
  com aviso informativo de que conciliacao por saldo nao esta disponivel;
- lacunas de saldo nao interrompem o calculo das linhas seguintes quando houver
  dados suficientes para continuar.

Fechamentos mensais devem ser derivados do Razao anual por empresa, conta e
mes. O fechamento mensal deve usar o ultimo saldo observado do mes para a
conta, preservando tambem o saldo calculado para comparacao futura.

O fechamento mensal derivado e dado de conferencia. Ele nao faz pareamento de
conciliacao com movimentos operacionais nesta spec.

## Processamento Assincrono

A importacao do Razao usa um unico contrato assincrono para arquivos de qualquer
tamanho. A API recebe e armazena integralmente o upload antes de criar ou
reutilizar o lote canonico. O processamento contabil nao ocorre no processo
HTTP e fica sob responsabilidade de um worker separado, executado com a mesma
imagem da aplicacao.

O PostgreSQL funciona como fila duravel inicial. Nao fazem parte desta etapa
Redis, RabbitMQ, Celery ou outro broker externo. A concorrencia inicial e `1`
por ambiente e deve ser configuravel sem alteracao de codigo.

### Estados e progresso do lote

Os estados publicos sao:

- `queued`: upload armazenado e aguardando worker;
- `processing`: worker possui lease valida e esta processando;
- `completed`: processamento concluido sem warnings;
- `completed_with_warnings`: linhas validas persistidas e warnings registrados;
- `failed`: falha tecnica ou deterministica encerrou a tentativa.

`queued` e `processing` sao estados ativos. Os demais sao terminais. O lote
expoe `total_linhas`, `linhas_processadas`, `total_importadas` e
`total_invalidas`. Antes de o parser descobrir o total, `total_linhas` pode ser
nulo e os demais contadores iniciam em zero. O consumidor calcula percentual
somente quando `total_linhas` for conhecido e maior que zero. Etapas internas
como parsing, validacao e persistencia ficam nos logs, nao no contrato publico.

Transicoes permitidas:

| Origem | Destino | Motivo |
| --- | --- | --- |
| inexistente | `queued` | upload integral aceito e lote criado |
| `queued` | `processing` | worker adquire lease exclusiva |
| `processing` | `completed` | resultado transacional sem warnings |
| `processing` | `completed_with_warnings` | resultado transacional com warnings |
| `processing` | `queued` | primeira falha transitoria ou lease expirada |
| `processing` | `failed` | falha deterministica ou segunda falha transitoria |
| `failed` | `queued` | repeticao manual aceita com arquivo temporario disponivel |

Cancelamento de job nao pertence a esta etapa. Ao repetir um lote, os
contadores de progresso da tentativa anterior sao reiniciados; o historico de
tentativas permanece auditavel.

### Contrato HTTP

`POST /api/v1/companies/{company_id}/razao/import` valida acesso, extensao e
capacidade enquanto grava o arquivo por streaming. Depois calcula o hash e:

- cria o lote como `queued` e responde `202 Accepted` para um arquivo novo;
- responde `202 Accepted` com o mesmo lote para hash em `queued` ou
  `processing`;
- responde `200 OK` com o mesmo lote para hash em `completed` ou
  `completed_with_warnings`;
- responde `409 Conflict` com o lote e a URL de repeticao para hash em
  `failed`, sem criar outro lote.

A resposta de aceite contem no minimo:

```json
{
  "lote_id": 123,
  "status": "queued",
  "status_url": "/api/v1/companies/7/razao/lotes/123"
}
```

Respostas `202` incluem `Retry-After: 3`. O cliente acompanha a importacao por
`GET /api/v1/companies/{company_id}/razao/lotes/{lote_id}`. O endpoint retorna
estado, contadores, resumo de warnings, tentativas, timestamps e, em falha,
`error_code`, mensagem segura, `request_id` e horario da falha. Caminho local,
traceback, payload bruto e detalhes contabeis nao fazem parte da resposta.

`POST /api/v1/companies/{company_id}/razao/lotes/{lote_id}/retry` aceita apenas
lote `failed`, arquivo temporario ainda disponivel e usuario com permissao de
operacao. Retorna `202`, move o mesmo lote para `queued` e nao cria nova
identidade. Depois do prazo de retencao, responde erro seguro informando que o
arquivo temporario nao esta mais disponivel; um arquivo corrigido deve entrar
como novo upload e possuir novo hash.

As permissoes existentes permanecem: upload e repeticao exigem `operacao` ou
`admin_empresa`; consultas exigem acesso de leitura a empresa. Admin global
respeita as regras ja definidas de acesso interno.

### Idempotencia e posse do job

A identidade canonica e formada por `empresa_id` e `file_hash`. Repeticao de
requisicao nao duplica lote nem processamento. A implementacao deve proteger
contra uploads concorrentes do mesmo hash por restricao de banco ou mecanismo
transacional equivalente.

O worker adquire jobs elegiveis com posse exclusiva no PostgreSQL, usando
selecao equivalente a `FOR UPDATE SKIP LOCKED`. Cada posse registra lease,
heartbeat e `attempt_count`. O heartbeat ocorre a cada 30 segundos e renova uma
lease de 10 minutos. Lease expirada permite recuperacao por outro worker.

Apenas falhas tecnicas transitorias recebem uma repeticao automatica,
limitando o lote a duas tentativas totais. Erros determinísticos de arquivo,
empresa, permissao, layout ou validacao nao sao repetidos automaticamente.

### Atomicidade e processamento em blocos

Lancamentos, vinculos, fechamentos e warnings produzidos por uma tentativa sao
persistidos em uma unica transacao de negocio. Uma falha tecnica reverte todos
esses resultados antes de atualizar o lote. Importacao parcial continua
significando que linhas validas entram juntas e linhas invalidas geram
warnings; nao significa expor resultados de uma tentativa incompleta.

O progresso, heartbeat e posse do job usam atualizacoes curtas e independentes
da transacao de negocio. Resultados derivados nao ficam disponiveis nos
endpoints enquanto o lote estiver ativo.

Para evitar consultas e objetos por lancamento, a implementacao deve:

- pre-carregar codigos do catalogo e vinculos relevantes;
- processar internamente blocos configuraveis de 1.000 lancamentos;
- usar escrita em lote sem commits intermediarios;
- liberar estruturas intermediarias quando nao forem mais necessarias;
- manter a quantidade de consultas proporcional aos blocos, nao as linhas.

### Armazenamento temporario e capacidade

O `.xlsx` e armazenado em volume privado compartilhado apenas entre API e
worker. O nome interno e aleatorio e nao deriva do nome original, CNPJ ou
empresa. O caminho fisico nunca e exposto pela API ou auditoria. O arquivo
original nao e arquivado como documento permanente.

A admissao do upload deve ser segura contra concorrencia, gravar por streaming
e interromper a escrita quando exceder o limite. Nenhum lote e criado se o
arquivo nao puder ser armazenado integralmente. Padroes iniciais, todos
substituiveis por ambiente:

- tamanho maximo por upload: 50 MB;
- reserva minima apos admissao: maior valor entre 5 GB e 15% do volume;
- retencao de arquivo em `failed`: 24 horas;
- bloco interno: 1.000 lancamentos;
- intervalo sugerido de polling: 3 segundos;
- heartbeat: 30 segundos;
- lease: 10 minutos renovaveis;
- concorrencia: 1.

Upload acima do limite responde `413`. Falta de capacidade temporaria segura
responde `507`. Nessas falhas nao existe lote incompleto. Arquivo concluido e
removido imediatamente depois da confirmacao do commit. Arquivo com falha fica
disponivel ate o prazo configurado. A limpeza automatica remove arquivos de
falhas expiradas e orfaos sem lote ativo, mas nunca remove arquivo de job com
lease valida ou aguardando processamento.

### Warnings normalizados e compatibilidade

Novos lotes persistem cada warning em tabela propria, relacionado ao lote e
contendo linha, codigo estavel, mensagem segura e detalhes controlados. O lote
mantem apenas totais agregados por codigo. Nao se grava novamente a lista
completa no JSON de metadata.

`GET /api/v1/companies/{company_id}/razao/lotes/{lote_id}/warnings` aceita
`page`, `limit`, `codigo` e `linha`. O limite padrao e 20 e os valores aceitos
pela interface sao 20, 50 e 100, com maximo 100. A resposta informa `total`,
`page`, `limit` e `has_next`.

Lotes historicos nao sofrem migracao retroativa. Para eles, o mesmo endpoint
adapta o JSON legado em memoria e identifica a origem como `legacy`; lotes
novos usam origem `normalized`. A compatibilidade pode ser removida apenas por
nova decisao documentada.

### Desempenho, seguranca e observabilidade

A validacao usa fixture sintetica deterministica e representativa, sem dados
reais. O benchmark registra separadamente parser, validacao, persistencia e
serializacao, com tempo e memoria antes e depois. Tempo absoluto de CI nao e
gate por variar conforme hardware. Os gates verificaveis sao ausencia de
consultas por linha, API responsiva durante o job, memoria controlada por
blocos e conclusao reproduzivel do arquivo representativo.

Recebimento, inicio, conclusao, falha e repeticao sao auditaveis. A auditoria
nao armazena o arquivo, caminho temporario, payload bruto ou dados contabeis.
Erros publicos seguem o envelope com `request_id`. Formato JSON, rotacao,
retencao e protecao dos logs tecnicos pertencem a issue #404.

## Deduplicacao e ML

Saldos devem ficar fora da chave de deduplicacao do lancamento. A chave de
deduplicacao continua baseada no conteudo do lancamento contabil, nao no saldo
observado ao redor dele.

Saldos tambem nao podem ser usados como feature de treino ou predicao de ML.
Eles servem para conferencia, fechamento mensal e diagnostico de divergencias.

## Testing Strategy

- Testar deteccao de bloco `Conta:`.
- Testar cabecalho, linhas vazias e saldo anterior sem transformar saldo em
  lancamento.
- Testar linha com debito.
- Testar linha com credito.
- Testar linha sem contrapartida.
- Testar troca correta entre debito e credito.
- Testar captura de `saldo_anterior`, `saldo` e `saldo_exercicio`.
- Testar normalizacao de valor decimal, natureza `D`/`C` e valor original dos
  saldos.
- Testar saldos numericos cujo `number_format` defina positivo `D`, negativo
  `C` e zero neutro.
- Testar que formato numerico nao suportado nao infere natureza contabil.
- Testar saldo anterior deslocado no layout real sem depender da coluna
  `Numero`.
- Testar troca de natureza entre saldos devedores e credores.
- Testar sequencia de saldo independente por bloco de conta e competencia mensal.
- Testar que `saldo` reinicia em zero por competencia e que `saldo_exercicio`
  inicia em `saldo_anterior` e permanece acumulado no bloco.
- Testar divergencia recuperavel de saldo como warning.
- Testar erro bloqueante apenas para sequencia sem conta, empresa ou estrutura
  minima confiavel.
- Testar saldo com valor ou natureza invalida como warning recuperavel quando
  o lancamento puder continuar.
- Testar arquivo sem colunas de saldo importado com warning informativo.
- Testar derivacao de fechamento mensal por empresa, conta e mes.
- Testar resposta de API com warnings de saldo e resumos de fechamento quando
  estes contratos forem implementados.
- Testar que saldo fica fora da chave de deduplicacao.
- Testar que saldo fica fora das features de ML e do dataset de treino.
- Testar criacao de lote de importacao.
- Testar vinculo automatico das contas usadas pela empresa.
- Testar reimportacao sem duplicar lancamentos.
- Testar bloqueio para usuario sem acesso a empresa.
- Testar reutilizacao do lote canonico para arquivo `.xlsx` ja recebido pela mesma empresa, conforme o estado.
- Testar validacao de contas contra o catalogo do plano de contas.
- Testar importacao parcial com warnings para linhas invalidas.
- Testar aceite `202`, consulta de status e resposta idempotente por hash.
- Testar posse exclusiva, lease expirada, heartbeat e limite de tentativas.
- Testar rollback integral dos resultados derivados em falha tecnica.
- Testar upload em streaming, limite individual, reserva de disco e limpeza.
- Testar warnings normalizados, filtros, paginacao e fallback do JSON legado.
- Testar quantidade de consultas por bloco, sem crescimento por lancamento.
- Testar que API permanece responsiva enquanto o worker processa uma fixture
  sintetica representativa.

## Boundaries

- Sempre: interpretar debito/credito em relacao a conta do bloco.
- Sempre: preservar conta de origem e contrapartida alem do par debito/credito.
- Sempre: associar importacao a empresa, usuario e lote.
- Sempre: aceitar apenas arquivos `.xlsx` nesta fase.
- Sempre: exigir que o plano de contas esteja importado antes do razao.
- Sempre: validar conta de origem e conta de contrapartida contra o catalogo.
- Sempre: registrar `original_filename` e `file_hash` no lote.
- Sempre: receber o arquivo por streaming e criar o lote somente apos a
  gravacao temporaria integral.
- Sempre: reutilizar o lote canonico para o mesmo `empresa_id` e `file_hash`.
- Sempre: usar chave composta de deduplicacao por conteudo do lancamento.
- Sempre: manter saldos fora da chave de deduplicacao.
- Sempre: manter saldos fora das features de ML.
- Sempre: preservar `valor_original`, `valor_decimal` e `natureza` `D`/`C` dos saldos.
- Sempre: tratar `saldo` por bloco e competencia mensal, com inicio em zero.
- Sempre: tratar `saldo_exercicio` por bloco, com inicio em `saldo_anterior`.
- Sempre: permitir importacao parcial, persistindo linhas validas e registrando warnings para invalidas.
- Sempre: importar arquivos antigos sem saldo, registrando aviso de conciliacao por saldo indisponivel.
- Sempre: persistir warnings de lotes novos em tabela normalizada e manter
  leitura compativel do JSON legado.
- Sempre: usar `completed_with_warnings` quando a transacao persistir linhas
  validas e registrar warnings.
- Sempre: processar o Razao fora da requisicao HTTP, com worker, lease e
  heartbeat.
- Sempre: remover o arquivo temporario apos sucesso e aplicar retencao
  configuravel apos falha.
- Sempre: manter resultados derivados invisiveis ate o commit da tentativa.
- Perguntar antes: aceitar layouts muito diferentes do razao lido.
- Perguntar antes: arquivar permanentemente o arquivo original completo.
- Perguntar antes: persistir linhas sem contrapartida como lancamento incompleto.
- Perguntar antes: bloquear lote inteiro por divergencia recuperavel de saldo.
- Perguntar antes: transformar saldo com formato invalido em erro bloqueante.
- Nunca: assumir que debito sempre significa banco.
- Nunca: usar o arquivo `.xls` ignorado como base desta fase.
- Nunca: persistir como valido lancamento cuja conta de origem ou contrapartida nao exista no catalogo.
- Nunca: usar saldo para definir valor, direcao, debito ou credito do lancamento.
- Nunca: usar saldo como feature de ML.

## Success Criteria

- Razao `.xlsx` legivel e importado por empresa.
- Lancamentos sao normalizados corretamente.
- Lotes de importacao sao registrados.
- Contas usadas sao vinculadas automaticamente a empresa.
- Reimportacoes nao geram duplicidades indevidas.
- Mesmo arquivo reutiliza o lote canonico da empresa sem duplicar processamento.
- Linhas invalidas geram warnings e nao viram lancamentos validos.
- Contas inexistentes no catalogo impedem persistencia do lancamento como valido.
- Testes cobrem debito, credito, cabecalho, saldos, sequencia de saldo,
  fechamento mensal e autorizacao.
- `saldo_anterior`, `saldo` e `saldo_exercicio` possuem semantica documentada.
- Natureza `D`/`C`, `valor_original` e `valor_decimal` dos saldos sao preservados.
- Arquivos antigos sem saldo continuam importaveis com aviso informativo.
- Divergencias recuperaveis de saldo geram warnings sem bloquear linhas validas.
- Fechamentos mensais podem ser derivados por empresa, conta e mes.
- Saldo nao participa de deduplicacao nem de ML.
- Upload aceito retorna rapidamente com lote e URL de acompanhamento.
- API permanece responsiva enquanto o worker processa o Razao.
- Falha tecnica nao deixa lancamentos, fechamentos ou warnings parciais.
- Warnings volumosos sao consultados com paginacao e resumo no lote.
- Arquivos temporarios respeitam limites, retencao e limpeza configuraveis.
- Benchmark sintetico demonstra consultas proporcionais aos blocos, nao as
  linhas.

## Decisoes Aprovadas

- Apenas arquivos `.xlsx` serao aceitos nesta fase.
- O plano de contas deve estar importado antes da importacao do razao.
- A importacao de razao exige permissao `operacao` ou `admin_empresa` na empresa.
- Quando o arquivo trouxer metadados obrigatorios, o CNPJ do arquivo deve
  corresponder ao CNPJ da empresa alvo da importacao.
- O lote de importacao armazenara `original_filename`, `file_hash`, usuario, empresa, status, contadores e timestamps.
- Lotes historicos preservam warnings no JSON; novos lotes usam tabela
  normalizada e endpoint paginado.
- O status de lote para importacao parcial sera `completed_with_warnings`.
- O arquivo original completo nao sera arquivado permanentemente. Uma copia
  temporaria privada sera mantida apenas durante o ciclo do job.
- O mesmo `file_hash` para a mesma empresa reutiliza o lote canonico conforme
  seu estado, sem criar outro processamento.
- Arquivos diferentes com lancamentos repetidos usarao deduplicacao por chave composta.
- A chave de deduplicacao sera `empresa_id`, `numero_lancamento`, `data`, `conta_origem`, `conta_contrapartida`, `valor`, `direcao` e `historico_normalizado`.
- Saldos ficam fora da chave de deduplicacao.
- Linhas sem contrapartida geram warning e nao sao persistidas como lancamento valido.
- Contas inexistentes no catalogo geram warning/erro e nao sao persistidas como lancamento valido.
- A importacao pode ser parcial: linhas validas entram, linhas invalidas ficam registradas em warnings.
- A tabela de warnings novos e o fallback de leitura do JSON legado nao exigem
  arquivamento permanente do arquivo original.
- Cada lancamento normalizado preserva conta de origem, contrapartida, conta de debito, conta de credito, direcao, historico, valor, data, numero do lancamento e lote.
- O Razao anual deve preservar `saldo_anterior`, `saldo` e `saldo_exercicio`.
- `Saldo` e `Saldo-Exercicio` sao saldos observados do Dominio e nao devem ser
  fundidos em um unico campo.
- `saldo_anterior` abre a sequencia de cada bloco de conta.
- `saldo_exercicio` e a referencia principal para conciliacao futura; `saldo`
  permanece como diagnostico secundario.
- Cada saldo preserva `valor_original`, `valor_decimal` e `natureza` `D`/`C`,
  quando informada.
- Saldos numericos derivam natureza apenas de formato contabil explicitamente
  suportado e preservam o decimal como magnitude positiva.
- Saldo numerico zero e valido e neutro, sem `saldo_invalido` por natureza
  ausente.
- Divergencia recuperavel de saldo gera warning e nao bloqueia a importacao das
  linhas validas.
- Arquivos antigos sem colunas de saldo continuam importaveis com aviso
  informativo de conciliacao por saldo indisponivel.
- Fechamentos mensais serao derivados por empresa, conta e mes usando o ultimo
  saldo observado do mes e preservando saldo calculado para comparacao futura.
- Saldos nao entram nas features de ML.
- Parser e persistencia permanecem separados.
- Contas validas encontradas no razao serao vinculadas automaticamente a empresa.
- `LancamentoRazaoNormalizado` e a fonte canonica do novo fluxo contabil e nao
  deve ser copiado automaticamente para `Transacao`; ver
  `docs/razao-transacoes-dataset-decisao.md`.

- A importacao usa contrato assincrono unico: upload novo ou ativo responde `202`;
  lote concluido reutilizado responde `200`.
- PostgreSQL e a fila duravel inicial; o worker e um servico separado com a
  mesma imagem da aplicacao.
- Estado e progresso sao consultados por polling; webhook, SSE e WebSocket
  ficam fora desta etapa.
- Processamento usa uma transacao de negocio, blocos internos de 1.000 linhas
  e nenhuma exposicao de resultado parcial.
- Lease, heartbeat e tentativas seguem os valores configuraveis definidos
  nesta spec.
- Uploads usam volume temporario privado com limite, reserva, retencao e
  limpeza preventiva.
- O PR da issue #475 fecha somente #475 e referencia a issue-pai #473.

## Matriz de Implementacao Assincrona

A issue #473 permanece como marco ate a conclusao das entregas abaixo. As
issues pequenas devem ser geradas somente depois do merge da #475 e seguir a
ordem de dependencias.

| Ordem | Entrega | Escopo principal | Dependencias | TDD |
| --- | --- | --- | --- | --- |
| 1 | Persistencia de jobs e warnings | Estados, contadores, lease, heartbeat, tentativas, erro publico e tabela de warnings | #475 | Obrigatorio |
| 2 | Armazenamento temporario | Streaming, nomes internos, capacidade, retencao e limpeza | Persistencia | Obrigatorio |
| 3 | Otimizacao do importador | Pre-carga de catalogo e vinculos, blocos e escrita sem consultas por linha | Persistencia | Obrigatorio |
| 4 | Worker transacional | Posse exclusiva, recuperacao, repeticao e commit atomico | Persistencia, armazenamento e otimizacao | Obrigatorio |
| 5 | API assincrona | `202`, status, idempotencia, retry e warnings paginados | Persistencia, armazenamento e worker | Obrigatorio |
| 6 | Benchmark e integracao | Fixture sintetica representativa, interrupcao, concorrencia e regressao | API e worker | Obrigatorio |
| 7 | Operacao e ambientes | Worker em dev, hml e prod, comandos Makefile e roteiro operacional | Benchmark aprovado | Conforme configuracao |

A issue #404 continua responsavel pelo formato e retencao dos logs tecnicos. A
issue #413 documenta o uso operacional de saldos, warnings e fechamentos depois
da estabilizacao do contrato. A issue #95 deve ser marcada como superada pela
#473 depois do merge da #475.

## Open Questions

Nenhuma pergunta bloqueante permanece para gerar as issues de implementacao.

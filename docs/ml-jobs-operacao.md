# Jobs duráveis de ML

## Contrato

`POST /api/v1/companies/{company_id}/ml/train`,
`POST /api/v1/companies/{company_id}/ml/classification` e
`POST /api/v1/companies/{company_id}/movimentos-operacionais/classificar`
exigem JWT com permissão `operacao` e `Idempotency-Key` (1 a 128 caracteres).
Retornam `202` com `job_id`, `status=queued` e `status_url`. Reenviar mesma
chave, tipo e payload devolve o mesmo job; reutilizar a chave com payload
diferente devolve `409`. Na classificação operacional, a lista de movimentos
pendentes é capturada ao enfileirar.

`GET {status_url}` exige `leitura` da mesma empresa e devolve estado técnico,
progresso, tentativas e resultado apenas após `completed`. Estados possíveis:
`queued`, `running`, `completed`, `failed` e `cancelled`. O resultado do treino
contém a versão `candidate`, que ainda exige promoção humana. O resultado da
classificação operacional contém apenas sugestões e revisões, sem aprovar
movimentos automaticamente. `POST {status_url}/cancel` exige `operacao` e
solicita parada cooperativa; `POST {status_url}/retry` reenfileira somente um
job `failed` e gera evento de auditoria. Falhas expõem apenas `error_code`
sanitizado, nunca payload ou histórico.

O pool `ml/cpu` usa `ML_CPU_WORKER_CONCURRENCY` (inicial 1),
`ML_JOB_LEASE_SECONDS` (600) e `ML_JOB_POLL_INTERVAL_SECONDS` (3). O pool
`io/importacao` continua na fila e no worker atuais do Razão, com
`RAZAO_WORKER_CONCURRENCY` próprio. O worker ML e a API compartilham somente o
volume de artefatos de modelo; o worker não expõe porta pública.

## Transição do armazenamento de modelos

Antes de ativar `ml-models-hml` ou `ml-models-prod`, verifique se o contêiner
atual da API contém artefatos em `/app/data/models`. Esses ambientes não tinham
volume compartilhado para esse caminho antes da #506; montar um volume vazio
ocultaria os arquivos antigos e quebraria versões já registradas. Em janela
controlada, copie os artefatos do contêiner anterior para uma área privada,
confira os SHA-256 contra `model_versions`, carregue o volume novo e confira
novamente os hashes antes de subir a API e o worker novos. Não remova o
contêiner anterior até concluir a verificação e o rollback da implantação.
Nenhum artefato deve entrar no Git ou no relatório de homologação.

## Roteiro de homologação

Use empresa e dados **sintéticos**, perfil operador e o commit exato do draft.
Anote ambiente, perfil, IDs de job, estados e horários sem incluir payloads,
credenciais ou artefatos. Aplique migrations antes de iniciar o worker.

1. Enfileire um treino com `Idempotency-Key` fixa. Confirme `202`, `queued`,
   `status_url` e ausência de versão antes de o worker concluir. Reenvie a mesma
   chave e confira o mesmo `job_id`; altere o payload com a mesma chave em uma
   classificação e confirme `409`.
2. Inicie `ml-worker` e acompanhe `GET {status_url}` até `completed`. Confira
   `version_id`, artefato no volume compartilhado e status `candidate`; confirme
   que o modelo ativo não mudou. Faça uma classificação canônica e uma
   operacional, confira resultado só ao concluir e movimentos ainda sujeitos à
   revisão humana.
3. Em um job sintético demorado, reinicie apenas `ml-worker` pelo Compose do
   ambiente. Espere a lease expirar ou use o tempo configurado para HML;
   confirme uma única posse vigente, tentativa incrementada e nenhum resultado
   parcial. Não altere banco manualmente para simular recuperação.
4. Solicite `POST {status_url}/cancel` enquanto um job sintético estiver
   `running`; confira `cancelled`, `result=null` e nenhuma versão candidata ou
   sugestão parcial. Force uma falha transitória controlada em HML e confira o
   retry limitado; para falha definitiva, use o endpoint de retry e registre
   a nova tentativa.
5. Execute a importação do Razão existente e confirme seus estados e worker
   independentes. Verifique acesso negado ao status de job de outra empresa.

## Benchmark controlado

Compare 1 e 2 consumidores `ml/cpu` em PostgreSQL isolado com as mesmas quatro
empresas e o mesmo dataset sintético treinável. Meça tempo de enqueue,
tempo até `completed`, CPU e memória do worker, sem processos concorrentes
alheios. Registre tamanho do dataset, commit, limites de concorrência,
hardware, número de execuções e mediana. Compare também a latência da fila do
Razão. Não interprete ganho de throughput sem essas condições; o benchmark não
substitui a homologação manual.

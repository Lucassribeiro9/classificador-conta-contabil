# Politica de Auditoria e Seguranca

Este documento resume as regras operacionais de auditoria aprovadas na spec
`docs/specs/07-auditoria-seguranca-operacional.md` e no PRD
`docs/prd/evolucao-plano-contas-importacao-ml.md`. Ele orienta implementacao e
review de PRs que adicionem ou alterem eventos auditaveis.

A auditoria registra a trilha de acoes sensiveis do sistema. Logs tecnicos
continuam existindo para diagnostico de execucao, mas nao substituem eventos de
auditoria.

## Tabela `audit_events`

A primeira versao usa uma tabela unica de auditoria, `audit_events`, modelada
por `AuditEvent` em `core/models.py`.

Campos atuais:

- `id`: identificador interno do evento.
- `timestamp`: data e hora de criacao do evento.
- `event_type`: nome canonico do evento, indexado para consulta.
- `user_id`: usuario executor, opcional para eventos sem usuario valido.
- `empresa_id`: empresa afetada, opcional para eventos globais.
- `resource_id`: identificador textual do recurso afetado, quando houver.
- `metadata`: JSON com detalhes seguros e minimamente necessarios.

Use `user_id` sempre que a acao tiver executor autenticado. Use `empresa_id`
sempre que a acao envolver dados de cliente. Use `resource_id` para apontar o
recurso principal da acao, como lote, feedback, conta, empresa ou modelo.

## Eventos iniciais

Os eventos abaixo formam a lista inicial de auditoria da primeira versao. Novos
eventos devem manter o padrao `<dominio>.<acao>` e ser adicionados somente
quando houver valor claro para rastreabilidade ou seguranca operacional.

### Autenticacao e autorizacao

- `auth.login_success`: login concluido com sucesso.
- `auth.login_failed`: login recusado por credenciais invalidas.
- `auth.user.inactive_blocked`: usuario inativo bloqueado em endpoint
  protegido.
- `auth.access.denied`: acesso negado por ausencia de vinculo com empresa ou
  permissao insuficiente.

### Plano de contas

- `plan.imported`: importacao do plano de contas concluida.
- `plan.import_failed`: importacao do plano de contas recusada ou falhou.
- `account.updated`: alteracao pontual em conta contabil.
- `account.deactivated`: desativacao de conta contabil.

### Razao contabil

- `ledger.imported`: importacao do razao concluida.
- `ledger.import_failed`: importacao do razao recusada ou falhou.
- `ledger.import_denied`: importacao do razao bloqueada por permissao.
- `ledger.deleted`: exclusao sensivel de lote ou dados do razao.

### Classificacao e modelo ML

- `classification.started`: solicitacao de classificacao iniciada.
- `classification.completed`: classificacao concluida.
- `classification.failed`: classificacao recusada ou falhou.
- `model.trained`: treinamento de modelo concluido.
- `model.train_failed`: treinamento de modelo recusado ou falhou.

### Feedback

- `feedback.created`: primeiro feedback registrado para um lancamento.
- `feedback.updated`: feedback posterior registrado para o mesmo lancamento.

### Empresas, usuarios e permissoes

- `company.deleted`: exclusao sensivel de empresa.
- `user.created`: usuario interno criado.
- `user.deactivated`: usuario interno desativado.
- `user_company_permission.changed`: permissao usuario-empresa criada ou
  alterada.

## Metadata permitida

`metadata` deve conter apenas informacoes necessarias para entender a acao, o
resultado e a causa de falha. Prefira valores pequenos, estruturados e sem
conteudo de cliente alem do minimo operacional.

Exemplos permitidos:

- Contadores de processamento, como `total_linhas`, `total_importadas`,
  `total_invalidas`, `total_processado` e `total_revisao`.
- Razoes controladas, como `invalid_credentials`, `access_denied`,
  `insufficient_permission`, `invalid_file`, `duplicate_file_hash` e
  `insufficient_dataset`.
- Identificadores internos, como `target_user_id`, `lancamento_id`,
  `company_id`, `lote_id`, codigo de conta e caminho logico de modelo.
- Hash de arquivo no formato `sha256:<digest>`.
- Campos antigos e novos de configuracoes nao sensiveis, como permissao ou
  flags booleanas.
- Tipo tecnico de erro, como `error_type`, quando ajudar o diagnostico sem
  vazar dados sensiveis.

## Metadata proibida

Nunca grave em auditoria:

- Senha, hash de senha, token JWT, API key ou segredo de ambiente.
- Conteudo completo de planilhas, arquivos, payloads de requisicao ou respostas
  externas.
- Dados contabeis extensos de cliente, historicos completos ou lotes inteiros.
- Dados pessoais desnecessarios para a trilha auditavel.
- Mensagens de erro que incluam credenciais, tokens, payload sensivel ou
  conteudo completo de arquivo.

Quando uma acao envolver arquivo, registre preferencialmente hash, contadores e
motivo controlado. Quando envolver login, registre somente o identificador
necessario para investigacao e nunca a senha recebida.

## Retencao

Eventos de auditoria tem retencao indefinida na primeira versao. Nao crie
rotina automatica de limpeza, expiracao ou compactacao sem issue propria e
decisao explicita de politica de retencao.

## Logs tecnicos x auditoria

Logs tecnicos ajudam a diagnosticar execucao, performance e erros de runtime.
Eles podem ser ajustados, filtrados ou descartados conforme a operacao.

Auditoria e a trilha persistente de responsabilidade sobre acoes sensiveis.
Eventos auditaveis devem ser gravados no banco, vinculados a usuario e empresa
quando aplicavel, e preservados para revisao futura.

Use logs para observabilidade tecnica. Use `audit_events` para responder quem
fez, quando fez, sobre qual empresa/recurso e com qual resultado.

## Orientacao para review de PR

Ao revisar PRs que adicionem ou alterem eventos de auditoria, confirme:

- O evento usa nome consistente com o padrao `<dominio>.<acao>`.
- A acao sensivel registra `user_id` e `empresa_id` quando aplicavel.
- A auditoria fica na mesma transacao da escrita sensivel quando possivel.
- O evento de falha registra motivo controlado sem expor segredo.
- `metadata` nao contem senha, token, API key, payload completo ou planilha.
- O PR inclui teste automatizado quando a mudanca altera comportamento de
  auditoria.
- O PR inclui evidencia de revisao manual quando a mudanca for apenas
  documental.

Se uma nova acao sensivel nao gerar evento auditavel, o PR deve justificar
explicitamente por que ela fica fora da trilha de auditoria.

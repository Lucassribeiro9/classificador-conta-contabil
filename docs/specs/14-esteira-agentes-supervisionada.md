# Spec: Esteira de Agentes Supervisionada

## Objetivo

Definir a arquitetura, os contratos e os limites de uma esteira supervisionada
para executar o fluxo de engenharia do projeto com agentes, sem substituir os
gates humanos existentes.

A esteira reduz a coordenacao manual entre Task Review, implementacao,
validacao e criacao de draft PR. O piloto fica restrito a uma issue documental
ou de spec por vez. Issues comportamentais somente poderao ser liberadas por
uma decisao posterior e por issue propria.

Esta spec pertence ao Ciclo 0 da Release 1, sob a issue-pai
[#360](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/360),
e deriva da
[#369](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/369).
Ela e uma iniciativa habilitadora e nao bloqueia a Release 1.

## Estado E Escopo

### Incluido

- responsabilidades de GitHub, n8n, runner, Codex, skills e worktrees;
- fontes canonicas para contratos e procedimentos;
- classificacao e roteamento de issues;
- estados, transicoes e intervencoes humanas;
- dupla confirmacao antes da implementacao;
- contrato logico e privado entre n8n e runner;
- autenticacao, idempotencia, concorrencia e protecao contra replay;
- allowlist de comandos do piloto documental;
- branch, worktree, checkpoints, timeout, cancelamento e recuperacao;
- limites de publicacao Git e criacao de draft PR;
- roteiro e registro da homologacao manual;
- notificacoes por Teams e e-mail;
- telemetria privada, retencao e agregacao;
- estrategia de testes da implementacao futura;
- criterio de calibracao do piloto;
- ordem recomendada das futuras issues.

### Fora De Escopo

- implementar runner, interface privada, workflow, skill, label ou servico;
- alterar Makefile, CI, containers ou ambientes;
- instalar ou autenticar o Codex CLI;
- configurar Teams, e-mail, credenciais ou URLs privadas;
- executar issues comportamentais;
- automatizar producao;
- aceitar shell livre vindo do n8n;
- aprovar decisoes por Teams ou e-mail;
- fazer merge ou iniciar automaticamente a proxima issue;
- ampliar o escopo da
  [#363](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/363);
- substituir a integracao contabil n8n prevista para o Ciclo 2;
- gerar as issues de implementacao nesta entrega.

## Principios

1. GitHub e a fonte oficial de escopo, decisoes, estados, PRs e checks.
2. Nenhuma automacao escreve diretamente na `main`.
3. Cada issue possui branch, worktree, execucao e PR focados.
4. Toda implementacao exige Task Review valida e autorizacao explicita.
5. O runner aceita acoes fechadas, nunca comandos shell enviados pelo n8n.
6. O runner consulta novamente o GitHub antes de iniciar ou retomar.
7. Falha de automacao ou notificacao nao impede o processo manual.
8. Evidencias e trabalho nao publicado sao preservados em falha.
9. Dados contabeis, credenciais e telemetria privada nao entram no repositorio.
10. A esteira sugere a proxima issue, mas nunca a inicia automaticamente.

## Componentes E Responsabilidades

| Componente | Responsabilidade | Nao e responsabilidade |
| --- | --- | --- |
| GitHub | Fonte oficial de issues, decisoes, estados, branches, PRs, checks e evidencias | Executar comandos no host |
| n8n | Observar eventos, solicitar acoes fechadas e enviar notificacoes | Interpretar decisoes, executar shell ou guardar credenciais do Codex |
| Runner local | Validar pedidos, consultar o GitHub, controlar execucao, worktree, idempotencia e checkpoints | Decidir produto, ampliar escopo ou operar producao |
| Codex CLI | Executar o procedimento selecionado dentro do escopo e dos limites aprovados | Escolher autonomamente outra issue ou ignorar gates |
| Skills | Definir o procedimento executavel de cada etapa | Substituir contratos arquiteturais da spec |
| Worktree | Isolar os arquivos e o estado Git de uma issue | Servir como estado oficial da execucao |
| Teams/e-mail | Alertar o mantenedor sobre gates e eventos relevantes | Registrar aprovacao ou alterar estado |
| Telemetria privada | Medir duracao, resultado, tentativas e consumo agregado | Armazenar prompts, diffs, segredos ou dados contabeis |

O runner deve ser executado no host remoto, fora do container do n8n, com o
usuario tecnico dedicado ao Codex. Credenciais do Codex nao podem ser montadas
no n8n. A interface do runner deve estar disponivel somente em rede privada e
nao pode ser publicada por ngrok.

## Fontes Canonicas

| Regra | Fonte canonica |
| --- | --- |
| Visao de produto, releases e ciclos | PRD |
| Arquitetura, contratos, estados e limites da esteira | Esta spec |
| Harness, matriz de ambientes e comandos comportamentais | Spec resultante da #363 |
| Procedimento executavel de cada etapa | Skill especializada |
| Referencia para execucao humana | `docs/prompts-fluxo-sdd-tdd.md` |
| Convencao de branch e merge | `.github/BRANCHING.md` |
| Estrutura base do PR | `.github/pull_request_template.md` |
| Procedimentos de homologacao | Documentos de homologacao existentes |
| Estado de uma execucao | GitHub e registro privado do runner, com GitHub prevalecendo |
| Segredos, limites privados e metricas detalhadas | Configuracao e armazenamento privados |

Uma skill pode detalhar como executar um contrato, mas nao pode alterar seus
estados, gates ou boundaries. O guia de prompts funciona como fallback humano
e nao deve duplicar integralmente as instrucoes executaveis das skills.

## Classificacao E Roteamento

Toda Task Review deve classificar a issue em uma destas categorias:

| Categoria | Regra |
| --- | --- |
| `documental` | Altera apenas documentacao; TDD nao se aplica |
| `comportamental` | Altera comportamento executavel; exige TDD |
| `configuracao-testavel` | Altera configuracao validavel; exige teste proporcional |
| `mista` | Combina categorias; deve ser reescopada quando nao couber em um PR focado |

Resultados possiveis da Task Review:

- `PRONTA PARA APROVACAO`;
- `BLOQUEADA`;
- `REQUER SPEC`;
- `REQUER REESCOPAGEM`.

O piloto aceita somente `documental` e issues de spec classificadas como
`PRONTA PARA APROVACAO`. Nenhuma classificacao por linguagem natural autoriza
uma execucao: o resultado deve estar registrado no GitHub.

## Estado Oficial E Labels

`ready-for-agent` indica apenas elegibilidade geral. Os futuros labels
`agent:*` indicam a etapa operacional e sao mutuamente exclusivos:

| Estado | Significado |
| --- | --- |
| `agent:awaiting-task-review` | Task Review ainda nao foi concluida ou perdeu validade |
| `agent:awaiting-human` | Existe pergunta, decisao ou autorizacao pendente |
| `agent:ready-to-implement` | Task Review valida e execucao explicitamente autorizada |
| `agent:running` | Runner possui a trava e esta executando a issue |
| `agent:awaiting-manual-test` | Draft e roteiro estao prontos para validacao humana |
| `agent:validated` | Conteudo relevante do commit foi homologado |
| `agent:blocked` | A execucao nao pode continuar sem intervencao |
| `agent:cancelled` | O mantenedor cancelou a execucao |

Apenas um label `agent:*` pode estar presente. O estado nativo `open` ou
`closed` da issue continua sendo a fonte oficial de conclusao. Depois do merge,
`Closes #<numero>` fecha a issue e o label operacional deve ser removido. O
historico permanece nos comentarios, no PR e nos checks.

## Maquina De Estados

| Origem | Evento ou condicao | Destino | Responsavel |
| --- | --- | --- | --- |
| Sem estado operacional | Inicio autorizado da Task Review | `agent:awaiting-task-review` | Orquestrador |
| `agent:awaiting-task-review` | Pergunta realmente pendente | `agent:awaiting-human` | Agente |
| `agent:awaiting-human` | `/agent decide <opcao>` valida | `agent:awaiting-task-review` | Orquestrador |
| `agent:awaiting-task-review` | Registro aprovado e autorizacao confirmada | `agent:ready-to-implement` | Mantenedor |
| `agent:ready-to-implement` | Pedido `implement` aceito e travas adquiridas | `agent:running` | Runner |
| `agent:running` | Decisao nova de produto, contrato ou arquitetura | `agent:awaiting-human` | Runner |
| `agent:running` | Validacoes concluidas e draft criado | `agent:awaiting-manual-test` | Runner |
| `agent:running` | Falha recuperavel esgotou a correcao automatica | `agent:blocked` | Runner |
| `agent:running` | Timeout controlado | `agent:blocked` | Runner |
| `agent:running` | `/agent cancel` valido | `agent:cancelled` | Runner |
| `agent:blocked` | `/agent retry` valido e contexto confirmado | `agent:running` | Runner |
| `agent:cancelled` | Nova autorizacao com contexto ainda valido | `agent:ready-to-implement` | Mantenedor |
| `agent:awaiting-manual-test` | Resultado `APROVADO` para o conteudo atual | `agent:validated` | Orquestrador |
| `agent:awaiting-manual-test` | Resultado `REPROVADO` ou `BLOQUEADO` | `agent:blocked` | Orquestrador |
| `agent:validated` | Conteudo relevante mudou | `agent:awaiting-manual-test` | Orquestrador |
| `agent:validated` | PR merged e issue fechada | Sem estado operacional | Orquestrador |

Uma transicao invalida deve ser rejeitada sem substituir o estado vigente. Toda
transicao aceita deve registrar estado anterior, estado novo, autor ou
componente, instante, issue, execucao e evidencia de origem.

## Intervencao Humana

O comando deve estar na primeira linha do comentario. Texto posterior e apenas
justificativa e nao deve ser interpretado como instrucao.

Comandos previstos:

```text
/agent approve-task-review
```

```text
/agent decide opcao-a

Justificativa opcional.
```

```text
/agent retry
```

```text
/agent cancel
```

No piloto, somente comentarios novos de `Lucassribeiro9`, publicados na issue
ou no PR esperado, sao aceitos. Edicao de comentario antigo, reacao, checkbox,
Teams ou e-mail nao autorizam uma acao.

Depois de aceitar um comando, a esteira deve publicar ou associar uma
confirmacao estruturada contendo:

- comando normalizado;
- autor;
- data e hora;
- repositorio e issue;
- comentario de origem;
- estado anterior e novo;
- identificador da execucao, quando existir;
- resultado da validacao do contexto.

## Dupla Confirmacao

Uma implementacao somente pode iniciar quando as duas condicoes forem
verdadeiras:

1. existe um Registro da Task Review aprovado pelo mantenedor;
2. a issue esta em `agent:ready-to-implement`.

A aprovacao deve ficar vinculada a:

- comentario ou referencia do Registro;
- versao vigente do corpo da issue;
- commit da spec aplicavel, quando existir;
- branch e escopo aprovados.

Mudanca material na issue, spec ou Registro invalida a aprovacao e retorna para
`agent:awaiting-task-review`. Correcao tipografica pode ser marcada como nao
material, mas essa classificacao deve ser registrada. O runner verifica todo o
contexto novamente antes de `implement` ou `resume`.

## Contrato Logico n8n Para Runner

O contrato usa um envelope comum. A implementacao futura pode expor uma ou mais
rotas, mas nao pode mudar a semantica abaixo.

### Requisicao

```json
{
  "contract_version": "1",
  "event_id": "00000000-0000-4000-8000-000000000000",
  "action": "implement",
  "repository": "owner/repository",
  "issue_number": 123,
  "requested_at": "2026-07-29T12:00:00Z",
  "nonce": "valor-aleatorio-de-uso-unico",
  "expected_state": "agent:ready-to-implement",
  "payload": {
    "base_branch": "main",
    "base_sha": "sha-verificado",
    "approved_branch": "spec/dominio-decisao",
    "task_review_ref": "referencia-publica-do-registro"
  }
}
```

Campos:

| Campo | Tipo | Validacao |
| --- | --- | --- |
| `contract_version` | string | Versao suportada e explicita |
| `event_id` | UUID | Obrigatorio, unico e persistido antes da execucao |
| `action` | enum | `implement`, `resume`, `cancel` ou `status` |
| `repository` | string | Repositorio previamente permitido |
| `issue_number` | inteiro positivo | Issue existente no repositorio permitido |
| `requested_at` | RFC 3339 UTC | Dentro da janela privada configurada |
| `nonce` | string opaca | Uso unico dentro da janela de replay |
| `expected_state` | enum | Estado que deve ser confirmado no GitHub |
| `payload` | objeto | Schema fechado e especifico da acao |

Payloads:

| Acao | Campos obrigatorios | Efeito permitido |
| --- | --- | --- |
| `implement` | `base_branch`, `base_sha`, `approved_branch`, `task_review_ref` | Iniciar uma execucao autorizada |
| `resume` | `execution_id`, `checkpoint_ref` | Retomar a mesma issue depois de nova validacao |
| `cancel` | `execution_id` | Solicitar encerramento controlado |
| `status` | `execution_id`, quando conhecido | Consultar estado sem alterar a execucao |

Campos desconhecidos devem ser rejeitados. Nenhum payload pode conter comando,
script, argumento de shell, prompt livre, segredo ou dado contabil.

### Autenticacao E Replay

A requisicao deve usar HMAC sobre uma representacao canonica que inclua, no
minimo:

- metodo e identificador logico da acao;
- timestamp;
- nonce;
- hash do corpo;
- identificador da chave.

O runner deve:

1. validar origem em rede privada;
2. validar chave ativa e assinatura em tempo constante;
3. validar timestamp dentro de uma janela limitada;
4. rejeitar nonce ja observado;
5. persistir `event_id` antes de iniciar efeitos;
6. nunca registrar segredo ou assinatura completa.

Os segredos, a janela real e a rotacao de chaves pertencem a configuracao
privada. A interface nao pode ser exposta por ngrok.

### Resposta

```json
{
  "contract_version": "1",
  "event_id": "00000000-0000-4000-8000-000000000000",
  "execution_id": "execucao-opaca",
  "action": "implement",
  "status": "accepted",
  "code": "EXECUTION_ACCEPTED",
  "message": "Acao aceita",
  "retryable": false,
  "github_ref": "referencia-publica-da-issue"
}
```

`status` deve ser um destes valores:

- `accepted`;
- `running`;
- `completed`;
- `rejected`;
- `blocked`;
- `cancelled`.

Codigos minimos:

| Codigo | Uso |
| --- | --- |
| `EXECUTION_ACCEPTED` | Acao nova aceita |
| `EVENT_ALREADY_PROCESSED` | Mesmo evento e mesmo payload ja registrados |
| `EVENT_PAYLOAD_CONFLICT` | Mesmo `event_id` com payload diferente |
| `INVALID_SIGNATURE` | HMAC invalido |
| `REPLAY_REJECTED` | Timestamp ou nonce invalido |
| `STATE_MISMATCH` | Estado do GitHub diverge de `expected_state` |
| `APPROVAL_REQUIRED` | Dupla confirmacao ausente ou invalida |
| `ISSUE_ALREADY_RUNNING` | Existe execucao ativa para a issue |
| `PILOT_CAPACITY_REACHED` | Outra issue ocupa a trava global |
| `ACTION_NOT_ALLOWED` | Acao ou payload fora do contrato |
| `EXECUTION_BLOCKED` | Execucao requer intervencao humana |
| `EXECUTION_NOT_FOUND` | Execucao solicitada nao existe |

Mensagens nao devem expor segredo, corpo de prompt, diff ou caminho privado.

## Idempotencia E Concorrencia

- Mesmo `event_id` e mesmo payload retornam o resultado persistido.
- Mesmo `event_id` com payload diferente retorna
  `EVENT_PAYLOAD_CONFLICT`.
- Cada issue possui uma trava exclusiva de execucao.
- O piloto possui uma trava global para apenas uma execucao ativa.
- Durante `agent:running`, `status` e `cancel` sao permitidos.
- Novos `implement` e `resume` sao rejeitados; eles nao entram em fila.
- Perda da trava, divergencia de estado ou evento concorrente interrompem
  efeitos novos e preservam evidencias.

O n8n pode reduzir eventos duplicados, mas a protecao deve existir no runner.

## Revalidacao Antes De Executar

Antes de `implement` ou `resume`, o runner deve confirmar:

1. repositorio e issue permitidos;
2. issue aberta e vinculada ao contexto esperado;
3. label `ready-for-agent`;
4. exatamente um estado `agent:*`;
5. estado igual a `expected_state`;
6. Task Review aprovada e ainda valida;
7. branch aprovada conforme `.github/BRANCHING.md`;
8. base SHA correspondente a `main` aprovada;
9. dependencias e bloqueios resolvidos;
10. ausencia de PR conflitante para branch ou issue;
11. ausencia de outra execucao ativa;
12. classificacao permitida pelo piloto;
13. escopo sem segredo ou dado contabil.

Qualquer divergencia deve impedir a execucao e gerar evidencia objetiva.

## Branch E Worktree

- A branch deve partir do SHA aprovado da `main`.
- O nome deve vir da Task Review e seguir `.github/BRANCHING.md`.
- Cada issue usa uma worktree exclusiva em raiz privada configurada.
- O caminho local nao e publicado no GitHub.
- Branch existente so pode ser reutilizada quando pertencer a mesma issue e
  seu historico for compativel com a base aprovada.
- Worktree com alteracao preexistente inesperada bloqueia a execucao.
- A automacao nunca descarta, sobrescreve ou faz stash silencioso.

### Ciclo De Vida

1. criar ou validar branch e worktree;
2. registrar base SHA e estado inicial;
3. executar apenas a issue aprovada;
4. manter a worktree enquanto issue ou PR estiverem ativos;
5. preservar worktree, diff, logs e checkpoints em falha, bloqueio ou
   cancelamento;
6. remover a worktree somente depois de merge ou encerramento explicito e
   depois de confirmar que nao existe alteracao local nao publicada;
7. nao excluir automaticamente a branch no piloto.

A limpeza automatica so pode atingir recursos identificados pela propria
execucao.

## Catalogo De Comandos

O n8n solicita acoes logicas. Ele nunca envia comandos. O runner e as skills
resolvem comandos a partir de uma allowlist versionada.

### Automaticos No Piloto Documental

| Finalidade | Comandos ou operacoes permitidas |
| --- | --- |
| Inspecao Git | `git status --short`, `git branch --show-current`, `git rev-parse`, `git log`, `git show`, `git diff`, `git diff --check` |
| Busca documental | `rg`, `rg --files` com caminhos restritos ao repositorio |
| Isolamento | `git worktree add` e `git switch` com branch e caminhos validados |
| Edicao | Ferramenta de patch restrita aos arquivos aprovados |
| Validacao | Validadores documentais existentes e comandos declarados na issue/spec |
| Publicacao do draft | `git add -- <arquivos-do-escopo>`, `git commit`, `git push` da branch e criacao de draft PR |

O commit e o push somente podem incluir arquivos previstos na Task Review e
confirmados pelo diff. O draft deve usar o template do repositorio e
`Closes #<numero>`.

### Condicionais

Dependem do tipo da issue e de contrato previamente aprovado:

- testes documentais adicionais existentes;
- validadores de Markdown, links ou schemas ja presentes;
- comandos de harness consolidados pela #363;
- testes focados e regressao para futuras issues comportamentais.

### Exigem Nova Aprovacao

- adicionar dependencia;
- ampliar a allowlist;
- alterar CI, schema, migracoes ou politica de retencao;
- executar instalacao de ferramenta;
- mudar template de issue ou PR;
- liberar issues comportamentais;
- adicionar canal de notificacao;
- alterar limites operacionais.

### Nunca Automaticos

- comando shell vindo do payload;
- escrita direta na `main`;
- force-push ou amend de commit publicado;
- PR nao draft ou merge;
- exclusao automatica de branch no piloto;
- producao;
- downgrade de migration;
- limpeza global;
- remocao de volumes;
- descarte de alteracao local;
- comando destrutivo fora de recurso identificado pela execucao.

Os comandos comportamentais permanecem sob responsabilidade da #363. Esta
spec nao antecipa `make check`, `make check-full` ou a matriz de ambientes.

## Execucao, Checkpoints E Limites

O piloto usa:

- uma issue ativa;
- uma execucao principal por issue;
- no maximo uma correcao automatica;
- timeout inicial de 30 minutos;
- nenhum subagente;
- tres execucoes documentais para calibracao.

Checkpoints devem ser registrados depois de:

1. validacao do contexto;
2. criacao da worktree;
3. conclusao das edicoes;
4. conclusao das validacoes;
5. commit;
6. push;
7. criacao do draft.

Um checkpoint contem apenas identificadores, etapa, resultado, SHA e
referencias necessarias para retomar. Nao contem prompt, raciocinio ou diff.

### Correcao Automatica

A unica correcao automatica pode tratar somente falha mecanica e objetiva, como:

- `git diff --check`;
- link ou caminho invalido;
- placeholder nao resolvido;
- arquivo alterado fora do escopo;
- criterio documental verificavel nao atendido.

Reprovacao humana, comentario de review, contradicao ou decisao nova nunca
acionam correcao automatica. Uma segunda falha move a issue para
`agent:blocked`.

### Timeout

Ao atingir 30 minutos, o runner deve:

1. solicitar encerramento controlado;
2. impedir nova etapa;
3. preservar worktree, diff, logs e ultimo checkpoint;
4. aplicar `agent:blocked`;
5. notificar o mantenedor.

A retomada exige `/agent retry`, novo `event_id`, nova leitura do GitHub e
acao `resume`.

### Cancelamento

`/agent cancel`:

- encerra a execucao de forma controlada;
- preserva worktree e evidencias;
- remove autorizacao de execucao;
- aplica `agent:cancelled`.

Para reiniciar, o mantenedor deve confirmar novamente
`agent:ready-to-implement`. A Task Review pode ser reutilizada somente quando
issue, spec e Registro continuarem materialmente inalterados.

## Skills

Skills planejadas:

| Skill | Responsabilidade |
| --- | --- |
| `issue-task-review` | Inspecionar contexto, conduzir decisoes e produzir o Registro |
| `spec-delivery` | Criar ou atualizar uma spec aprovada e suas referencias minimas |
| `implement-issue` | Executar uma unica issue conforme sua classificacao |
| `prepare-draft-pr` | Validar diff, publicar branch e criar draft com evidencias |
| `issue-delivery-loop` | Coordenar a etapa corrente e delegar para a skill especializada |

`issue-delivery-loop` nao deve concentrar os procedimentos internos das demais
skills. Cada skill deve:

- carregar apenas o contexto necessario;
- respeitar os contratos desta spec;
- interromper diante de decisao nova;
- nao criar TDD artificial em issue documental;
- nao avancar para outra issue;
- devolver resultado estruturado ao runner.

## Draft PR E Homologacao Manual

Todo draft deve conter roteiro manual reproduzivel ou justificativa explicita
de `NAO APLICAVEL`. Para mudanca documental, validacao de conteudo e
rastreabilidade e aplicavel mesmo quando testes de codigo nao forem.

O roteiro deve informar:

- ambiente e commit;
- perfil do executor;
- servicos necessarios;
- fixtures sanitizadas, quando aplicavel;
- preparacao;
- passos numerados;
- resultado esperado por passo;
- casos de erro;
- evidencias;
- limpeza.

### Registro No PR

O resultado deve ser comentado no draft PR:

```text
## Homologacao manual

- Resultado: APROVADO | REPROVADO | BLOQUEADO | NAO APLICAVEL
- Commit testado: <sha>
- Ambiente: <ambiente>
- Perfil: <perfil>
- Roteiro executado: <referencia>
- Evidencias: <referencias sanitizadas>
- Divergencias: <nenhuma ou descricao>
- Justificativa de NAO APLICAVEL: <quando aplicavel>
```

A issue recebe apenas a transicao resumida e o link para o comentario. Rodadas
formais de ciclo ou release usam issue propria e os documentos de homologacao
existentes.

### Invalidacao

O resultado e valido para o conteudo relevante do commit testado. Qualquer
mudanca nos arquivos do escopo retorna para `agent:awaiting-manual-test`.
Rebase, merge da `main` ou novo commit que mantenha a mesma arvore relevante
nao exige repeticao.

Para futuras mudancas comportamentais, a comparacao relevante inclui codigo,
testes, contratos e configuracoes afetados.

## Notificacoes

Teams e e-mail devem alertar:

- Task Review pronta para aprovacao;
- decisao bloqueante;
- timeout ou falha bloqueante;
- draft pronto para teste manual;
- homologacao reprovada ou bloqueada;
- execucao cancelada;
- validacao concluida.

A notificacao pode conter:

- repositorio e numero da issue;
- titulo;
- estado;
- resumo sanitizado;
- acao humana esperada;
- link para issue, comentario ou PR.

Ela nao pode conter segredo, URL privada, prompt, diff, log bruto, dado
contabil, consumo real ou comando executavel. Falha de notificacao deve ser
registrada privadamente e nunca alterar o estado oficial no GitHub.

TomTicket e aprovacoes por botoes de Teams permanecem no backlog.

## Telemetria Privada

Campos permitidos:

- identificador da execucao;
- repositorio e issue;
- etapa;
- timestamps e duracao;
- resultado;
- categoria dos comandos;
- quantidade de tentativas;
- codigo de erro;
- uso agregado;
- referencias tecnicas nao secretas.

Conteudo proibido:

- prompts e respostas completas;
- raciocinio;
- conteudo de arquivos ou diffs;
- logs brutos;
- credenciais, assinaturas ou URLs privadas;
- dados contabeis;
- valores reais publicados no GitHub.

Dados detalhados sao mantidos por 90 dias. Depois desse periodo, somente
agregados mensais necessarios para custo, confiabilidade e capacidade podem ser
preservados. O armazenamento e os valores de limite ficam fora do repositorio
publico.

## Workflows n8n Versionados

As futuras issues devem versionar exportacoes sanitizadas dos workflows n8n.
Esses artefatos nao podem conter:

- credenciais ou tokens;
- URLs privadas;
- IDs reais de credenciais;
- dados de execucao;
- dados contabeis.

Configuracao runtime e referencias privadas permanecem no n8n e no
armazenamento privado. Esta regra permite review e recuperacao sem publicar o
ambiente operacional.

## Estrategia De Testes

A implementacao futura deve usar testes por seam publico.

### GitHub E Estados

- transicoes validas e invalidas;
- exclusividade dos labels `agent:*`;
- dupla confirmacao;
- invalidacao por mudanca material;
- autor e local corretos do comando;
- fechamento nativo depois do merge;
- ausencia de inicio automatico da proxima issue.

### Contrato Do Runner

- schema fechado por acao;
- assinatura HMAC valida e invalida;
- timestamp expirado;
- nonce repetido;
- `event_id` repetido com mesmo payload;
- `event_id` repetido com payload diferente;
- payload com comando livre;
- repositorio ou issue nao permitidos;
- divergencia entre estado esperado e GitHub.

### Concorrencia

- trava por issue;
- trava global;
- `status` e `cancel` durante execucao;
- rejeicao de `implement` e `resume` concorrentes;
- recuperacao depois de perda controlada da execucao.

### Git E Worktrees

- branch baseada no SHA aprovado;
- isolamento por issue;
- rejeicao de worktree suja inesperada;
- preservacao em falha;
- limpeza restrita ao recurso da execucao;
- protecao de alteracao nao publicada;
- ausencia de force-push, merge ou exclusao automatica da branch.

### Skills E Comandos

- roteamento por classificacao;
- carregamento sob demanda;
- ausencia de TDD artificial em documento;
- interrupcao por decisao nova;
- bloqueio de comando fora da allowlist;
- commit limitado aos arquivos aprovados.

### Draft E Homologacao

- roteiro reproduzivel;
- justificativa quando nao aplicavel;
- comentario estruturado;
- vinculo ao commit;
- invalidacao por mudanca relevante;
- manutencao da validade quando a arvore relevante nao muda.

### Telemetria E Notificacoes

- ausencia de conteudo proibido;
- retencao e agregacao;
- notificacoes somente nos eventos previstos;
- falha de canal sem mudanca do estado oficial.

Testes de codigo nao se aplicam a criacao desta spec. O PR da #369 deve usar
validacoes documentais e revisao manual.

## Validacoes Documentais Da Spec

- `git diff --check`;
- inspecao integral do diff;
- confirmacao dos arquivos alterados;
- validacao de links e caminhos;
- busca por placeholders e decisoes nao resolvidas;
- busca por segredo, URL privada, token e metrica real;
- comparacao com PRD e specs 00, 07, 11, 12 e 13;
- confirmacao de que a #363 nao foi ampliada;
- confirmacao de que nenhum codigo ou artefato operacional foi criado.

## Fallback Manual

Se runner, n8n, Codex, Teams, e-mail ou telemetria estiverem indisponiveis:

1. consultar issue, PRD, spec e Task Review manualmente;
2. criar branch conforme `.github/BRANCHING.md`;
3. executar a skill ou o prompt humano equivalente;
4. validar diff e testes aplicaveis;
5. preparar draft conforme o template;
6. registrar homologacao no PR;
7. manter as decisoes e o estado oficial no GitHub.

Falha da esteira nao pode bloquear uma entrega autorizada pelo fluxo manual.

## Calibracao Do Piloto

O piloto termina depois de tres execucoes documentais que atendam, em todas as
rodadas:

1. nenhuma mudanca fora do escopo;
2. nenhum segredo ou dado privado exposto;
3. nenhuma execucao duplicada;
4. estados e gates corretos;
5. worktrees e evidencias preservadas;
6. draft e roteiro manual reproduziveis;
7. notificacoes funcionando ou falhando sem corromper o estado;
8. consumo registrado privadamente;
9. no maximo uma correcao automatica por execucao;
10. fallback manual disponivel.

Mesmo com os criterios atendidos, issues comportamentais somente podem ser
liberadas por nova decisao e issue especifica.

## Ordem Recomendada Das Futuras Issues

1. Definir e criar protocolo GitHub, labels e comentarios estruturados.
2. Criar skills especializadas e validar o fallback manual.
3. Implementar runner local e isolamento por worktree.
4. Implementar interface privada, HMAC, replay protection e idempotencia.
5. Criar workflow n8n e notificacoes por Teams/e-mail.
6. Implementar telemetria privada, retencao e agregacao.
7. Executar e registrar tres calibracoes documentais.
8. Avaliar em issue separada a liberacao de issues comportamentais.

Cada item deve virar issue focada, com Task Review propria, testes esperados,
branch aprovada e um unico PR.

## Project Structure Esperada

Esta spec nao fixa framework nem nomes internos da futura implementacao. As
issues futuras devem manter separados:

- contratos e documentacao publica;
- skills versionadas;
- runner e testes;
- exportacoes sanitizadas do n8n;
- configuracao e telemetria privadas;
- evidencias publicas no GitHub.

Qualquer estrutura concreta deve ser aprovada na Task Review da primeira issue
que criar o respectivo artefato.

## Boundaries

### Sempre

- consultar novamente o GitHub antes de iniciar ou retomar;
- exigir dupla confirmacao;
- operar uma issue e uma worktree por vez no piloto;
- usar a allowlist aprovada;
- preservar diff, checkpoints e evidencias em falha;
- criar roteiro manual especifico no draft;
- usar exemplos e fixtures sanitizados;
- manter fallback manual.

### Perguntar Antes

- liberar issue comportamental;
- ampliar permissao ou allowlist;
- alterar estados ou transicoes;
- modificar timeout, tentativas ou retencao;
- automatizar criacao de issue;
- modificar templates;
- alterar CI, schema ou dependencias;
- adicionar canal de notificacao;
- automatizar qualquer acao em producao.

### Nunca

- escrever diretamente na `main`;
- fazer merge ou iniciar outra issue automaticamente;
- aceitar shell vindo do n8n;
- expor o runner publicamente;
- montar credenciais do Codex no n8n;
- versionar segredo, URL privada, metrica real ou dado contabil;
- ignorar teste ou criterio para reduzir consumo;
- executar downgrade, limpeza global ou remocao de volumes;
- descartar mudanca local;
- alterar PRD ou spec silenciosamente durante uma implementacao.

## Criterios De Sucesso

- responsabilidades dos componentes nao se sobrepoem;
- fontes canonicas estao explicitas;
- estados e transicoes possuem condicoes verificaveis;
- dupla confirmacao impede autorizacao obsoleta;
- contrato n8n para runner nao aceita comando livre;
- autenticacao, replay protection e idempotencia sao testaveis;
- concorrencia nao inicia execucoes duplicadas;
- branch e worktree preservam isolamento e evidencias;
- comandos destrutivos e producao permanecem proibidos;
- draft e homologacao ficam vinculados ao conteudo validado;
- notificacoes nao se tornam fonte de aprovacao;
- telemetria privada nao armazena conteudo sensivel;
- piloto possui limites e criterios objetivos;
- fallback manual permanece completo;
- futuras issues podem ser geradas sem decisao arquitetural implicita;
- a iniciativa permanece nao bloqueante para a Release 1.

## Open Questions

Nenhuma decisao bloqueante permanece aberta para gerar as futuras issues. Uma
mudanca nos contratos desta spec exige nova Task Review e atualizacao
documental antes da implementacao correspondente.

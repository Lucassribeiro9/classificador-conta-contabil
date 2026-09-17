# Spec: Evolucao Arquitetural, Operacao e Governanca Contabil

## Objetivo

Definir a arquitetura canonica da Fase 4, posterior a Release 1, para que o
Classificador Contabil trate contexto contabil por empresa e no tempo sem
transformar sugestoes de ML em decisoes humanas finais.

O principio do produto e: automatizar somente o que for deterministico e
auditavel; quando houver ambiguidade contabil ou contexto insuficiente, o
sistema se abstem e encaminha a revisao humana.

## Rastreabilidade

- PRD: `docs/prd/evolucao-plano-contas-importacao-ml.md`, versao 4.0.
- Fase: Fase 4 / Pos-Release 1.
- Issue desta spec: [#498](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/498).
- Arquitetura de partida: documento aprovado em 16/09/2026.
- Processo de agentes: `docs/specs/14-esteira-agentes-supervisionada.md` e
  `.github/agent-protocol.json` continuam canonicos para a execucao.

Esta spec concentra as decisoes transversais. Specs de dominio detalharao o
contrato executavel de cada entrega e devem apontar para esta fonte, sem copiar
suas regras integrais.

## Escopo

### Incluido

- identidade, versao e snapshot de conta contabil por empresa;
- temporalidade, alias e divergencias do Razao;
- Central de Revisoes para ambiguidade que exige decisao humana;
- elegibilidade e manifesto do dataset;
- modelos imutaveis por empresa, thresholds e promocao humana;
- jobs de ML, observabilidade, backup e disaster recovery;
- matriz de transicao para as issues #499 a #510.

### Fora de escopo

- implementacao direta de migrations, API, workers, dashboards, backup ou DR;
- Redis, Celery, broker externo, vector database, embeddings e retraining
  automatico;
- autoaprovacao de classificacoes;
- alteracao do protocolo agentic enquanto a decisao da #382 estiver pendente;
- substituicao da fila assincrona especifica do Razao nesta fase documental.

## Fontes e Fronteiras

| Area | Responsabilidade | Nao e responsabilidade |
| --- | --- | --- |
| Dominio contabil | identidades, versoes, snapshots, aliases e regras temporais | decidir revisoes de forma generica |
| Revisao | estado, claim, evidencias, justificativas e auditoria de pendencias | regra contabil especifica de cada origem |
| ML | dataset, treino, avaliacao, modelos e sugestoes | decisao contabil final |
| Jobs | lifecycle tecnico, posse, retry, cancelamento e progresso | estado funcional do lote ou da classificacao |
| Observabilidade | metricas agregadas de operacao | logs brutos, auditoria decisoria ou telemetria privada de agentes |
| Backup e DR | recuperacao independente do n8n | codigo-fonte, recuperado do Git |

O PRD define produto e fases; esta spec define arquitetura; a issue e a Task
Review definem a unidade autorizada. Nenhuma fonte substitui outra fora de sua
responsabilidade.

## Modelo Contabil por Empresa e Tempo

Uma conta contabil passa a ter identidade logica estavel dentro de uma empresa.
O codigo deixa de ser identidade global: empresas diferentes podem usar o mesmo
codigo para significados distintos.

Cada identidade pode possuir versoes de atributos e participar de snapshots do
plano. Um snapshot pertence a uma empresa, e registra vigencia, origem e hash
de conteudo normalizado. O desenho final de tabelas pertence a #499 e #501;
esta spec fixa os contratos, nao nomes internos.

### Regras de snapshot

- Conteudo normalizado identico reutiliza o snapshot logico, mas preserva o
  evento de importacao para auditoria.
- Conteudo alterado cria um novo snapshot imutavel.
- Vigencia conhecida e explicita; sem vigencia informada, a data de importacao
  e usada com marca de inferencia.
- Um snapshot retroativo entra na linha do tempo sem alterar snapshots
  anteriores ou reescrever classificacoes historicas.
- Dois snapshots distintos para a mesma empresa e vigencia sao conflito
  explicito e exigem revisao humana.
- Mudanca de codigo ou mudanca semantica relevante nunca gera continuidade
  automatica apenas por texto ou codigo; pode gerar sugestao para confirmacao.

## Razao, Movimentos e Revisao Humana

O Razao e evidencia historica; ele nao altera automaticamente o plano canonico.
Descricao equivalente pode ser normalizada. Alias provavel, codigo ausente ou
divergencia semantica deve gerar o tratamento proporcional ao risco.

Warnings sao sinais tecnicos ou operacionais. Um `ReviewItem` existe somente
quando uma acao humana e necessaria. Itens de Razao e plano podem agrupar
evidencias compatíveis; movimentos mantem uma decisao final por registro.

O lifecycle minimo da revisao e `pending`, `in_review`, `resolved` e
`dismissed`. Claim impede conclusao concorrente. Descarte, reatribuicao sensivel
e resolucao de conflito de snapshot exigem justificativa e eventos auditaveis.

Para registros temporais, a prioridade e competencia explicita, data do
lancamento e fallback auditavel. Um intervalo que atravesse duas vigencias nao
escolhe um snapshot pelo inicio ou pelo fim: cria pendencia de revisao.

## Dataset, Modelos e Classificacao

Um registro e elegivel ao dataset somente se nao possuir pendencia critica
aberta, tiver contexto temporal valido e usar conta validada. Registros
rejeitados, ambiguos ou em conflito ficam fora ate a resolucao valida.

Todo treinamento deve produzir manifesto imutavel com empresa, hash, fontes,
exclusoes, snapshots, regras de elegibilidade e versao da pipeline. O dataset
nao precisa ser duplicado se puder ser reconstruido deterministicamente.

Modelos sao `candidate`, `active` ou `retired`; apenas um pode estar ativo por
empresa. Uma versao e imutavel e registra manifesto, avaliacao e threshold
proprio. Promocao e rollback sao acoes humanas de admin. O threshold por versao
e um gate de sugestao, nunca de aprovacao automatica.

Toda classificacao registra a versao do modelo. Previsao abaixo do threshold,
invalida no snapshot ou bloqueada por pendencia critica gera abstencao e
revisao. O revisor pode ver confianca, alternativas e evidencias objetivas;
nenhuma explicacao causal e inventada.

## Jobs, Observabilidade e Recuperacao

Jobs mantem estado tecnico independente do estado funcional: por exemplo, um
job pode concluir enquanto um lote historico permanece
`completed_with_warnings`. Payload e idempotencia sao imutaveis; retry e
cancelamento sao cooperativos e preservam evidencias.

Os pools iniciais sao `io/importacao` e `ml/cpu`. A entrega de jobs da Fase 4
generaliza somente o necessario para ML e nao reescreve a fila PostgreSQL do
Razao. A configuracao de concorrencia deve respeitar isolamento por empresa e
recurso.

Metricas devem ser agregadas e internas, sem conteudo contabil, segredos ou
telemetria privada do agent runner. Logs tecnicos e `audit_events` continuam
separados.

Backup deve conter o conjunto necessario para restaurar banco, artefatos de ML
e metadados, com manifesto, integridade, retencao, criptografia e alerta.
n8n nao e dependencia unica do proprio backup. Restauracao funcional e rebuild
completo precisam de evidencia medida antes de qualquer alegacao de RPO ou RTO.

## Matriz de Transicao

| Contrato atual | Regra da Fase 4 | Issue responsavel | Estado ate a entrega |
| --- | --- | --- | --- |
| Catalogo unico e `codigo` global | identidade por empresa, com versao e compatibilidade | #499 | contrato atual permanece legivel |
| Importacao do plano atualiza por codigo | snapshot por empresa, hash e vigencia | #501 | sem mudanca executavel |
| Revisao isolada de movimentos | Central de Revisoes com evidencias e claim | #500 | fluxo atual permanece valido |
| Razao com warnings e fila propria | validacao temporal, alias e revisao sem reescrever status historico | #502 | #473 a #486 permanecem preservadas |
| Movimento sem gate temporal | contexto por competencia/data/fallback e abstencao | #503 | contratos de layout e round-trip preservados |
| Dataset sem manifesto | gate de elegibilidade e manifesto reconstruivel | #504 | fontes atuais nao sao reclassificadas |
| ML sem lifecycle de versao | modelos imutaveis, avaliacao e promocao humana | #505 | algoritmo atual nao e trocado por esta decisao |
| Processamento ML no request | jobs duraveis por pool para ML | #506 | fila do Razao nao migra obrigatoriamente |
| Predicao como fluxo local | sugestao contextual, sem autoaprovacao | #507 | decisao humana final preservada |
| Logs e auditoria locais | metricas internas agregadas e separadas | #508 | #404 continua complementar |
| Backup manual inicial | backup automatizado, cifrado e monitorado | #509 | procedimento manual continua fallback |
| Restore nao certificado | teste de DR e runbooks com evidencia | #510 | nenhum restore produtivo nesta issue |

## Compatibilidade e Migracao

Mudancas de modelo com dados existentes seguem `expand -> migrate -> transition
-> contract`. A fase de expand introduz o novo contrato sem quebrar leitores;
migrate faz backfill idempotente e verificavel; transition move consumidores
por recorte; contract remove o legado somente quando nao houver dependentes.

Nenhuma issue pode usar esta spec para alterar silenciosamente dados historicos,
substituir classificacao por sugestao, apagar snapshots ou escolher um conflito
temporal sem revisao.

## Governanca de Agentes

Cada issue oficial usa branch e worktree exclusivas, com Task Review imutavel,
validacoes e draft PR antes de revisao humana. A Spec 14 e o protocolo GitHub
sao mais restritivos que esta spec durante o piloto: uma issue documental por
vez e nenhuma issue comportamental automatizada antes da decisao da #382.

O documento arquitetural nao autoriza inicio automatico, merge, producao,
forca em Git, descarte de alteracoes locais ou execucao de comando arbitrario.

## Criterios de Aceite

1. A Fase 4 possui objetivo, fronteiras, contratos e fora de escopo claros.
2. A matriz identifica o destino de cada contrato afetado sem duplicar fontes.
3. A Release 1 permanece historicamente preservada ate supersessao por issue
   especifica.
4. As regras de compatibilidade, ambiguidade e decisao humana sao explicitas.
5. Jobs, metricas e recuperacao ficam separados de regras contabeis.
6. Nenhuma regra desta spec exige ou permite mudanca executavel nesta issue.

## Decisoes Aprovadas

- A Fase 4 e posterior a Release 1 e usa esta spec como fonte arquitetural.
- PRD e specs sao a convencao documental canonica; ADR paralelo nao sera criado.
- A migracao do modelo contabil sera incremental e compativel.
- ML sugere; humano decide nesta fase.
- Snapshot e modelo sao imutaveis; status final de importacao e historico.
- A esteira agentic vigente prevalece ate que uma decisao aprovada a superseda.

## Open Questions

Nenhuma decisao estrutural adicional bloqueia as issues #499 a #510. Cada uma
deve receber Task Review propria antes de alterar comportamento, dados ou
operacao.

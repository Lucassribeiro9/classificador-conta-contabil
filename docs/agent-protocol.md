# Protocolo GitHub da esteira supervisionada

Este documento explica como operar o contrato versionado pela issue #372. A
arquitetura, os limites e as responsabilidades continuam definidos em
`docs/specs/14-esteira-agentes-supervisionada.md`. O protocolo não bloqueia a Release 1 e não implementa o runner, o orquestrador ou qualquer transição
automática.

## Artefatos e fontes

- `.github/agent-protocol.json`: contrato operacional consumível por máquina.
- `.github/agent-protocol.schema.json`: JSON Schema do manifesto e das
  confirmações estruturadas.
- `docs/specs/14-esteira-agentes-supervisionada.md`: fonte arquitetural.
- Este documento: referência humana curta; não substitui o manifesto.

O protocolo começa em `1.0.0` e usa SemVer próprio. Correções compatíveis
incrementam patch, extensões retrocompatíveis incrementam minor e quebras de
contrato incrementam major.

## Estado oficial

`ready-for-agent` informa apenas que a issue é elegível. Ele pode coexistir com
um estado operacional. O estado nativo `open/closed` do GitHub continua sendo
a fonte oficial de conclusão.

Os estados operacionais são mutuamente exclusivos:

| Estado | Uso |
| --- | --- |
| `agent:awaiting-task-review` | Task Review em elaboração ou invalidada |
| `agent:awaiting-human` | Uma decisão ou autorização humana está pendente |
| `agent:ready-to-implement` | Registro aprovado e implementação autorizada |
| `agent:running` | Runner executando com a trava adquirida |
| `agent:awaiting-manual-test` | Draft e roteiro aguardando homologação |
| `agent:validated` | Conteúdo relevante do commit homologado |
| `agent:blocked` | Intervenção necessária antes de continuar |
| `agent:cancelled` | Execução cancelada pelo mantenedor |

Ausência de estado operacional é representada por `null`; não existe label
`agent:none`. Mais de um `agent:*` resulta em `state_conflict`: nenhuma label é
removida ou escolhida automaticamente, e a correção deve ser humana.

Uma transição substitui somente a label operacional e preserva
`ready-for-agent` e as demais labels. Transições não declaradas são rejeitadas
sem mudar estado ou labels. Depois de qualquer fechamento, a execução deixa de
ser elegível, evidências são preservadas e a label operacional deve ser
removida. Uma reabertura começa em `null` e exige nova Task Review.

## Task Review e decisões

A Task Review percorre uma pergunta por vez:

1. o agente publica a pergunta na issue;
2. o estado passa para `agent:awaiting-human`;
3. o mantenedor responde em comentário novo com `/agent decide A`;
4. a opção é normalizada, confirmada e o estado retorna para
   `agent:awaiting-task-review`;
5. depois de todas as decisões, o agente publica o Registro estruturado;
6. o mantenedor usa `/agent approve-task-review` uma única vez.

A aprovação só é válida para um Registro `PRONTA PARA APROVACAO`, sem pergunta,
contradição ou bloqueio pendente. Ela fica vinculada aos hashes do corpo da
issue e do Registro, ao comentário do Registro, à spec aplicável, ao commit da
spec e à branch aprovada. Mudança do contexto exige nova validação.

## Comandos humanos

No piloto, somente `Lucassribeiro9` pode emitir comandos. Eles são aceitos
somente como comentários novos na issue correspondente:

```text
/agent approve-task-review
```

```text
/agent decide A

Justificativa opcional.
```

```text
/agent retry
```

```text
/agent cancel
```

A primeira linha deve seguir exatamente a gramática do manifesto: `/agent` e o
comando em minúsculas, um espaço ASCII entre elementos e nenhum texto ou espaço
extra. A justificativa pode começar na segunda linha. A opção de `decide` não
diferencia maiúsculas e minúsculas, mas precisa ter sido oferecida na pergunta
pendente; `A`, `a` e `opcao-a` são normalizados para `opcao-a`.

Edição de comentário, reação, checkbox, Teams e e-mail não autorizam ações.
Resultados de homologação são registrados no draft PR esperado, não por um
comando `/agent` no PR.

## Pedidos assíncronos

`/agent retry` e `/agent cancel` registram inicialmente `accepted_pending`.
Eles não mudam o estado ao serem aceitos:

- `retry` mantém `agent:blocked` até o runner revalidar o contexto e readquirir
  as travas;
- `cancel` mantém `agent:running` até o encerramento controlado preservar as
  evidências e concluir a operação.

Falha preserva o estado anterior. `/agent approve-task-review` também pode
renovar uma execução cancelada quando todos os hashes e referências continuam
válidos.

## Rejeições e confirmações

Um comando inválido do mantenedor produz uma confirmação estruturada e não
altera estado. Os códigos estáveis estão no manifesto, incluindo
`transition_not_allowed`, `wrong_location`, `no_pending_decision`,
`invalid_option`, `task_review_incomplete` e `state_conflict`.

Eventos de autores não autorizados não recebem resposta pública. Comentários
editados, reações e checkboxes são ignorados sem mudança de estado.

Cada confirmação aceita ou rejeitada contém um resumo Markdown e um bloco JSON
validável por `#/$defs/structuredConfirmation`. O registro inclui comando,
ator, instante, repositório, issue, comentário de origem, estados anterior e
novo, execução quando houver e resultado das validações. Campos desconhecidos
são rejeitados; credenciais, assinaturas, prompts, raciocínio, diffs, logs
brutos, URLs privadas, métricas privadas e dados contábeis são proibidos.

## Criação e verificação das labels

A configuração da #372 cria ou atualiza as oito labels a partir do manifesto e
as consulta novamente no GitHub. Nome, cor e descrição precisam coincidir. A
CI valida os artefatos localmente e não recebe acesso de escrita ou nova
permissão de rede.

A #372 não recebe estados retroativos, pois sua Task Review começou antes deste
contrato. O uso prospectivo pode começar na #373 como acompanhamento manual;
essa execução não conta como uma das três calibrações formais da #381.

## Limites desta entrega

Este protocolo define dados e invariantes. Ele não implementa o runner, parser
de eventos, skills, n8n, worktrees, HMAC, notificações, telemetria ou
sincronização contínua de labels. Essas capacidades permanecem nas issues
subsequentes da #371. Até lá, o fluxo manual da Spec 14 continua sendo o
fallback oficial.

## Validação local

Execute:

```bash
./venv/bin/pytest -q tests/test_agent_protocol.py
```

A validação também deve incluir `git diff --check`, inspeção do diff, busca de
segredos e leitura posterior das labels reais no GitHub.

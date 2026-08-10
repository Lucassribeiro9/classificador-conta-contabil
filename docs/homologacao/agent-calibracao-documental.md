# Checklist de calibração documental da esteira (#381)

Issue: <https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/381>
Branch: `docs/agent-calibracao-documental`

Este documento consolida a calibração operacional do piloto de agentes
supervisionado. Ele deve ser atualizado ao fim de cada rodada documental e
concluído somente depois das três execuções previstas.

## Objetivo

Validar que a esteira consegue conduzir três issues documentais/spec reais,
uma por vez, preservando escopo, estados, evidências, notificações, telemetria
privada e fallback manual.

## Decisões aprovadas na Task Review

- As três rodadas usam issues documentais/spec reais.
- As issues selecionadas são #363, #364 e #365.
- O workflow real do n8n deve ser usado sempre que possível.
- Falha de infraestrutura não deve ser corrigida dentro da rodada; deve ser
  classificada como bloqueante ou melhoria futura.
- Uma rodada válida exige issue, PR, commit, homologação manual e registro
  comparativo completo.
- Telemetria deve ser registrada apenas de forma privada, sem valores, caminhos
  reais ou consultas sensíveis no GitHub.
- Notificações Teams/e-mail devem ser conferidas pelo efeito operacional:
  sucesso ou falha tratada sem corromper estado.
- O checklist consolidado deve ser atualizado ao fim de cada rodada.
- A #381 terá PR próprio para versionar este checklist.

## Issues da calibração

| Rodada | Issue | Título | Status da rodada | PR | Commit homologado | Comentário de homologação |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | #363 | `spec(harness): consolidar fundação, qualidade e documentação do Ciclo 0` | Pendente | Pendente | Pendente | Pendente |
| 2 | #364 | `spec(razao): incorporar saldos contábeis e fechamentos mensais à spec 04` | Pendente | Pendente | Pendente | Pendente |
| 3 | #365 | `spec(movimentos): definir dois layouts operacionais com saldo na spec 08` | Pendente | Pendente | Pendente | Pendente |

Se uma issue selecionada revelar escopo inadequado durante a Task Review
própria, a substituição deve ser registrada nesta seção com justificativa e
link para a evidência.

## Critérios por rodada

Marque cada item apenas com evidência pública segura. Não cole métricas
privadas, caminhos locais reais, prompts, respostas completas, diffs, logs
brutos, URLs privadas, segredos ou dados contábeis.

| Critério | Rodada 1 | Rodada 2 | Rodada 3 |
| --- | --- | --- | --- |
| Task Review aprovada | Pendente | Pendente | Pendente |
| Execução única, sem duplicidade | Pendente | Pendente | Pendente |
| Escopo limitado à issue | Pendente | Pendente | Pendente |
| Nenhum segredo ou dado privado exposto | Pendente | Pendente | Pendente |
| Estados e gates corretos | Pendente | Pendente | Pendente |
| Worktree/evidências preservadas quando aplicável | Pendente | Pendente | Pendente |
| Draft PR criado com roteiro reproduzível | Pendente | Pendente | Pendente |
| Homologação manual registrada no PR | Pendente | Pendente | Pendente |
| Workflow real do n8n usado ou fallback justificado | Pendente | Pendente | Pendente |
| Notificações funcionando ou falhando sem corromper estado | Pendente | Pendente | Pendente |
| Telemetria privada conferida sem publicar valores | Pendente | Pendente | Pendente |
| No máximo uma correção automática | Pendente | Pendente | Pendente |
| Fallback manual disponível | Pendente | Pendente | Pendente |

## Registro por rodada

### Rodada 1 — #363

- Resultado: Pendente
- Issue: <https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/363>
- PR: Pendente
- Commit testado: Pendente
- Ambiente: Pendente
- Perfil: Pendente
- Workflow n8n: Pendente
- Notificações: Pendente
- Telemetria privada: Pendente
- Fallback manual: Pendente
- Divergências: Pendente
- Decisão da rodada: Pendente

### Rodada 2 — #364

- Resultado: Pendente
- Issue: <https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/364>
- PR: Pendente
- Commit testado: Pendente
- Ambiente: Pendente
- Perfil: Pendente
- Workflow n8n: Pendente
- Notificações: Pendente
- Telemetria privada: Pendente
- Fallback manual: Pendente
- Divergências: Pendente
- Decisão da rodada: Pendente

### Rodada 3 — #365

- Resultado: Pendente
- Issue: <https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/365>
- PR: Pendente
- Commit testado: Pendente
- Ambiente: Pendente
- Perfil: Pendente
- Workflow n8n: Pendente
- Notificações: Pendente
- Telemetria privada: Pendente
- Fallback manual: Pendente
- Divergências: Pendente
- Decisão da rodada: Pendente

## Classificação de falhas

Use esta classificação quando a esteira não concluir uma etapa como esperado.

| Classificação | Quando usar | Efeito esperado |
| --- | --- | --- |
| Bloqueante da rodada | Impede validar a rodada sem risco de perder evidência ou corromper estado | Pausar a rodada e registrar intervenção necessária |
| Melhoria futura | Não impede concluir a rodada com fallback seguro | Registrar evidência e criar issue futura somente se necessário |
| Não reprodutível | Ocorreu uma vez e não pôde ser confirmado | Registrar contexto mínimo sem ampliar escopo |
| Fora de escopo | Exige alterar infraestrutura, contrato ou comportamento não aprovado | Não corrigir na rodada; encaminhar para nova Task Review/issue |

## Decisão final da calibração

- Resultado final: Pendente
- As três rodadas atenderam aos critérios? Pendente
- Fallback manual permaneceu funcional? Pendente
- Houve exposição de segredo, métrica privada ou dado sensível? Pendente
- Há pendências antes da #382? Pendente
- Recomendação para a #382: Pendente

Mesmo que as três rodadas sejam aprovadas, issues comportamentais só podem ser
avaliadas na #382 e não ficam liberadas automaticamente.

## Evidências permitidas

- Links de issues, PRs e comentários de homologação.
- SHAs de commits públicos.
- Resultado resumido de testes e validações.
- Confirmação textual de telemetria privada conferida, sem valores.
- Confirmação textual de notificações ou falha tratada, sem payload privado.

## Evidências proibidas

- Métricas privadas de consumo.
- Caminhos locais reais.
- URLs privadas.
- Prompts, respostas completas ou raciocínio.
- Diffs ou logs brutos.
- Segredos, tokens, assinaturas ou dados contábeis.

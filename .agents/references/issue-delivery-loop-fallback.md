# Fallback manual da coordenadora

Use esta referência quando `issue-delivery-loop` ou o futuro runner estiver
indisponível. GitHub continua sendo a fonte oficial de estado e decisões.

## Mapeamento de etapas

| `prompt_section` | Etapa | Execução humana | Checkpoint |
| --- | --- | --- | --- |
| `task-review` | Task Review | `issue-task-review` | Issue |
| `spec-delivery` | Entrega de spec | `spec-delivery` | Issue |
| `implementation` | Implementação | `implement-issue` | Issue |
| `draft-pr` | Preparação do draft | `prepare-draft-pr` | Pull request |
| `manual-homologation` | Homologação | Mantenedor | Pull request |

## Retomada

1. Leia a issue, a Task Review aprovada, a spec e o último checkpoint válido.
2. Confirme que o estado GitHub é compatível com a etapa do checkpoint.
3. Confirme `contract_version`, tentativa e `previous_output_ref`.
4. Use no guia o prompt indicado por `prompt_section`.
5. Valide a saída contra o contrato compartilhado.
6. Publique o novo checkpoint como comentário novo e append-only.
7. Na issue, registre Task Review e entrega. No PR, registre draft,
   homologação e conclusão.

Comentário editado não substitui checkpoint aceito. Uma nova tentativa exige
intervenção humana válida e incrementa `attempt`. Repetir a mesma chave de
idempotência não autoriza nova delegação.

## Conteúdo público permitido

O comentário contém somente o envelope estruturado e sanitizado necessário à
retomada: issue, classificação, resultado, bloqueios, referências, checkpoint,
evidências resumidas e payload contratado.

Não publique prompts completos, respostas, raciocínio, métricas de tokens,
segredos, dados contábeis, logs brutos ou diffs. Se a sanitização não puder ser
confirmada, não publique o artefato e solicite intervenção humana.

## Limites

- Não corrija estado contraditório por inferência.
- Não faça retry automático.
- Não altere a issue seguinte.
- A próxima sub-issue elegível pode ser sugerida, nunca iniciada.
- Merge e operação de produção permanecem humanos.

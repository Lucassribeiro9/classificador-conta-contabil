# Fontes das skills de entrega

Use esta matriz para carregar somente o contexto necessário à etapa atual.
Quando duas fontes divergirem, interrompa o trabalho e registre a contradição;
não escolha silenciosamente uma interpretação.

## Hierarquia canônica

1. PRD: visão de produto, releases e ciclos.
2. Spec aplicável: contrato técnico, estados e limites.
3. Issue e Task Review aprovada: unidade e autorização de trabalho.
4. Skill especializada: procedimento executável da etapa.
5. `docs/prompts-fluxo-sdd-tdd.md`: fallback para execução humana.

O protocolo em `.github/agent-protocol.json` é canônico para nomes de estados,
eventos e comandos. `.github/BRANCHING.md` governa branches e
`.github/pull_request_template.md` governa o conteúdo do PR.

## Política por skill

| Skill | Obrigatório | Condicional | Proibido |
| --- | --- | --- | --- |
| `issue-task-review` | Issue, comentários, issue-pai, dependências, PRD/spec aplicáveis, protocolo e branching | Histórico recente, specs relacionadas, templates e documentos de homologação quando afetarem o escopo | Código ou documentos sem relação, segredos, telemetria privada, prompts completos |
| `spec-delivery` | Issue, Task Review aprovada, PRD e spec autorizada, specs diretamente relacionadas | Histórico e templates necessários para rastreabilidade | Outras specs não autorizadas, implementação, novas issues, dados privados |
| `implement-issue` | Issue, Task Review aprovada, spec aplicável, branch aprovada, arquivos previstos e comandos de validação | Código vizinho, fixtures e docs somente quando necessários ao seam público | Outra issue, refatoração oportunista, segredos, produção, contexto amplo sem justificativa |
| `prepare-draft-pr` | Issue, Task Review, template de PR, branching, diff, commits, worktree e evidências reais | Spec/PRD e roteiro de homologação quando citados pelo diff | Arquivos fora do diff, resultados inventados, logs brutos, segredos, próxima issue |

## Saída comum

Valide toda saída JSON contra
`.agents/contracts/delivery-skill-output.schema.json`. Um resumo Markdown pode
acompanhar a resposta para leitura humana, mas o coordenador deve consumir
somente o JSON. Nunca inclua prompt, raciocínio, segredo, dado contábil, log
bruto ou métrica privada no envelope. Não use subagentes no piloto; cada skill
executa somente a própria etapa dentro da única execução autorizada.

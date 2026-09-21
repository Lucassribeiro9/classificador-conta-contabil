# Project Agents — Runtime Foundation

## Objetivo

Definir a fundacao compartilhada para quatro Agents especificos do projeto Classificador Contabil:

- Task Reviewer Agent;
- Issue Executor Agent;
- PR Reviewer Agent;
- Delivery Closer Agent.

Esta camada nao substitui nem altera a esteira agentic operacional atual do projeto. Ela sera desenvolvida e validada de forma isolada para uso futuro, quando a esteira supervisionada estiver amadurecida e uma issue propria autorizar a integracao.

## Principios

1. Agent define contexto de projeto; Skill blueprint define comportamento reutilizavel.
2. Agents devem permanecer finos e nao duplicar regras de dominio, planejamento, execucao ou revisao.
3. Git/GitHub e os contratos aprovados sao a verdade material; handoffs sao transporte efemero.
4. Nenhum Agent chama automaticamente o proximo.
5. O contexto de runtime e reconstruido a cada execucao; nao existe estado persistido em `.agents/runs`, `.agents/state` ou `.agents/handoffs`.
6. A identidade do projeto deve ser comprovada antes de executar qualquer blueprint.
7. Os novos Agents podem coexistir com a esteira atual sem interferir nela.
8. A integracao com a esteira atual, seus labels, checkpoints, comandos e protocolo sera tratada somente por issue futura.

## Estrutura canonica

```text
.agents/
├── agents/
│   ├── task-reviewer.md
│   ├── issue-executor.md
│   ├── pr-reviewer.md
│   └── delivery-closer.md
├── contracts/
│   ├── project-agent.schema.json
│   └── project-context-envelope.schema.json
├── references/
│   └── project-context-bootstrap.md
└── local/
    ├── project-manifest.yaml
    └── capability-registry.yaml
```

Os arquivos em `.agents/agents/` sao as definicoes canonicas, independentes de Cursor, Codex ou Trae. Adapters especificos de ferramenta ficam fora desta entrega.

Durante a fase de validacao, as definicoes canonicas podem permanecer versionadas no repositorio. A politica definitiva de versionamento, ignorar arquivos locais ou adotar templates fica para decisao posterior.

## Formato do Agent

Cada Agent usa Markdown com frontmatter declarativo.

O frontmatter declara, no minimo:

- `id`;
- identidade esperada do projeto;
- Skill blueprint;
- bootstrap de contexto;
- entradas;
- saidas;
- providers;
- handoff.

O corpo Markdown deve conter apenas instrucoes curtas de contextualizacao. Procedimentos detalhados continuam na Skill blueprint.

Exemplo conceitual:

```yaml
---
id: task-reviewer

project:
  id: classificador-conta-contabil
  repository: Lucassribeiro9/classificador-conta-contabil

blueprint: task-review

context:
  bootstrap: ../references/project-context-bootstrap.md

inputs:
  - issue
  - project_context

outputs:
  - review_report
  - execution_plan

handoff:
  next: issue-executor
  gate: human_approval
---
```

## Project Context Bootstrap

Todo Agent executa o mesmo bootstrap antes da blueprint:

```text
override explicito, se houver
        ↓
descobrir raiz Git
        ↓
identificar branch/worktree
        ↓
validar identidade do projeto
        ↓
localizar Manifest/Registry
        ↓
resolver e validar issue
        ↓
detectar providers
        ↓
montar Project Context Envelope em memoria
```

O bootstrap nao executa logica de negocio e nao substitui a Skill blueprint.

### Identidade do projeto

A identidade e validada por evidencias hierarquizadas:

1. Git remote / GitHub;
2. Project Manifest;
3. estrutura e evidencias do repositorio.

Remote/GitHub e a evidencia mais forte, mas nao e dependencia absoluta.

Se nao houver evidencia suficiente para provar que o workspace pertence ao Classificador Contabil:

```yaml
status: blocked
reason: project_identity_unverified
```

Path fisico diferente, clone diferente ou worktree nao alteram a identidade logica do repositorio.

### Resolucao da issue

A issue deve ser explicita por padrao. Se nao for fornecida, o bootstrap pode fazer inferencia controlada a partir da branch ou worktree, mas deve confirmar a correspondencia no GitHub.

Se nao houver prova suficiente:

```yaml
status: blocked
reason: issue_required
```

## Project Context Envelope

O envelope e efemero e nunca e salvo como estado.

Exemplo:

```yaml
project_context:
  repository:
    root: /workspace/classificador-conta-contabil
    identity: Lucassribeiro9/classificador-conta-contabil
    verification:
      status: verified
      confidence: high
      sources:
        - git_remote

  issue:
    id: 484
    source: explicit
    verified: true

  workspace:
    type: worktree
    branch: feat/484-card-limits

  manifest:
    path: .agents/local/project-manifest.yaml
    status: present

  capability_registry:
    path: .agents/local/capability-registry.yaml
    status: present

  providers:
    github: mcp
    git: available
    terminal: available
```

O envelope responde apenas:

- onde estou;
- qual projeto e issue estao ativos;
- qual workspace esta em uso;
- quais fontes locais estao disponiveis;
- quais providers podem ser usados.

Ele nao duplica Project Manifest nem Capability Registry.

## Contrato entre Agents

Os Agents nao se autoencadeiam.

Fluxo canonico:

```text
Task Reviewer Agent
        ↓
Review Report + Execution Plan
        ↓
HUMAN APPROVAL
        ↓
Issue Executor Agent
        ↓
Execution Evidence
        ↓
PR Reviewer Agent
        ↓
Draft PR + Findings
        ↓
HUMAN REVIEW / MERGE
        ↓
Delivery Closer Agent
```

O handoff e efemero e estruturado.

Exemplo:

```yaml
handoff:
  status: ready
  current_agent: task-reviewer
  next_agent: issue-executor

  issue:
    id: 484

  artifacts:
    execution_plan:
      plan_id: issue-484
      revision: 1
      schema_version: "1.1"

  gate:
    type: human_approval
    satisfied: false
```

Nao criar:

```text
.agents/runs/
.agents/state/
.agents/handoffs/
```

## Execution Plan 1.1

A evolucao do Execution Plan adiciona `references` estruturadas sem quebrar consumidores 1.x.

Regra de versao:

- 1.0: contrato original;
- 1.1: adiciona `references`;
- 1.x: mudancas backward-compatible;
- 2.0: mudancas incompatíveis.

Exemplo:

```yaml
schema_version: "1.1"

capabilities:
  required:
    - tdd
    - django
    - accounting-classification-domain

references:
  specs:
    - path: docs/specs/005-cartoes-faturas-limites.md
      role: behavior_contract
      required: true

  architecture:
    - path: docs/architecture/accounting-classifier.md
      role: architecture_context
      required: false

  code:
    - path: cards/selectors.py
      role: implementation_context
      required: true
```

A Task Review descobre e declara capabilities e referencias. O Capability Registry resolve como atender as capabilities. O Executor consome o plano aprovado e apenas revalida sua disponibilidade e validade.

## Revalidacao no Executor

O Executor nao redescobre o projeto inteiro.

```text
referencia/capability valida
→ usar

referencia apenas movida
→ resolver + registrar local deviation

referencia ou premissa semanticamente invalida
→ material deviation
→ interromper
→ nova Task Review/revisao do plano
```

## Estados de saida

Todos os Agents terminam com um estado estruturado.

Estados canonicos:

- `ready`;
- `blocked`;
- `needs_re_review`;
- `failed`;
- `completed`.

Razoes comuns incluem:

- `project_identity_unverified`;
- `issue_required`;
- `provider_unavailable`;
- `manifest_invalid`;
- `capability_unresolved`;
- `reference_unavailable`;
- `approval_required`;
- `material_deviation`;
- `validation_failed`;
- `dirty_workspace`;
- `merge_not_proven`;
- `unsafe_cleanup`.

Erro operacional e bloqueio de governanca devem permanecer distintos.

Nenhum Agent pode converter silenciosamente um bloqueio em outro tipo de trabalho para continuar.

## Relacao com a esteira atual

O repositorio ja possui Skills locais, contratos, `issue-delivery-loop` e `.github/agent-protocol.json`.

Eles permanecem inalterados nesta entrega.

Os novos Agents:

- nao fazem parte da operacao atual;
- nao substituem o `issue-delivery-loop`;
- nao precisam reproduzir seus labels, checkpoints ou comandos;
- podem ser definidos e testados de forma isolada;
- serao integrados apenas quando uma issue futura decidir como reconciliar os dois modelos.

Diferencas entre a esteira atual e os novos contratos nao sao defeitos desta entrega. A integracao futura deve analisar compatibilidade e realizar os ajustes necessarios.

## Estrategia de testes

### Validacao estrutural

Validar:

- frontmatter dos Agents contra `project-agent.schema.json`;
- Project Context Envelope contra `project-context-envelope.schema.json`;
- campos obrigatorios;
- referencias de blueprint;
- handoffs;
- providers.

### Bootstrap

Cobrir:

- main;
- worktree valido;
- repo correto via remote;
- repo correto sem remote;
- repo incorreto;
- Manifest presente/ausente;
- Registry presente/ausente;
- issue explicita valida;
- issue inferida e confirmada;
- issue inferida nao comprovada;
- provider disponivel/indisponivel.

### Fluxo integrado

Happy path:

```text
Task Reviewer
→ approval
→ Issue Executor
→ PR Reviewer
→ merge humano
→ Delivery Closer
```

Fluxo de revisao:

```text
Task Reviewer rev1
→ Executor encontra material deviation
→ Task Reviewer rev2
→ approval
→ Executor
→ PR Reviewer
```

Teste de isolamento obrigatorio:

```text
Agent do Classificador
+
outro repositorio
→ execucao bloqueada
```

## Fora de escopo

- integrar os Agents a esteira operacional atual;
- alterar `.github/agent-protocol.json`;
- substituir ou remover Skills locais existentes;
- alterar labels `agent:*`;
- criar orquestrador central;
- auto-chaining;
- gerar adapters para Cursor, Codex ou Trae;
- persistir runtime state;
- decidir politica definitiva de versionamento dos Agents;
- automatizar merge.

## Criterios de aceite

1. Existe um contrato canonico para definicao de Agent.
2. Existe um contrato canonico para Project Context Envelope.
3. O bootstrap prova projeto, workspace, issue e providers antes da blueprint.
4. Os quatro Agents compartilham a mesma fundacao sem duplicar regras.
5. Handoffs sao estruturados e efemeros.
6. Execution Plan 1.1 carrega `references` estruturadas.
7. O Agent do Classificador bloqueia quando a identidade do projeto nao e comprovada.
8. Os testes cobrem estrutura, bootstrap, comportamento e fluxo integrado.
9. A esteira atual permanece operacionalmente inalterada.
10. A integracao futura fica explicitamente fora do escopo.

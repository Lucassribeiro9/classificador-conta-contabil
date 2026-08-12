# Prompts e Fluxo de Trabalho SDD/TDD

Este guia define a sequencia recomendada para continuar o projeto usando PRD, specs, issues, TDD e pull requests pequenos.

## Sequencia Recomendada

1. Revisar PRD.
2. Revisar specs derivadas.
3. Gerar issues pequenas a partir de cada spec.
4. Priorizar issues.
5. Escolher uma issue por vez.
6. Fazer review da issue antes de implementar.
7. Sugerir branch seguindo `.github/BRANCHING.md`.
8. Classificar a issue como documental, comportamental ou configuracao testavel.
9. Usar TDD apenas quando a issue alterar comportamento, contrato executavel ou configuracao testavel.
10. Implementar o minimo necessario.
11. Rodar testes ou validacoes proporcionais ao escopo.
12. Refatorar se necessario.
13. Atualizar docs/specs apenas se alguma decisao mudar.
14. Preparar PR em bloco unico Markdown ou draft no GitHub seguindo `.github/pull_request_template.md`.

Fluxo resumido:

```text
PRD aprovado
-> Specs revisadas
-> Issues pequenas
-> Task Review
-> Branch sugerida
-> TDD quando aplicavel
-> Implementacao minima
-> Testes ou validacoes verdes
-> PR
```

## Ordem Inicial das Specs

1. `docs/specs/01-postgresql-migracao.md`
2. `docs/specs/02-auth-usuarios-permissoes.md`
3. `docs/specs/03-plano-contas-catalogo.md`
4. `docs/specs/04-importacao-razao-normalizacao.md`
5. `docs/specs/05-dataset-treino-contrapartida.md`
6. `docs/specs/06-ml-classificacao-feedback.md`
7. `docs/specs/07-auditoria-seguranca-operacional.md`
8. `docs/specs/15-harness-qualidade-documentacao.md` para Ciclo 0 da Release 1

## Regra Principal

Trabalhe sempre em uma issue por vez.

Nao misture specs diferentes no mesmo ciclo de implementacao. Se uma issue tocar PostgreSQL, autenticacao e importacao ao mesmo tempo, ela provavelmente esta grande demais e deve ser quebrada.

## Prompt Para Gerar Issues de Uma Spec

Use quando uma spec ja foi revisada e voce quer transforma-la em issues pequenas.

```text
Use spec-driven-development.

Vamos gerar issues pequenas a partir da spec:
<caminho-da-spec>

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: <caminho-da-spec>

Regras:
1. Nao implemente nada.
2. Gere issues pequenas e ordenadas por dependencia.
3. Cada issue deve ter titulo, contexto, escopo, criterios de aceite, testes esperados e riscos.
4. Cada issue deve caber em um PR focado.
5. Separe issues funcionais, tecnicas, testes e docs quando fizer sentido.
6. Aponte quais issues devem usar TDD obrigatoriamente.
7. Quando gerar texto para GitHub, siga o template correspondente em `.github/ISSUE_TEMPLATE/`.
8. Seja conciso para economizar tokens, sem remover criterios de aceite e validacao.
```

## Prompt Para Revisar Uma Issue Antes de Implementar

Use antes de comecar qualquer implementacao.

```text
Use spec-driven-development.

Vamos fazer Task Review da issue:
<titulo-da-issue>

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: <caminho-da-spec>
- Issue: <cole aqui o texto da issue ou informe o caminho do arquivo>

Separe:
1. escopo exato;
2. testes que devem ser escritos primeiro;
3. riscos;
4. arquivos provaveis;
5. branch sugerida seguindo `.github/BRANCHING.md`;
6. perguntas bloqueantes.

Nao implemente nada ainda. Quero responder as decisoes primeiro.
```

## Prompt Para Implementar Uma Issue Com TDD

Use depois que a issue ja foi revisada e as perguntas bloqueantes foram respondidas.

```text
Use spec-driven-development e TDD.

Implemente a issue:
<titulo-da-issue>

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: <caminho-da-spec>
- Issue: <cole aqui o texto da issue ou informe o caminho do arquivo>

Regras:
1. Nao implemente nada fora do escopo da issue.
2. Comece revisando PRD, spec e issue.
3. Antes de editar arquivos, sugira o nome da branch seguindo `.github/BRANCHING.md`.
4. Liste um plano curto.
5. Escreva ou ajuste testes primeiro.
6. Rode os testes e confirme que falham pelo motivo esperado.
7. Implemente o minimo necessario.
8. Rode os testes novamente.
9. Refatore apenas se necessario.
10. Atualize docs/spec somente se alguma decisao mudar.
11. No final, informe arquivos alterados, testes executados e riscos restantes.

Nao avance para outra issue.
```

## Prompt Para Implementar Uma Issue Frontend

Use depois que PRD, spec e issue de frontend ja estiverem revisados.

```text
Use spec-driven-development, frontend-design e TDD.

Implemente a issue:
<titulo-da-issue>

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: <caminho-da-spec-frontend>
- Issue: <cole aqui o texto da issue ou informe o caminho do arquivo>
- Figma: <cole o link do frame, se aplicavel>

Regras:
1. Nao implemente nada fora do escopo da issue.
2. Antes de editar arquivos, sugira a branch seguindo `.github/BRANCHING.md`.
3. Preserve a direcao visual aprovada: branco, #007693, #004E61, cinzas neutros e UI operacional compacta.
4. Comece pelos testes/validacoes cabiveis: typecheck, lint, teste de componente ou Playwright quando houver fluxo.
5. Implemente o minimo necessario em `frontend/`.
6. Rode as validacoes relevantes.
7. Informe arquivos alterados, validacoes executadas e riscos restantes.

Nao avance para outra issue.
```

## Prompt Para Corrigir Uma Falha de Teste

Use quando uma issue esta em andamento e algum teste falhou.

```text
Use TDD.

Temos uma falha ao executar:
<comando-de-teste>

Resultado relevante:
<cole o erro ou resumo>

Contexto:
- Spec: <caminho-da-spec>
- Issue: <titulo-da-issue>

Tarefa:
1. Explique a causa provavel.
2. Corrija apenas o necessario para esta issue.
3. Rode novamente os testes relevantes.
4. Nao altere escopo, specs ou comportamento fora da issue.
```

## Prompt Para Atualizar Uma Spec Depois de Nova Decisao

Use quando durante a implementacao surgir uma decisao nova.

```text
Use spec-driven-development.

Durante a issue <titulo-da-issue>, decidimos:
<descreva a decisao>

Atualize somente a spec:
<caminho-da-spec>

Regras:
1. Nao implemente codigo.
2. Adicione a decisao em "Decisoes Aprovadas".
3. Ajuste Boundaries, Success Criteria ou Open Questions se necessario.
4. Mantenha portugues tecnico e ASCII.
```

## Prompt Para Preparar Pull Request

Use depois de implementar e testar uma issue.

```text
Prepare o PR para a issue:
<titulo-da-issue>

Contexto:
- Spec: <caminho-da-spec>
- Issue: <numero-ou-titulo>
- Branch: <branch-usada>
- Template: .github/pull_request_template.md

Regras:
1. Siga `.github/pull_request_template.md`.
2. Entregue o corpo do PR em um unico bloco de codigo Markdown.
3. Nao quebre a formatacao fora do bloco.
4. Inclua `Closes #<numero>` quando houver numero de issue.
5. Seja conciso, mas mantenha resumo, escopo, evidencias, riscos e rollback.
6. Se tiver acesso ao GitHub e eu pedir, crie o PR como draft em vez de apenas gerar o texto.
```

## Prompt Para Criar Draft PR no GitHub

Use quando a implementacao ja estiver validada e houver acesso ao GitHub.

```text
Use github:yeet ou github:github.

Crie um draft PR para a issue:
<titulo-da-issue>

Contexto:
- Issue: #<numero>
- Branch: <branch-usada>
- Template: .github/pull_request_template.md

Regras:
1. Confirme que a branch atual e a branch esperada.
2. Use o template de PR do repositorio.
3. Inclua `Closes #<numero>`.
4. Crie como draft.
5. No final, informe o link do PR, testes executados e riscos restantes.
```

## Fase 2 - Interface Grafica Interna

Use esta fase para PRD, specs, issues e implementacao do frontend separado em `frontend/`.

### Skills por Etapa

- `brainstorming`: antes de alterar escopo, fluxo de usuario ou experiencia operacional.
- `grill-me`: para fechar decisoes de produto, permissoes, homologacao e riscos.
- `to-prd`: para consolidar decisoes aprovadas em PRD.
- `spec-driven-development`: para criar specs, revisar issues e manter escopo.
- `frontend-design`: para design system, telas, Figma e aderencia visual.
- `tdd`: para implementacao guiada por testes e validacoes.
- `github:github` ou `github:yeet`: para publicar issues, branches, PRs e revisar fluxo GitHub.

### Specs Previstas

1. PRD da interface grafica interna.
2. Spec de UX e fluxos do frontend.
3. Spec de arquitetura tecnica React/Vite/SPA.
4. Spec de Docker, ambientes e homologacao.
5. Spec de padroes de codigo, comentarios e documentacao.
6. Spec de massa sanitizada de homologacao.

### Prompt Para Consolidar PRD da Interface

```text
Use to-prd, brainstorming e grill-me.

Consolide o PRD da interface grafica interna com base nas decisoes ja aprovadas.

Contexto:
- PRD atual: docs/prd/evolucao-plano-contas-importacao-ml.md
- Frontend separado em `frontend/`
- Stack aprovada: React, TypeScript, Vite, Tailwind, React Router e TanStack Query
- MVP: Login, Empresas, Operacao da Empresa, Importar Movimentos, Lote de Movimentos, Revisar Movimento, Razao e Contas Vinculadas

Regras:
1. Nao implemente codigo.
2. Preserve o fluxo operador/contador como foco da primeira homologacao.
3. Deixe CRUD admin de usuarios fora do MVP inicial.
4. Liste criterios de aceite e fora de escopo.
5. Mantenha texto conciso e pronto para virar issue/spec.
```

### Prompt Para Gerar Specs do Frontend

```text
Use spec-driven-development.

Gere as specs da fase de interface grafica interna.

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Figma: <link-do-figma>
- Stack: React, TypeScript, Vite, Tailwind, React Router, TanStack Query

Regras:
1. Nao implemente codigo.
2. Separe specs de UX, tecnica frontend, Docker/ambientes, padroes de codigo e homologacao.
3. Inclua boundaries, decisoes aprovadas, success criteria, riscos e perguntas abertas.
4. Use portugues tecnico, ASCII e seco o suficiente para economizar tokens.
```

### Prompt Para Validar Aderencia ao Figma

```text
Use frontend-design.

Valide a tela implementada contra o Figma:
<link-do-frame>

Contexto:
- Issue: <titulo-da-issue>
- Spec: <caminho-da-spec>
- Tela/rota: <rota>

Regras:
1. Verifique layout, hierarquia visual, cores, estados, responsividade e textos.
2. Aponte apenas divergencias acionaveis.
3. Nao proponha redesign fora do escopo da issue.
4. Indique validacoes executadas ou pendentes.
```

### Prompt Para Homologacao

```text
Use spec-driven-development e TDD.

Prepare a validacao de homologacao para:
<escopo>

Contexto:
- Ambiente: homologacao
- Perfil testado: operador/contador
- Dados sanitizados: plano de contas, razao e movimentos operacionais

Regras:
1. Nao use dados reais ou sensiveis.
2. Liste checklist objetivo de aceite.
3. Inclua comandos de validacao e evidencias esperadas.
4. Separe falhas bloqueantes de melhorias futuras.
```

## Casos de Uso

### Caso 1: Criar Issues da Spec de PostgreSQL

```text
Use spec-driven-development.

Vamos gerar issues pequenas a partir da spec:
docs/specs/01-postgresql-migracao.md

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: docs/specs/01-postgresql-migracao.md

Regras:
1. Nao implemente nada.
2. Gere issues pequenas e ordenadas por dependencia.
3. Cada issue deve ter titulo, contexto, escopo, criterios de aceite, testes esperados e riscos.
4. Cada issue deve caber em um PR focado.
5. Aponte quais issues devem usar TDD obrigatoriamente.
```

### Caso 2: Revisar Issue Antes de Implementar

```text
Use spec-driven-development.

Vamos fazer Task Review da issue:
chore(config): ajustar DATABASE_URL para SQLite e PostgreSQL

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: docs/specs/01-postgresql-migracao.md
- Issue: <cole aqui a issue>

Separe:
1. escopo exato;
2. testes que devem ser escritos primeiro;
3. riscos;
4. arquivos provaveis;
5. perguntas bloqueantes.

Nao implemente nada ainda. Quero responder as decisoes primeiro.
```

### Caso 3: Implementar Issue Com TDD

```text
Use spec-driven-development e TDD.

Implemente a issue:
chore(config): ajustar DATABASE_URL para SQLite e PostgreSQL

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: docs/specs/01-postgresql-migracao.md
- Issue: <cole aqui a issue>

Regras:
1. Nao implemente nada fora do escopo da issue.
2. Escreva ou ajuste testes primeiro.
3. Rode os testes e confirme que falham pelo motivo esperado.
4. Implemente o minimo necessario.
5. Rode os testes novamente.
6. No final, informe arquivos alterados, testes executados e riscos restantes.
```

### Caso 4: Atualizar PRD e Criar Specs da Interface

```text
Use spec-driven-development, to-prd e documentation-writer.

Implemente a issue:
spec(frontend): atualizar PRD e criar specs da interface grafica interna

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Guia de prompts: docs/prompts-fluxo-sdd-tdd.md
- Template de issue: .github/ISSUE_TEMPLATE/prd_spec.md
- Branching: .github/BRANCHING.md
- PR template: .github/pull_request_template.md
- Figma: <link-do-figma>
- Issue: <cole aqui a issue completa>

Regras:
1. Nao implemente codigo de aplicacao.
2. Antes de editar arquivos, sugira a branch seguindo `.github/BRANCHING.md`.
3. Atualize o PRD existente com a fase de interface grafica interna.
4. Crie as specs necessarias em `docs/specs/`.
5. Use portugues tecnico e ASCII.
6. Preserve o MVP aprovado: Login, Empresas, Operacao da Empresa, Importar Movimentos, Lote de Movimentos, Revisar Movimento, Razao e Contas Vinculadas.
7. Registre fora de escopo: CRUD admin no MVP, OFX, TXT/Dominio e implementacao do frontend.
8. Nao altere endpoints, banco, testes ou codigo backend.
9. Ao final, informe arquivos alterados, validacoes executadas e riscos restantes.
```

### Caso 5: Gerar Issues a Partir das Specs do Frontend

```text
Use spec-driven-development.

Vamos gerar issues pequenas a partir das specs da interface grafica interna:
- <spec-ux>
- <spec-tecnica-frontend>
- <spec-docker-ambientes>
- <spec-padroes-codigo>
- <spec-homologacao>

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Template de issue: .github/ISSUE_TEMPLATE/
- Branching: .github/BRANCHING.md

Regras:
1. Nao implemente nada.
2. Gere issues pequenas, ordenadas por dependencia.
3. Cada issue deve caber em um PR focado.
4. Cada issue deve conter contexto, escopo, criterios de aceite, validacoes, riscos e branch sugerida.
5. Separe docs/spec, setup frontend, telas, integracao API, testes, Docker e homologacao.
6. Aponte quais issues devem usar TDD, frontend-design ou Playwright.
7. Seja conciso para economizar tokens.
```

### Caso 6: Implementar Primeira Issue do Frontend

```text
Use spec-driven-development, frontend-design e TDD.

Implemente a issue:
<titulo-da-issue-frontend>

Contexto:
- PRD: docs/prd/evolucao-plano-contas-importacao-ml.md
- Spec: <caminho-da-spec-frontend>
- Issue: <cole aqui a issue>
- Figma: <link-do-frame>

Regras:
1. Nao implemente nada fora do escopo da issue.
2. Antes de editar arquivos, sugira a branch seguindo `.github/BRANCHING.md`.
3. Preserve a direcao visual aprovada: branco, #007693, #004E61, cinzas neutros e UI operacional compacta.
4. Comece por validacoes cabiveis: typecheck, lint, teste de componente ou Playwright quando houver fluxo.
5. Implemente o minimo necessario em `frontend/`.
6. Rode as validacoes relevantes.
7. No final, informe arquivos alterados, validacoes executadas e riscos restantes.
```

### Caso 7: Preparar PR em Bloco Markdown ou Draft

```text
Prepare o PR para a issue:
<titulo-da-issue>

Contexto:
- Spec: <caminho-da-spec>
- Issue: #<numero>
- Branch: <branch-usada>
- Template: .github/pull_request_template.md

Regras:
1. Siga `.github/pull_request_template.md`.
2. Entregue o corpo do PR em um unico bloco de codigo Markdown.
3. Inclua `Closes #<numero>`.
4. Mantenha resumo, escopo, evidencias, riscos e rollback.
5. Se eu pedir publicacao e houver acesso ao GitHub, crie como draft.
```

## Checklist Antes de Implementar

- [ ] A issue vem de uma spec revisada.
- [ ] A issue cabe em um PR pequeno.
- [ ] O escopo esta claro.
- [ ] As perguntas bloqueantes foram respondidas.
- [ ] Os testes esperados foram definidos.
- [ ] A implementacao nao mistura outra spec.
- [ ] A branch sugerida segue `.github/BRANCHING.md`.

## Checklist Depois de Implementar

- [ ] Testes relevantes passaram.
- [ ] Nenhum segredo ou dado sensivel foi versionado.
- [ ] Docs/specs foram atualizados apenas se alguma decisao mudou.
- [ ] PR referencia a issue.
- [ ] Riscos e rollback estao descritos.
- [ ] Corpo do PR segue `.github/pull_request_template.md`.
- [ ] Se o PR for apenas texto, ele foi entregue em um unico bloco Markdown.

## Fallback Manual da Esteira Supervisionada

Use estes prompts quando a automação estiver indisponível. Antes de cada
retomada, valide o último checkpoint conforme
`.agents/references/issue-delivery-loop-fallback.md`.

### Task Review

`prompt_section: task-review`

```text
Use issue-task-review e github:github.

Revise uma única issue:
<url-ou-numero>

Contexto:
- Repositório: Lucassribeiro9/classificador-conta-contabil
- PRD: <caminho-ou-nao-aplicavel>
- Spec: <caminho-ou-nao-aplicavel>
- Issue-pai: <numero-ou-nao-aplicavel>
- Checkpoint anterior: <referencia-ou-null>

Não altere arquivos ou o GitHub. Resolva pelo repositório tudo que for
descoberto, faça somente uma pergunta pendente por vez e aguarde aprovação
explícita do Registro da Task Review.
```

### Entrega de Spec

`prompt_section: spec-delivery`

```text
Use spec-delivery e github:github.

Entregue somente a spec autorizada pela issue:
<url-ou-numero>

Contexto:
- Task Review aprovada: <referencia>
- PRD: <caminho>
- Spec autorizada: <caminho>
- Branch aprovada: <branch>
- Checkpoint anterior: <referencia>

Não implemente código, não gere issues e não altere contratos superiores sem
nova decisão. Execute as validações documentais previstas e devolva o envelope
estruturado.
```

### Implementação Condicional

`prompt_section: implementation`

```text
Use implement-issue, spec-driven-development e github:github.
Use TDD somente para mudança comportamental ou configuração testável.

Implemente uma única issue:
<url-ou-numero>

Contexto:
- Task Review aprovada: <referencia>
- PRD/spec: <caminhos aplicáveis>
- Branch aprovada: <branch>
- Checkpoint anterior: <referencia>

Revalide issue, dependências, branch e worktree. Execute RED → GREEN em fatias
quando aplicável, não faça commit/push/PR e não avance para outra issue.
```

### Preparação do Draft PR

`prompt_section: draft-pr`

```text
Use prepare-draft-pr e github:github. Use github:yeet somente para publicar.

Prepare o draft PR de uma única issue:
<url-ou-numero>

Contexto:
- Task Review: <referencia>
- Branch aprovada: <branch>
- Base: main
- Resultado da entrega: <referencia>
- Template: .github/pull_request_template.md

Use somente evidências reais. Inclua roteiro manual reproduzível, faça commit e
push apenas do escopo aprovado, crie somente draft e nunca faça merge.
```

### Homologação Manual

`prompt_section: manual-homologation`

```text
Homologue o draft PR:
<url-ou-numero>

1. Execute exatamente o roteiro manual do PR.
2. Registre resultado APROVADO, REPROVADO ou BLOQUEADO.
3. Vincule o resultado ao commit testado.
4. Liste divergências observadas sem incluir dados sensíveis.
5. Publique o checkpoint sanitizado no PR.

Não marque como aprovado se algum passo estiver pendente. Alteração relevante
após a homologação exige novo teste manual.
```

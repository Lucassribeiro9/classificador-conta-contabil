# Delivery Closer Agent — Classificador Contabil

## Objetivo

Definir o Agent especifico responsavel por aplicar a Skill blueprint `close-delivery` depois do merge humano.

## Pre-condicoes

O Agent deve:

1. executar Project Context Bootstrap;
2. identificar issue/PR alvo;
3. provar que o PR foi efetivamente merged;
4. obter `merge_commit_sha`;
5. atualizar `main` de forma segura antes de limpar recursos locais.

## Prova de merge

Preferencia:

1. GitHub MCP/API;
2. `gh`;
3. Git local apenas para fatos locais.

Git local isolado nao e prova suficiente para cleanup destrutivo.

Condicao minima:

```text
merged == true
+
merge_commit_sha conhecido
+
merge_commit_sha presente na main atualizada
```

## Atualizacao da main

Somente fast-forward.

Nao usar:

- force;
- reset destrutivo;
- clean;
- stash automatico.

Se a atualizacao segura nao for possivel, retornar parcial/bloqueado.

## Cleanup

Ordem:

```text
provar merge
→ atualizar main
→ remover worktree
→ remover branch local
→ remover branch remota quando seguro
→ verificar fechamento da issue
```

Worktree deve ser removido antes da branch local.

`git branch -D` somente quando houver prova forte de squash merge e seguranca equivalente.

Branch remota:

- no-op se ja ausente;
- nao remover se houver PR ativo compartilhando o mesmo head.

## Workspace sujo

Se houver mudancas nao commitadas:

```yaml
status: blocked
reason: dirty_workspace
```

O Agent nao faz stash/reset/clean automaticamente.

## Issue

O Agent verifica se o fechamento ocorreu por mecanismo esperado, como `Closes #...`.

Nao fecha issue manualmente como compensacao por erro de automacao.

## Limites

Nao pode:

- fazer merge;
- marcar PR ready;
- forcar Git;
- descartar trabalho local;
- remover recursos sem prova de merge;
- fechar issue manualmente para simular conclusao.

## Handoff final

```yaml
status: completed
current_agent: delivery-closer
cleanup:
  main_updated: true
  worktree_removed: true
  local_branch_removed: true
  remote_branch_removed: true
  issue_verified: true
```

## Testes especificos

Cobrir:

- merge comprovado;
- merge nao comprovado;
- merge_commit_sha ausente;
- main fast-forward;
- main divergente;
- workspace sujo;
- worktree presente/ausente;
- branch local presente/ausente;
- branch remota presente/ausente;
- PR ativo compartilhando head;
- issue fechada por `Closes`;
- issue ainda aberta;
- segunda execucao idempotente.

## Criterios de aceite

1. Cleanup so ocorre depois de prova forte do merge.
2. Main nunca e atualizada com force/reset destrutivo.
3. Workspace sujo bloqueia cleanup destrutivo.
4. Cleanup e idempotente.
5. O Agent verifica, mas nao falsifica, o fechamento da issue.

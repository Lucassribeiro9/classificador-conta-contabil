---
name: prepare-draft-pr
description: Validar uma entrega concluída, preparar commit focado, publicar somente a branch aprovada e criar um draft PR com evidências reais e roteiro manual reproduzível. Usar após a implementação de uma única issue quando commit, push e criação do draft já estiverem autorizados; nunca usar para merge, fechamento ou avanço automático.
---

# Preparar e publicar um draft PR

Publique somente uma entrega validada. Leia
`.agents/references/delivery-skill-sources.md`, siga
`.github/pull_request_template.md` e valide a saída contra
`.agents/contracts/delivery-skill-output.schema.json`.

## Política de contexto

### Contexto obrigatório

- Leia issue, Task Review aprovada, branching e template de PR.
- Inspecione branch atual, worktree, diff, commits, arquivos alterados e PRs
  existentes para a mesma branch ou issue.
- Reúna somente evidências reais dos testes e validações executados.

### Contexto condicional

- Leia PRD, spec e documentos de homologação somente quando forem citados pelo
  diff ou necessários ao roteiro manual.
- Use `github:yeet` para commit, push e draft quando disponível; use
  `github:github` para contexto e criação de PR já publicado.

### Contexto proibido

- Não carregue outra issue, arquivos fora do diff ou resultados não executados.
- Não publique segredo, dado contábil, prompt, log bruto, URL privada ou
  telemetria privada.

## Gate de publicação

Bloqueie antes de qualquer publicação quando houver arquivo inesperado,
teste obrigatório falhando, validação pendente, critério não atendido, segredo, branch
incorreta, diff misto ou PR conflitante. Não invente comandos ou resultados.

## Procedimento

1. Confirme que a branch aprovada está ativa, não é `main` e contém somente o
   escopo da issue.
2. Confira título ASCII no formato `tipo(dominio): resumo`, sem seção de título
   sugerido no corpo.
3. Preencha integralmente `.github/pull_request_template.md` com problema,
   solução, escopo, evidências reais, riscos, impacto, mitigação e rollback.
4. Inclua `Closes #` seguido do número da issue e marque checkboxes apenas com evidência.
5. Escreva roteiro manual reproduzível com ambiente, commit, perfil, serviços,
   fixtures, preparação, passos, resultado esperado, erros, evidências e limpeza.
6. Confirme os arquivos que entrarão no commit focado e inclua somente eles.
7. Faça commit e push exclusivamente na branch aprovada.
8. Crie o PR obrigatoriamente como draft PR e confirme URL, número, base, head e
   commit publicados.
9. Se `github:yeet` ou a integração necessária estiver indisponível, retorne
   bloqueio estruturado e indique `docs/prompts-fluxo-sdd-tdd.md` como fallback.

## Limites

- Nunca altere labels ou estados; recomende `draft_ready` somente após o draft.
- Nunca marque o PR como ready.
- Nunca faça merge ou force-push.
- Nunca feche a issue manualmente; deixe `Closes` atuar após o merge.
- Não exclua branch nem descarte alteração local.
- Não avance para outra issue.

Entregue resumo Markdown e um objeto JSON `prepare-draft-pr`. Use
`outcome: draft_created` somente depois de verificar o draft e o commit remoto;
caso contrário, use `blocked`, `pull_request: null` e evidências da causa.

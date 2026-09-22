---
name: issue-delivery-loop
description: Coordenar somente a etapa atual de uma issue supervisionada, validar estado e checkpoint, produzir hand-off estruturado para a skill especializada ou bloquear com segurança.
---

# Coordenar a etapa atual

Coordene uma única issue sem executar o trabalho das skills especializadas.
Leia `.agents/contracts/issue-delivery-loop-routing.json`, valide a saída com
`.agents/contracts/delivery-skill-output.schema.json` e trate
`.github/agent-protocol.json` como fonte canônica dos estados.

## Política de contexto

### Contexto obrigatório

- Issue, comentários estruturados, estado GitHub e issue-pai.
- Classificação, `delivery_track` e Task Review aprovada quando aplicáveis.
- Último checkpoint válido e resultado anterior referenciado.
- Manifesto de roteamento e contrato de saída na versão exigida.

### Contexto condicional

- Ordem das sub-issues da issue-pai para sugerir a próxima candidata.
- `docs/prompts-fluxo-sdd-tdd.md` quando for necessário fallback manual.
- A skill especializada escolhida somente depois de validar a rota.

### Contexto proibido

- Outra issue não selecionada pelo fluxo.
- Prompt completo, raciocínio, diff, log bruto, segredo ou dado contábil.
- Telemetria privada e métricas reais de consumo.

## Coordenação

1. Valide issue, estado oficial, classificação, `delivery_track`, checkpoint,
   versão do contrato e referência do resultado anterior.
2. Encontre uma única rota exata no manifesto. Estado desconhecido, combinação
   incompatível ou múltiplas rotas bloqueiam o fluxo.
3. Produza um hand-off com a skill, sua fonte, a entrada validada, o checkpoint
   e a chave de idempotência.
4. Depois do hand-off, carregue a skill selecionada pela fonte declarada e
   deixe que ela execute somente a própria etapa.
5. Em nova passagem, valide a saída especializada antes de avançar o
   checkpoint.

Na rota de homologação manual, pare no gate humano. Só aceite a transição
quando o gate executável confirmar comentário novo e não editado no draft PR
esperado, de `Lucassribeiro9`, com todos os campos estruturados e o commit
testado. `APROVADO` para o mesmo conteúdo relevante move para
`agent:validated`; `REPROVADO` ou `BLOQUEADO` move para `agent:blocked`; se o
conteúdo relevante mudou, retorne a `agent:awaiting-manual-test`. A
idempotência reutiliza a mesma decisão para o mesmo comentário e digest da
árvore relevante; nunca sintetize resultado humano.

Para a rota de Task Review, carregue a skill selecionada em
`.agents/skills/issue-task-review/SKILL.md`. Não copie suas instruções.

## Limites

- Nunca execute shell, controle branch ou worktree.
- Nunca altere labels, estados, issue ou PR.
- Nunca faça retry sem intervenção humana válida.
- Nunca inicie a próxima issue; no máximo sugira uma candidata elegível.
- Nunca faça merge nem opere produção.
- Se a automação estiver indisponível, indique a seção humana equivalente em
  `docs/prompts-fluxo-sdd-tdd.md`.

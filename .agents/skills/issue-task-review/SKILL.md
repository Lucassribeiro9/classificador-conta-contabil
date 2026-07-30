---
name: issue-task-review
description: Revisar uma única issue antes da implementação, resolver somente decisões realmente pendentes e produzir um Registro da Task Review estruturado. Usar quando uma issue precisa ter escopo, classificação, testes, riscos, dependências e branch validados sem editar arquivos ou executar a entrega.
---

# Revisar uma issue

Conduza a Task Review sem implementar a issue. Leia
`.agents/references/delivery-skill-sources.md` e valide a saída final contra
`.agents/contracts/delivery-skill-output.schema.json`.

## Política de contexto

### Contexto obrigatório

- Leia integralmente a issue, seus comentários, a issue-pai e dependências.
- Leia PRD, spec aplicável, `.github/agent-protocol.json` e
  `.github/BRANCHING.md` apenas nas partes relacionadas ao escopo.
- Confirme estado, elegibilidade, bloqueios e decisões já registradas.

### Contexto condicional

- Inspecione histórico recente, specs relacionadas, templates e documentos de
  homologação somente quando alterarem escopo, riscos ou validações.
- Use GitHub e busca local para responder tudo que for descobrível no projeto.

### Contexto proibido

- Não carregue arquivos sem relação apenas por estarem no repositório.
- Não exponha segredos, dados contábeis, prompts completos, logs brutos ou
  telemetria privada.

## Procedimento

1. Confirme que a issue está aberta, focada e com dependências resolvidas.
2. Classifique-a como `documental`, `comportamental`,
   `configuracao-testavel` ou `mista`.
3. Separe escopo, fora de escopo, decisões aprovadas, critérios de aceite,
   validações, riscos, arquivos prováveis, dependências e branch sugerida.
4. Não reabra decisão explícita sem apresentar contradição concreta.
5. Se faltar uma decisão, use `grill-me` e faça uma pergunta por vez, com
   opções objetivas, recomendação e impacto nas decisões anteriores.
6. Se `grill-me` ou outra skill necessária estiver indisponível, retorne um
   bloqueio estruturado e indique `docs/prompts-fluxo-sdd-tdd.md` como fallback
   humano. Não copie o prompt completo.
7. Depois de todas as respostas, produza o Registro da Task Review e aguarde
   aprovação explícita.

Use os resultados humanos `PRONTA PARA APROVACAO`, `BLOQUEADA`, `REQUER SPEC`
e `REQUER REESCOPAGEM`. Mapeie-os para o enum `outcome` do contrato. Recomende
`blocking_question_raised` somente quando existir uma única pergunta pendente;
caso contrário, use `recommended_event: null`. A recomendação não altera o
estado por conta própria.

## Limites

- Nunca implemente, edite arquivos, crie branch, commit, PR ou issue.
- Nunca altere labels ou estados; apenas recomende um evento válido.
- Não aprove a própria Task Review.
- Não avance para outra issue.
- Interrompa diante de contradição, decisão nova ou ampliação de escopo.

Entregue um resumo Markdown conciso para a pessoa e um único objeto JSON válido
para o futuro coordenador. Não coloque texto livre dentro do JSON.

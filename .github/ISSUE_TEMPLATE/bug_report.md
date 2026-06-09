---
name: "Bug report"
about: Reportar erro na API, importacao, classificacao, seguranca ou infraestrutura
title: "fix(<dominio>): <resumo curto do problema>"
labels: ["bug"]
assignees: []
---

## Contexto
- Dominio afetado: (ex: `api`, `auth`, `importacao`, `ml`, `postgres`, `seguranca`, `docs`)
- Empresa/dataset afetado, se aplicavel:
- Ambiente: (dev/homolog/prod)

## Problema observado
Descreva o comportamento atual e o impacto operacional ou contabil.

## Passos para reproduzir
1.
2.
3.

## Comportamento esperado
Descreva o resultado esperado apos a correcao.

## Evidencias
- Logs relevantes:
- Payload de entrada ou arquivo usado (sem segredos/dados sensiveis):
- Resposta da API, traceback ou mensagem de erro:
- Prints, se aplicavel:

## Criterios de aceite
- [ ] Erro reproduzido e causa confirmada
- [ ] Correcao validada por teste automatizado no maior seam possivel
- [ ] Cenarios relacionados de seguranca/empresa foram verificados
- [ ] Nao houve regressao em API, importadores ou classificacao
- [ ] PR vinculado com `Closes #<numero>`

## Risco e rollback
- Risco principal:
- Impacto esperado se falhar:
- Plano de rollback:

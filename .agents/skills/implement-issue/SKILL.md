---
name: implement-issue
description: Implementar uma única issue com Task Review aprovada, respeitando classificação, branch, escopo e validações, com TDD em fatias verticais quando aplicável. Usar depois da autorização explícita para mudanças documentais, comportamentais ou de configuração testável; bloquear issues mistas que precisem de reescopagem.
---

# Implementar uma issue aprovada

Implemente uma única issue e devolva evidências estruturadas. Leia
`.agents/references/delivery-skill-sources.md` e valide a saída contra
`.agents/contracts/delivery-skill-output.schema.json`.

## Política de contexto

### Contexto obrigatório

- Leia issue, comentários, Task Review aprovada, spec aplicável e branch
  aprovada.
- Confirme issue aberta, dependências resolvidas, base aprovada e worktree sem
  alteração inesperada.
- Identifique arquivos previstos, critérios de aceite e comandos de validação.

### Contexto condicional

- Leia código vizinho, fixtures e docs apenas quando necessários ao maior seam
  público existente.
- Use `tdd` para comportamento e configuração testável,
  `spec-driven-development` para checar contrato e `frontend-design` somente
  quando a issue de frontend exigir decisão visual já aprovada.

### Contexto proibido

- Não carregue outra issue nem contexto amplo sem relação demonstrável.
- Não acesse produção nem exponha segredos, dados contábeis, prompts, logs
  brutos ou telemetria privada.

## Classificação e TDD

- `documental`: não crie TDD artificial; execute validações documentais reais.
- `comportamental`: aplique TDD obrigatório por seam público.
- `configuracao-testavel`: aplique teste de contrato, build, lint ou validador
  proporcional ao risco.
- `mista`: interrompa e solicite reescopagem quando não couber em um PR focado.

## Procedimento

1. Revalide autorização, branch e diff inicial antes de editar.
2. Preserve alterações preexistentes que não pertençam à issue.
3. Para TDD, execute uma fatia vertical por vez: um teste no seam público,
   confirmação do RED pelo motivo esperado, implementação mínima e GREEN.
4. Repita RED → GREEN somente para o próximo comportamento aprovado.
5. Refatore apenas com testes verdes e benefício concreto.
6. Execute testes focados e regressão proporcional ao risco.
7. Inspecione diff, arquivos alterados, segredos, placeholders e critérios.
8. Se uma skill necessária estiver indisponível, retorne bloqueio estruturado e
   indique `docs/prompts-fluxo-sdd-tdd.md` como fallback humano.
9. Interrompa diante de contradição, decisão nova, teste obrigatório falhando
   ou ampliação de escopo.

## Limites

- Não altere PRD ou spec silenciosamente.
- Não adicione dependência, schema, CI ou contrato público sem autorização.
- Nunca altere labels ou estados; apenas recomende um evento válido.
- Não faça commit, push ou draft PR nesta etapa.
- Não avance para outra issue.

Entregue resumo Markdown e um objeto JSON `implement-issue`. Registre comandos
e resultados reais em `evidence`; não invente RED, GREEN ou regressão. Use
`outcome: completed` e `ready_for_draft: true` somente quando todos os critérios
e validações estiverem atendidos.

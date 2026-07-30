---
name: spec-delivery
description: Criar ou atualizar uma única spec já autorizada por issue e Task Review, preservando contratos superiores e produzindo rastreabilidade e validações estruturadas. Usar quando a unidade de trabalho é exclusivamente uma entrega de spec, sem implementar código ou gerar novas issues.
---

# Entregar uma spec autorizada

Execute somente a entrega documental aprovada. Leia
`.agents/references/delivery-skill-sources.md` e valide a saída contra
`.agents/contracts/delivery-skill-output.schema.json`.

## Política de contexto

### Contexto obrigatório

- Leia a issue, a Task Review aprovada, o PRD e a spec autorizada.
- Leia specs diretamente relacionadas apenas para preservar contratos e links.
- Confirme branch, arquivos permitidos e validações documentais aprovadas.

### Contexto condicional

- Consulte histórico, templates e documentos de homologação somente quando
  forem necessários à rastreabilidade ou ao critério de aceite.
- Use `spec-driven-development` para estruturar a entrega quando disponível.

### Contexto proibido

- Não carregue outras specs por conveniência nem edite fontes não autorizadas.
- Não inclua segredos, dados contábeis, prompts, logs brutos ou métricas
  privadas.

## Procedimento

1. Revalide a issue, a Task Review e os limites da spec antes de editar.
2. Edite somente a spec autorizada e referências mínimas explicitamente
   previstas.
3. Preserve o nível de abstração: PRD para visão de produto;
   spec para contrato técnico; issue para unidade de trabalho.
4. Mantenha decisões, boundaries, critérios de aceite e rastreabilidade sem
   duplicar integralmente fontes canônicas.
5. Verifique links, caminhos, placeholders, contradições e arquivos alterados.
6. Execute validadores documentais existentes, incluindo `git diff --check`.
7. Se `spec-driven-development` estiver indisponível, retorne um bloqueio
   estruturado e indique `docs/prompts-fluxo-sdd-tdd.md` como fallback humano.
8. Interrompa se surgir decisão nova, alteração de arquitetura ou ampliação de
   escopo.

## Limites

- Não implemente código, comportamento ou configuração executável.
- Não gere issues, branches adicionais ou specs não autorizadas.
- Nunca altere labels ou estados; apenas recomende um evento válido.
- Não faça commit, push ou PR nesta etapa.
- Não avance para outra issue.

Entregue resumo Markdown conciso e um objeto JSON `spec-delivery`. Use
`outcome: completed` apenas com todas as validações aprovadas; em qualquer
impedimento, use `blocked`, preencha `blocking_reasons` e solicite intervenção
sem alterar o estado diretamente.

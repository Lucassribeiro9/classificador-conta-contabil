<!--
Título do PR: tipo(dominio): resumo

Use ASCII no título: sem acentos, emojis ou símbolos decorativos. Preserve
`(`, `)`, `:` e `-` quando fizerem parte da convenção.

Preencha somente com evidências reais. Mantenha itens não aplicáveis
desmarcados e acrescente `NAO APLICAVEL: <justificativa>`.
-->

## Issue relacionada

`Closes #<numero>`

## Problema e contexto

<!-- Explique por que a mudança é necessária e quem ou qual fluxo é afetado. -->

## Tipo de mudança

- [ ] `feat` (nova capacidade)
- [ ] `fix` (correção de comportamento)
- [ ] `refactor` (melhoria sem mudar comportamento esperado)
- [ ] `chore` (estrutura, scripts, migrações, CI)
- [ ] `docs` (documentação)
- [ ] `spec` (PRD, spec ou decisão de arquitetura)

## Solução entregue

<!-- Descreva o que foi efetivamente entregue e o resultado esperado. -->

## Escopo impactado

- Domínios:
- Arquivos ou módulos principais:
- Dependências externas afetadas:
- Contratos, schemas, PRD ou specs afetados:

## Checklist de validação

<!--
Marque somente itens concluídos com evidência. Para um item não aplicável,
mantenha-o desmarcado e registre a justificativa na própria linha.
-->

- [ ] O diff está limitado ao escopo aprovado da issue
- [ ] Testes automatizados relevantes foram executados
- [ ] Casos de erro críticos foram testados
- [ ] Regras de acesso por usuário e empresa foram verificadas
- [ ] Migrações Alembic foram revisadas
- [ ] Contratos de API e schemas foram atualizados
- [ ] Documentação, PRD ou specs foram atualizados
- [ ] Não há segredos, credenciais ou dados sensíveis versionados
- [ ] O diff foi revisado e está legível

## Evidências automatizadas

- Classificação da mudança:
- TDD:
- Comandos executados:
- Resultados:

<!--
Mudança documental: justifique por que testes de código não se aplicam e
registre validações como `git diff --check`, inspeção do diff, links,
placeholders e Markdown.

Mudança comportamental: registre os ciclos RED -> GREEN, testes focados e
regressões proporcionais ao risco.

Configuração testável: registre validadores, testes de contrato, build, lint ou
comandos equivalentes.
-->

## Roteiro de homologação manual

### Ambiente e commit

- Ambiente:
- Commit:
- Perfil:
- Serviços necessários:
- Fixtures:

### Preparação

1. <ação de preparação>

Resultado esperado:

### Passos

1. <ação de validação>
   - Resultado esperado:

### Casos de erro

1. <cenário de erro>
   - Resultado esperado:

### Evidências

- <referência sanitizada>

### Limpeza

1. <ação de limpeza ou `NAO APLICAVEL: justificativa`>

<!--
O roteiro deve ser proporcional ao escopo, mas reproduzível.

Para documentação, use passos curtos para conferir conteúdo renderizado,
links, placeholders, rastreabilidade e diff.

Para comportamento ou configuração, informe serviços, fixtures, preparação,
fluxo principal, casos de erro, resultados esperados, evidências e limpeza.

Depois da execução, publique no draft PR um comentário com este formato:

## Homologação manual

- Resultado: APROVADO | REPROVADO | BLOQUEADO | NAO APLICAVEL
- Commit testado: <sha>
- Ambiente: <ambiente>
- Perfil: <perfil>
- Roteiro executado: <referência>
- Evidências: <referências sanitizadas>
- Divergências: <nenhuma ou descrição>
- Justificativa de NAO APLICAVEL: <quando aplicável>
-->

## Riscos e rollback

- Risco principal:
- Impacto em caso de falha:
- Mitigação:
- Rollback:

## Observações para review

<!-- Indique os pontos que exigem atenção especial durante o code review. -->

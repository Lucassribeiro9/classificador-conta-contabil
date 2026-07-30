# Agents e Skills do Projeto

Esta pasta guarda as skills usadas para conduzir a evolucao do classificador contabil com PRD, specs, issues e TDD.

## Skills Incluidas

- `brainstorming`: explorar requisitos, riscos e alternativas antes de fechar escopo.
- `grill-me`: tensionar decisoes de produto, seguranca, dados e arquitetura antes de documentar.
- `to-prd`: transformar contexto validado em PRD.
- `spec-driven-development`: criar specs, revisar decisoes e gerar tarefas antes de implementar.
- `tdd`: implementar cada issue com ciclo red-green-refactor.
- `documentation-writer`: criar ou revisar documentacao do projeto, PRs, guias e README com estrutura clara.

## Skills de Entrega Supervisionada

- `issue-task-review`: revisar uma issue e registrar decisões antes da implementação.
- `spec-delivery`: criar ou atualizar somente uma spec autorizada.
- `implement-issue`: executar uma issue aprovada com TDD condicional.
- `prepare-draft-pr`: validar, publicar a branch aprovada e criar somente o draft PR.

As quatro skills usam o contrato
`.agents/contracts/delivery-skill-output.schema.json` e a matriz de contexto
`.agents/references/delivery-skill-sources.md`. Elas executam uma etapa e
não coordenam a esteira, não alteram estados diretamente e não avançam para
outra issue.

## Fluxo Recomendado

1. Usar `brainstorming` quando a ideia ainda estiver aberta.
2. Usar `grill-me` quando uma decisao precisar ser testada com perguntas duras.
3. Usar `to-prd` para consolidar a decisao em PRD.
4. Usar `spec-driven-development` para criar specs derivadas do PRD.
5. Fazer review das specs antes de gerar issues.
6. Gerar issues pequenas a partir de cada spec.
7. Usar `tdd` apenas quando uma issue for escolhida para implementacao.
8. Usar `documentation-writer` para preparar PRs, atualizar README e organizar docs para leitura humana.

## Regra Principal

Nao implementar comportamento novo sem PRD/spec/issue correspondente, salvo ajuste pequeno e isolado.

## Comando de Teste Padrao

```powershell
.\venv\Scripts\python.exe -m pytest -q tests
```

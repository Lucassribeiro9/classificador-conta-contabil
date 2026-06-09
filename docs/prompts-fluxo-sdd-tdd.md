# Prompts e Fluxo de Trabalho SDD/TDD

Este guia define a sequencia recomendada para continuar o projeto usando PRD, specs, issues, TDD e pull requests pequenos.

## Sequencia Recomendada

1. Revisar PRD.
2. Revisar specs derivadas.
3. Gerar issues pequenas a partir de cada spec.
4. Priorizar issues.
5. Escolher uma issue por vez.
6. Fazer review da issue antes de implementar.
7. Escrever teste falhando.
8. Implementar o minimo necessario.
9. Rodar testes.
10. Refatorar se necessario.
11. Atualizar docs/specs apenas se alguma decisao mudar.
12. Abrir PR pequeno vinculado a issue.

Fluxo resumido:

```text
PRD aprovado
-> Specs revisadas
-> Issues pequenas
-> Task Review
-> Teste falhando
-> Implementacao minima
-> Testes verdes
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
5. perguntas bloqueantes.

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
3. Liste um plano curto.
4. Escreva ou ajuste testes primeiro.
5. Rode os testes e confirme que falham pelo motivo esperado.
6. Implemente o minimo necessario.
7. Rode os testes novamente.
8. Refatore apenas se necessario.
9. Atualize docs/spec somente se alguma decisao mudar.
10. No final, informe arquivos alterados, testes executados e riscos restantes.

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
Prepare um resumo de PR para a issue:
<titulo-da-issue>

Contexto:
- Spec: <caminho-da-spec>
- Issue: <numero-ou-titulo>

Inclua:
1. resumo da mudanca;
2. arquivos alterados;
3. testes executados;
4. riscos e rollback;
5. checklist de validacao;
6. referencia `Closes #<numero>` se houver numero de issue.
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

## Checklist Antes de Implementar

- [ ] A issue vem de uma spec revisada.
- [ ] A issue cabe em um PR pequeno.
- [ ] O escopo esta claro.
- [ ] As perguntas bloqueantes foram respondidas.
- [ ] Os testes esperados foram definidos.
- [ ] A implementacao nao mistura outra spec.

## Checklist Depois de Implementar

- [ ] Testes relevantes passaram.
- [ ] Nenhum segredo ou dado sensivel foi versionado.
- [ ] Docs/specs foram atualizados apenas se alguma decisao mudou.
- [ ] PR referencia a issue.
- [ ] Riscos e rollback estao descritos.

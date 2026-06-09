# Padrao de Branches e Merge

Guia rapido para manter a `main` estavel e o fluxo de entrega previsivel.

## Branch principal

- `main` e a unica branch estavel.
- Nao e permitido commit direto na `main`.
- Toda mudanca deve entrar por Pull Request.

## Padrao de nomes de branch

Use sempre prefixo por tipo:

- `feat/<dominio>-<objetivo-curto>`
- `fix/<dominio>-<problema-curto>`
- `chore/<escopo>-<ajuste-curto>`
- `docs/<escopo>-<ajuste-curto>`
- `refactor/<dominio>-<ajuste-curto>`
- `spec/<dominio>-<decisao-curta>`

Dominios recomendados:

- `api`
- `auth`
- `empresas`
- `plano-contas`
- `razao`
- `ml`
- `feedback`
- `postgres`
- `seguranca`
- `docs`

Exemplos:

- `feat/plano-contas-importador`
- `feat/razao-normalizar-partidas`
- `fix/auth-escopo-empresa`
- `chore/postgres-compose`
- `spec/ml-contrapartida-banco-caixa`

## Fluxo recomendado

1. Abrir uma issue usando template.
2. Criar branch a partir da `main`.
3. Implementar mudanca focada e guiada por testes quando aplicavel.
4. Abrir PR usando template e incluir `Closes #<numero>`.
5. Revisar, aprovar e fazer merge.

## Regras de Pull Request

- O titulo deve seguir o padrao `tipo(dominio): resumo`.
- O PR deve referenciar issue com `Closes #<numero>`.
- Deve conter evidencia de validacao: testes, logs curtos, payloads ou exemplos de entrada/saida.
- Deve explicitar risco principal e plano de rollback.
- Mudancas de comportamento devem ter cenario de aceite coberto por teste ou justificativa clara.

## Criterios para merge na `main`

- [ ] Checklist do template de PR preenchido
- [ ] Sem segredos, credenciais ou dados sensiveis no repositorio
- [ ] Testes automatizados relevantes executados
- [ ] Migracoes Alembic revisadas quando houver mudanca de schema
- [ ] Contratos de API, PRD ou specs atualizados quando aplicavel
- [ ] Diff legivel e escopo focado
- [ ] Pelo menos 1 aprovacao de review

## Quando NAO mergear

- PR sem issue vinculada
- Mudanca grande sem recorte claro
- Falta de evidencia de teste
- Risco alto sem rollback definido
- Alteracao de seguranca sem validacao de acesso por empresa
- Mudanca de banco sem plano de migracao ou rollback

## Estrategia de merge

- Preferir `Squash and merge` para manter historico limpo.
- Em caso de conflito, atualizar a branch com `main` e revalidar antes de mergear.

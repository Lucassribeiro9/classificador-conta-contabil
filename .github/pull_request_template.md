## Titulo sugerido

`<tipo>(<dominio>): <resumo curto>`

Exemplos:
- `feat(plano-contas): importar catalogo do escritorio`
- `feat(razao): normalizar debito credito e contrapartida`
- `fix(auth): bloquear acesso cross-company`
- `refactor(ml): separar parser e treino do classificador`

## Issue relacionada

`Closes #<numero>`

## Resumo

Descreva em 3-6 linhas:
- O problema ou oportunidade
- O que foi alterado
- O resultado esperado

## Tipo de mudanca

- [ ] `feat` (nova capacidade)
- [ ] `fix` (correcao de comportamento)
- [ ] `refactor` (melhoria sem mudar comportamento esperado)
- [ ] `chore` (estrutura, scripts, migracoes, CI)
- [ ] `docs` (documentacao)
- [ ] `spec` (PRD, spec ou decisao de arquitetura)

## Escopo impactado

- Dominios: (ex: `api`, `auth`, `plano-contas`, `razao`, `ml`, `postgres`, `seguranca`)
- Arquivos/modulos principais alterados:
- Dependencias externas afetadas: (PostgreSQL, planilhas, Docker, n8n, banco)

## Checklist de validacao

- [ ] Testes automatizados relevantes foram executados
- [ ] Casos de erro criticos foram testados
- [ ] Regras de acesso por usuario/empresa foram verificadas quando aplicavel
- [ ] Migracoes Alembic foram revisadas quando aplicavel
- [ ] Contratos de API e schemas foram atualizados quando aplicavel
- [ ] Documentacao/PRD/specs foram atualizados quando aplicavel
- [ ] Nao ha segredos, credenciais ou dados sensiveis versionados
- [ ] Diff foi revisado e esta legivel (mudanca focada)

## Evidencias

Inclua evidencias objetivas:
- Comando de teste executado e resultado
- Exemplo de entrada/saida ou payload esperado
- Logs curtos ou prints quando ajudarem a validar comportamento

## Riscos e rollback

- Risco principal:
- Impacto esperado se falhar:
- Plano de rollback:

## Observacoes para review

Pontos que voce quer atencao especial no code review.

# Backfill de identidade contábil por empresa

Este procedimento orienta a pré-validação, execução e reversão controlada do
backfill da #516. Use somente banco descartável ou ambiente de homologação
isolado. Esta entrega não autoriza operação em produção.

## Pré-requisitos

- PostgreSQL com a migration da identidade empresarial e a trilha de auditoria
  do backfill aplicadas (`alembic upgrade head`).
- `DATABASE_URL` configurada no ambiente do processo sem publicar seu valor.
- `APP_ENV` explicitamente configurado como `dev`, `test` ou `hml` para ações
  mutáveis. `prod`/`production` e valor ausente são recusados.
- Backup/snapshot do banco descartável ou de homologação antes de testar
  reversão.

## Pré-validação sem escrita

```bash
APP_ENV=hml python -m scripts.backfill_company_accounts preflight
```

A saída é JSON sanitizado, com totais de referências elegíveis, identidades já
presentes, conflitos e referências inelegíveis. `preflight` não cria execução
nem altera linhas de conta. Investigue conflitos antes de aplicar; o backfill
nunca sobrescreve a identidade empresarial existente.

## Aplicação

```bash
APP_ENV=hml python -m scripts.backfill_company_accounts apply
```

Guarde o `run_id` retornado junto ao commit testado e ao roteiro de
homologação. O comando processa cada vínculo em transação própria. Uma falha
fica registrada pelo tipo técnico do erro e pode ser tentada novamente em uma
nova execução; as identidades já criadas serão reconhecidas e não duplicadas.
Saídas não incluem código, nome ou classificação de conta.

## Reversão seletiva

```bash
APP_ENV=hml python -m scripts.backfill_company_accounts rollback --run-id <run_id>
```

O rollback só remove identidade que a execução selecionada registrou como
criada, cujo fingerprint dos atributos ainda corresponde ao estado criado e
que não tenha dependentes por chave estrangeira. Identidade alterada depois,
com dependente, ou sem proveniência suficiente permanece intacta e aparece
como `rollback_blocked`. A trilha da execução é mantida para auditoria e a
repetição do rollback é idempotente.

Não remova as tabelas de auditoria enquanto houver rollback pendente ou
bloqueado. O downgrade da migration recusa esse caso; resolva e documente a
preservação dos dados antes de qualquer remoção.

## Resultado e homologação

Registre no draft PR o commit, perfil e ambiente descartável, comandos
executados, `run_id`, totais sanitizados, evidência da repetição idempotente,
resultado do rollback e divergências. Use `APROVADO`, `REPROVADO` ou
`BLOQUEADO`; não inclua `DATABASE_URL`, nomes/códigos de contas ou logs brutos.

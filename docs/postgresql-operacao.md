# Operacao PostgreSQL

Este documento registra decisoes operacionais iniciais da migracao para
PostgreSQL descrita na spec `docs/specs/01-postgresql-migracao.md` e no PRD
`docs/prd/evolucao-plano-contas-importacao-ml.md`.

## Migracao inicial de dados legados

A migracao obrigatoria inicial preserva apenas as empresas cadastradas no
SQLite atual.

Devem ser migrados, quando disponiveis, os campos atuais de empresa:

- `nome_empresa`
- `cnpj_cpf`
- `api_key`
- `cod_dominio`
- `is_active`
- `created_at`

Transacoes e classificacoes antigas nao entram na migracao inicial. Elas ficam
fora desta fase porque o novo dominio passa a modelar plano de contas, livro
razao, contrapartida contabil e dataset normalizado de ML. Migrar transacoes
antigas diretamente para o novo banco poderia misturar dados historicos do
modelo anterior com dados que ainda nao passaram pelas novas regras de
normalizacao.

Uma migracao futura de transacoes ou classificacoes antigas pode ser criada se
houver necessidade operacional clara. Essa migracao deve ter issue propria,
criterios de aceite, estrategia de validacao e decisao explicita sobre como
mapear os dados legados para o novo dominio.

## Backup inicial do PostgreSQL

Antes de rodar migrations, importacoes ou scripts de migracao em um ambiente
com dados reais, gere um dump do PostgreSQL.

Com o servico `postgres` rodando no Docker Compose, use um comando no formato:

```bash
docker compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --format=custom \
  --file=/tmp/classificador-contabil.backup
```

Em seguida, copie o arquivo para um local seguro fora do container:

```bash
docker compose cp postgres:/tmp/classificador-contabil.backup ./backups/classificador-contabil.backup
```

O diretorio `./backups` e os arquivos de dump nao devem ser commitados no
repositorio. Backups podem conter dados contabeis de clientes, chaves de API e
outros dados sensiveis.

Para restaurar um dump em ambiente controlado, use um comando no formato:

```bash
docker compose exec -T postgres pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists \
  /tmp/classificador-contabil.backup
```

## Backlog operacional

A primeira entrega registra a estrategia manual de backup. Automacao, politica
de retencao, criptografia em repouso, armazenamento externo e rotina de teste
de restore ficam como backlog operacional e devem ser tratados em issue propria
antes de uso recorrente em producao.

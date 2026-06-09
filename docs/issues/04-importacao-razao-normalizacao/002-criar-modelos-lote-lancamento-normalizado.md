# Issue 002: feat(razao): criar modelos de lote e lancamento normalizado

## Contexto

O razao importado precisa preservar lote, usuario, empresa, arquivo, status, contadores e lancamentos normalizados com debito/credito/contrapartida.

## Escopo

- Criar modelo de lote de importacao do razao.
- Criar modelo de lancamento normalizado.
- Incluir campos aprovados: empresa, usuario, `original_filename`, `file_hash`, status, contadores e timestamps.
- Incluir no lancamento: conta origem, contrapartida, conta debito, conta credito, direcao, historico, valor, data, numero e lote.
- Criar migration Alembic.
- Nao implementar parser nesta issue.

## Criterios de Aceite

- Lote de importacao pode ser persistido.
- Lancamento normalizado pode ser persistido.
- Lancamento referencia lote e empresa.
- Campos essenciais do razao estao representados.
- Migration cria tabelas e relacionamentos.

## Testes Esperados

- Teste de persistencia de lote.
- Teste de persistencia de lancamento normalizado.
- Teste de relacionamento lote-lancamentos.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Recomendado.

## Riscos

- Modelar campos antes de fechar warnings/status.
- Criar schema que dificulte deduplicacao posterior.

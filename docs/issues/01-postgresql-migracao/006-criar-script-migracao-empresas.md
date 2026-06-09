# Issue 006: feat(migracao): criar script SQLite -> PostgreSQL para empresas

## Contexto

A migracao para PostgreSQL deve preservar obrigatoriamente as empresas ja cadastradas no SQLite atual. Transacoes e classificacoes antigas ficam fora da migracao inicial.

## Escopo

- Criar script interno para migrar empresas do SQLite atual para PostgreSQL.
- Migrar campos atuais de empresa, incluindo `nome_empresa`, `cnpj_cpf`, `api_key`, `cod_dominio`, `is_active` e `created_at` quando disponivel.
- Validar duplicidade por `cnpj_cpf`, `cod_dominio` e `api_key`.
- Tornar o script idempotente.
- Nao migrar transacoes nesta issue.

## Criterios de Aceite

- Empresas existentes no SQLite sao criadas ou atualizadas no PostgreSQL.
- Reexecutar o script nao duplica empresas.
- Duplicidades conflitantes geram erro claro.
- Transacoes nao sao migradas.
- O script permite informar origem SQLite e destino PostgreSQL de forma explicita.

## Testes Esperados

- Teste com SQLite temporario contendo empresas.
- Teste com destino temporario ou sessao isolada simulando PostgreSQL quando possivel.
- Teste de reexecucao idempotente.
- Teste de conflito por `cnpj_cpf`, `cod_dominio` ou `api_key`.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio. Criar testes do comportamento da migracao antes do script final.

## Riscos

- Sobrescrever dados de empresas sem regra clara.
- Perder `api_key` existente e quebrar integracoes futuras.
- Migrar dados alem do escopo.

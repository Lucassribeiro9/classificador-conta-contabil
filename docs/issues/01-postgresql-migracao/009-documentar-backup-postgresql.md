# Issue 009: docs(postgres): registrar estrategia inicial de backup

## Contexto

A spec deixa backup como pergunta aberta. Mesmo que a automacao completa fique para depois, a primeira entrega precisa registrar uma estrategia inicial para evitar operar PostgreSQL sem plano de recuperacao.

## Escopo

- Documentar uma estrategia inicial de backup para o PostgreSQL.
- Indicar comando ou abordagem recomendada para dump.
- Indicar onde backups nao devem ser armazenados.
- Marcar automacao/retencao como backlog se nao for implementada agora.

## Criterios de Aceite

- Existe documentacao clara de backup inicial.
- Nao ha credenciais reais no documento.
- O documento deixa claro que backups nao devem ser commitados no repositorio.
- Automacao de backup, se nao implementada, vira backlog explicito.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Adiar backup sem registrar decisao operacional.
- Sugerir armazenamento inseguro de dumps.

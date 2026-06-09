# Issue 009: docs(contas): documentar regra para contas ausentes em reimportacao

## Contexto

A spec decidiu que contas ausentes em nova importacao permanecem ativas. Elas nao serao excluidas nem inativadas automaticamente.

## Escopo

- Documentar a regra de contas ausentes.
- Explicar o motivo: relatorios podem vir filtrados ou incompletos.
- Registrar que inativacao automatica fica fora da primeira fase.

## Criterios de Aceite

- Regra esta documentada.
- Texto deixa claro que reimportacao nao exclui nem inativa por ausencia.
- Backlog de inativacao futura fica explicito se necessario.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Operadores assumirem que nova importacao substitui integralmente o catalogo.
- Inativar conta sem revisao humana.

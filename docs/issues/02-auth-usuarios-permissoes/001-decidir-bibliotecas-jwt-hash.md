# Issue 001: spec(auth): decidir bibliotecas JWT e hash de senha

## Contexto

A spec aprovou JWT bearer com access token de 12 horas e senha armazenada apenas com hash seguro. Falta decidir as bibliotecas concretas para JWT e hash.

## Escopo

- Escolher biblioteca JWT para criar e validar tokens.
- Escolher biblioteca/algoritmo para hash de senha.
- Registrar a decisao na spec de auth.
- Nao implementar endpoints nesta issue.

## Criterios de Aceite

- Bibliotecas escolhidas sao compativeis com Python 3.12 e FastAPI.
- A decisao documenta algoritmo de hash e formato geral do token.
- A decisao nao introduz refresh token nesta fase.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Escolher biblioteca sem manutencao ou com API pouco clara.
- Tomar decisao que dificulte testes de token expirado.

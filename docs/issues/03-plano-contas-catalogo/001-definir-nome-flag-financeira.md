# Issue 001: spec(contas): definir nome da flag de origem financeira

## Contexto

A spec decidiu que contas de banco, caixa e aplicacao serao identificadas por heuristica inicial e flag persistida. Falta escolher o nome final da flag.

## Escopo

- Definir nome do campo de flag financeira.
- Registrar a decisao na spec de plano de contas.
- Manter consistencia com a spec de dataset.
- Nao implementar migration nesta issue.

## Criterios de Aceite

- Nome final da flag esta decidido.
- Spec de plano de contas e spec de dataset usam o mesmo nome.
- Nome deixa claro que a conta pode ser origem financeira do dataset.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Escolher nome ambiguo que pareca indicar conta classificavel em geral.
- Divergir do nome usado em specs futuras.

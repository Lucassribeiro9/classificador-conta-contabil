# Issue 007: feat(contas): criar endpoint de consulta do catalogo

## Contexto

Outras partes do sistema precisam consultar contas por codigo, nome, tipo e flag financeira. A consulta deve respeitar autenticacao interna.

## Escopo

- Criar endpoint de listagem de contas.
- Permitir filtros simples por codigo, nome, tipo, ativo e flag financeira.
- Criar endpoint de detalhe por codigo ou id.
- Exigir JWT.
- Nao permitir edicao manual de campos oficiais.

## Criterios de Aceite

- Usuario autenticado lista contas.
- Filtros simples funcionam.
- Detalhe de conta retorna dados oficiais.
- Usuario sem JWT e bloqueado.
- Nenhum endpoint desta issue edita conta.

## Testes Esperados

- Teste de listagem autenticada.
- Teste de filtro por tipo.
- Teste de filtro por flag financeira.
- Teste de detalhe.
- Teste sem JWT bloqueado.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Criar endpoint de edicao fora do escopo.
- Retornar dados demais ou formato inconsistente.

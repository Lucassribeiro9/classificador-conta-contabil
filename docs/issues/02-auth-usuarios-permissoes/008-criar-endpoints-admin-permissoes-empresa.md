# Issue 008: feat(auth): criar endpoints admin de permissoes por empresa

## Contexto

Empresas podem ser vinculadas a usuarios com permissoes `leitura`, `operacao` e `admin_empresa`. Apenas `admin` gerencia usuarios e permissoes na primeira versao.

## Escopo

- Criar endpoint admin para vincular usuario a empresa.
- Criar endpoint admin para alterar permissao do vinculo.
- Criar endpoint admin para remover/desativar vinculo.
- Validar usuario e empresa existentes.
- Bloquear nao admin.

## Criterios de Aceite

- Admin vincula usuario a empresa com permissao valida.
- Admin altera permissao existente.
- Admin remove ou desativa vinculo.
- Permissao invalida e rejeitada.
- Nao admin e bloqueado.

## Testes Esperados

- Teste criar vinculo.
- Teste alterar permissao.
- Teste remover/desativar vinculo.
- Teste permissao invalida.
- Teste nao admin bloqueado.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Criar duplicidade de vinculo usuario-empresa.
- Permitir que contador gerencie permissoes nesta fase.

# Issue 010: feat(api): criar endpoint de importacao do razao

## Contexto

Usuarios com permissao `operacao` ou `admin_empresa` na empresa devem poder importar razao `.xlsx` via API. Usuario sem permissao deve ser bloqueado.

## Escopo

- Criar endpoint de upload/importacao do razao.
- Exigir JWT.
- Exigir permissao `operacao` ou `admin_empresa`.
- Aceitar apenas `.xlsx`.
- Chamar servico de importacao.
- Retornar resumo do lote, contadores e warnings.

## Criterios de Aceite

- Usuario com `operacao` importa razao.
- Usuario com `admin_empresa` importa razao.
- Usuario com `leitura` e bloqueado.
- Usuario sem vinculo e bloqueado.
- Arquivo nao `.xlsx` e rejeitado.
- Resposta informa status e contadores.

## Testes Esperados

- Teste de permissao `operacao`.
- Teste de permissao `admin_empresa`.
- Teste de permissao `leitura` bloqueada.
- Teste sem vinculo bloqueado.
- Teste arquivo invalido.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Permitir importacao sem escopo de empresa.
- Retornar warnings de forma dificil de consumir.

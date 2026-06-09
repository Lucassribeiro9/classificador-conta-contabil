# Issue 006: feat(auth): criar dependencia de acesso por empresa

## Contexto

Usuarios so podem operar empresas vinculadas. Permissoes por empresa suportam `leitura`, `operacao` e `admin_empresa`.

## Escopo

- Criar dependencia para validar acesso do usuario atual a uma empresa.
- Suportar nivel minimo requerido por rota.
- Permitir que `admin` global acesse/gerencie conforme regra aprovada.
- Bloquear usuario sem vinculo suficiente.
- Nao implementar endpoints de importacao nesta issue.

## Criterios de Aceite

- Usuario com permissao suficiente acessa a empresa.
- Usuario sem vinculo recebe bloqueio.
- Usuario com permissao inferior ao exigido recebe bloqueio.
- `admin` global tem comportamento definido e testado.
- Dependencia pode ser reutilizada por rotas futuras.

## Testes Esperados

- Teste para `leitura`.
- Teste para `operacao`.
- Teste para `admin_empresa`.
- Teste de usuario sem vinculo.
- Teste de permissao insuficiente.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Permitir cross-company por erro de dependencia.
- Confundir papel global com permissao por empresa.

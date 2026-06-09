# Issue 011: feat(audit): auditar gestao de usuarios e permissoes

## Contexto

Criacao, desativacao e mudanca de permissao afetam quem pode acessar dados de clientes.

## Escopo

- Registrar `user.created`.
- Registrar `user.deactivated`.
- Registrar `user_company_permission.changed`.
- Incluir usuario executor quando houver.
- Incluir usuario alvo e empresa quando aplicavel.
- Nao registrar senha inicial ou tokens.

## Criterios de Aceite

- Criacao de usuario gera evento.
- Desativacao de usuario gera evento.
- Alteracao de permissao por empresa gera evento.
- Metadata nao contem senha ou token.

## Testes Esperados

- Teste de criacao de usuario.
- Teste de desativacao.
- Teste de alteracao de permissao.
- Teste de sanitizacao de metadata.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Nao conseguir rastrear quem concedeu acesso a empresa.
- Registrar credenciais temporarias em metadata.

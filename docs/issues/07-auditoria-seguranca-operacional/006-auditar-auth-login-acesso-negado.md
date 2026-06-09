# Issue 006: feat(audit): auditar autenticacao e acesso negado

## Contexto

Eventos de login, login falho, usuario inativo e acesso negado sao essenciais para responsabilidade individual mesmo em rede interna.

## Escopo

- Registrar `auth.login.success`.
- Registrar `auth.login.failed`.
- Registrar `auth.user.inactive_blocked`.
- Registrar `auth.access.denied`.
- Incluir usuario quando conhecido.
- Incluir empresa quando o acesso negado envolver empresa.
- Nao registrar senha, token ou API key.

## Criterios de Aceite

- Login bem-sucedido gera evento.
- Login falho gera evento sem segredo.
- Usuario inativo bloqueado gera evento.
- Acesso negado por permissao gera evento.

## Testes Esperados

- Teste de login com sucesso.
- Teste de login falho.
- Teste de usuario inativo.
- Teste de acesso negado por empresa.
- Teste garantindo ausencia de senha/token na metadata.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Registrar credenciais em auditoria.
- Falhar login por problema de auditoria se a politica for best-effort.

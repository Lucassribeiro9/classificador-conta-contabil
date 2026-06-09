# Issue 005: feat(auth): criar dependencia get_current_user

## Contexto

Endpoints internos novos exigem JWT. A API precisa de uma dependencia central para validar token, carregar usuario e bloquear usuario inativo a cada request.

## Escopo

- Criar dependencia `get_current_user`.
- Validar assinatura e expiracao do JWT.
- Carregar usuario do banco.
- Bloquear usuario inexistente ou inativo.
- Retornar usuario atual para rotas internas.

## Criterios de Aceite

- Token valido retorna usuario atual.
- Token expirado e rejeitado.
- Token invalido e rejeitado.
- Usuario inativo e rejeitado mesmo com token previamente emitido.
- Rotas internas podem depender de `get_current_user`.

## Testes Esperados

- Teste de token valido.
- Teste de token expirado.
- Teste de token malformado.
- Teste de usuario inativo com token.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Aceitar token expirado.
- Nao consultar status atual do usuario.
- Misturar validacao JWT com permissao por empresa antes da hora.

# Issue 004: feat(auth): criar endpoint de login JWT

## Contexto

Usuarios internos precisam autenticar na API com JWT bearer. A primeira versao usa apenas access token, sem refresh token, com expiracao de 12 horas.

## Escopo

- Criar endpoint de login com login/email e senha.
- Validar senha contra hash.
- Bloquear usuario inativo.
- Retornar access token JWT com expiracao de 12 horas.
- Nao implementar refresh token.

## Criterios de Aceite

- Login valido retorna access token.
- Login com senha invalida falha.
- Login de usuario inexistente falha.
- Usuario inativo nao recebe token.
- Token contem identificador do usuario e expiracao.

## Testes Esperados

- Teste de login valido.
- Teste de senha invalida.
- Teste de usuario inexistente.
- Teste de usuario inativo.
- Teste de expiracao configurada em 12 horas.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio. Escrever testes de login antes da implementacao.

## Riscos

- Vazar diferenca entre usuario inexistente e senha invalida.
- Gerar token sem expiracao.
- Permitir login de usuario inativo.

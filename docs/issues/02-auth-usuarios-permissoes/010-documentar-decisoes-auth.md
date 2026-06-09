# Issue 010: docs(auth): documentar decisoes de autenticacao e permissoes

## Contexto

A spec aprovou JWT bearer, access token de 12 horas, papeis globais e permissoes por empresa. Essas decisoes precisam estar visiveis para implementacao e review.

## Escopo

- Documentar o fluxo de autenticacao humana.
- Documentar papeis globais.
- Documentar permissoes por empresa.
- Documentar diferenca entre JWT de usuario e API key de integracao.
- Documentar que refresh token e reset de senha ficam fora da primeira fase.

## Criterios de Aceite

- Documento ou secao de docs existe.
- Decisoes batem com a spec `02`.
- Nao ha segredos ou exemplos de tokens reais.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Documentacao divergir da spec.
- Dar exemplo inseguro de token/senha.

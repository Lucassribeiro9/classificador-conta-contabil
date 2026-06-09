# Issue 002: feat(auth): criar modelos de usuario e permissao por empresa

## Contexto

O sistema precisa de usuarios internos individuais, papeis globais e vinculos de permissao por empresa. A primeira versao usa papeis `admin`, `contador`, `operador` e permissoes `leitura`, `operacao`, `admin_empresa`.

## Escopo

- Criar modelo de usuario interno.
- Criar modelo de vinculo usuario-empresa.
- Incluir campos para papel global e status ativo.
- Garantir unicidade de login/email.
- Criar migration Alembic correspondente.
- Nao implementar login nesta issue.

## Criterios de Aceite

- Usuarios internos podem ser persistidos.
- Usuario tem nome, login/email, senha hash, papel, ativo e timestamps.
- Vinculo usuario-empresa registra permissao.
- Papeis e permissoes aceitam os valores aprovados na spec.
- Migration cria as tabelas necessarias.

## Testes Esperados

- Teste de persistencia dos modelos.
- Teste de unicidade de login/email.
- Teste de vinculo usuario-empresa.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Recomendado, mas pode usar testes de modelo/migration como primeira camada.

## Riscos

- Misturar auth humana com API key de empresa.
- Criar permissoes granulares demais antes da necessidade.

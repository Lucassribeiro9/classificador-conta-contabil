# Issue 002: feat(contas): criar modelo ContaContabil

## Contexto

O sistema precisa de um catalogo unico do escritorio com contas sinteticas e analiticas. O codigo da conta sera identificador unico.

## Escopo

- Criar modelo de conta contabil.
- Campos esperados: codigo, classificacao, nome, tipo, grau, ativo, flag financeira, timestamps.
- Garantir unicidade de `codigo`.
- Criar migration Alembic correspondente.
- Nao implementar parser nesta issue.

## Criterios de Aceite

- Conta contabil pode ser persistida.
- `codigo` e unico.
- `tipo` diferencia sintetica e analitica.
- Flag financeira existe no modelo.
- Contas podem ser marcadas ativas.
- Migration cria tabela e constraints necessarias.

## Testes Esperados

- Teste de persistencia do modelo.
- Teste de unicidade de codigo.
- Teste dos valores de `tipo`.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Recomendado.

## Riscos

- Tratar `classificacao` como chave unica quando a spec definiu `codigo`.
- Bloquear contas sinteticas que devem existir para hierarquia.

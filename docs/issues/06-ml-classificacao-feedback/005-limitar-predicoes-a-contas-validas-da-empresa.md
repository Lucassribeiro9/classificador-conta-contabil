# Issue 005: feat(ml): limitar predicoes a contas validas da empresa

## Contexto

Predicoes devem respeitar a empresa e considerar apenas contas analiticas validas vinculadas a ela.

## Escopo

- Filtrar classes candidatas por contas analiticas existentes.
- Respeitar vinculo de uso da conta pela empresa.
- Evitar predicoes para contas sinteticas.
- Evitar predicoes para contas nao vinculadas a empresa.
- Nao implementar revisao manual de vinculos nesta issue.

## Criterios de Aceite

- Predicao retornada pertence a conta analitica valida.
- Predicao retornada esta vinculada a empresa.
- Conta sintetica nunca e retornada.
- Conta de outra empresa nunca e retornada.

## Testes Esperados

- Teste com conta analitica vinculada.
- Teste bloqueando conta sintetica.
- Teste bloqueando conta nao vinculada.
- Teste com duas empresas e classes parecidas.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Sugerir conta que o cliente nao usa.
- Vazar padroes de outra empresa pelo modelo.

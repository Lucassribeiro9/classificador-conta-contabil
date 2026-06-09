# Issue 008: test(contas): bloquear contas sinteticas como classificaveis

## Contexto

Contas sinteticas devem existir para hierarquia, mas nao podem ser alvo de classificacao, contrapartida prevista ou dataset.

## Escopo

- Criar comportamento ou helper que indique se uma conta e classificavel.
- Garantir que apenas contas analiticas (`tipo = A`) sejam classificaveis.
- Cobrir uso futuro por dataset/ML.
- Nao implementar dataset nesta issue.

## Criterios de Aceite

- Conta analitica e considerada classificavel.
- Conta sintetica nao e considerada classificavel.
- Comportamento e testado de forma reutilizavel.

## Testes Esperados

- Teste de conta analitica.
- Teste de conta sintetica.
- Teste de conta inativa, se campo ativo ja existir.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Deixar regra duplicada em varios pontos do sistema.
- Permitir conta sintetica como target de ML futuramente.

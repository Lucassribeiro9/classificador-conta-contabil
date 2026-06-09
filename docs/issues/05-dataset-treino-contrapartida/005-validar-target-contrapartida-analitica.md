# Issue 005: feat(dataset): validar contrapartida como target analitico

## Contexto

O alvo do modelo inicial e a conta de contrapartida. Para ser valido, o target precisa existir no catalogo e ser conta analitica.

## Escopo

- Usar `conta_contrapartida` como target do dataset.
- Validar que a contrapartida existe no catalogo.
- Validar que a contrapartida e analitica, preferencialmente `tipo = A`.
- Descartar linhas sem contrapartida, com contrapartida inexistente ou sintetica.
- Registrar descartes nos metadados.

## Criterios de Aceite

- Target do dataset e sempre a contrapartida.
- Contas sinteticas nao aparecem como target.
- Contrapartida inexistente nao gera exemplo de treino.
- Total de descartes reflete linhas invalidadas por target.

## Testes Esperados

- Teste de contrapartida analitica valida.
- Teste de contrapartida sintetica descartada.
- Teste de contrapartida inexistente descartada.
- Teste de linha sem contrapartida descartada.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Ensinar o modelo a prever contas nao lancaveis.
- Tratar conta de origem como alvo por engano.

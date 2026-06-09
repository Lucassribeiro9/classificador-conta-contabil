# Issue 002: feat(ml): adaptar engine para dataset de contrapartida

## Contexto

O classificador deve prever `conta_contrapartida` usando dados ja normalizados pelo builder da spec 05, sem conhecer parser de Excel.

## Escopo

- Fazer `core/ml_engine.py` consumir linhas do builder de dataset.
- Usar `features` como entrada do modelo.
- Usar `target_conta_contrapartida` como alvo.
- Manter pipeline de texto com scikit-learn.
- Nao trocar algoritmo principal.
- Nao chamar parser de Excel dentro do classificador.

## Criterios de Aceite

- O classificador treina com target de contrapartida.
- O classificador nao usa conta de origem como alvo.
- O classificador recebe dados normalizados, nao planilhas.
- Testes existentes sao ajustados para a semantica de contrapartida quando necessario.

## Testes Esperados

- Teste de treino com dataset suficiente.
- Teste garantindo que target usado e `target_conta_contrapartida`.
- Teste garantindo que parser de Excel nao participa do ML.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Manter comportamento antigo por compatibilidade e treinar conta errada.
- Acoplar ML ao formato do arquivo importado.

# Issue 012: test(ml): consolidar testes de comportamento de ML e feedback

## Contexto

O comportamento esperado deve ser testado sem depender de detalhes frageis do algoritmo. A cobertura precisa focar em contrato, confianca, revisao, escopo e feedback.

## Escopo

- Consolidar testes de ML para contrapartida.
- Cobrir dataset insuficiente e HTTP `422`.
- Cobrir resposta de predicao.
- Cobrir baixa confianca marcando revisao.
- Cobrir feedback corrigindo dado usado em treino futuro.
- Evitar assertar classes exatas quando depender de comportamento instavel do algoritmo.

## Criterios de Aceite

- Testes cobrem os criterios da spec 06.
- Testes sao estaveis e focados em comportamento.
- Fixtures diferenciam claramente empresa, conta valida, conta sintetica e conta nao vinculada.
- Suite completa passa localmente.

## Testes Esperados

- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.
- Cobertura comportamental para ML, API e feedback.

## TDD

Obrigatorio.

## Riscos

- Testes ficarem acoplados a probabilidades exatas do modelo.
- Faltar cobertura de autorizacao por empresa.

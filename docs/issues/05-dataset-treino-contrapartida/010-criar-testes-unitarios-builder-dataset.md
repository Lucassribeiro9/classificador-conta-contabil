# Issue 010: test(dataset): consolidar testes unitarios do builder

## Contexto

O builder concentra regras de alto risco para qualidade do ML: isolamento por empresa, origem financeira, target e features.

## Escopo

- Criar ou consolidar arquivo de testes para builder de dataset.
- Cobrir filtros, target, features, metadados e insuficiencia.
- Usar fixtures pequenas e legiveis.
- Evitar testes dependentes de detalhes privados do algoritmo de ML.

## Criterios de Aceite

- Todos os criterios da spec 05 possuem pelo menos um teste.
- Testes deixam claro por que linhas entram ou saem do dataset.
- Testes rodam sem depender de arquivo Excel real.
- Testes sao pequenos o suficiente para orientar implementacao TDD.

## Testes Esperados

- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.
- Cobertura comportamental para empresa, origem financeira, target, features, metadados e treinabilidade.

## TDD

Obrigatorio.

## Riscos

- Testar demais a implementacao interna e pouco o comportamento.
- Criar fixtures grandes que dificultam manutencao.

# Issue 002: feat(dataset): criar contrato do builder de dataset

## Contexto

O dataset deve ser produzido por um componente separado do treino de ML. Esse contrato sera a fronteira entre dados normalizados e classificador.

## Escopo

- Criar funcao ou classe de builder de dataset em `core/`.
- Receber `empresa_id` e dependencias de consulta necessarias.
- Retornar linhas de dataset e metadados em estrutura explicita.
- Padronizar nomes de saida, como `features` e `target_conta_contrapartida`.
- Nao treinar modelo nesta issue.
- Nao chamar parser de Excel nesta issue.

## Criterios de Aceite

- Builder pode ser chamado por empresa.
- Retorno separa dados de treino e metadados.
- Contrato nao depende diretamente de arquivo Excel.
- Contrato nao mistura responsabilidades de ML.

## Testes Esperados

- Teste de chamada do builder com empresa conhecida.
- Teste de formato basico do retorno.
- Teste de retorno vazio quando nao ha linhas elegiveis.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Criar contrato acoplado ao modelo atual de scikit-learn.
- Retornar apenas dataframe sem metadados de diagnostico.

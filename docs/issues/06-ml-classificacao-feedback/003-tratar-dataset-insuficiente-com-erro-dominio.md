# Issue 003: feat(ml): retornar erro de dominio 422 para dataset insuficiente

## Contexto

Quando o dataset nao atende ao minimo recomendado para treino, a API deve responder `422`, nao erro generico `500`.

## Escopo

- Criar erro de dominio para dataset insuficiente, se ainda nao existir.
- Mapear esse erro para HTTP `422` nos endpoints relevantes.
- Incluir mensagem clara e metadados uteis quando seguro.
- Considerar criterios da spec 05: minimo recomendado de 10 linhas e 2 classes.
- Nao mascarar erros inesperados como `422`.

## Criterios de Aceite

- Dataset insuficiente retorna HTTP `422`.
- Resposta explica que nao ha dados suficientes para treino.
- Erros inesperados continuam tratados como falha tecnica adequada.
- O retorno nao expoe dados sensiveis.

## Testes Esperados

- Teste de dataset vazio retornando `422`.
- Teste de dataset com menos de 10 linhas retornando `422`.
- Teste de dataset com apenas 1 classe retornando `422`.
- Teste de erro inesperado nao sendo confundido com insuficiencia.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Retornar `500` para uma condicao operacional esperada.
- Transformar qualquer erro de ML em `422` e esconder bugs reais.

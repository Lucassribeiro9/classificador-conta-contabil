# Issue 008: feat(api): adaptar /classification para lancamentos pendentes

## Contexto

`/classification` deve classificar lancamentos normalizados pendentes de contrapartida prevista ou revisao, respeitando empresa e usuario.

## Escopo

- Adaptar fluxo de classificacao em lote para lancamentos normalizados.
- Selecionar apenas lancamentos da empresa autorizada.
- Classificar pendentes conforme criterio definido.
- Persistir resultado quando aplicavel, ou devolver resposta clara.
- Retornar `422` se dataset for insuficiente para treino.

## Criterios de Aceite

- Endpoint opera apenas em lancamentos da empresa permitida.
- Lancamentos pendentes recebem predicao de contrapartida.
- Respostas incluem contadores de processados e revisao quando aplicavel.
- Dataset insuficiente retorna `422`.

## Testes Esperados

- Teste de classificacao de pendentes.
- Teste de isolamento por empresa.
- Teste de dataset insuficiente.
- Teste de nenhum pendente encontrado.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Reclassificar lancamentos ja corrigidos manualmente.
- Processar dados de empresa sem permissao.

# Issue 013: docs(ml): documentar fluxo de predicao e feedback

## Contexto

O fluxo novo muda a semantica do classificador: ele passa a prever contrapartida para origem financeira e registrar revisao.

## Escopo

- Documentar fluxo de `/predict`.
- Documentar fluxo de `/classification`.
- Documentar comportamento de dataset insuficiente com `422`.
- Documentar limiar de confianca `0.70`.
- Documentar feedback e efeito no proximo treino.
- Referenciar PRD e spec 06.

## Criterios de Aceite

- Documento diferencia predicao automatica de decisao contabil final.
- Documento explica `needs_review`.
- Documento explica que feedback corrige registro existente.
- Documento deixa claro que o classificador nao consome Excel diretamente.

## Testes Esperados

- Revisao manual do documento.

## TDD

Nao obrigatorio.

## Riscos

- Consumidores internos continuarem usando semantica antiga.
- Documentacao sugerir que previsao e definitiva.

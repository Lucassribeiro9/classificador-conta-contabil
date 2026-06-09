# Issue 001: chore(ml): confirmar contratos de endpoints e campos persistidos

## Contexto

A spec permite adaptar endpoints existentes ou criar schemas novos para evitar confusao com o fluxo antigo. Tambem ha campos persistidos de predicao que precisam de nomes finais.

## Escopo

- Confirmar se `/predict` e `/classification` serao adaptados diretamente com schemas novos.
- Confirmar nomes de campos persistidos para contrapartida prevista, confianca e revisao.
- Confirmar dependencia com a spec de auditoria para evento de feedback.
- Confirmar que dataset insuficiente sera retornado como `422`.
- Nao implementar comportamento nesta issue.

## Criterios de Aceite

- Contratos de API ficam claros antes das issues funcionais.
- Campos persistidos possuem nomes definidos.
- Dependencia com auditoria fica explicita.
- A spec e atualizada se alguma decisao mudar.

## Testes Esperados

- Nao se aplica, issue de alinhamento.

## TDD

Nao obrigatorio.

## Riscos

- Misturar semantica antiga de conta contabil generica com nova contrapartida.
- Persistir campos com nomes ambiguos e precisar migrar logo depois.

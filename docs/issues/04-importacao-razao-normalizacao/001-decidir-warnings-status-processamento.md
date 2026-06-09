# Issue 001: spec(razao): decidir armazenamento de warnings e status parcial

## Contexto

A spec aprovou importacao parcial com warnings, mas ainda falta decidir se warnings ficam em tabela propria ou metadata JSON do lote, e qual nome usar para status parcial.

## Escopo

- Decidir onde armazenar warnings de linhas invalidas.
- Decidir nome do status de lote parcial.
- Registrar a decisao na spec de razao.
- Nao implementar modelos nesta issue.

## Criterios de Aceite

- Local de armazenamento dos warnings esta definido.
- Nome do status parcial esta definido.
- Decisao fica registrada na spec.
- Decisao nao exige armazenar arquivo original completo.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Escolher metadata JSON simples demais para futura consulta.
- Criar tabela de warnings cedo demais se o volume for baixo.

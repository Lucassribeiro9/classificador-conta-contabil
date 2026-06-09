# Issue 011: docs(razao): documentar layout aceito e regra debito/credito

## Contexto

A regra contabil central da spec e interpretar debito/credito em relacao a conta do bloco, nunca como regra global.

## Escopo

- Documentar layout `.xlsx` aceito.
- Documentar que `.xls` esta fora desta fase.
- Documentar bloco `Conta:` como conta de origem.
- Documentar regra de debito e credito.
- Documentar importacao parcial e warnings.

## Criterios de Aceite

- Documento explica a regra com exemplos.
- Documento deixa claro que plano de contas deve ser importado antes.
- Documento informa que linhas invalidas geram warnings.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Usuario interpretar debito/credito como regra global.
- Tentar importar layout fora do escopo sem clareza.

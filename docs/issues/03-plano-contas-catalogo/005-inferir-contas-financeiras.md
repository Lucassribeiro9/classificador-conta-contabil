# Issue 005: feat(contas): inferir candidatas a origem financeira

## Contexto

O dataset inicial usara apenas origens banco, caixa ou aplicacao. A spec decidiu usar heuristica inicial e flag persistida no catalogo.

## Escopo

- Criar heuristica inicial para marcar candidatas financeiras.
- Considerar `nome` e `classificacao`; `grau` pode ser usado se ajudar.
- Marcar flag financeira persistida.
- Cobrir exemplos como caixa, bancos, banco especifico e aplicacoes.
- Nao criar interface de revisao manual nesta issue.

## Criterios de Aceite

- Contas de caixa sao candidatas financeiras.
- Contas de bancos conta corrente sao candidatas financeiras.
- Bancos especificos sao candidatos financeiros.
- Aplicacoes financeiras sao candidatas financeiras.
- Contas nao financeiras comuns nao sao marcadas.

## Testes Esperados

- Teste para `CAIXA`.
- Teste para `BANCOS CONTA CORRENTE`.
- Teste para `BCO. SANTANDER`.
- Teste para `APLICACOES`.
- Teste para conta nao financeira, como IRRF ou duplicatas.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Marcar conta nao financeira como origem financeira.
- Deixar de marcar conta financeira por nome com variacao.

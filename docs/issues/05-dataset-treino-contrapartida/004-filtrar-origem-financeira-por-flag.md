# Issue 004: feat(dataset): filtrar origem financeira pela flag persistida

## Contexto

O dataset inicial deve usar apenas lancamentos cujo bloco de origem seja banco, caixa ou aplicacao financeira. A decisao deve vir da flag persistida no catalogo, nao de nova heuristica no builder.

## Escopo

- Incluir apenas lancamentos cuja `conta_origem` aponte para conta com flag financeira ativa.
- Usar a flag persistida do catalogo, como `is_financial_origin`.
- Descartar origens nao financeiras.
- Nao recalcular heuristica de banco/caixa/aplicacao no builder.

## Criterios de Aceite

- Lancamento com origem financeira entra no dataset.
- Lancamento com origem nao financeira fica fora.
- Mudanca na flag do catalogo altera a elegibilidade do lancamento.
- Builder nao contem lista solta de palavras-chave para identificar origem financeira.

## Testes Esperados

- Teste com origem financeira marcada.
- Teste com origem nao financeira.
- Teste garantindo que a heuristica textual nao e usada no builder.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Duplicar regra da spec de plano de contas.
- Treinar com blocos ambiguos do razao completo.

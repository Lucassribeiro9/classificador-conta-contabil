# Modelo de movimentos operacionais

A Spec 08 e o contrato canonico dos modelos de movimentos operacionais:
`docs/specs/08-movimentos-operacionais-classificacao.md`.

A Release 1 define dois modelos oficiais futuros para a aba obrigatoria
`Movimentos`:

- `tests/fixtures/modelo_movimentos_operacionais_valor_saldo.xlsx`:
  layout A, com `valor` assinado e `saldo`;
- `tests/fixtures/modelo_movimentos_operacionais_debito_credito_saldo.xlsx`:
  layout B, com `debito`, `credito` e `saldo` na convencao do extrato.

O modelo legado `tests/fixtures/modelo_movimentos_operacionais_classificacao.xlsx`
continua aceito como compatibilidade do layout A sem `saldo`. A ausencia de
`saldo` deve gerar aviso informativo de que a conferencia por saldo nao esta
disponivel para aquele lote ou conta.

## Metadados

A planilha contem a aba obrigatoria `Movimentos` e pode conter abas auxiliares
`Instrucoes` e `Exemplos`.

Metadados obrigatorios por rotulo:

- `CNPJ/CPF`
- `Periodo inicio`
- `Periodo fim`

Metadados informativos por rotulo:

- `Empresa`
- `Codigo dominio`

## Layout A: valor assinado e saldo

Colunas obrigatorias:

- `data`
- `conta_financeira`
- `historico`
- `valor`

Coluna recomendada:

- `saldo`

Colunas opcionais:

- `contrapartida`
- `tipo_movimento`
- `documento`
- `observacao`

No layout A, `valor > 0` representa entrada na conta financeira e `valor < 0`
representa saida.

## Layout B: debito, credito e saldo do extrato

Colunas obrigatorias:

- `data`
- `conta_financeira`
- `historico`
- `debito`
- `credito`

Coluna recomendada:

- `saldo`

Colunas opcionais:

- `contrapartida`
- `tipo_movimento`
- `documento`
- `observacao`

No layout B, `credito` do extrato representa entrada na conta financeira e
`debito` do extrato representa saida. Exatamente uma entre `debito` e `credito`
deve estar preenchida por linha.

## Colunas preenchidas pelo sistema

Colunas preenchidas pelo sistema e ignoradas como decisao de entrada:

- `status_sugerido`
- `confidence_sugerida`
- `mensagem_validacao`

## Regras de saldo

Saldo e informacao de conferencia. Ele deve ser preservado como saldo observado,
comparado ao saldo calculado por conta financeira e mantido fora das features de
ML.

Varias contas financeiras podem existir no mesmo lote. Cada `conta_financeira`
possui sequencia de saldo independente, calculada pela ordem das linhas no
arquivo.

Esta documentacao e os modelos devem permanecer sem identificacao real de
empresa ou cliente.

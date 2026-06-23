# Modelo de movimentos operacionais

Use `tests/fixtures/modelo_movimentos_operacionais_classificacao.xlsx` como
contrato base para o parser de movimentos operacionais.

A planilha contem a aba obrigatoria `Movimentos` e abas auxiliares
`Instrucoes` e `Exemplos`. O contrato inicial da aba `Movimentos` e:

- metadados obrigatorios por rotulo: `CNPJ/CPF`, `Periodo inicio` e
  `Periodo fim`;
- metadados informativos por rotulo: `Empresa` e `Codigo dominio`;
- colunas obrigatorias: `data`, `conta_financeira`, `historico` e `valor`;
- colunas opcionais: `contrapartida`, `tipo_movimento`, `documento` e
  `observacao`;
- colunas preenchidas pelo sistema e ignoradas como decisao de entrada:
  `status_sugerido`, `confidence_sugerida` e `mensagem_validacao`.

Esta fixture deve permanecer sanitizada e sem identificacao real de empresa.
O parser/importador operacional deve ser implementado em issues posteriores,
sem alterar o contrato versionado aqui sem atualizar a spec correspondente.

# Overview: validacao operacional com lotes ficticios

## Contexto

Esta validacao cobre a issue #210 e a spec
`docs/specs/04-importacao-razao-normalizacao.md`.

O objetivo foi verificar o fluxo operacional de importacao do razao com dois
lotes ficticios e versionaveis:

- `tests/fixtures/razao_lote_valido.xlsx`
- `tests/fixtures/razao_lote_com_warnings.xlsx`

Os dados sao ficticios e foram inspirados nos arquivos historicos
`classificacao_contas_resultado.xlsx` e `lanc_cont_ml.xlsx`, sem reutilizar
dados reais de cliente.

## Pre-condicoes usadas

- Empresa ativa criada no banco de teste.
- Usuario interno ativo com permissao `operacao` na empresa.
- Plano de contas de teste contendo as contas usadas pelas linhas validas.
- Arquivos `.xlsx` no layout tabular do modelo, com metadados de empresa, CNPJ
  e periodo.

## Resultado do parser

O parser passou a reconhecer o layout tabular do modelo com coluna
`conta_origem`, sem exigir bloco `Conta:` quando a conta de origem estiver na
propria linha.

Tambem passou a aceitar metadados em linhas separadas:

- `Periodo inicio`
- `Periodo fim`

O layout por blocos `Conta:` continua coberto pelos testes existentes.

## Resultado do importador

O lote valido importa com:

- status `completed`;
- `total_linhas = 3`;
- `total_importadas = 3`;
- `total_invalidas = 0`;
- `warnings = []`.

O lote com erros controlados importa parcialmente com:

- status `completed_with_warnings`;
- `total_linhas = 3`;
- `total_importadas = 1`;
- `total_invalidas = 2`;
- warning para linha sem contrapartida;
- warning para contrapartida inexistente no catalogo.

Durante a validacao foi corrigido o vinculo automatico de contas usadas pela
empresa para lidar com varias linhas da mesma conta de origem no mesmo lote.

## Resultado do endpoint

As fixtures foram importadas via endpoint de upload usando `TestClient`:

- `razao_lote_valido.xlsx` retornou `completed`;
- `razao_lote_com_warnings.xlsx` retornou `completed_with_warnings`;
- os contadores e warnings retornados pela API ficaram alinhados ao importador.

O teste manual contra a empresa teste local pode reutilizar copias desses
arquivos, ajustando apenas os dados operacionais necessarios do ambiente local.

## Lacunas encontradas

- O parser aceitava o layout por blocos `Conta:`, mas nao reconhecia linhas do
  modelo tabular quando a conta vinha na coluna `conta_origem`.
- O parser nao aceitava `Periodo inicio` e `Periodo fim` em linhas separadas.
- O vinculo empresa-conta podia tentar inserir a mesma conta mais de uma vez
  dentro do mesmo flush quando varias linhas usavam a mesma conta de origem.

Essas lacunas foram tratadas dentro da issue #210 porque eram necessarias para
cumprir o contrato ja aprovado da spec 04.

## Issues derivadas recomendadas

Nenhuma issue derivada e obrigatoria a partir desta validacao automatizada.

Se o teste manual com uma planilha real sanitizada do escritorio revelar novo
layout ou campos adicionais, abrir uma issue especifica para esse layout,
mantendo dados reais fora do repositorio.

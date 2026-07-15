# Massa Sanitizada De Homologacao

Os arquivos deste diretorio contem somente dados ficticios, criados para a
primeira homologacao interna. Eles nao foram derivados de clientes, documentos
ou movimentacoes reais.

Identidade ficticia compartilhada:

- empresa: `EMPRESA MODELO HOMOLOGACAO LTDA`;
- CNPJ sanitizado e deliberadamente invalido: `22.333.444/0001-55`;
- codigo Dominio: `7701`.

## Arquivos

- `plano_contas_hml.xlsx`: catalogo com contas sinteticas, analiticas,
  financeiras e contrapartidas ficticias.
- `razao_hml.xlsx`: doze lancamentos em caixa, banco e aplicacao, com debitos e
  creditos referenciando somente contas do catalogo.
- `movimentos_operacionais_hml.xlsx`: cinco movimentos que cobrem
  pre-classificacao, classificacao pendente e revisao por warning recuperavel.

Use os arquivos na ordem plano, razao e movimentos. O razao vincula a empresa
as contas necessarias para que os movimentos sem inconsistencias sejam aceitos.
O movimento `HML-004` omite deliberadamente a contrapartida de uma transferencia
e deve seguir para revisao sem invalidar o lote.

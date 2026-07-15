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

## Executar O Seed

O banco de homologacao deve estar criado e com as migracoes aplicadas. Defina os
segredos apenas no ambiente do terminal, execute o seed dentro do container da
API e remova as variaveis ao terminar:

```bash
export HML_ADMIN_PASSWORD='<senha-temporaria>'
export HML_OPERATOR_PASSWORD='<senha-temporaria>'
export HML_COMPANY_API_KEY='<chave-temporaria>'

docker compose --env-file .env.hml -f docker-compose.hml.yml exec \
  -e HML_ADMIN_PASSWORD \
  -e HML_OPERATOR_PASSWORD \
  -e HML_COMPANY_API_KEY \
  api-contabil python -m scripts.seed_homologacao

unset HML_ADMIN_PASSWORD HML_OPERATOR_PASSWORD HML_COMPANY_API_KEY
```

O comando exige `APP_ENV=hml`, usa `DATABASE_URL` do container e pode ser
reexecutado sem duplicar a massa. A reexecucao nao redefine senhas nem API key
de identidades ja existentes.

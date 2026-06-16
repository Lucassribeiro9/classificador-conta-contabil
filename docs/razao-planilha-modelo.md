# Planilha modelo de importacao do Razao

Use `modelo-razao-importacao.xlsx` quando quiser importar o Razao em um
formato higienizado e previsivel.

## Campos do cabecalho

- `Empresa`: nome da empresa no arquivo.
- `CNPJ`: documento da empresa. A importacao normaliza para digitos.
- `Periodo inicio`: data inicial do Razao.
- `Periodo fim`: data final do Razao.

## Campos dos lancamentos

Campos obrigatorios:

- `data`
- `conta_origem`
- `historico`
- `contrapartida`

Campos opcionais:

- `numero`: preencha somente se o relatorio trouxer numero de lancamento.
- `conta_origem_classificacao`
- `conta_origem_nome`
- `debito`
- `credito`
- `saldo_exercicio_original`

Cada linha deve ter `debito` ou `credito` preenchido. Nunca preencha os dois
na mesma linha.

`saldo_exercicio_original` serve apenas para conferencia visual. Ele nao define
debito, credito, valor do lancamento nem direcao contabil.

## Regras importantes

- Nao use o `id` interno do sistema como `numero`.
- Nao informe `cod_dominio`; este modelo nao cria empresa automaticamente.
- Se o CNPJ pertencer a uma empresa inativa, a importacao deve ser bloqueada.

# Planilha modelo de importacao do Razao

Use `modelo-razao-importacao.xlsx` quando quiser importar o Razao em um
formato higienizado e previsivel.

O arquivo aceito nesta fase e `.xlsx`. Arquivos `.xls` ficam fora do escopo.

Antes de importar o Razao, importe o plano de contas do escritorio. A importacao
valida a conta de origem e a contrapartida contra o catalogo; contas ausentes
geram warning e nao viram lancamento valido.

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

- `numero`: numero externo do lancamento. Pode ficar vazio quando o relatorio
  nao trouxer esse dado.
- `conta_origem_classificacao`
- `conta_origem_nome`
- `debito`
- `credito`
- `saldo_anterior`
- `saldo`
- `saldo_exercicio`
- `saldo_exercicio_original`: alias legado de `saldo_exercicio`.

Cada linha deve ter `debito` ou `credito` preenchido. Nunca preencha os dois
na mesma linha.

Campos de saldo servem para conferencia visual, fechamento mensal e diagnostico
de divergencia. Eles nao definem debito, credito, valor do lancamento, direcao
contabil, chave de deduplicacao nem feature de ML.

Cada saldo deve preservar a forma original do arquivo e, quando possivel, uma
representacao normalizada com `valor_decimal` e `natureza` `D` ou `C`.

## Regras importantes

- Nao use o `id` interno do sistema como `numero`. O `id` interno identifica o
  registro persistido; o `numero` representa somente o numero externo do
  lancamento quando existir no relatorio.
- Nao informe `cod_dominio`; este modelo nao cria empresa automaticamente.
- Se o CNPJ pertencer a uma empresa inativa, a importacao deve ser bloqueada.

## Layout com blocos `Conta:`

Relatorios do Razao tambem podem vir em blocos iniciados por `Conta:`. Nesse
layout, o bloco define a conta de origem de todas as linhas uteis seguintes,
ate que outro bloco `Conta:` seja encontrado.

Exemplo simplificado:

```text
Conta: 10046 BCO. SANTANDER
data        numero  historico              contrapartida  debito   credito
2026-01-10  42      PAGAMENTO FORNECEDOR   20010          150,00
2026-01-11  43      RECEBIMENTO CLIENTE    30020                    900,00
```

Nesse exemplo, `10046` e a conta de origem das duas linhas. A coluna
`contrapartida` informa o outro lado do lancamento.

## Saldos

O Razao anual pode trazer:

- `saldo_anterior`: saldo que abre a sequencia do bloco de conta;
- `saldo`: saldo observado na sequencia exibida no bloco ou relatorio;
- `saldo_exercicio`: saldo acumulado do exercicio informado pelo Dominio.

`saldo` e `saldo_exercicio` sao preservados separadamente. A importacao nao
tenta recalcular a diferenca conceitual entre eles nesta fase.

`saldo_exercicio` sera a referencia principal para conciliacao futura. `saldo`
permanece como diagnostico secundario.

Arquivos antigos sem colunas de saldo continuam importaveis, mas a conciliacao
por saldo fica indisponivel e deve gerar aviso informativo.

## Regra de debito e credito

Debito e credito sempre sao interpretados em relacao a conta do bloco ou ao
campo `conta_origem`. Nao existe regra global como "debito sempre e banco" ou
"credito sempre e receita".

Quando a linha tem valor em `debito`:

- `conta_debito` = conta de origem
- `conta_credito` = contrapartida
- `direcao` = `debito`
- `valor` = valor do debito

Exemplo:

```text
conta_origem: 10046
contrapartida: 20010
debito: 150,00
credito:
```

Resultado normalizado:

```text
conta_debito: 10046
conta_credito: 20010
direcao: debito
valor: 150,00
```

Quando a linha tem valor em `credito`:

- `conta_debito` = contrapartida
- `conta_credito` = conta de origem
- `direcao` = `credito`
- `valor` = valor do credito

Exemplo:

```text
conta_origem: 10046
contrapartida: 30020
debito:
credito: 900,00
```

Resultado normalizado:

```text
conta_debito: 30020
conta_credito: 10046
direcao: credito
valor: 900,00
```

## Importacao parcial e warnings

A importacao pode ser parcial. Linhas validas sao persistidas; linhas invalidas
geram warnings e nao viram lancamentos validos.

Geram warning, entre outros casos:

- linha sem contrapartida;
- conta de origem inexistente no catalogo;
- conta de contrapartida inexistente no catalogo;
- divergencia recuperavel na sequencia de saldo;
- valor ou natureza de saldo em formato invalido, quando as demais informacoes
  do lancamento permitirem continuar;
- arquivo antigo sem colunas de saldo, quando a conciliacao por saldo nao puder
  ser feita.

Se houver linhas validas e warnings, o lote fica com status
`completed_with_warnings`. Se nenhuma linha for valida, o lote fica `failed`.

## Diagnostico de layout e formatacao

Se a planilha tiver metadados obrigatorios, mas nao tiver cabecalho reconhecivel
de lancamentos, a importacao deve falhar com mensagem clara de layout nao
reconhecido. Verifique se existem colunas equivalentes a `data`, `historico`,
`contrapartida`, `debito` e `credito`.

Linhas reconhecidas com formatacao invalida nao devem gerar erro interno
generico. Quando houver outras linhas validas no mesmo arquivo, a importacao
deve ser parcial e registrar warnings. Exemplos:

- codigos inteiros exportados como `10046.0` sao tratados como `10046`;
- data invalida gera warning de data do lancamento invalida;
- valor invalido em `debito` ou `credito` gera warning de valor do lancamento
  invalido;
- linha sem exatamente um lado preenchido entre `debito` e `credito` gera
  warning de debito/credito invalido.

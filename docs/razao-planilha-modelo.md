# Planilha modelo de importacao do Razao

Use [`modelo-razao-importacao.xlsx`](../modelo-razao-importacao.xlsx) quando quiser
importar o Razao em um formato higienizado e previsivel. Os valores do modelo
sao ficticios.

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

O cabecalho antigo `saldo_exercicio_original` continua aceito como alias de
`saldo_exercicio`; use apenas um dos dois nomes para a mesma coluna.

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

`saldo_anterior` abre a sequencia acumulada do exercicio de cada bloco de
conta. `saldo` e o observado da competencia mensal: seu calculo comeca em zero
a cada mes. `saldo_exercicio` e o observado acumulado do exercicio: seu calculo
comeca em `saldo_anterior` e nao reinicia a cada mes. As duas sequencias sao
preservadas e conferidas separadamente por empresa, lote e bloco de conta.

O valor original de cada saldo permanece disponivel. A normalizacao conserva
uma magnitude decimal positiva e a natureza `D` (devedora) ou `C` (credora)
quando informada. Em texto, o sufixo `D` ou `C` define a natureza. Uma celula
numerica so permite inferi-la quando seu formato contabil for suportado.
Zero e valido sem natureza. A natureza do saldo nao muda a regra de debito e
credito do lancamento.

`saldo_exercicio` sera a referencia principal para conciliacao futura. `saldo`
permanece como diagnostico secundario.

Arquivos antigos sem colunas de saldo continuam importaveis. O lote recebe um
aviso informativo por bloco sem saldo e a conferencia por saldo fica limitada.
O alias legado tambem continua importavel.

## Fechamentos mensais

O fechamento e derivado do Razao anual por empresa, conta, ano e mes. Ele
preserva o ultimo saldo observado do mes e o saldo calculado para comparacao.
Quando existe `saldo_exercicio`, ele e a fonte observada preferida do
fechamento; `saldo` continua separado para diagnostico da sequencia mensal.
O fechamento e dado de conferencia: nao pareia movimentos operacionais nem
executa conciliacao. Uma lacuna ou divergencia recuperavel nao impede a
continuidade do calculo quando os lancamentos validos fornecem dados
suficientes.

Consulte `GET /api/v1/companies/{company_id}/razao/lotes/{lote_id}/fechamentos`
depois que o lote terminar. A lista aceita `conta_codigo`, `ano`, `mes`,
`page` e `limit` (maximo 100). `items` e paginado; `warnings_saldo` no topo
resume ate 100 avisos do lote, com o total em `warnings_saldo_total` e o
indicador `warnings_saldo_truncados`. O acesso e restrito a empresa autorizada.

Exemplo ficticio de fechamento sem divergencia:

```json
{
  "lote_id": 42,
  "empresa_id": 7,
  "status": "completed",
  "warnings_saldo": [],
  "warnings_saldo_total": 0,
  "warnings_saldo_truncados": false,
  "items": [{
    "id": 101,
    "lote_id": 42,
    "empresa_id": 7,
    "conta_codigo": 10046,
    "ano": 2026,
    "mes": 1,
    "saldo_observado_original": "1.250,75D",
    "saldo_observado_decimal": "1250.75",
    "saldo_observado_natureza": "D",
    "saldo_observado_fonte": "saldo_exercicio",
    "saldo_calculado_decimal": "1250.75",
    "divergente": false,
    "warnings_saldo": [],
    "created_at": "2026-02-01T12:00:00",
    "updated_at": "2026-02-01T12:00:00"
  }],
  "total": 1,
  "page": 1,
  "limit": 20,
  "has_next": false
}
```

O exemplo representa um fechamento, nao um lancamento. Os campos e formatos
seguem o schema `RazaoFechamentoListResponse` da API.

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

Warnings de saldo usam os codigos `saldo_ausente`, `saldo_invalido` e
`saldo_divergente`. Eles nao aumentam `total_invalidas` quando o lancamento
continua valido. Se houver linhas validas e warnings, o lote fica com status
`completed_with_warnings`. Se nenhuma linha for valida, o lote fica `failed`.

Uma divergencia recuperavel de saldo nao desfaz lancamentos validos. A falta
de identificacao segura da empresa, da conta do bloco ou da estrutura minima
do Razao e bloqueante. O CNPJ divergente da empresa alvo ou uma empresa
inativa tambem bloqueiam a importacao antes de persistir lote ou lancamentos.

Consulte os avisos paginados em
`GET /api/v1/companies/{company_id}/razao/lotes/{lote_id}/warnings`.
Esse endpoint aceita `codigo`, `linha`, `page` e `limit` (maximo 100); o campo
`source` informa se o lote usa avisos normalizados ou legados. Exemplo
ficticio de aviso normalizado:

```json
{
  "source": "normalized",
  "items": [{
    "linha": 12,
    "codigo": "saldo_divergente",
    "mensagem": "Saldo observado diverge do saldo calculado para a conta do razao.",
    "detalhes": {"bloco_id": "bloco:1", "conta_codigo": 10046}
  }],
  "total": 1,
  "page": 1,
  "limit": 20,
  "has_next": false
}
```

Para o contrato completo, consulte o [PRD](prd/evolucao-plano-contas-importacao-ml.md),
a [Spec 04](specs/04-importacao-razao-normalizacao.md), a
[issue do Ciclo 1](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/361)
e a [issue da spec de saldos](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/364).

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

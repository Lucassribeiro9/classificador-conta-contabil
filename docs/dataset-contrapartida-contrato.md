# Contrato do Dataset de Contrapartida

Este documento descreve o contrato retornado por
`build_dataset_treino_contrapartida`, definido em `core/dataset_builder.py`.
Ele complementa a [spec 05](specs/05-dataset-treino-contrapartida.md) e deve
ser usado como referencia para integracoes com ML e futuros endpoints de
diagnostico.

O dataset documentado aqui e uma fonte de exemplos para treino. Ele nao executa
treino, nao retorna predicao e nao decide a resposta HTTP dos fluxos de ML.

## Entrada do Builder

O builder recebe uma sessao SQLAlchemy e um escopo obrigatorio de empresa:

```python
build_dataset_treino_contrapartida(session, empresa_id=empresa_id)
```

`empresa_id` e obrigatorio. Chamadas sem escopo de empresa devem falhar antes de
consultar dados, para evitar dataset global ou mistura de clientes.

## Quando Uma Linha Entra

Uma linha normalizada do Razao entra no dataset quando todos os criterios abaixo
sao verdadeiros:

- pertence a empresa informada em `empresa_id`;
- a `conta_origem` existe no catalogo `ContaContabil`;
- a `conta_origem` esta marcada com `is_financial_origin=True`;
- a `conta_contrapartida` existe no catalogo;
- a `conta_contrapartida` esta ativa;
- a `conta_contrapartida` e analitica (`tipo = "A"`).

O builder usa a flag persistida `is_financial_origin` do catalogo. Ele nao
recalcula heuristica textual de banco, caixa ou aplicacao a partir do nome ou
classificacao da conta.

## Quando Uma Linha E Descartada

Uma linha normalizada da empresa e descartada quando nao vira exemplo valido do
dataset. Isso inclui, entre outros casos:

- origem nao financeira;
- origem ausente no catalogo;
- contrapartida ausente no catalogo;
- contrapartida sintetica;
- contrapartida inativa.

Os descartes sao contabilizados em `metadata.total_descartes`. O total considera
as linhas normalizadas da empresa que nao entraram no dataset, incluindo filtros
de origem e validacoes de target.

## Estrutura Das Linhas

Cada linha valida do dataset tem a forma:

```python
{
    "features": "recebimento cliente origem_10046 direcao_credito",
    "target_conta_contrapartida": 50057,
}
```

`features` e um texto deterministico composto, nesta ordem, por:

1. `historico_normalizado`;
2. token `origem_<conta_origem>`;
3. token `direcao_<direcao>`.

Historico vazio ou minimo e permitido; nesse caso, os tokens estruturais
continuam compondo a feature. Espacos excedentes nas bordas do historico sao
removidos.

O valor monetario bruto nao entra nas features da primeira versao. Features com
valor normalizado pertencem a backlog separado.

## Metadados Retornados

O builder sempre retorna `metadata` junto com `linhas`:

```python
{
    "empresa_id": 1,
    "total_linhas": 10,
    "total_descartes": 2,
    "contagem_por_target": {50057: 5, 70001: 5},
    "treinavel": True,
}
```

Campos:

- `empresa_id`: empresa usada como escopo da consulta.
- `total_linhas`: quantidade de exemplos validos retornados em `linhas`.
- `total_descartes`: quantidade de linhas normalizadas da empresa que nao
  entraram no dataset.
- `contagem_por_target`: agregacao por `target_conta_contrapartida`.
- `treinavel`: indicador de suficiencia recomendado para treino.

O criterio atual de `treinavel` e:

- pelo menos 10 linhas validas;
- pelo menos 2 classes de contrapartida.

Datasets menores podem ser gerados e usados para diagnostico, mas devem ser
tratados como insuficientes para treino automatico.

## Dataset Gerado Versus Modelo Treinado

Gerar o dataset nao significa treinar um modelo.

Responsabilidades do builder:

- consultar lancamentos normalizados por empresa;
- aplicar filtros de elegibilidade;
- montar features iniciais;
- definir target de contrapartida;
- retornar metadados de diagnostico.

Responsabilidades da camada de ML:

- decidir se tentara treinar;
- treinar o pipeline;
- produzir predicoes;
- lidar com erro de dominio ou resposta HTTP quando o dataset for insuficiente.

Assim, o builder pode retornar `linhas=[]` ou `treinavel=False` sem levantar erro
de treino. A traducao disso para comportamento de API pertence a spec de ML.

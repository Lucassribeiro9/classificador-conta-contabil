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
- possui snapshot aplicavel a data do lancamento, sem conflito de vigencia;
- origem, contrapartida, debito, credito e target final sao contas analiticas
  no snapshot da empresa; alias do Razao exige confirmacao humana nesse mesmo
  snapshot;
- nao possui pendencia critica sem resolucao valida vinculada a linha;
- a `conta_origem` existe na identidade contabil da empresa ou no fallback
  legado ainda autorizado;
- a `conta_origem` esta marcada com `is_financial_origin=True`;
- a `conta_contrapartida` existe no contexto da empresa;
- a `conta_contrapartida` esta ativa;
- a `conta_contrapartida` e analitica (`tipo = "A"`).

O builder usa a flag persistida `is_financial_origin` da identidade da empresa,
com fallback ao catalogo legado apenas durante a transicao. Ele nao
recalcula heuristica textual de banco, caixa ou aplicacao a partir do nome ou
classificacao da conta.

Um movimento operacional importado entra como fonte complementar quando todos os
criterios abaixo sao verdadeiros:

- pertence a empresa informada em `empresa_id`;
- possui snapshot aplicavel a data do movimento, sem conflito de vigencia;
- as contas finais sao analiticas nesse snapshot e nao existe pendencia critica
  sem resolucao valida vinculada ao movimento;
- `status` e `aprovado` ou `corrigido`;
- `elegivel_treino=True`;
- `contrapartida_final`, `conta_debito` e `conta_credito` estao preenchidas;
- `conta_financeira` existe, esta ativa, e analitica;
- `conta_financeira` esta marcada com `is_financial_origin=True`;
- `contrapartida_final`, `conta_debito` e `conta_credito` existem, estao ativas
  e sao analiticas.

## Quando Uma Linha E Descartada

Uma linha normalizada da empresa e descartada quando nao vira exemplo valido do
dataset. Isso inclui, entre outros casos:

- origem nao financeira;
- origem ausente no catalogo;
- contrapartida ausente no catalogo;
- contrapartida sintetica;
- contrapartida inativa.
- movimento operacional pendente, sugerido, em revisao, pre-classificado ou
  rejeitado;
- movimento operacional sem contrapartida final ou sem par debito/credito final;
- movimento operacional sem conta financeira valida.

Os descartes sao contabilizados em `metadata.total_descartes`. O total considera
as linhas normalizadas e movimentos operacionais da empresa que nao entraram no
dataset, incluindo filtros de origem, status e validacoes de target.

Cada descarte tambem aparece no manifesto com tipo de fonte, identificador e
motivo estavel. Motivos incluem `snapshot_missing`, `snapshot_conflict`,
`account_not_in_snapshot`, `critical_review_unresolved`, `rejected`,
`no_final_decision` e invalidade da conta ou da origem financeira. Uma
resolucao humana valida muda a elegibilidade apenas nas composicoes seguintes.

## Manifesto Da Composicao

Cada chamada persistida do builder cria uma linha imutavel em
`dataset_manifests` e retorna `manifesto` ao lado de `linhas` e `metadata`.
O manifesto contem `id`, `hash`, `empresa_id`, `pipeline_version`,
`schema_version`, IDs dos snapshots, fontes incluidas, exclusoes, regras,
hashes das fontes candidatas e uma copia exata das linhas elegiveis. O hash
SHA-256 usa JSON canonico com chaves ordenadas. Composicoes com o mesmo
conteudo possuem o mesmo hash, mas IDs de execucao diferentes.

`reconstruct_dataset_from_manifest(session, empresa_id=..., manifest_id=...)`
verifica o hash e devolve as linhas gravadas naquele manifesto, mesmo que as
fontes atuais tenham mudado. O acesso exige a mesma empresa. No PostgreSQL,
um trigger impede `UPDATE` e `DELETE` da linha do manifesto. O chamador deve
confirmar a transacao para preservar o registro; um rollback cancela toda a
composicao. Exemplos publicados no PR devem usar apenas massa sanitizada.

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
2. token `origem_<conta_origem>` para Razao ou
   `origem_<conta_financeira>` para movimento operacional;
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
    "total_linhas_razao": 8,
    "total_linhas_movimentos": 2,
    "total_descartes": 2,
    "total_descartes_razao": 1,
    "total_descartes_movimentos": 1,
    "contagem_por_target": {50057: 5, 70001: 5},
    "treinavel": True,
}
```

Campos:

- `empresa_id`: empresa usada como escopo da consulta.
- `total_linhas`: quantidade de exemplos validos retornados em `linhas`.
- `total_linhas_razao`: quantidade de exemplos validos vindos do Razao.
- `total_linhas_movimentos`: quantidade de exemplos validos vindos de movimentos
  operacionais.
- `total_descartes`: quantidade de linhas normalizadas e movimentos da empresa
  que nao entraram no dataset.
- `total_descartes_razao`: quantidade de linhas do Razao descartadas.
- `total_descartes_movimentos`: quantidade de movimentos operacionais
  descartados.
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
- consultar movimentos operacionais aprovados/corrigidos por empresa;
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

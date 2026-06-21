# Decisao: Razao, Transacoes e Dataset de ML

## Contexto

O fluxo novo importa o livro-razao por empresa e persiste linhas validas em
`LancamentoRazaoNormalizado`. O projeto tambem possui o modelo legado
`Transacao`, usado pelo classificador inicial antes da evolucao com plano de
contas, razao e contrapartida contabil.

A decisao desta issue define qual fonte deve alimentar o novo dataset de treino
e como o legado deve ser tratado sem misturar dominios.

## Decisao

`LancamentoRazaoNormalizado` e a fonte canonica do novo fluxo contabil.

Ele representa o dado ja validado pelo plano de contas, associado a empresa,
lote de importacao, conta de origem, contrapartida, par debito/credito,
historico normalizado, valor, data e numero externo do lancamento.

O dataset de treino de contrapartida deve consumir diretamente
`LancamentoRazaoNormalizado`, filtrando origens financeiras conforme a spec
`docs/specs/05-dataset-treino-contrapartida.md`.

`Transacao` permanece como legado/compatibilidade do classificador antigo e nao
deve ser usada como destino automatico da importacao do razao nesta fase.

Nao havera sincronizacao automatica de razao para transacoes no fluxo atual. Se
uma compatibilidade temporaria for necessaria, ela deve ser implementada como
adaptador explicito, em issue propria, sem duplicar dados como fonte de verdade.

## Papel de Cada Modelo

`LancamentoRazaoNormalizado`:

- fonte canonica para importacao do razao;
- fonte principal para dataset de treino de contrapartida;
- entidade associada a feedback humano de classificacao;
- base para auditoria e diagnostico de importacoes;
- unidade preferencial para futuras classificacoes de contrapartida.

`Transacao`:

- modelo legado do fluxo anterior de classificacao;
- pode continuar existindo para compatibilidade enquanto endpoints antigos
  forem mantidos;
- nao deve receber copia automatica de lancamentos do razao;
- nao deve ser fonte do novo dataset de contrapartida;
- nao deve ser migrada para o novo dominio sem decisao e issue especificas.

## Impactos

### Importacao do Razao

A importacao continua persistindo apenas lotes e lancamentos normalizados do
razao. Ela nao cria `Transacao`.

### Dataset de Treino

O builder de dataset deve continuar consultando `LancamentoRazaoNormalizado` por
`empresa_id`. A contrapartida contabil e o target inicial. Feedback humano
aplicado ao lancamento pode sobrescrever o target em treinos futuros, conforme o
contrato atual do dataset.

### Classificacao ML

O fluxo novo de ML deve treinar a partir do dataset de contrapartida. Metodos
que ainda treinam ou classificam `Transacao` devem ser tratados como legado ate
serem isolados, adaptados ou removidos em issue propria.

### Feedback

Feedback novo deve se vincular a `LancamentoRazaoNormalizado`, porque a
correcao humana altera a contrapartida usada pelo dataset futuro. Feedback sobre
`Transacao` antiga nao deve ser misturado automaticamente com feedback do razao.

### Auditoria

Eventos de importacao, classificacao e feedback devem referenciar o recurso do
fluxo novo quando a acao envolver razao normalizado. Eventos ligados a
`Transacao` legada devem permanecer distinguiveis ate a descontinuacao do fluxo
antigo.

## Issues Derivadas

As seguintes implementacoes devem ser tratadas separadamente:

- #214: alimentar dataset a partir dos lancamentos do razao.
- #218: adaptar ou isolar metodos legados do ML que ainda usam `Transacao`.
- #219: definir contrato dos endpoints antigos de classificacao durante a
  transicao para lancamentos normalizados.
- #220: criar consulta operacional para lancamentos normalizados do razao, se a
  API precisar expor diagnostico de lote/lancamentos.
- #221: documentar politica de descontinuacao de `Transacao` quando o fluxo
  novo estiver completo.

## Fora de Escopo

- Criar migracoes.
- Copiar dados do razao para `Transacao`.
- Migrar transacoes antigas.
- Alterar endpoints de classificacao.
- Implementar novo builder de dataset.

## Criterios de Revisao

- A decisao nao muda comportamento em runtime.
- O novo fluxo tem uma fonte canonica unica para ML.
- O legado fica nomeado como legado/compatibilidade.
- Implementacoes futuras ficam quebradas em issues pequenas.

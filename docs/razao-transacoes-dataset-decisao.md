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
`docs/specs/05-dataset-treino-contrapartida.md`. Movimentos operacionais podem
entrar como fonte complementar quando estiverem totalmente classificados,
aprovados ou corrigidos por decisao humana e marcados como elegiveis para
treino.

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
`empresa_id` como fonte principal. A contrapartida contabil e o target inicial.
Feedback humano aplicado ao lancamento pode sobrescrever o target em treinos
futuros, conforme o contrato atual do dataset. O builder tambem pode consultar
`MovimentoOperacionalImportado` da mesma empresa como fonte complementar, desde
que o movimento tenha decisao final humana, contas finais preenchidas e
elegibilidade explicita para treino.

### Classificacao ML

O fluxo novo de ML deve treinar a partir do dataset de contrapartida. Metodos
que ainda treinam ou classificam `Transacao` devem ser tratados como legado ate
serem isolados, adaptados ou removidos em issue propria.

Contratos atuais durante a transicao:

- `POST /companies/{company_id}/classification`: legado/compatibilidade baseado
  em `Transacao`.
- `POST /companies/{company_id}/predict`: legado/compatibilidade enquanto puder
  persistir ou responder no contrato de `Transacao`.
- `POST /companies/{company_id}/ml/classification`: contrato novo de
  classificacao de contrapartida, sem depender de `Transacao`.

### Feedback

Feedback novo deve se vincular a `LancamentoRazaoNormalizado`, porque a
correcao humana altera a contrapartida usada pelo dataset futuro. Feedback sobre
`Transacao` antiga nao deve ser misturado automaticamente com feedback do razao.

Contratos atuais durante a transicao:

- `POST /companies/{company_id}/ml/feedback`: contrato novo de feedback sobre
  `LancamentoRazaoNormalizado`.
- `PATCH /transactions/{transaction_id}/feedback`: legado/compatibilidade
  baseado em `Transacao`.

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
- #260: permitir movimentos operacionais aprovados/corrigidos como fonte
  complementar do dataset.

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

## Politica de ciclo de vida de `Transacao`

`Transacao` permanece em suporte de compatibilidade, sem prazo de sunset e sem
versionamento definido nesta decisao. Enquanto existir consumidor autorizado de
um contrato legado, seus dados e endpoints devem preservar o comportamento
vigente e permanecer identificados como legado.

O fluxo novo nao deve introduzir novos consumidores, novos datasets ou novas
sincronizacoes que dependam de `Transacao`. Novas capacidades de classificacao,
feedback e consulta devem usar `LancamentoRazaoNormalizado` e os contratos de
contrapartida descritos na Spec 06.

O ciclo de vida tem tres estados documentais:

| Estado | Significado | Regra |
| --- | --- | --- |
| Compatibilidade ativa | Consumidores legados ainda podem usar `Transacao` e seus endpoints. | Nenhuma remocao, migracao automatica ou mudanca de contrato. |
| Elegivel para descontinuacao | Todos os gates abaixo possuem evidencia atual e aprovada. | Abrir issue funcional especifica; a elegibilidade nao remove nada. |
| Descontinuada | Uma issue funcional aprovada executou a mudanca e a homologacao. | Preservar evidencias, plano de rollback e decisao sobre retencao. |

## Gates objetivos para descontinuacao

`Transacao` e seus endpoints legados somente podem ser considerados elegiveis
quando todos os itens forem comprovados em uma revisao futura:

1. O fluxo de contrapartida baseado em `LancamentoRazaoNormalizado` esta
   disponivel para cada operacao que substitui o caso de uso legado.
2. O dataset canonico, treino, classificacao e feedback novos possuem testes e
   homologacao de acesso por empresa, sem depender de `Transacao`.
3. Todos os consumidores internos identificados migraram, foram retirados por
   decisao humana ou receberam adaptador explicitamente aprovado.
4. Os endpoints `POST /companies/{company_id}/classification`,
   `POST /companies/{company_id}/predict` e
   `PATCH /transactions/{transaction_id}/feedback` possuem inventario de uso e
   confirmacao de que nao ha consumidor autorizado remanescente.
5. A retencao de dados historicos, a auditoria e a consulta necessaria para
   suporte foram decididas sem copiar automaticamente Razao para `Transacao`.
6. Existe issue funcional focada, com plano de rollout, rollback, testes de
   contrato e homologacao manual aprovados.

Esses gates nao criam data, versao de API, aviso de deprecation ou obrigacao de
migracao. Qualquer um desses contratos exige nova decisao e issue propria.

## Dados historicos e rollback

Nenhuma transacao historica sera migrada, arquivada ou removida por esta
politica. O historico de `Transacao` permanece no armazenamento atual para
compatibilidade e consulta enquanto o legado estiver ativo. A ausencia de
migracao automatica tambem impede que uma divergencia de semantica contabil
seja ocultada por copia de dados.

Uma futura entrega de descontinuacao deve decidir separadamente a retencao,
consulta, exportacao e eventual arquivamento dos dados. Antes de qualquer
mudanca mutavel, ela deve registrar inventario de consumidores, backup
verificavel quando aplicavel, plano de retorno e criterio de reversao.

Rollback de uma futura retirada significa restaurar a versao e o contrato
legados aprovados, sem recriar dados a partir do Razao e sem descartar
evidencias. Esta issue nao autoriza migration, delete, alteracao de tabela ou
mudanca de endpoint.

## Riscos e proximas issues funcionais

Os riscos principais sao remocao prematura de consumidor legado, migracao sem
equivalencia contabil demonstrada e manutencao indefinida sem revisar os gates.
O acompanhamento deve ocorrer por issues funcionais pequenas, quando os gates
forem observaveis:

- inventariar consumidores e telemetria sanitizada dos endpoints legados;
- migrar ou isolar um consumidor legado por vez;
- definir retencao e consulta historica antes de qualquer remocao;
- retirar um endpoint somente com testes de contrato, rollout, rollback e
  homologacao aprovados.

Nenhuma dessas entregas esta criada ou autorizada por este documento. Elas nao
devem alterar a fonte canonica, os dados historicos ou os contratos legados sem
uma nova Task Review e decisao humana.

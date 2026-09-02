# Guia de uso da planilha operacional

Este guia explica como preencher a planilha operacional de movimentos para
classificacao contabil. O contrato canonico esta na Spec 08:
`docs/specs/08-movimentos-operacionais-classificacao.md`.

A planilha operacional serve para importar movimentos de banco, caixa ou outra
fonte operacional, classificar a contrapartida contabil e permitir revisao
humana. Ela nao substitui o Razao canonico e nao vira Razao automaticamente.

## Modelos disponiveis

Use um dos modelos oficiais abaixo:

- `tests/fixtures/modelo_movimentos_operacionais_valor_saldo.xlsx`: layout A,
  com `valor` assinado e `saldo`;
- `tests/fixtures/modelo_movimentos_operacionais_debito_credito_saldo.xlsx`:
  layout B, com `debito`, `credito` e `saldo` na convencao do extrato.

O modelo legado `tests/fixtures/modelo_movimentos_operacionais_classificacao.xlsx`
continua aceito como compatibilidade do layout A sem saldo. Use-o apenas quando
o arquivo antigo ja existir ou quando ainda nao for possivel informar saldo.

## Antes de preencher

Na aba `Movimentos`, preencha os metadados:

- `Empresa`: nome interno ou razao social usada para identificacao humana;
- `Codigo dominio`: codigo da empresa no Dominio, quando houver;
- `CNPJ/CPF`: obrigatorio e usado para validar a empresa selecionada;
- `Periodo inicio`: data inicial do lote em `dd/mm/aaaa`;
- `Periodo fim`: data final do lote em `dd/mm/aaaa`.

Depois, preencha uma linha por movimento. Nao altere os nomes das colunas.

As cores da aba `Movimentos` ajudam o preenchimento:

- amarelo: colunas obrigatorias;
- verde: colunas opcionais ou recomendadas;
- azul: colunas preenchidas pelo sistema.

## Quando usar o layout A

Use o layout A quando o arquivo recebido tiver uma unica coluna de valor com
sinal.

Colunas principais:

- `data`: data do movimento;
- `conta_financeira`: codigo reduzido da conta de banco, caixa ou origem;
- `historico`: historico original do extrato, planilha ou comprovante;
- `valor`: valor assinado do movimento;
- `saldo`: saldo observado no extrato apos o movimento.

No layout A:

- valor positivo representa entrada na conta financeira;
- valor negativo representa saida da conta financeira;
- valor zero nao representa movimento valido.

Exemplo operacional:

| Movimento | valor | Interpretacao |
| --- | ---: | --- |
| Recebimento de cliente | 1500,00 | Entrada na conta financeira |
| Pagamento de fornecedor | -300,00 | Saida da conta financeira |

## Quando usar o layout B

Use o layout B quando o arquivo recebido vier na convencao do extrato, com
colunas separadas para `debito` e `credito`.

Colunas principais:

- `data`: data do movimento;
- `conta_financeira`: codigo reduzido da conta de banco, caixa ou origem;
- `historico`: historico original do extrato, planilha ou comprovante;
- `debito`: valor de saida no extrato;
- `credito`: valor de entrada no extrato;
- `saldo`: saldo observado no extrato apos o movimento.

No layout B:

- credito representa entrada na conta financeira;
- debito representa saida da conta financeira;
- exatamente uma entre `debito` e `credito` deve ser preenchida por linha;
- linha com `debito` e `credito` preenchidos ao mesmo tempo e invalida;
- linha sem valor em `debito` e `credito` tambem e invalida.

Exemplo operacional:

| Movimento | debito | credito | Interpretacao |
| --- | ---: | ---: | --- |
| Recebimento de cliente |  | 1500,00 | Entrada na conta financeira |
| Pagamento de fornecedor | 300,00 |  | Saida da conta financeira |

## Modelo legado

O modelo legado e o arquivo
`tests/fixtures/modelo_movimentos_operacionais_classificacao.xlsx`.

Ele continua aceito para compatibilidade, mas nao possui `saldo`. Quando usado,
o lote pode gerar warning informativo porque a conferencia por saldo fica
limitada.

Use o modelo legado somente quando necessario. Para novos envios, prefira um dos
dois modelos oficiais com saldo.

## Campos operacionais

### `conta_financeira`

Informe o codigo reduzido da conta financeira de origem, como banco, caixa ou
aplicacao. Essa conta e obrigatoria. O sistema nao prediz a conta financeira no
MVP.

### `contrapartida`

Informe a contrapartida quando souber a classificacao correta. Se deixar em
branco, o movimento pode seguir para sugestao do classificador ou revisao.

Contrapartida preenchida na planilha e pre-classificacao, nao aprovacao final.
A aprovacao depende de revisao humana ou fluxo de feedback.

### `tipo_movimento`

Campo opcional para ajudar filtros, validacao e interpretacao. Exemplos:
`entrada`, `saida`, `transferencia`, `aplicacao` e `resgate`.

Para `transferencia`, `aplicacao` e `resgate`, informe a `contrapartida` sempre
que possivel. Sem contrapartida, o movimento tende a exigir revisao.

### `documento`

Campo opcional. Use para numero de documento, identificador de extrato, boleto,
cheque ou referencia interna. Nao coloque dados sensiveis desnecessarios.

### `observacao`

Campo opcional para comentario curto de apoio a revisao. Evite informacoes de
cliente, segredo, dado pessoal ou historico completo desnecessario.

## Colunas preenchidas pelo sistema

As colunas abaixo podem estar no modelo, mas devem ficar em branco no
preenchimento inicial:

- `status_sugerido`;
- `confidence_sugerida`;
- `mensagem_validacao`.

Elas sao preenchidas pelo sistema em fluxos de classificacao, validacao ou
devolucao de planilha classificada.

## Saldo, conferencia e warnings

Saldo ajuda conferencia, nao classificacao.

O saldo informado na planilha e tratado como saldo observado. O sistema tambem
pode calcular o saldo esperado da sequencia de movimentos, chamado de saldo
calculado.

A comparacao entre saldo observado e saldo calculado ajuda a identificar lacunas
ou divergencias no fechamento, mas o saldo nao entra no aprendizado do
classificador e nao deve influenciar a sugestao de contrapartida.

Regras praticas:

- cada `conta_financeira` tem sua propria sequencia de saldo dentro do lote;
- a ordem das linhas no arquivo e preservada no calculo;
- saldo ausente gera warning, mas nao deve bloquear movimentos validos;
- saldo divergente gera warning, mas nao deve bloquear movimentos validos;
- saldo invalido pode gerar warning quando os demais campos da linha forem
  recuperaveis.

Quando houver linhas validas e warnings, o lote pode ficar como
`completed_with_warnings`. Isso significa que parte do arquivo foi aproveitada,
mas existem pontos que precisam de atencao na conferencia.

## Status e revisao

Principais status operacionais:

- `pendente`: movimento valido, sem contrapartida e ainda sem sugestao;
- `pre_classificado`: movimento veio com `contrapartida` preenchida na planilha;
- `sugerido`: classificador sugeriu uma contrapartida;
- `revisao`: movimento exige decisao humana antes de seguir;
- `aprovado`: usuario aprovou a classificacao;
- `corrigido`: usuario corrigiu a contrapartida e aprovou;
- `rejeitado`: usuario decidiu que a linha nao deve seguir.

Somente movimentos aprovados ou corrigidos por decisao humana podem virar fonte
confiavel futura. Movimento importado, sugerido ou pre-classificado ainda nao e
classificacao final.

## Razao canonico x movimento operacional

O Razao canonico vem da contabilidade e representa lancamentos contabeis
normalizados. Ele e a fonte principal de aprendizado e conferencia contabil.

A planilha operacional vem da operacao, banco, caixa, extrato ou controle
interno. Ela e uma entrada para classificacao e revisao.

Por isso:

- movimento operacional nao vira Razao automaticamente;
- movimento operacional nao deve ser tratado como dado contabil final;
- contrapartida sugerida pela ML nao e aprovacao;
- aprovacao humana define quando o movimento fica confiavel;
- exportacao para Dominio, OFX e PDF/OCR continuam fora deste fluxo atual.

## Erros e warnings comuns

| Situacao | Tipo esperado | Como corrigir |
| --- | --- | --- |
| CNPJ/CPF divergente da empresa selecionada | Bloqueio do lote | Conferir empresa selecionada e metadado da planilha |
| Aba `Movimentos` ausente | Bloqueio do lote | Usar um dos modelos oficiais |
| Layout ambiguo com `valor` junto de `debito`/`credito` | Bloqueio do lote | Escolher layout A ou B, sem misturar colunas |
| debito e credito preenchidos na mesma linha | Linha invalida | Manter exatamente uma coluna preenchida |
| `debito` e `credito` vazios no layout B | Linha invalida | Preencher a saida em `debito` ou a entrada em `credito` |
| Valor zero | Linha invalida | Remover a linha ou informar valor valido |
| `conta_financeira` ausente | Linha invalida | Informar a conta financeira de origem |
| `contrapartida` inexistente ou inativa | Linha invalida ou revisao | Conferir plano de contas |
| Saldo ausente | Warning | Preencher saldo quando houver no extrato |
| Saldo divergente | Warning | Conferir se falta linha, se a ordem esta correta ou se houve saldo inicial diferente |
| Codigo dominio divergente | Warning de lote | Conferir cadastro da empresa |

## Checklist antes de enviar

Antes de enviar a planilha:

- confirme que esta usando o modelo correto;
- preencha `CNPJ/CPF`, `Periodo inicio` e `Periodo fim`;
- confira se nao misturou layout A e layout B;
- confira se `conta_financeira` foi preenchida em todas as linhas;
- no layout A, confira sinais positivos e negativos;
- no layout B, confira se cada linha tem apenas `debito` ou `credito`;
- informe `saldo` quando disponivel;
- deixe colunas do sistema em branco;
- nao use dados reais em exemplos, testes ou evidencias publicas;
- nao anexe planilhas de cliente em issues ou PRs.

## Evidencias seguras

Para validar ou pedir ajuda, compartilhe apenas evidencias tratadas:

- nome do modelo usado;
- status do lote;
- totais de linhas importadas, invalidas e com warnings;
- trecho de mensagem sem dado sensivel;
- print cortado sem nome de cliente, documento, token ou valor real sensivel.

Nao use dados reais em exemplos publicos. Nao anexe planilhas de cliente no
repositorio, em issues ou em PRs.

# Homologacao do MVP de UX da Interface

Documento operacional da issue #282 para conduzir a primeira homologacao da
interface grafica interna.

Referencias:

- PRD: `docs/prd/evolucao-plano-contas-importacao-ml.md`
- Spec UX: `docs/specs/09-frontend-ux-fluxos.md`
- Spec de homologacao: `docs/specs/13-homologacao-massa-sanitizada.md`

## Objetivo

Validar, com operador/contador do escritorio, se o MVP permite operar o fluxo
principal sem chamadas manuais a API e sem expor dados sensiveis.

A homologacao deve usar massa sanitizada em ambiente de homologacao separado de
producao. Nao use dados reais, prints com informacoes sensiveis, senhas,
tokens, documentos reais de clientes ou arquivos contabeis reais.
Regra de aceite: a rodada deve ser executada sem dados reais.

## Preparacao

Antes da rodada, confirme:

- ambiente de homologacao separado de producao;
- banco de homologacao separado de producao;
- API e frontend apontando para o ambiente correto;
- usuario admin de preparacao criado;
- usuario operador/contador de teste criado;
- empresa ficticia vinculada ao usuario operador;
- plano de contas sanitizado importado;
- razao sanitizado importado;
- arquivo `.xlsx` de movimentos operacionais sanitizado disponivel;
- nenhuma credencial ou informacao sensivel usada como evidencia.

## Checklist por Tela

Registre `Aprovado`, `Bloqueante` ou `Melhoria` em cada item.

| Tela | Checklist de homologacao | Evidencias esperadas |
| --- | --- | --- |
| Login | Usuario acessa a tela, informa credenciais de teste, entra com identidade individual e recebe orientacao clara em erro de acesso. | Data/hora, usuario de teste, resultado do login, print sem senha. |
| Empresas | Usuario ve apenas empresas autorizadas; usuario sem empresas recebe orientacao para contatar administrador. | Empresa ficticia exibida, perfil usado, resultado de lista vazia quando aplicavel. |
| Operacao da Empresa | Hub mostra empresa selecionada, status do modelo/classificacao, resumo de razao, contas vinculadas quando disponiveis e atalhos operacionais. | Print do hub, status apresentado, atalhos disponiveis. |
| Importar Movimentos | Usuario seleciona `.xlsx` sanitizado, envia arquivo e recebe resumo do lote. | Nome do arquivo sanitizado, status do lote, linhas lidas, importadas, warnings e bloqueios. |
| Lote de Movimentos | Usuario filtra por status, seleciona movimentos, abre revisao individual, aprova ou rejeita selecionados quando elegivel e aciona classificacao de pendentes da empresa. | Filtro usado, quantidade selecionada, acao executada, mensagem de resultado. |
| Revisar Movimento | Usuario ve dados do movimento, sugestao, confianca, warnings, busca conta vinculada primeiro, busca no plano completo quando necessario e salva decisao humana. | Movimento ficticio, conta escolhida, decisao salva, aviso de vinculo quando aplicavel. |
| Razao e Contas Vinculadas | Usuario consulta lotes de razao, lancamentos normalizados e contas vinculadas quando a API fornecer dados. | Lote consultado, busca usada, resultado exibido, paginacao quando houver. |

## Evidencias Esperadas

Ao final da rodada, registre:

- versao, commit ou branch testada;
- data da homologacao;
- ambiente testado;
- usuario de teste e papel operacional;
- empresa ficticia usada;
- arquivos sanitizados usados;
- resultado dos comandos de validacao;
- prints ou logs curtos sem dados sensiveis;
- lista de falhas bloqueantes;
- lista de melhorias futuras;
- decisao final de liberacao ou reprova.

## Criterios de Liberacao

A primeira homologacao pode ser liberada para usuarios internos somente quando:

- backend tests relevantes estiverem verdes;
- frontend typecheck estiver verde;
- frontend lint estiver verde;
- frontend build estiver verde;
- validacao do fluxo principal estiver registrada, manual ou automatizada;
- API `/health` responder no ambiente de homologacao;
- login, selecao de empresa, importacao, classificacao, revisao e consulta
  tiverem evidencia suficiente;
- falhas bloqueantes estiverem resolvidas ou formalmente justificadas;
- dados e arquivos usados na rodada forem sanitizados;
- ambiente de homologacao estiver separado de producao.

## Riscos Conhecidos

| Risco | Impacto | Mitigacao |
| --- | --- | --- |
| Homologacao informal sem evidencia comparavel. | Falhas operacionais podem ser discutidas sem base objetiva. | Usar este checklist e anexar evidencias curtas por tela. |
| Uso acidental de dados reais. | Exposicao de informacoes sensiveis de clientes. | Usar apenas massa sanitizada e revisar prints antes de compartilhar. |
| Ambiente apontando para producao. | Alteracao indevida de dados operacionais. | Conferir variaveis, URL da API e banco antes da rodada. |
| Melhoria cosmetica tratada como bloqueio. | Atraso na liberacao do MVP. | Separar `Bloqueante` de `Melhoria` pelo impacto no fluxo operacional. |
| Fluxo principal validado parcialmente. | Usuario pode encontrar bloqueio em etapa nao testada. | Cobrir as sete telas e registrar lacunas explicitamente. |

## Registro de Resultado

Use este modelo ao fechar a rodada:

```text
Data:
Branch/commit:
Ambiente:
Usuario de teste:
Empresa ficticia:
Arquivos sanitizados:

Resultado por tela:
- Login:
- Empresas:
- Operacao da Empresa:
- Importar Movimentos:
- Lote de Movimentos:
- Revisar Movimento:
- Razao e Contas Vinculadas:

Validacoes tecnicas:
- backend tests relevantes:
- frontend typecheck:
- frontend lint:
- frontend build:
- validacao do fluxo principal:

Falhas bloqueantes:
- 

Melhorias futuras:
- 

Decisao:
```

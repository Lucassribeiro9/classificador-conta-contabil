# Roteiro de Homologacao do Operador/Contador

Use este roteiro para validar o fluxo operacional do MVP com um usuario
operador/contador. Execute a rodada somente em ambiente de homologacao separado
de producao e com banco de homologacao separado de producao.

Documentos complementares:

- gate de liberacao: `docs/homologacao-checklist-tecnico.md`;
- criterios por tela: `docs/frontend-homologacao-mvp-ux.md`;
- contrato da massa: `docs/specs/13-homologacao-massa-sanitizada.md`.

## Regra de Seguranca

Nao use dados reais. Nao registre senhas, tokens, chaves, documentos de clientes
ou informacoes contabeis reais nas evidencias.

## Pre-condicoes

Antes de iniciar, confirme:

- ambiente de homologacao separado de producao;
- banco de homologacao separado de producao;
- usuario operador/contador individual ativo;
- permissao do usuario para `EMPRESA MODELO HOMOLOGACAO LTDA`;
- fixtures `plano_contas_hml.xlsx`, `razao_hml.xlsx` e
  `movimentos_operacionais_hml.xlsx` carregadas ou disponiveis para a rodada.

Em cada etapa, marque `Aprovado`, `Bloqueante` ou `Melhoria` e anexe somente a
evidencia indicada.

## 1. Login

**Acao:** acesse a aplicacao por HTTPS e entre com o usuario operador/contador
de teste. Repita uma vez com credenciais invalidas.

**Resultado esperado:** o login valido abre a lista de empresas e a tentativa
invalida exibe mensagem clara, sem revelar detalhes tecnicos.

**Evidencia:** data/hora, identificador do usuario e resultados das duas
tentativas. Nao capture a senha.

## 2. Empresas Permitidas

**Acao:** confira a lista de empresas e abra `EMPRESA MODELO HOMOLOGACAO LTDA`.

**Resultado esperado:** apenas empresas permitidas ao usuario ficam visiveis e
a empresa selecionada abre no contexto correto.

**Evidencia:** perfil usado, empresas sanitizadas exibidas e empresa aberta.

## 3. Painel e Contexto Contabil

**Acao:** no painel da empresa, consulte o resumo do razao, os lotes importados,
as contas vinculadas e os atalhos operacionais.

**Resultado esperado:** o painel preserva a empresa selecionada e apresenta o
contexto contabil carregado pelas fixtures sanitizadas.

**Evidencia:** empresa, lote de razao consultado, quantidade ou amostra de
contas vinculadas e atalhos disponiveis.

## 4. Importacao e Resumo

**Acao:** importe `movimentos_operacionais_hml.xlsx` para a empresa selecionada.

**Resultado esperado:** o sistema aceita o `.xlsx` e mostra resumo com status do
lote, linhas lidas, importadas, pendentes, warnings e erros.

**Evidencia:** nome do arquivo, identificador e status do lote e totais do
resumo. Nao anexe o conteudo integral da planilha.

## 5. Lote e Classificacao

**Acao:** abra o lote criado, filtre os movimentos e execute `Classificar
pendentes` para a empresa.

**Resultado esperado:** a lista corresponde ao lote e a classificacao atualiza
somente movimentos pendentes da empresa selecionada.

**Evidencia:** lote, filtro, totais antes e depois e mensagem final da
classificacao.

## 6. Revisao em Lista

**Acao:** selecione itens elegiveis e use `Aprovar selecionados elegiveis`.
Depois, rejeite um movimento com motivo e outro sem motivo.

**Resultado esperado:** somente itens elegiveis sao aprovados; e possivel
rejeitar movimento com motivo opcional; decisoes finais nao sao alteradas por
nova acao em lote.

**Evidencia:** identificadores ficticios, quantidade selecionada, resultado por
acao e estados finais.

## 7. Revisao Individual

**Acao:** abra um movimento em revisao, busque primeiro nas contas vinculadas,
consulte o plano completo quando necessario e use a selecao para trocar a conta
e salvar.

**Resultado esperado:** a busca prioriza contas da empresa, permite ampliar ao
catalogo e persiste a decisao humana no movimento correto.

**Evidencia:** identificador ficticio do movimento, origem da conta escolhida,
conta sanitizada e estado final salvo.

## Triagem do Resultado

Classifique como `Bloqueante` quando a falha:

- compromete seguranca, autenticacao ou isolamento por empresa;
- usa ou expoe dado real, segredo ou ambiente de producao;
- causa perda, duplicacao ou alteracao indevida de dados;
- impede concluir o fluxo operacional de login ate revisao; ou
- apresenta resultado contabil incorreto sem alternativa segura.

Classifique como `Melhoria` quando for um problema visual ou ergonomico que nao
compromete seguranca, integridade, entendimento do resultado nem conclusao do
fluxo. Registre o impacto observado; nao reclassifique uma falha funcional como
cosmetica apenas para liberar a rodada.

A decisao final deve ser `Bloqueado` se houver qualquer bloqueante aberto. Sem
bloqueantes, registre `Aprovado` e encaminhe as melhorias futuras separadamente.

## Registro de Evidencias

Preencha o modelo sem incluir credenciais ou dados reais:

```text
Branch/commit:
Data/hora:
Ambiente/URL interna:
Usuario e papel:
Empresa sanitizada:
Arquivos sanitizados:
Comandos e resultados:

Resultado por etapa:
1. Login: Aprovado / Bloqueante / Melhoria
2. Empresas permitidas: Aprovado / Bloqueante / Melhoria
3. Painel e contexto contabil: Aprovado / Bloqueante / Melhoria
4. Importacao e resumo: Aprovado / Bloqueante / Melhoria
5. Lote e classificacao: Aprovado / Bloqueante / Melhoria
6. Revisao em lista: Aprovado / Bloqueante / Melhoria
7. Revisao individual: Aprovado / Bloqueante / Melhoria

Falhas bloqueantes:
- identificador, etapa, resultado esperado, resultado observado e evidencia

Melhorias futuras:
- identificador, etapa, impacto e sugestao

Decisao final: Aprovado / Bloqueado
Responsavel pela decisao:
```

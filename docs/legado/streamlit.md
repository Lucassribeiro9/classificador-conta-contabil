# Streamlit legado

## Status e finalidade

O arquivo [`app.py`](../../app.py) oferece uma interface Streamlit legada para
classificar linhas de uma planilha Excel. Ele treina um modelo temporario com
as linhas que ja possuem conta e tenta preencher as linhas sem conta.

Esse fluxo e **best-effort**: permanece disponivel apenas como apoio local e
nao possui garantia de disponibilidade, compatibilidade ou suporte continuo.
Falhas nele nao bloqueiam a homologacao do frontend interno nem a Release 1.

A arquitetura canonica do projeto e composta pela API FastAPI e pela SPA em
`frontend/`. Consulte o [guia de consumo da API](../api-openapi-consumo.md) e o
[guia do frontend](../../frontend/README.md) para os fluxos suportados.

## Uso local

Use somente dados ficticios ou sanitizados. A interface nao possui
autenticacao, autorizacao por empresa ou auditoria e nao deve receber dados
contabeis reais.

Na raiz do repositorio, prepare o ambiente conforme o
[`README.md`](../../README.md) e execute:

```bash
./venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

Abra `http://127.0.0.1:8501` e interrompa o processo com `Ctrl+C` ao terminar.
Nao altere o endereco para `0.0.0.0` nem encaminhe a porta para fora da maquina.

Na primeira inicializacao, o codigo pode tentar baixar a lista de stopwords do
NLTK caso ela ainda nao esteja instalada. Essa operacao depende de acesso de
rede e permissao de escrita no cache local; sua falha faz parte do suporte
best-effort.

## Formato observado

A interface aceita arquivos `.xlsx`. O processamento usa diretamente as
colunas `CONTA` e `DESCRIÇÃO DO LANÇAMENTO`, com essa grafia exata. O modelo
baixado pela propria interface mostra as demais colunas auxiliares.

O modelo e treinado novamente a cada envio. Cada conta precisa ter pelo menos
cinco exemplos, e o treinamento precisa conservar pelo menos duas contas
distintas. Linhas com confianca abaixo de 70% sao marcadas para revisao no
arquivo resultante.

Essas regras descrevem apenas o comportamento atual de `app.py`; elas nao sao
contrato do pipeline canonico de importacao, classificacao ou feedback.

## Limites de seguranca e arquitetura

- O fluxo nao consome a API e nao deve acessar diretamente o banco de dados.
- Nao ha login, permissao por empresa, auditoria ou persistencia de resultados
  no dominio da aplicacao.
- O upload, o treinamento e a geracao da planilha ocorrem no processo local;
  nao trate a sessao como armazenamento duravel.
- Mensagens de erro do legado podem incluir detalhes da excecao. Use somente
  arquivos sanitizados e nao compartilhe capturas ou logs sem revisao.
- Nao publique esse servico no Streamlit Community Cloud, em `ngrok`, na
  internet ou como endpoint permanente da rede interna.
- Nao inclua o Streamlit em rotinas de producao, homologacao, Compose ou
  monitoramento do caminho canonico.

## Politica de suporte

Correcoes no legado devem ser pequenas, justificadas e tratadas em issue
propria. Modernizacao, novas funcionalidades, integracao com API ou banco e
mudancas no modelo de classificacao ficam fora do suporte best-effort.

Quando o Streamlit divergir da API, do frontend, do PRD ou da
[Spec 15](../specs/15-harness-qualidade-documentacao.md), prevalecem as fontes
canonicas. A indisponibilidade do legado deve ser registrada como limitacao,
sem bloquear a validacao do frontend interno.

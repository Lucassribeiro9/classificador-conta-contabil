# Spec: Harness, Qualidade e Documentacao do Ciclo 0

## Objetivo

Consolidar a fundacao tecnica do Ciclo 0 da Release 1 em uma unica fonte
canonica. Esta spec define os contratos de validacao, ambientes, qualidade,
erros, logs e documentacao que serao implementados depois por issues pequenas.

Sucesso significa que o projeto passa a ter comandos, gates e documentos
reproduziveis antes das mudancas contabeis dos Ciclos 1 e 2.

## Rastreabilidade

- PRD: `docs/prd/evolucao-plano-contas-importacao-ml.md`.
- Release: Fase 3 / Release 1.
- Ciclo: Ciclo 0 - Fundacao, Harness e Documentacao.
- Issue-pai: #360.
- Issue desta spec: #363.

## Fonte Canonica

Esta spec e a fonte canonica para:

- matriz de comandos `dev`, `hml`, `prod` e `all`;
- contratos de `make check` e `make check-full`;
- validacoes esperadas em PR;
- uso de PostgreSQL real e Playwright relevante;
- eliminacao de testes ignorados e dependentes de ordem;
- lint backend e gates de CI;
- docstrings e comentarios orientados a contrato ou complexidade;
- OpenAPI como fonte canonica da API;
- envelope de erro com `code`, `message`, `details` e `request_id`;
- logs tecnicos JSON locais, rotacao e retencao;
- separacao entre logs tecnicos e auditoria;
- estrutura alvo do README geral;
- Streamlit legado best-effort;
- criterio de homologacao formal do Ciclo 0.

Specs existentes devem referenciar esta spec quando tratarem destes assuntos,
sem repetir contratos completos.

## Matriz de Ambientes e Comandos

Os comandos do Ciclo 0 devem seguir a matriz:

| Ambiente | Uso | Build | Test | Clean-cache | Logs | Limites |
| --- | --- | --- | --- | --- | --- | --- |
| `dev` | desenvolvimento local | sim | sim | sim | sim | pode recriar recursos locais nao sensiveis |
| `hml` | homologacao interna | sim | sim | sim | sim | deve preservar dados e evidencias de homologacao |
| `prod` | producao interna | sim | validacoes seguras | somente com confirmacao explicita | sim | nenhuma acao mutavel sem confirmacao |
| `all` | orquestracao dos ambientes | sim | sim | nao destrutivo por padrao | sim | nao executa acao destrutiva em producao |

Comandos comuns devem preservar volumes por padrao. Qualquer operacao que possa
apagar dados, remover volumes, recriar banco ou alterar producao exige comando
explicito, alvo identificado e confirmacao humana.

Servicos auxiliares, como o proxy de borda ou stack `edge`, devem entrar nos
comandos do ambiente que depender deles.

## `make check`

`make check` e o contrato padrao para PRs.

Ele deve ser proporcional ao escopo do PR, mas precisa representar a confianca
minima antes de merge. Quando as respectivas partes estiverem implementadas, o
comando deve cobrir:

- testes backend relevantes;
- validacao backend com PostgreSQL real quando o PR tocar persistencia,
  queries, migracoes, API que dependa de banco ou fluxos de importacao;
- validacoes frontend relevantes, incluindo lint, typecheck e build quando o
  PR tocar `frontend/`;
- Playwright relevante quando o PR tocar fluxo de usuario, roteamento, login,
  importacao, revisao, razao, empresas ou comportamento visual critico;
- verificacoes documentais quando o PR for documental;
- validacao de ausencia de segredos ou dados sensiveis no diff.

Um PR nao deve ocultar teste falho, marcar falha conhecida como sucesso ou
depender de ordem de execucao para passar.

## `make check-full`

`make check-full` e o contrato ampliado para validacao pre-merge de maior risco,
pre-release ou homologacao tecnica.

Ele deve cobrir tudo que `make check` cobre e adicionar, quando disponivel:

- matriz completa de backend, frontend, PostgreSQL e Playwright;
- validacoes de Docker Compose e ambientes;
- smoke tests de API e frontend;
- validacoes documentais completas;
- checagens de integridade dos contratos publicos.

`make check-full` nao substitui os roteiros de homologacao manual, mas fornece a
base automatizada para executa-los com confianca.

## PostgreSQL Real e Playwright

PostgreSQL real e Playwright relevante fazem parte do padrao da Release 1 em
todo PR que puder afetar persistencia, API, frontend ou fluxo operacional.

Excecoes devem ser explicitas no PR com justificativa objetiva, por exemplo:

- mudanca exclusivamente documental sem contrato executavel;
- ajuste que nao toca backend, frontend, ambiente ou fluxo;
- indisponibilidade temporaria documentada como bloqueio ou risco.

SQLite permanece apenas como legado/teste onde ja existir compatibilidade
justificada. Ele nao deve substituir PostgreSQL como alvo de confianca da
Release 1.

## Testes Ignorados e Ordem de Execucao

O Ciclo 0 deve remover ou resolver testes ignorados sem justificativa vigente.

Cada teste ignorado deve ter:

- motivo objetivo;
- issue de correcao vinculada, quando permanecer temporariamente;
- criterio para remocao do skip.

A suite nao deve depender da ordem de execucao. Quando houver dependencia de
estado compartilhado, a correcao deve priorizar fixtures isoladas, limpeza
controlada ou separacao do teste.

## Lint Backend e CI

O lint backend deve ser definido antes de ser exigido em CI. Adicionar ou trocar
dependencia de lint exige issue propria, porque muda a configuracao testavel do
projeto.

Os gates de CI devem deixar claro:

- comandos executados;
- ambiente e servicos necessarios;
- quais falhas bloqueiam merge;
- quais validacoes sao condicionais ao escopo;
- como falhas conhecidas serao tratadas sem serem escondidas.

## Docstrings e Comentarios

Docstrings e comentarios devem explicar contrato, regra ou complexidade. Eles
nao devem repetir nomes obvios nem transformar codigo simples em burocracia.

Devem ser usados em:

- contratos publicos de API, servicos e parsers;
- regras contabeis ou operacionais nao obvias;
- importadores, normalizadores e classificadores;
- integracoes com banco, frontend, n8n ou arquivos externos;
- testes com fixtures, massas ou asserts nao triviais;
- decisoes temporarias, limites conhecidos e compatibilidade legado.

Nao sao obrigatorios em funcoes triviais quando nomes e tipos ja comunicam o
comportamento.

## OpenAPI e Contrato de Erros

OpenAPI e a fonte canonica para consumo da API. A documentacao humana deve
explicar fluxos e exemplos, mas o contrato de endpoint deve continuar
rastreavel pela especificacao exposta pela FastAPI.

Erros publicos da API devem convergir para o envelope:

```json
{
  "code": "codigo_estavel",
  "message": "Mensagem clara para o usuario ou integrador.",
  "details": {},
  "request_id": "identificador-correlacionavel"
}
```

Regras:

- `code` deve ser estavel e adequado para automacao;
- `message` deve ser clara e segura;
- `details` deve conter contexto util sem segredos;
- `request_id` deve permitir correlacionar erro, log tecnico e investigacao;
- payloads, tokens, credenciais e dados sensiveis nao devem aparecer em erros.

A implementacao do envelope pertence a issues futuras.

## Logs Tecnicos e Auditoria

Logs tecnicos e auditoria sao conceitos separados.

Logs tecnicos:

- formato JSON local;
- rotacao por tamanho e/ou dias;
- retencao inicial de 30 dias;
- foco em diagnostico operacional;
- devem conter `request_id` quando houver request HTTP;
- nao podem conter senhas, tokens, API keys, dados contabeis sensiveis,
  planilhas completas ou payloads brutos.

Auditoria:

- registra eventos de negocio e seguranca;
- fica no contrato da Spec 07;
- possui retencao indefinida na primeira versao;
- deve manter usuario, empresa, acao e recurso quando aplicavel.

Falha de log tecnico nao deve corromper uma operacao de negocio. Falha de
auditoria em acao sensivel deve seguir o contrato da Spec 07.

## README Geral

O README geral deve ser reescrito em issue propria depois desta spec.

Estrutura alvo:

1. visao geral do projeto;
2. requisitos locais;
3. containers e stacks disponiveis;
4. matriz de ambientes `dev`, `hml`, `prod` e `all`;
5. comandos principais, incluindo `make check` e `make check-full`;
6. como subir, testar, limpar cache e consultar logs;
7. notebooks e artefatos auxiliares;
8. workflows operacionais e esteira supervisionada;
9. API, OpenAPI e autenticacao;
10. homologacao manual e evidencias;
11. troubleshooting;
12. limites de seguranca, dados sensiveis e producao.

O README deve permitir que um clone novo execute o projeto com seguranca, sem
exigir conhecimento espalhado em chats ou arquivos obsoletos.

## Documentos Obsoletos

Os documentos `TAREFAS_PENDENTES.md` e `PLANO_IMPLEMENTACAO.md` foram
considerados obsoletos para a Release 1. Eles devem ser removidos nesta issue,
porque o PRD, as specs, as issues e os PRs passam a ser as fontes oficiais de
planejamento e execucao.

Se algum conteudo desses arquivos ainda for util, ele deve ser reaproveitado
em PRD, spec, issue ou README futuro antes da remocao.

## Streamlit Legado

O Streamlit permanece como legado best-effort.

Regras:

- nao e caminho critico da Release 1;
- nao deve acessar banco diretamente na arquitetura-alvo;
- nao bloqueia homologacao do frontend interno;
- deve ser documentado no README como apoio legado, com limites claros;
- correcoes nele devem ser pequenas e justificadas, sem competir com o fluxo
  API-first.

## Homologacao Formal do Ciclo 0

A homologacao formal do Ciclo 0 deve registrar:

- ambiente;
- commit testado;
- responsavel pela execucao;
- perfil utilizado;
- servicos necessarios;
- roteiro executado;
- evidencias tratadas;
- divergencias;
- decisao final.

Os checklists atuais podem continuar como base, mas nao devem ser alterados
nesta issue. Ajustes de roteiro e preenchimento devem entrar em issue futura
derivada desta spec.

## Ordem Recomendada das Issues Futuras

Depois do merge desta spec, gerar issues pequenas nesta ordem:

1. `docs(readme): reescrever README geral do projeto`;
2. `chore(make): padronizar matriz dev-hml-prod-all`;
3. `chore(make): implementar make check e make check-full`;
4. `chore(ci): explicitar gates backend frontend postgres playwright`;
5. `test(harness): resolver testes ignorados e dependencia de ordem`;
6. `chore(quality): definir e aplicar lint backend`;
7. `docs(api): consolidar OpenAPI e exemplos de consumo`;
8. `feat(api): padronizar envelope de erro e request_id`;
9. `chore(logs): implementar logs JSON locais com rotacao`;
10. `docs(homologacao): formalizar roteiro preenchivel do Ciclo 0`;
11. `docs(legacy): documentar Streamlit best-effort`.

A criacao efetiva das issues deve ocorrer somente apos merge da spec e revisao
do backlog para evitar duplicidade.

## Testing Strategy

Issues derivadas desta spec devem cobrir, conforme o escopo:

- contrato dos workflows do CI;
- testes de configuracao Compose;
- testes de comandos Make;
- backend com PostgreSQL real;
- frontend com lint, typecheck, build e Playwright relevante;
- contrato de erro e correlacao por `request_id`;
- ausencia de segredos em erros e logs;
- validacoes documentais existentes.

Mudancas exclusivamente documentais nao devem criar TDD artificial. Elas devem
executar validacoes documentais reais.

## Boundaries

### Sempre

- manter uma fonte canonica por decisao;
- preservar volumes em comandos comuns;
- exigir confirmacao para producao e operacoes destrutivas;
- manter logs tecnicos separados de auditoria;
- manter segredos e dados sensiveis fora de docs, logs e erros;
- documentar excecoes de teste ou CI no PR;
- gerar issues pequenas depois da spec, nao antes.

### Perguntar Antes

- adicionar dependencia de lint;
- alterar politica de retencao;
- alterar CI;
- mudar template de issue ou PR;
- automatizar producao;
- remover volume, banco ou evidencia de homologacao.

### Nunca

- ocultar teste falho;
- expor segredo, credencial, token ou dado contabil sensivel;
- implementar CI, Makefile, logs, erros ou codigo nesta issue;
- usar Streamlit como arquitetura-alvo;
- executar acao destrutiva em producao por comando comum.

## Criterios de aceite

- Esta spec existe e esta vinculada a #363.
- Specs 00, 07, 11 e 12 apontam para esta spec sem contradicao.
- Comandos e ambientes possuem contrato verificavel.
- Criterios de saida do Ciclo 0 podem virar issues pequenas.
- Logs, auditoria, erros e OpenAPI possuem limites claros.
- README e Streamlit possuem direcao documental definida.
- Documentos obsoletos aprovados foram removidos.
- Nenhuma implementacao de codigo ou configuracao executavel foi incluida.

## Decisoes Aprovadas

- Esta spec usa o nome `15-harness-qualidade-documentacao`.
- Atualizacoes nas specs 00, 07, 11 e 12 devem ser minimas.
- O README sera reescrito em issue futura.
- `TAREFAS_PENDENTES.md` e `PLANO_IMPLEMENTACAO.md` devem ser removidos nesta
  issue.
- `make check` e o contrato padrao de PR.
- `make check-full` e o contrato ampliado para pre-merge, release e homologacao
  tecnica.
- Producao exige confirmacao para acoes mutaveis.
- Logs tecnicos tem retencao inicial de 30 dias.
- Auditoria permanece com retencao indefinida.
- OpenAPI e a fonte canonica da API.
- O envelope de erro alvo usa `code`, `message`, `details` e `request_id`.
- Prompts e guias podem ser atualizados nesta issue somente se houver
  necessidade concreta de alinhamento.

## Open Questions

- Nenhuma pendencia bloqueante registrada para iniciar as issues futuras apos o
  merge desta spec.

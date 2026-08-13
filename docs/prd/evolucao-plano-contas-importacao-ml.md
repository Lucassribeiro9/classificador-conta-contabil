# PRD: Evolucao do Classificador Contabil com Plano de Contas, Importacao do Razao e ML de Contrapartida

Este e o PRD unico e vivo da evolucao do produto. Ele registra objetivos,
limites e resultados esperados; contratos tecnicos detalhados permanecem nas
specs especializadas.

| Metadado | Valor |
| --- | --- |
| Versao do PRD | `3.0` |
| Fase | `3` |
| Release | `1` |
| Status | `Em especificacao` |
| Data da versao | `2026-07-28` |
| Vigencia | Merge do PR vinculado a [issue #359](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/359) |

## Historico de Versoes

As versoes `1.0` e `2.0` foram atribuidas retrospectivamente na versao `3.0`
para tornar a evolucao do PRD rastreavel. As datas correspondem aos commits que
consolidaram cada marco documental.

| Versao | Fase/Release | Data | Status atual | Resumo | Referencia |
| --- | --- | --- | --- | --- | --- |
| `1.0` | Fase 1 | 2026-06-09 | Entregue e em manutencao | Fundacao API-first, PostgreSQL, seguranca, plano de contas, Razao e ML de contrapartida. | Commit `e81da7f` |
| `2.0` | Fase 2 | 2026-07-02 | Implementada, em homologacao/estabilizacao | Interface grafica interna, ambientes e massa sanitizada de homologacao. | Commit `195d153` / PR `#270` |
| `3.0` | Fase 3 / Release 1 | 2026-07-28 | Em especificacao | Fundacao tecnica, saldos, dois layouts operacionais, planilha classificada e integracao n8n. | [Issue #359](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/359) |

## Estado das Fases

### Fase 1 - Entregue e em manutencao

A fundacao API-first, a persistencia principal em PostgreSQL, autenticacao,
permissoes por empresa, plano de contas, importacao do Razao, dataset de
contrapartida, classificacao e auditoria foram entregues. Correcoes,
compatibilidade e manutencao continuam permitidas sem reabrir o escopo
historico.

### Fase 2 - Implementada, em homologacao/estabilizacao

O frontend e o ambiente de homologacao foram implementados. Existem checklists,
smoke tests e roteiros, mas a homologacao operador/contador ainda nao foi
executada integralmente com evidencia unica e rastreavel. A fase somente sera
considerada concluida depois de registrar:

- data, ambiente e commit homologado;
- participantes ou responsaveis;
- checklist preenchido e resultado por cenario;
- falhas e limitacoes conhecidas;
- decisao final de aprovacao ou correcao.

Formalizar e executar essa homologacao da baseline e gate do Ciclo 0 da
Release 1.

### Fase 3 / Release 1 - Em especificacao

A Release 1 inicia a nova etapa de confiabilidade operacional e conferencia
contabil. Seu escopo e detalhado na secao
[Fase 3 / Release 1](#fase-3--release-1).

## Problema

O escritorio precisa evoluir o classificador contabil de um modelo que apenas aprende padroes de historico para um sistema interno capaz de usar contexto contabil estruturado. Hoje a conta contabil e tratada como um codigo isolado, sem catalogo de contas, sem descricao semantica, sem vinculo formal por cliente e sem normalizacao explicita de debito, credito e contrapartida.

Isso limita a qualidade do modelo, dificulta explicar previsoes, aumenta o risco de sugerir contas que nao sao usadas por uma empresa especifica e torna nebulosa a interpretacao de lancamentos do livro-razao. O escritorio tambem precisa fortalecer seguranca, controle de acesso, auditoria e persistencia antes de ampliar importacoes e treinar modelos com dados reais dos clientes.

O sistema sera usado apenas em ambiente interno do escritorio, por usuarios individuais, com acesso restrito as empresas que cada usuario tem permissao para operar. A primeira entrega priorizou API, testes e importadores confiaveis. A Fase 2 disponibilizou uma interface grafica interna, ainda em homologacao/estabilizacao, para operar os fluxos sem depender de chamadas diretas a API. A Fase 3 deve consolidar a baseline, incorporar saldos e dois layouts operacionais e devolver a classificacao em um arquivo reutilizavel.

## Solucao

A solucao sera uma evolucao API-first do sistema atual, usando PostgreSQL como banco principal, autenticacao de usuarios internos, autorizacao por empresa e importadores de dados contabeis.

O plano de contas do escritorio sera importado como catalogo unico. Cada empresa tera vinculos com as contas que utiliza, inicialmente descobertos a partir das importacoes do livro-razao. O livro-razao sera importado por empresa, interpretando blocos de conta, contrapartida e direcao do valor para normalizar cada lancamento em conta de debito, conta de credito, conta de origem do relatorio e conta de contrapartida.

Para a primeira versao do ML, o sistema usara como fonte principal de treino os lancamentos cujo bloco de origem seja banco, caixa ou aplicacao financeira. Nesses casos, o alvo do modelo sera a contrapartida contabil. Essa abordagem reduz ambiguidade, evita misturar o mesmo lancamento em diferentes blocos do razao e gera valor operacional mais rapidamente para classificacao de movimentos financeiros.

A interface e um frontend separado, mantido no mesmo repositorio, consumindo a API FastAPI. O n8n permaneceu fora do caminho critico das Fases 1 e 2. Na Release 1, o workflow existente sera adaptado depois da aprovacao dos contratos de planilha classificada, feedback e autenticacao de integracao.

## Historias de Usuario

1. Como admin, quero criar usuarios internos, para que cada pessoa use o sistema com identidade propria.
2. Como admin, quero desativar usuarios internos, para que ex-colaboradores ou usuarios inativos nao acessem dados de clientes.
3. Como admin, quero vincular empresas a usuarios, para que cada usuario veja apenas as empresas sob sua responsabilidade.
4. Como admin, quero atribuir papeis aos usuarios, para que acoes administrativas fiquem restritas a pessoas autorizadas.
5. Como admin, quero auditar acoes sensiveis, para que importacoes, feedbacks e alteracoes de classificacao sejam rastreaveis.
6. Como contador, quero acessar apenas minhas empresas vinculadas, para que os dados dos clientes permanecam isolados.
7. Como contador, quero importar o plano de contas do escritorio, para que o sistema tenha um catalogo canonico de codigos e nomes de contas.
8. Como contador, quero que a importacao do plano atualize contas existentes sem duplica-las, para que reimportacoes sejam seguras.
9. Como contador, quero identificar contas sinteticas e analiticas, para que apenas contas lancaveis sejam usadas em classificacoes.
10. Como contador, quero manter hierarquia e classificacao das contas, para que previsoes possam ser explicadas em contexto contabil.
11. Como contador, quero importar o livro-razao de uma empresa, para que lancamentos historicos virem dados de treino.
12. Como contador, quero que a importacao do razao detecte blocos de conta, para que o sistema saiba a conta de origem de cada linha.
13. Como contador, quero que debitos e creditos sejam interpretados a partir da conta do bloco, para que cada lancamento seja normalizado corretamente.
14. Como contador, quero capturar a conta de contrapartida, para que o sistema aprenda o outro lado dos movimentos de banco e caixa.
15. Como contador, quero distinguir saldos anteriores, cabecalhos e linhas vazias dos movimentos reais, preservando os saldos necessarios para conferencia sem trata-los como lancamentos.
16. Como contador, quero registrar lotes de importacao, para saber quando e por quem um arquivo foi processado.
17. Como contador, quero mensagens claras de erro na importacao, para corrigir layouts invalidos sem corromper dados.
18. Como contador, quero evitar duplicidade em reimportacoes, para que reprocessamentos acidentais nao poluam os dados de treino.
19. Como contador, quero que o sistema vincule automaticamente a empresa as contas encontradas no razao, para descobrir o uso real de contas por cliente.
20. Como contador, quero visualizar quais contas uma empresa usa, para que treino e predicao sejam corretamente limitados.
21. Como contador, quero identificar contas de banco, caixa e aplicacoes, para que o modelo inicial treine nos blocos mais confiaveis.
22. Como contador, quero transformar linhas de origem financeira em exemplos de treino, para que o modelo aprenda a prever contrapartidas.
23. Como contador, quero que o modelo use historico, conta de origem, direcao e valor, para aumentar a qualidade das previsoes.
24. Como contador, quero que o modelo preveja a contrapartida de movimentos de banco e caixa, para reduzir classificacao manual.
25. Como contador, quero que previsoes tragam confianca, para revisar resultados de baixa certeza.
26. Como contador, quero que previsoes de baixa confianca sejam marcadas para revisao, para evitar aceitacao silenciosa de classificacoes arriscadas.
27. Como contador, quero corrigir uma conta prevista, para que o feedback humano melhore dados futuros.
28. Como contador, quero que feedback fique vinculado a usuario e empresa, para manter auditoria.
29. Como operador, quero importar arquivos apenas para empresas que posso acessar, para nao alterar dados de outro cliente.
30. Como operador, quero mensagens de validacao claras, para corrigir erros operacionais sem depender de desenvolvedor.
31. Como operador, quero saber se uma importacao foi concluida, falhou ou falhou parcialmente, para tomar a proxima acao.
32. Como usuario interno, quero que o sistema seja acessivel apenas pela rede do escritorio, para que dados de clientes nao fiquem expostos publicamente.
33. Como usuario interno, quero que a aplicacao exija login mesmo na rede interna, para preservar responsabilidade individual.
34. Como responsavel pelo negocio, quero PostgreSQL como banco principal, para suportar usuarios simultaneos, importacoes e backups com mais robustez que SQLite.
35. Como responsavel pelo negocio, quero estrategia de backup considerada desde o inicio, para recuperar dados contabeis importados.
36. Como responsavel pelo negocio, quero adiar a integracao n8n, para que a primeira entrega foque nos fluxos internos seguros.
37. Como desenvolvedor, quero PRD e specs antes da implementacao, para que escopo e criterios de aceite fiquem claros.
38. Como desenvolvedor, quero TDD para parsers, autorizacao, importacoes e geracao de dataset de ML, para testar comportamentos de risco antes da implementacao.
39. Como desenvolvedor, quero issues derivadas das specs, para que cada pull request seja focado e revisavel.
40. Como revisor, quero que cada pull request traga evidencias de validacao, para que mudancas sejam integradas com seguranca.
41. Como operador, quero fazer login em uma interface interna simples, para operar o sistema com meu usuario individual.
42. Como operador, quero cair sempre na lista de empresas apos o login, para escolher conscientemente o cliente que vou operar.
43. Como operador, quero ver apenas as empresas vinculadas ao meu usuario, para evitar acesso indevido a dados de outros clientes.
44. Como admin, quero visualizar todas as empresas na interface, para apoiar operacao e diagnostico.
45. Como usuario sem empresas vinculadas, quero receber uma mensagem clara orientando contato com o administrador, para entender por que nao consigo operar.
46. Como operador, quero abrir um painel operacional da empresa, para consultar contexto de razao, contas vinculadas, movimentos e status do modelo.
47. Como operador, quero importar movimentos operacionais por `.xlsx`, para classificar dados recebidos fora do livro-razao canonico.
48. Como operador, quero ver um resumo apos importar movimentos, para decidir se abro o lote ou corrijo o arquivo.
49. Como operador, quero classificar todos os movimentos pendentes da empresa, para reduzir trabalho manual.
50. Como operador, quero revisar movimentos em lista, para aprovar, rejeitar ou enviar varios itens para revisao sem abrir um por um.
51. Como operador, quero revisar um movimento individualmente, para corrigir a conta sugerida quando necessario.
52. Como operador, quero buscar primeiro nas contas vinculadas da empresa e, quando necessario, no plano completo, para manter classificacoes consistentes.
53. Como contador, quero consultar razoes importados e contas vinculadas da empresa, para entender a base usada pelo modelo.
54. Como responsavel pelo negocio, quero homologar a interface com dados sanitizados, para validar o fluxo com usuarios sem expor dados reais.
55. Como desenvolvedor, quero specs de frontend, UX, ambientes e homologacao antes de implementar telas, para manter o fluxo SDD/TDD do projeto.

### Historias de Usuario da Release 1

As historias anteriores registram as Fases 1 e 2. As historias abaixo
delimitam os resultados da Release 1.

1. `R1-US01` - Como mantenedor, quero comandos e gates uniformes para dev, hml e prod, para reproduzir e validar o sistema com seguranca.
2. `R1-US02` - Como revisor, quero PostgreSQL real e os fluxos Playwright relevantes em todo PR, para detectar regressao antes do merge.
3. `R1-US03` - Como operador, quero mensagens de erro correlacionadas e documentacao clara da API, para diagnosticar falhas sem depender do frontend.
4. `R1-US04` - Como contador, quero importar o Razao anual preservando saldo anterior, Saldo e Saldo-Exercicio, para derivar fechamentos mensais e identificar divergencias.
5. `R1-US05` - Como operador, quero importar movimentos pelo layout de `valor` assinado ou pelo layout de `debito` e `credito`, para trabalhar com fontes diferentes sem preencher dados desnecessarios.
6. `R1-US06` - Como contador, quero comparar saldo observado e calculado por conta, para reconhecer lacunas e inconsistencias sem bloquear classificacoes recuperaveis.
7. `R1-US07` - Como operador, quero receber warnings de saldo sem perder o processamento das linhas validas, para continuar a operacao com os agravantes visiveis.
8. `R1-US08` - Como responsavel pelo modelo, quero manter saldo fora das features de ML, para evitar peso sem valor classificatorio.
9. `R1-US09` - Como operador, quero baixar a planilha no estado atual da classificacao, para revisar ou entregar o resultado sem depender da interface.
10. `R1-US10` - Como contador, quero revisar individualmente pelo frontend ou em lote pela planilha, para aplicar aceite, rejeicao e correcao pela forma mais adequada.
11. `R1-US11` - Como integracao n8n, quero consumir os contratos da API com identidade e escopos proprios, para automatizar o fluxo sem credenciais humanas ou globais excessivas.
12. `R1-US12` - Como responsavel pelo negocio, quero homologacao formal e rastreavel da baseline e da Release 1, para saber quais resultados foram realmente validados.

## Decisoes de Implementacao

- O sistema permanece API-first: a interface interna deve consumir a API e nunca acessar o banco diretamente.
- A fase de interface grafica sera implementada como frontend separado em `frontend/`, no mesmo repositorio.
- O frontend aprovado para a fase 2 usara React, TypeScript, Vite, Tailwind CSS, React Router e TanStack Query.
- A interface sera uma SPA interna, voltada a uso na rede do escritorio.
- O login inicial sera simples, usando autenticacao JWT ja exposta pela API.
- Apos login, o usuario deve sempre cair na tela de empresas.
- Usuario comum visualiza apenas empresas vinculadas; admin visualiza todas.
- Se o usuario nao possuir empresas vinculadas, a interface deve exibir estado vazio orientando contato com o administrador.
- O MVP visual da fase 2 cobre: Login, Empresas, Operacao da Empresa, Importar Movimentos, Lote de Movimentos, Revisar Movimento, Razao e Contas Vinculadas.
- CRUD administrativo de usuarios e permissoes fica fora do MVP inicial de frontend.
- A aprovacao em lote de movimentos operacionais faz parte do MVP, mas deve respeitar elegibilidade e nao alterar decisoes finais.
- Rejeicao de movimento tera motivo opcional.
- A busca de conta em revisao deve priorizar contas vinculadas a empresa e permitir busca no plano completo.
- A primeira homologacao da interface sera focada no perfil operador/contador; admin prepara ambiente, usuarios, empresas e dados.
- Homologacao e producao devem ser ambientes separados, com bancos e variaveis de ambiente proprios.
- A massa inicial de homologacao deve ser sanitizada e conter plano de contas, razao e movimentos operacionais coerentes.
- As proximas implementacoes devem seguir issues pequenas, branch sugerida antes de editar arquivos e PR seguindo `.github/pull_request_template.md`.
- O sistema rodara no servidor Ubuntu existente com Docker, restrito a rede do escritorio.
- A aplicacao nao deve ser exposta via Streamlit Community Cloud nem via ngrok permanente para este fluxo interno.
- PostgreSQL substituira SQLite como banco-alvo desta evolucao.
- O acesso ao banco deve permanecer privado ao ambiente da aplicacao. O banco nao deve ser exposto publicamente.
- A autenticacao usara usuarios internos individuais, nao credenciais compartilhadas.
- A autorizacao tera permissoes por empresa, para que usuarios operem apenas empresas vinculadas.
- API keys podem permanecer para integracoes futuras, mas acesso humano deve usar autenticacao de usuario interno.
- O n8n permaneceu fora das Fases 1 e 2; na Release 1, o workflow existente sera adaptado com identidade de integracao, escopos proprios e artefato sanitizado.
- O plano de contas sera modelado como catalogo unico do escritorio.
- O uso de contas por empresa sera representado por um relacionamento entre empresa e conta.
- A importacao do plano de contas deve ser idempotente: contas existentes sao atualizadas e contas novas sao criadas.
- Contas sinteticas e analiticas devem ser distinguiveis. Apenas contas analiticas/lancaveis devem ser candidatas a classificacao.
- A importacao do razao deve interpretar planilhas de relatorio com cabecalhos, blocos de conta e linhas de lancamento.
- No razao, o bloco de conta representa a conta de origem das linhas exibidas.
- A coluna de contrapartida representa o outro lado de cada linha exibida.
- Se a linha tem valor em debito, a conta do bloco e debitada e a contrapartida e creditada.
- Se a linha tem valor em credito, a conta do bloco e creditada e a contrapartida e debitada.
- O registro normalizado do razao deve manter conta de origem, contrapartida, conta de debito, conta de credito, historico, valor, data, numero do lancamento e lote de importacao.
- O primeiro dataset de treino de ML usara apenas linhas cujo bloco de origem seja banco, caixa ou aplicacao financeira.
- O primeiro alvo do ML sera a contrapartida, nao o par debito/credito completo.
- Predicao de par debito/credito completo e lancamentos compostos ficam adiados.
- Feedback humano continua fazendo parte do ciclo de aprendizado e deve ser persistido com contexto de usuario e empresa.
- Acoes sensiveis devem ser auditaveis, incluindo eventos relevantes de login, importacoes, execucoes de classificacao e feedbacks.
- PRD, specs, issues e TDD serao usados como fluxo de trabalho desta evolucao.

## Decisoes de Teste

- Os testes devem validar comportamento externo e resultado de dominio, nao detalhes privados de implementacao.
- Testes de API devem seguir o estilo atual com FastAPI TestClient como seam principal para autenticacao, autorizacao, importacoes, classificacao e feedback.
- Testes de parser devem validar entradas semelhantes a planilhas e saidas normalizadas. Devem cobrir cabecalhos, linhas vazias, saldos, deteccao de blocos de conta, linhas de debito, linhas de credito e casos sem contrapartida.
- Testes de importacao devem verificar persistencia, idempotencia, criacao de lote, vinculo de contas por empresa e prevencao de duplicidade.
- Testes de autorizacao devem garantir que usuarios nao importem, consultem, classifiquem ou alterem dados de empresas sem permissao.
- Testes de dataset devem garantir que apenas contas de banco, caixa e aplicacao financeira entrem no dataset inicial.
- Testes de dataset devem garantir que o alvo do primeiro modelo seja a conta de contrapartida.
- Testes de comportamento do ML devem validar formato de resposta, confianca e marcacao de revisao, sem depender de detalhes frageis do modelo.
- Testes de feedback devem garantir que correcoes respeitem permissoes por empresa e sejam registradas como acoes auditaveis.
- A migracao para PostgreSQL e a configuracao de banco devem ser verificadas por testes de integracao ou checagens controladas quando o container for introduzido.
- Testes de seguranca devem cobrir usuario inativo, acesso entre empresas e tentativa de importacao sem permissao.
- Os testes de API existentes servem como referencia para uso do TestClient, escopo por empresa e fluxos de predicao/feedback.
- Os testes de ML existentes servem como referencia para treino, formato de predicao e atualizacao de transacoes.
- A interface deve ter validacoes proprias: typecheck, lint, build, testes de componentes e Playwright nos fluxos principais quando aplicavel.
- Testes de frontend devem validar comportamento percebido pelo usuario e integracao com contratos da API, evitando acoplamento a detalhes internos dos componentes.
- A primeira homologacao so deve ser liberada quando backend tests relevantes estiverem verdes, frontend build/typecheck/lint estiverem verdes e o fluxo principal tiver validacao manual ou automatizada registrada.

## Limites e Fora de Escopo

### Limites Permanentes da Solucao

- A interface e integracoes consomem a API; nao acessam o banco diretamente.
- Aplicacao, banco e dados contabeis permanecem restritos aos ambientes internos autorizados.
- Segredos, credenciais, IDs reais e dados de clientes nao sao versionados.
- Previsao de ML nao substitui decisao contabil humana final.
- O plano de contas permanece um catalogo unico do escritorio, com uso vinculado por empresa.
- Razao canonico e movimentos operacionais permanecem fontes separadas.
- Movimento operacional nao se transforma automaticamente em Razao canonico nem em `Transacao` legada.

### Fora da Release 1 / Backlog Futuro

- Importacao de PDF ou OCR.
- Importacao de OFX.
- Exportacao para o Dominio.
- Dashboards e relatorios para clientes.
- Conciliacao por pareamento entre Razao, extrato e movimentos operacionais.
- CRUD administrativo completo de usuarios e permissoes no frontend.
- Portal para clientes externos.
- GraphQL ou migracao para Django.
- Predicoes de lancamentos compostos ou multiplas partidas.
- Uso de todos os blocos do Razao como fonte principal do treino inicial.

### Limites por Ciclo

Cada ciclo da Release 1 registra seu proprio fora de escopo. Um item excluido
de um ciclo nao pode ser antecipado por uma issue de implementacao de outro
ciclo sem nova decisao no PRD e na spec correspondente.

## Observacoes Finais

A decisao de produto mais importante e tratar esta evolucao como fundacao de dados e seguranca antes de tratar como troca de UI ou troca de modelo. O modelo so deve melhorar de forma sustentavel quando contas, uso por empresa, importacoes do razao e semantica de contrapartida estiverem representados explicitamente.

A decisao contabil mais importante e evitar uma regra global como "debito significa banco". Debito e credito devem ser interpretados em relacao a conta do bloco do razao. Isso torna o par debito/credito normalizado confiavel e mantem o primeiro problema de ML focado na predicao de contrapartida para origens financeiras.

A sequencia historica das Fases 1 e 2 foi:

1. Base de configuracao e migracao para PostgreSQL.
2. Usuarios internos e autenticacao.
3. Permissoes por empresa.
4. Modelo de dominio do plano de contas.
5. Importador do plano de contas.
6. Modelo de lote de importacao.
7. Parser do razao.
8. Normalizacao de debito, credito e contrapartida.
9. Vinculo automatico entre empresa e contas usadas.
10. Geracao do dataset de treino para banco/caixa.
11. Predicao de contrapartida pelo ML.
12. Feedback e trilha de auditoria.
13. Interface interna apos estabilizacao dos fluxos de backend.
14. Homologacao da interface com massa sanitizada.

Pendencias historicas foram resolvidas pelas specs ou encaminhadas para o backlog.
Na Release 1:

- a convivencia entre JWT, API keys, admin token e n8n e tratada pela issue [#351](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/351);
- contratos de Razao e movimentos sao atualizados pelas issues [#364](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/364) e [#365](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/365);
- download e feedback round-trip sao especificados pela issue [#366](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/366);
- PDF, OFX, exportacao Dominio, dashboards e relatorios permanecem no backlog futuro.

## Atualizacao da Fase 2: Interface Grafica Interna

A fase 2 transforma a fundacao API-first em uma ferramenta operacional para usuarios internos. O objetivo nao e reabrir decisoes de dominio, mas oferecer uma interface segura e eficiente para operar empresas, razao, contas vinculadas, movimentos operacionais, classificacao, revisao e homologacao.

O frontend deve nascer separado do backend, dentro de `frontend/`, mantendo a API FastAPI como fronteira de integracao. A stack aprovada e React, TypeScript, Vite, Tailwind CSS, React Router e TanStack Query. A direcao visual aprovada usa branco como base, a cor institucional `#007693`, apoio em `#004E61`, cinzas neutros e uma interface operacional compacta.

O MVP da interface inclui Login, Empresas, Operacao da Empresa, Importar Movimentos, Lote de Movimentos, Revisar Movimento, Razao e Contas Vinculadas. A primeira homologacao deve priorizar operadores/contadores, com dados sanitizados e ambientes separados de producao. Telas administrativas, OFX, PDF/OCR e exportacao para Dominio continuam como evolucoes posteriores.

## Fase 3 / Release 1

### Objetivo

Transformar a baseline implementada em uma operacao confiavel, conferivel e
reutilizavel sem depender do frontend. A release fortalece o harness, incorpora
saldos ao Razao e aos movimentos, aceita dois layouts operacionais, devolve a
planilha no estado atual da classificacao e adapta o workflow n8n existente.

Sucesso significa que operadores e contadores conseguem importar, classificar,
conferir, revisar e entregar movimentos com rastreabilidade, enquanto o sistema
preserva isolamento por empresa, decisao humana e compatibilidade com a
baseline.

### Estados e Atualizacao

A Release 1 usa os estados:

- `Em especificacao`: PRD e specs ainda estao sendo aprovados;
- `Em implementacao`: ao menos um ciclo possui spec aprovada e implementacao autorizada;
- `Em homologacao`: os tres ciclos foram implementados e aguardam validacao integrada;
- `Concluida`: criterios de saida e homologacao formal foram aprovados;
- `Suspensa`: trabalho interrompido por decisao explicita, com motivo e condicao de retomada registrados.

Issues e sub-issues sao a fonte do progresso detalhado. O PRD e atualizado
somente quando:

- a release muda de estado;
- uma issue-pai de ciclo cumpre seus criterios de saida;
- o escopo, um limite permanente ou uma decisao de produto muda.

Cada atualizacao entra por branch e PR. Quando nenhuma issue documental cobrir
o marco, deve ser criada uma issue pequena `docs(release)`.

### Governanca e Revisao do Backlog

O backlog deve ser revisado:

- antes de cada Task Review;
- antes de criar ou atualizar uma spec;
- antes de gerar issues de implementacao;
- antes de encerrar cada ciclo.

A revisao procura duplicidades, decisoes superadas, dependencias resolvidas,
itens implementados e issues que mudaram de ciclo. Divergencias relevantes sao
corrigidas no PRD ou na spec antes de prosseguir.

Task Reviews e specs dos ciclos posteriores podem ser antecipadas depois do
merge da issue #359. A implementacao e sequencial: Ciclo 0, Ciclo 1 e Ciclo 2.
Uma spec antecipada nao autoriza antecipar sua implementacao.

### Ciclo 0 - Fundacao, Harness e Documentacao

Issue-pai: [#360](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/360).

Objetivo: tornar o estado atual confiavel, documentado, reproduzivel e
formalmente homologado antes das mudancas contabeis.

Resultados esperados:

- README geral para containers, stacks, notebooks, uso e workflows;
- matriz de comandos `dev`, `hml`, `prod` e `all`, incluindo build, test, clean-cache e logs;
- `make check` e `make check-full`;
- PostgreSQL real e Playwright relevante em todo PR;
- eliminacao de testes ignorados e dependentes de ordem;
- lint backend e gates de CI explicitos;
- docstrings e comentarios orientados a contrato ou complexidade, inclusive em testes;
- OpenAPI como fonte canonica da API;
- erros com `code`, `message`, `details` e `request_id`;
- logs tecnicos JSON locais com rotacao, separados da auditoria;
- auditoria com retencao indefinida;
- Streamlit legado documentado como best-effort;
- roteiro preenchivel e evidencia formal da homologacao da baseline da Fase 2.

Fora do Ciclo 0:

- mudancas nas regras contabeis;
- dois layouts e saldos;
- planilha classificada e feedback round-trip;
- conciliacao.

Criterios de saida:

1. PRD 3.0 aprovado na `main`.
2. Spec de fundacao/harness aprovada e implementada por issues focadas.
3. README permite executar um clone novo.
4. CI nao oculta falhas conhecidas nem depende de ordem de testes.
5. Comandos e ambientes possuem validacao reproduzivel.
6. Baseline da Fase 2 foi homologada formalmente com checklist e evidencias.
7. Nenhuma regra contabil foi alterada inadvertidamente.

### Ciclo 1 - Dois Layouts, Saldos e Normalizacao

Issue-pai: [#361](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/361).

Objetivo: aceitar dois layouts operacionais com saldo, ampliar os saldos do
Razao e convergir as entradas para um contrato interno unico.

Resultados esperados:

- layout A com `valor` assinado e `saldo`;
- layout B com `debito`, `credito` e `saldo` na convencao do extrato;
- credito do extrato como entrada e debito como saida;
- multiplas contas financeiras por lote, com sequencias independentes;
- saldo observado separado do saldo calculado;
- lacunas e divergencias recuperaveis registradas como warning;
- continuidade do calculo atraves de lacunas;
- normalizacao para valor assinado, valor absoluto e direcao contabil;
- saldo fora das features de treino e predicao;
- Razao anual com saldo anterior, Saldo e Saldo-Exercicio;
- fechamentos mensais derivados por conta;
- Razao e movimentos operacionais preservados como fontes separadas;
- movimentos aprovados ou corrigidos como fonte incremental confiavel.

Fora do Ciclo 1:

- pareamento de conciliacao;
- download da planilha classificada;
- feedback round-trip;
- PDF, OFX e exportacao Dominio.

Criterios de saida:

1. Specs 04 e 08 atualizadas e aprovadas.
2. Dois templates oficiais e versionados.
3. Implementacao validada para os dois layouts e para saldos do Razao.
4. Compatibilidade retroativa com arquivos sem saldo ou no layout atual.
5. Warnings nao bloqueiam classificacoes recuperaveis.
6. Saldo nao participa do ML.
7. Fechamentos mensais podem ser derivados do Razao anual.

### Ciclo 2 - Planilha Classificada e Loop de Feedback

Issue-pai: [#362](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/362).

Objetivo: devolver o estado atual da classificacao, permitir revisao pelo
frontend ou pelo round-trip do arquivo e adaptar com seguranca o workflow n8n
existente.

Resultados esperados:

- saida reconstruida dos templates e dados persistidos, sem depender do binario original;
- ordem e identificadores das linhas preservados;
- `contrapartida` de entrada imutavel;
- `contrapartida_sugerida` e `contrapartida_final` separadas;
- um unico download representando o estado atual, preliminar ou final;
- revisao individual pelo frontend e em lote pelo arquivo;
- processamento parcial com resultado por linha;
- idempotencia de reenvio e concorrencia otimista contra arquivo desatualizado;
- endpoint individual preservado e endpoint separado para revisoes em lote;
- regra de dominio compartilhada entre frontend, arquivo e integracao;
- identidade e escopos de integracao definidos sem expor segredo ao frontend;
- workflow n8n existente adaptado, sanitizado e validado em homologacao.

Fora do Ciclo 2:

- criar um workflow generico concorrente;
- armazenar credenciais ou IDs reais;
- autoaprovacao baseada apenas em confianca;
- PDF, OFX e exportacao Dominio.

Criterios de saida:

1. Spec de planilha classificada e feedback round-trip aprovada e implementada.
2. Decisao de autenticacao #351 incorporada aos contratos relevantes.
3. Spec de adaptacao do n8n aprovada e implementada sobre o workflow existente.
4. Download, revisao parcial, idempotencia e concorrencia possuem testes.
5. Frontend e round-trip produzem a mesma decisao de dominio.
6. Workflow sanitizado funciona em homologacao sem segredos ou dados reais.
7. Fluxo completo possui evidencia formal de homologacao.

### Dependencias e Ordem

1. A issue #359 formaliza este PRD.
2. O Ciclo 0 consolida o harness e homologa a baseline.
3. Somente depois do Ciclo 0 a implementacao do Ciclo 1 e autorizada.
4. O Ciclo 2 depende dos contratos implementados do Ciclo 1.
5. A adaptacao n8n depende da decisao #351 e da spec de planilha #366.

### Matriz de Rastreabilidade

| Ciclo | Issue-pai | Issue de spec/decisao | Spec canonica | Estado documental |
| --- | --- | --- | --- | --- |
| Ciclo 0 | [#360](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/360) | [#363](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/363) | [Spec 15](../specs/15-harness-qualidade-documentacao.md) | Criada pela #363 |
| Ciclo 0 | [#360](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/360) | [#363](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/363) | [Spec 00](../specs/00-visao-fluxo-sdd.md), [Spec 07](../specs/07-auditoria-seguranca-operacional.md), [Spec 11](../specs/11-frontend-docker-ambientes.md) e [Spec 12](../specs/12-frontend-padroes-codigo-documentacao.md) | Existentes; atualizadas com referencia canonica para a Spec 15 |
| Ciclo 0 | [#360](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/360) | [#369](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/369) | [Spec 14](../specs/14-esteira-agentes-supervisionada.md) | Habilitadora nao bloqueante da Release 1 |
| Ciclo 1 | [#361](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/361) | [#364](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/364) | [Spec 04](../specs/04-importacao-razao-normalizacao.md) | Atualizada com saldos e fechamentos pela #364 |
| Ciclo 1 | [#361](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/361) | [#365](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/365) | [Spec 08](../specs/08-movimentos-operacionais-classificacao.md) | Atualizada com dois layouts operacionais e saldos pela #365 |
| Ciclo 2 | [#362](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/362) | [#366](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/366) | [Spec 16](../specs/16-planilha-classificada-feedback-roundtrip.md) | Criada pela #366 |
| Ciclo 2 | [#362](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/362) | [#351](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/351) | [Spec 02](../specs/02-auth-usuarios-permissoes.md) | Atualizacao planejada |
| Ciclo 2 | [#362](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/362) | [#367](https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/367) | Sem arquivo canonico - issue de spec ainda nao executada | Planejada |

### Evolucao das Decisoes

| Decisao historica | Regra vigente na Release 1 | Responsavel pelo contrato |
| --- | --- | --- |
| Linhas de saldo eram ignoradas como movimentos. | Saldo anterior, Saldo e Saldo-Exercicio sao preservados para conferencia, sem virar lancamento nem feature de ML. | #364 / Spec 04 |
| `saldo_exercicio_original` era apenas auxiliar visual. | Saldo e Saldo-Exercicio ganham semantica explicita, representacao normalizada e uso em fechamentos mensais. | #364 / Spec 04 |
| O layout operacional oficial usava apenas `valor` assinado. | Dois layouts oficiais convergem para o mesmo contrato interno e ambos aceitam saldo. | #365 / Spec 08 |
| O fluxo operacional era descrito a partir de uma conta financeira por linha. | Um lote pode conter varias contas financeiras, cada uma com sua sequencia de saldo. | #365 / Spec 08 |
| O n8n estava adiado para depois da interface. | O workflow existente e parte da entrega do Ciclo 2, apos #351, #366 e #367. | #351, #366 e #367 |
| A Fase 2 possuia checklists e roteiros sem gate unico de aceite. | Homologacao formal com ambiente, commit, responsaveis, resultados e decisao e gate do Ciclo 0. | #363 |

### Criterios de Sucesso da Release 1

1. Baseline da Fase 2 homologada formalmente.
2. Harness e documentacao permitem reproduzir e validar os ambientes.
3. Razao anual preserva os saldos necessarios e permite derivar fechamentos mensais.
4. Ambos os layouts operacionais classificam pelo mesmo contrato interno.
5. Warnings de saldo informam agravantes sem bloquear linhas recuperaveis.
6. Saldo permanece fora do treino e da predicao.
7. Planilha classificada pode ser baixada e revisada sem depender do frontend.
8. Feedback individual e em lote compartilham regras, auditoria e concorrencia segura.
9. Workflow n8n existente opera em homologacao com identidade adequada e artefato sanitizado.
10. Os tres ciclos possuem criterios de saida e evidencias aprovados.

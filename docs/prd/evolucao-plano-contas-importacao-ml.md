# PRD: Evolucao do Classificador Contabil com Plano de Contas, Importacao do Razao e ML de Contrapartida

## Problema

O escritorio precisa evoluir o classificador contabil de um modelo que apenas aprende padroes de historico para um sistema interno capaz de usar contexto contabil estruturado. Hoje a conta contabil e tratada como um codigo isolado, sem catalogo de contas, sem descricao semantica, sem vinculo formal por cliente e sem normalizacao explicita de debito, credito e contrapartida.

Isso limita a qualidade do modelo, dificulta explicar previsoes, aumenta o risco de sugerir contas que nao sao usadas por uma empresa especifica e torna nebulosa a interpretacao de lancamentos do livro-razao. O escritorio tambem precisa fortalecer seguranca, controle de acesso, auditoria e persistencia antes de ampliar importacoes e treinar modelos com dados reais dos clientes.

O sistema sera usado apenas em ambiente interno do escritorio, por usuarios individuais, com acesso restrito as empresas que cada usuario tem permissao para operar. A primeira entrega deve priorizar API, testes e importadores confiaveis antes de construir uma interface operacional completa.

## Solucao

A solucao sera uma evolucao API-first do sistema atual, usando PostgreSQL como banco principal, autenticacao de usuarios internos, autorizacao por empresa e importadores de dados contabeis.

O plano de contas do escritorio sera importado como catalogo unico. Cada empresa tera vinculos com as contas que utiliza, inicialmente descobertos a partir das importacoes do livro-razao. O livro-razao sera importado por empresa, interpretando blocos de conta, contrapartida e direcao do valor para normalizar cada lancamento em conta de debito, conta de credito, conta de origem do relatorio e conta de contrapartida.

Para a primeira versao do ML, o sistema usara como fonte principal de treino os lancamentos cujo bloco de origem seja banco, caixa ou aplicacao financeira. Nesses casos, o alvo do modelo sera a contrapartida contabil. Essa abordagem reduz ambiguidade, evita misturar o mesmo lancamento em diferentes blocos do razao e gera valor operacional mais rapidamente para classificacao de movimentos financeiros.

A interface Streamlit ou outro painel interno podera ser reaproveitada no futuro, mas a primeira entrega deve estabilizar a API, dominio, importacao, seguranca, auditoria e testes. O n8n continuara fora do caminho critico desta fase e sera tratado como integracao posterior com credenciais e escopos proprios.

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
15. Como contador, quero ignorar saldos anteriores, cabecalhos e linhas vazias, para que apenas movimentos reais sejam importados.
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

## Decisoes de Implementacao

- O sistema permanecera API-first na primeira entrega. Trabalho de UI fica adiado ate os fluxos de backend estarem estaveis e testados.
- A interface interna podera reaproveitar Streamlit futuramente, mas Streamlit nao deve acessar o banco diretamente. Ferramentas de usuario devem chamar a API.
- O sistema rodara no servidor Ubuntu existente com Docker, restrito a rede do escritorio.
- A aplicacao nao deve ser exposta via Streamlit Community Cloud nem via ngrok permanente para este fluxo interno.
- PostgreSQL substituira SQLite como banco-alvo desta evolucao.
- O acesso ao banco deve permanecer privado ao ambiente da aplicacao. O banco nao deve ser exposto publicamente.
- A autenticacao usara usuarios internos individuais, nao credenciais compartilhadas.
- A autorizacao tera permissoes por empresa, para que usuarios operem apenas empresas vinculadas.
- API keys podem permanecer para integracoes futuras, mas acesso humano deve usar autenticacao de usuario interno.
- n8n fica fora do escopo da primeira entrega e sera tratado depois como integracao com escopo proprio.
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

## Fora de Escopo

- Portal para clientes externos.
- GraphQL.
- Migracao para Django.
- Deploy publico no Streamlit Community Cloud.
- Exposicao permanente por ngrok para a aplicacao contabil.
- Mudancas no workflow n8n na primeira entrega.
- Frontend completo na primeira entrega.
- Predicoes avancadas de lancamentos compostos ou multiplas partidas.
- Uso de todos os blocos do razao como fonte principal de treino inicial.
- Decisoes automaticas de politica contabil que exigem julgamento humano.
- Substituir o catalogo unico do escritorio por planos independentes por cliente.

## Observacoes Finais

A decisao de produto mais importante e tratar esta evolucao como fundacao de dados e seguranca antes de tratar como troca de UI ou troca de modelo. O modelo so deve melhorar de forma sustentavel quando contas, uso por empresa, importacoes do razao e semantica de contrapartida estiverem representados explicitamente.

A decisao contabil mais importante e evitar uma regra global como "debito significa banco". Debito e credito devem ser interpretados em relacao a conta do bloco do razao. Isso torna o par debito/credito normalizado confiavel e mantem o primeiro problema de ML focado na predicao de contrapartida para origens financeiras.

A ordem recomendada de implementacao e:

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

Itens em aberto para specs futuras:

- Mecanismo exato de autenticacao de usuarios internos.
- Estrategia operacional de backup do PostgreSQL.
- Regra precisa para identificar contas de banco, caixa e aplicacao financeira a partir do plano de contas.
- Contratos de API para cada endpoint de importacao e revisao.
- Caminho de migracao para dados SQLite existentes que precisem ser preservados.
